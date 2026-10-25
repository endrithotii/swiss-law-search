"""Build the aligned corpus: one record per article, with its text in every
language Fedlex publishes for that act."""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from .fedlex import OFFICIAL, download, latest_files, parse

# The acts a person in Switzerland most often needs at work: data protection,
# employment, equal pay, competition and liability. SR numbers are the
# Systematic Compilation numbers lawyers cite.
ACTS = [
    {"eli": "cc/2022/491", "sr": "235.1", "short": {"de": "DSG", "fr": "LPD", "it": "LPD", "en": "FADP"}},
    {"eli": "cc/2022/568", "sr": "235.11", "short": {"de": "DSV", "fr": "OPDo", "it": "OPDa", "en": "DPO"}},
    {"eli": "cc/27/317_321_377", "sr": "220", "short": {"de": "OR", "fr": "CO", "it": "CO", "en": "CO"}},
    {"eli": "cc/1966/57_57_57", "sr": "822.11", "short": {"de": "ArG", "fr": "LTr", "it": "LL", "en": "EmpA"}},
    {"eli": "cc/1996/1498_1498_1498", "sr": "151.1", "short": {"de": "GlG", "fr": "LEg", "it": "LPar", "en": "GEA"}},
    {"eli": "cc/1988/223_223_223", "sr": "241", "short": {"de": "UWG", "fr": "LCD", "it": "LCSl", "en": "UCA"}},
    {"eli": "cc/1993/3122_3122_3122", "sr": "221.112.944", "short": {"de": "PrHG", "fr": "LRFP", "it": "LRDP", "en": "PLA"}},
]


def build(out: Path, cache_dir: Path, on: date | None = None, log=print) -> dict:
    acts, articles = [], []
    for act in ACTS:
        files = latest_files(act["eli"], on)
        versions = {l: f["date"] for l, f in files.items()}
        log(f"{act['sr']:>12}  {act['short']['de']:<5} " + "  ".join(f"{l} {d}" for l, d in versions.items()))
        parsed = {l: {a.eid: a for a in parse(download(f["url"], cache_dir))} for l, f in files.items()}
        # The German text decides which articles exist and in what order: it is
        # authoritative and, with French and Italian, always the newest version.
        authoritative = max((l for l in OFFICIAL if l in parsed), key=lambda l: (versions[l], l == "de"))
        acts.append({**act, "title": {l: f["title"] for l, f in files.items()}, "version": versions,
                     "source": {l: f["url"] for l, f in files.items()}, "authoritative": authoritative})
        for eid, base in parsed[authoritative].items():
            if base.repealed:
                continue
            texts = {}
            for l, arts in parsed.items():
                a = arts.get(eid)
                if a is None or a.repealed:
                    continue
                heading, path = a.heading, a.path
                if not heading and path:
                    # The Code of Obligations puts an article's subject in the last
                    # heading above it ("b. During the probation period").
                    heading, path = re.sub(r"^(?:[a-z]{1,3}|[IVXLC]+|[A-Z]|\d+)\.\s+", "", path[-1]), path[:-1]
                texts[l] = {"num": a.num, "heading": heading, "text": a.text, "path": path}
            articles.append({"id": f"{act['short']['en']} {eid}", "act": act["eli"], "eid": eid, "lang": texts})
    corpus = {"built": date.today().isoformat(), "acts": acts, "articles": articles}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(corpus, ensure_ascii=False), encoding="utf-8")
    log(f"{len(articles)} articles -> {out}")
    return corpus


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
