"""Command line.

  python -m swisslaw build                         download the acts from Fedlex, build data/corpus.json
  python -m swisslaw search "Probezeit Kündigung"  search one language (detected from --lang, default de)
  python -m swisslaw ask "Can I be fired while sick?"   translate, retrieve, answer with checked citations
  python -m swisslaw evaluate                      retrieval evaluation on evals/questions.json
  python -m swisslaw site                          write the static site to site/
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .corpus import build, load

CORPUS = Path("data/corpus.json")
TRANSLATOR = "groq:openai/gpt-oss-20b"
WRITER = "groq:openai/gpt-oss-120b"
CHECKER = "groq:qwen/qwen3.8-27b"


def _searcher():
    from .search import Searcher
    return Searcher(load(CORPUS))


def _translator(spec: str, cache: Path = Path("cache/translations.json")):
    from .llm import make_model
    from .translate import Translator
    return Translator(make_model(spec), cache)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="swisslaw")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--lang", default="de", choices=["de", "fr", "it", "en"])
    s.add_argument("-k", type=int, default=10)
    a = sub.add_parser("ask")
    a.add_argument("question")
    a.add_argument("--translator", default=TRANSLATOR)
    a.add_argument("--writer", default=WRITER)
    a.add_argument("--checker", default=CHECKER, help="'none' to skip the second model")
    a.add_argument("-k", type=int, default=6, help="articles given to the writer")
    e = sub.add_parser("evaluate")
    e.add_argument("--questions", type=Path, default=Path("evals/questions.json"))
    e.add_argument("--translator", default=TRANSLATOR)
    e.add_argument("--out", type=Path, default=Path("evals/results.json"))
    an = sub.add_parser("answers", help="answer evaluation questions with checked citations, for the site (resumable)")
    an.add_argument("--ids", default="q01,q03,q05,q08,q13,q17,q21,q23,q27,q32,q36,q39")
    an.add_argument("--writer", default=WRITER)
    an.add_argument("--checker", default=CHECKER)
    an.add_argument("--translator", default=TRANSLATOR)
    an.add_argument("-k", type=int, default=6)
    st = sub.add_parser("site")
    st.add_argument("--out", type=Path, default=Path("site"))
    args = ap.parse_args(argv)

    if args.cmd == "build":
        build(CORPUS, Path("cache/xml"))
        return 0

    if args.cmd == "search":
        S = _searcher()
        for rank, doc in enumerate(S.one(args.query, args.lang, args.k), 1):
            e = S.by_id[doc]["lang"].get(args.lang) or {}
            print(f"{rank:>2}. {doc:<16} {e.get('heading', '')}")
        return 0

    if args.cmd == "ask":
        from .answer import answer
        from .llm import QuotaExhausted, family, make_model
        if args.checker != "none" and family(args.checker) == family(args.writer):
            print("The checker must come from a different model family than the writer.", file=sys.stderr)
            return 2
        corpus = load(CORPUS)
        S = _searcher()
        try:
            t = _translator(args.translator)(args.question)
            ids = S.multi({"en": args.question, **{l: t[l] for l in ("de", "fr", "it") if l in t}}, args.k)
            acts = {x["eli"]: x for x in corpus["acts"]}
            res = answer(args.question, [S.by_id[i] for i in ids], acts, make_model(args.writer),
                         None if args.checker == "none" else make_model(args.checker))
        except QuotaExhausted as err:
            print(err, file=sys.stderr)
            return 3
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 0

    if args.cmd == "evaluate":
        from . import evaluate
        from .llm import QuotaExhausted
        qs = json.loads(args.questions.read_text(encoding="utf-8"))["questions"]
        try:
            res = evaluate.run(_searcher(), qs, _translator(args.translator, Path("evals/translations.json")))
        except QuotaExhausted as err:
            print(f"{err}\nTranslations done so far are cached; run again later.", file=sys.stderr)
            return 3
        res["translator"] = args.translator
        args.out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        for m, v in res["summary"].items():
            print(m, v)
        return 0

    if args.cmd == "answers":
        from .answer import answer
        from .llm import QuotaExhausted, family, make_model
        if family(args.checker) == family(args.writer):
            print("The checker must come from a different model family than the writer.", file=sys.stderr)
            return 2
        out = Path("evals/answers.json")
        done = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"items": []}
        have = {x["id"] for x in done["items"]}
        qs = {q["id"]: q for q in json.loads(Path("evals/questions.json").read_text(encoding="utf-8"))["questions"]}
        corpus, S = load(CORPUS), _searcher()
        acts = {x["eli"]: x for x in corpus["acts"]}
        tr = _translator(args.translator, Path("evals/translations.json"))
        writer, checker = make_model(args.writer), make_model(args.checker)
        done["note"] = (f"Written by {writer.name} from the {args.k} articles the four-language search returned, "
                        f"checked by {checker.name}, a model from a different family. A point stays only if its "
                        "quote is found in the cited paragraph; points the second model does not fully accept "
                        "are shown in ochre.")
        try:
            for qid in args.ids.split(","):
                if qid in have:
                    continue
                q = qs[qid]
                t = tr(q["q"])
                ids = S.multi({"en": q["q"], **{l: t[l] for l in ("de", "fr", "it") if l in t}}, args.k)
                res = answer(q["q"], [S.by_id[i] for i in ids], acts, writer, checker)
                res["id"], res["gold"] = qid, q["gold"]
                done["items"].append(res)
                out.write_text(json.dumps(done, ensure_ascii=False, indent=1), encoding="utf-8")
                print(qid, len(res["points"]), "points,", len(res["dropped"]), "dropped")
        except QuotaExhausted as err:
            print(f"{err}\nAnswers so far are saved; run again later.", file=sys.stderr)
            return 3
        return 0

    if args.cmd == "site":
        from .site import write
        write(load(CORPUS), args.out)
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
