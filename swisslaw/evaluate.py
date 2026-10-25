"""Retrieval evaluation: does the right article come back, and how high?

For every question the gold articles were checked by hand against the statute.
A question counts as found at k when any gold article is in the top k.
"""

from __future__ import annotations

from math import comb

MODES = {
    "en": "English translation only",
    "de": "German text, question translated",
    "official": "German + French + Italian, fused",
    "all": "All four languages, fused",
}


def rankings(searcher, question: str, t: dict[str, str], k: int = 10) -> dict[str, list[str]]:
    return {
        "en": searcher.one(question, "en", k),
        "de": searcher.one(t.get("de", ""), "de", k),
        "official": searcher.multi({l: t[l] for l in ("de", "fr", "it") if l in t}, k),
        "all": searcher.multi({"en": question, **{l: t[l] for l in ("de", "fr", "it") if l in t}}, k),
    }


def first_hit(ranking: list[str], gold: list[str]) -> int | None:
    for i, d in enumerate(ranking):
        if d in gold:
            return i + 1
    return None


def mcnemar_exact(a: list[bool], b: list[bool]) -> tuple[int, int, float]:
    only_a = sum(x and not y for x, y in zip(a, b))
    only_b = sum(y and not x for x, y in zip(a, b))
    n = only_a + only_b
    if n == 0:
        return 0, 0, 1.0
    tail = sum(comb(n, i) for i in range(min(only_a, only_b) + 1)) / 2 ** n
    return only_a, only_b, min(1.0, 2 * tail)


def run(searcher, questions: list[dict], translate, k: int = 10) -> dict:
    rows = []
    for q in questions:
        t = translate(q["q"])
        r = rankings(searcher, q["q"], t, k)
        rows.append({"id": q["id"], "q": q["q"], "gold": q["gold"], "translation": t,
                     "rank": {m: first_hit(r[m], q["gold"]) for m in MODES},
                     "top": {m: r[m][:5] for m in MODES}})
    return {"rows": rows, "summary": summarise(rows, searcher)}


def summarise(rows: list[dict], searcher) -> dict:
    n = len(rows)
    out = {}
    for m in MODES:
        ranks = [r["rank"][m] for r in rows]
        out[m] = {
            "label": MODES[m],
            "hit@1": sum(1 for x in ranks if x and x <= 1) / n,
            "hit@5": sum(1 for x in ranks if x and x <= 5) / n,
            "hit@10": sum(1 for x in ranks if x and x <= 10) / n,
            "mrr": sum(1 / x for x in ranks if x) / n,
        }
    # Questions whose answer exists only in acts Fedlex publishes no English text for.
    no_en = [r for r in rows if not any(searcher.by_id[g]["lang"].get("en") for g in r["gold"])]
    out["no_english"] = {"questions": len(no_en),
                         "found_en@5": sum(1 for r in no_en if r["rank"]["en"] and r["rank"]["en"] <= 5),
                         "found_all@5": sum(1 for r in no_en if r["rank"]["all"] and r["rank"]["all"] <= 5)}
    a = [bool(r["rank"]["en"] and r["rank"]["en"] <= 5) for r in rows]
    b = [bool(r["rank"]["all"] and r["rank"]["all"] <= 5) for r in rows]
    only_en, only_all, p = mcnemar_exact(a, b)
    out["all_vs_en@5"] = {"only_en": only_en, "only_all": only_all, "p": p}
    return out
