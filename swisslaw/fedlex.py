"""Swiss federal law from Fedlex, the Confederation's official publication platform.

Fedlex publishes every consolidated act as Akoma Ntoso XML, one file per
language, and describes them in a public SPARQL endpoint. Articles carry the
same eId (`art_24`, `art_335_b`) in every language, which is what lets this
project line the German, French, Italian and English texts up article by
article without guessing.

Only German, French and Italian are official languages of federal law. The
English texts are translations without legal force, and Fedlex does not
translate every act or every version: the latest English text can be older
than the latest authoritative one, or missing. Each language here keeps its
own version date so that a mismatch is visible, never hidden.
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

ENDPOINT = "https://fedlex.data.admin.ch/sparqlendpoint"
ELI = "https://fedlex.data.admin.ch/eli/"
USER_AGENT = "swiss-law-search/0.1 (+https://github.com/endrithotii/swiss-law-search)"
AKN = "{http://docs.oasis-open.org/legaldocml/ns/akn/3.0}"
LANGS = {"DEU": "de", "FRA": "fr", "ITA": "it", "ENG": "en"}
OFFICIAL = ("de", "fr", "it")


def sparql(query: str, timeout: int = 120) -> list[dict]:
    data = urllib.parse.urlencode({"query": query}).encode()
    req = urllib.request.Request(ENDPOINT, data=data, headers={
        "accept": "application/sparql-results+json", "user-agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        rows = json.load(resp)["results"]["bindings"]
    return [{k: v["value"] for k, v in r.items()} for r in rows]


def latest_files(eli: str, on: date | None = None) -> dict[str, dict]:
    """For each language, the XML of the newest consolidation in force on `on`.

    Returns {"de": {"date": "2025-07-07", "url": ..., "title": ...}, ...}.
    Languages are chosen independently, so English may point to an older version.
    """
    on = on or date.today()
    rows = sparql(f"""PREFIX jolux: <http://data.legilux.public.lu/resource/ontology/jolux#>
SELECT ?date ?lang ?file ?title WHERE {{
  ?cons jolux:isMemberOf <{ELI}{eli}> ; jolux:dateApplicability ?date ; jolux:isRealizedBy ?expr .
  ?expr jolux:language ?lang ; jolux:isEmbodiedBy ?m .
  ?m jolux:isExemplifiedBy ?file ; jolux:format ?fmt .
  FILTER(CONTAINS(LCASE(STR(?fmt)), "xml"))
  FILTER(?date <= "{on.isoformat()}"^^<http://www.w3.org/2001/XMLSchema#date>)
  OPTIONAL {{ <{ELI}{eli}> jolux:isRealizedBy ?work . ?work jolux:language ?lang ; jolux:title ?title }}
}} ORDER BY DESC(?date)""")
    out: dict[str, dict] = {}
    for r in rows:
        lang = LANGS.get(r["lang"].rsplit("/", 1)[-1])
        if lang and lang not in out:
            out[lang] = {"date": r["date"], "url": r["file"], "title": r.get("title", "")}
    return out


def download(url: str, cache_dir: Path) -> bytes:
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / url.rsplit("/", 1)[-1]
    if path.exists():
        return path.read_bytes()
    req = urllib.request.Request(url, headers={"user-agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=180) as resp:
        body = resp.read()
    path.write_bytes(body)
    return body


@dataclass
class Article:
    eid: str            # "art_24", aligned across languages
    num: str            # "Art. 24"
    heading: str        # "Notification of data security breaches"
    paragraphs: list[tuple[str, str]] = field(default_factory=list)  # [("1", "text"), ...]
    path: list[str] = field(default_factory=list)  # chapter and section headings above it

    @property
    def text(self) -> str:
        return "\n".join(f"{n} {t}".strip() for n, t in self.paragraphs)

    @property
    def repealed(self) -> bool:
        t = self.text.strip().lower().rstrip(".")
        return t in {"", "aufgehoben", "abrogé", "abrogato", "repealed"} or bool(
            re.fullmatch(r"(\d+\s*)?(aufgehoben|abrogé|abrogato|repealed)\b.*", t) and len(t) < 80)


def _text(el: ET.Element) -> str:
    """Visible text of an element, without footnotes."""
    parts: list[str] = []

    def walk(e: ET.Element) -> None:
        if e.tag == AKN + "authorialNote":
            if e.tail:
                parts.append(e.tail)
            return
        if e.text:
            parts.append(e.text)
        for c in e:
            walk(c)
        if e.tail and e is not el:
            parts.append(e.tail)

    walk(el)
    return re.sub(r"\s+", " ", "".join(parts)).strip()


def _paragraph(p: ET.Element) -> tuple[str, str]:
    num_el = p.find(AKN + "num")
    num = _text(num_el) if num_el is not None else ""
    content = p.find(AKN + "content")
    if content is None:
        content = p
    lines: list[str] = []
    for el in content.iter():
        if el.tag == AKN + "listIntroduction":
            lines.append(_text(el))
        elif el.tag == AKN + "item":
            n = el.find(AKN + "num")
            body = " ".join(_text(c) for c in el if c.tag in (AKN + "p", AKN + "content"))
            lines.append(f"{_text(n) if n is not None else ''} {body}".strip())
        elif el.tag == AKN + "p" and not _inside_item(el, content):
            lines.append(_text(el))
    return num, " ".join(x for x in lines if x)


def _inside_item(el: ET.Element, root: ET.Element) -> bool:
    for item in root.iter(AKN + "item"):
        if any(c is el for c in item.iter()):
            return True
    return False


def _strip_notes(root: ET.Element) -> None:
    """Remove footnotes (authorialNote) everywhere, keeping the text around them."""
    for p in list(root.iter()):
        kept: list[ET.Element] = []
        for c in list(p):
            if c.tag != AKN + "authorialNote":
                kept.append(c)
                continue
            tail = c.tail or ""
            if kept:
                kept[-1].tail = (kept[-1].tail or "") + tail
            else:
                p.text = (p.text or "") + tail
            p.remove(c)


def parse(xml: bytes) -> list[Article]:
    root = ET.fromstring(xml)
    _strip_notes(root)
    parent = {c: p for p in root.iter() for c in p}
    articles: list[Article] = []
    for a in root.iter(AKN + "article"):
        eid = a.get("eId", "")
        if not eid.startswith("art_"):
            continue
        num_el, head_el = a.find(AKN + "num"), a.find(AKN + "heading")
        art = Article(eid=eid, num=_text(num_el) if num_el is not None else "",
                      heading=_text(head_el) if head_el is not None else "")
        paras = a.findall(AKN + "paragraph")
        if paras:
            art.paragraphs = [_paragraph(p) for p in paras]
        else:
            body = [c for c in a if c.tag not in (AKN + "num", AKN + "heading")]
            art.paragraphs = [("", " ".join(_text(c) for c in body).strip())]
        # Chapter / section / title headings above the article, outermost first.
        node, path = parent.get(a), []
        while node is not None:
            if node.tag in (AKN + "chapter", AKN + "section", AKN + "title", AKN + "part",
                            AKN + "subsection", AKN + "level", AKN + "book"):
                h, n = node.find(AKN + "heading"), node.find(AKN + "num")
                label = " ".join(x for x in (_text(n) if n is not None else "",
                                             _text(h) if h is not None else "") if x)
                if label:
                    path.append(label)
            node = parent.get(node)
        art.path = path[::-1]
        articles.append(art)
    return articles
