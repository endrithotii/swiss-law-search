"""Answer a question from the retrieved articles only, with citations that code
and a second model both check.

1. Retrieve: the fused multilingual search returns the candidate articles.
2. Write: one model answers in short points. Every point must cite an article,
   a paragraph and a quote copied from that paragraph.
3. Ground: code drops any citation whose article was not retrieved, whose
   paragraph does not exist, or whose quote is not in that paragraph. A point
   left with no valid citation is dropped, and the reader is told.
4. Check: a model from a different family reads each remaining point next to
   the paragraphs it cites and says whether they support it. Points it rejects
   are shown as disputed, not silently kept.

The model never sees anything but the retrieved text, and the authoritative
German, French or Italian wording is always shown next to the English one.
"""

from __future__ import annotations

import re

from .text import normalise

WRITER = """You answer questions about Swiss federal law using ONLY the articles provided.
Rules:
- Answer in short points, in English. Each point states one rule from the articles.
- Every point cites at least one article and paragraph, with a quote copied exactly from that paragraph
  (a short span, 5 to 30 words, in the language of the text you quote).
- If the articles do not answer the question, say so: set "answerable" to false and give no points.
- Do not add rules, numbers or exceptions that are not in the quoted text. Do not give advice.
Reply with JSON only:
{"answerable": true, "points": [{"text": "...", "cites": [{"article": "<id>", "para": "<paragraph number or empty>", "quote": "..."}]}]}"""

CHECKER = """You check whether a statement about Swiss law is supported by the quoted statutory text.
Read the statement and the paragraphs it cites. Answer "supported" only if the paragraphs
state it; "partly" if they state part of it or the statement adds a condition, number or
exception that is not there; "not_supported" otherwise.
Reply with JSON only: {"verdict": "supported" | "partly" | "not_supported", "reason": "one sentence"}"""

PARA = re.compile(r"^(\d+[a-z]*)\s+(.*)$", re.S)


def paragraphs(entry: dict) -> dict[str, str]:
    """{"1": "...", "5bis": "...", "": "..."} from an article's text."""
    out: dict[str, str] = {}
    for line in entry["text"].split("\n"):
        m = PARA.match(line)
        if m:
            out[m.group(1)] = m.group(2)
        else:
            out[""] = (out.get("", "") + " " + line).strip()
    return out


def label(article: dict, acts: dict) -> str:
    act = acts[article["act"]]
    e = article["lang"].get("en") or article["lang"][act["authoritative"]]
    return f"{e['num']} {act['short']['en']}"


def context(articles: list[dict], acts: dict) -> str:
    blocks = []
    for a in articles:
        act = acts[a["act"]]
        parts = [f"[{a['id']}] {label(a, acts)} (SR {act['sr']})"]
        auth = act["authoritative"]
        for lang in (auth, "en"):
            e = a["lang"].get(lang)
            if not e or (lang == "en" and auth == "en"):
                continue
            tag = "authoritative" if lang == auth else "English translation, not legally binding"
            parts.append(f"--- {lang} ({tag}): {e['heading']}\n{e['text']}")
        blocks.append("\n".join(parts))
    return "\n\n".join(blocks)


def ground(points: list[dict], articles: list[dict]) -> tuple[list[dict], list[dict]]:
    """Keep only citations that exist and whose quote is in the cited paragraph."""
    by_id = {a["id"]: a for a in articles}
    kept, dropped = [], []
    for p in points:
        good, bad = [], []
        for c in p.get("cites") or []:
            a = by_id.get(str(c.get("article", "")).strip())
            reason = None
            if a is None:
                reason = "article was not among the retrieved ones"
            else:
                para = str(c.get("para") or "").strip()
                quote = normalise(str(c.get("quote") or ""))
                found_lang = None
                for lang, e in a["lang"].items():
                    paras = paragraphs(e)
                    texts = [paras[para]] if para in paras else ([] if para else list(paras.values()))
                    if quote and any(quote in normalise(t) for t in texts):
                        found_lang = lang
                        break
                if len(quote) < 12:
                    reason = "quote missing or too short to check"
                elif not found_lang:
                    reason = "quote not found in the cited paragraph"
                else:
                    c = {**c, "lang": found_lang}
            (bad if reason else good).append({**c, "problem": reason} if reason else c)
        if good:
            kept.append({**p, "cites": good, "rejected_cites": bad})
        else:
            dropped.append({**p, "rejected_cites": bad})
    return kept, dropped


def cited_text(point: dict, articles: list[dict], acts: dict) -> str:
    by_id = {a["id"]: a for a in articles}
    out = []
    for c in point["cites"]:
        a = by_id[c["article"]]
        e = a["lang"][c["lang"]]
        paras = paragraphs(e)
        para = str(c.get("para") or "")
        out.append(f"{label(a, acts)} para {para or '-'} ({c['lang']}): {paras.get(para) or e['text']}")
    return "\n".join(out)


def answer(question: str, articles: list[dict], acts: dict, writer, checker=None) -> dict:
    draft = writer.complete_json(WRITER, f"Question: {question}\n\nArticles:\n{context(articles, acts)}")
    points = draft.get("points") or []
    if not isinstance(points, list):
        points = []
    kept, dropped = ground([p for p in points if isinstance(p, dict)], articles)
    for p in kept:
        p["check"] = None
        if checker is not None:
            v = checker.complete_json(CHECKER, f"Statement: {p.get('text', '')}\n\nCited text:\n{cited_text(p, articles, acts)}")
            verdict = str(v.get("verdict", "")).strip().lower().replace(" ", "_")
            p["check"] = {"verdict": verdict if verdict in ("supported", "partly", "not_supported") else "unclear",
                          "reason": str(v.get("reason", ""))[:400]}
    return {"question": question, "answerable": bool(draft.get("answerable", bool(points))),
            "points": kept, "dropped": dropped, "articles": [a["id"] for a in articles],
            "writer": writer.name, "checker": checker.name if checker else None}
