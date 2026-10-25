"""Tokenising for four languages: lower case, accents folded, stop words removed,
and a light suffix strip so that "Kündigung" and "Kündigungen", or "résiliation"
and "résiliations", meet. Deliberately simple and the same in Python and in the
site's JavaScript (site/search.js), so both rank identically."""

from __future__ import annotations

import re
import unicodedata

STOP = {
    "en": set("a an and are as at be been by can do does for from has have how i if in is it its may must "
              "my not of on or shall that the their there this to was what when where which who will with "
              "within without would under during any other such than these those they them he she his her".split()),
    "de": set("der die das den dem des ein eine einer eines einem einen und oder ist sind wird werden wurde "
              "kann können muss müssen darf zu zum zur im in an am auf aus bei mit nach von vor für über "
              "unter durch als auch nicht nur wie wenn ob so dass es er sie ihr ihre sein seine sich wer was "
              "welche welcher welches diese dieser dieses jeder jede alle bis während".split()),
    "fr": set("le la les l un une des du de d et ou est sont être a ont peut peuvent doit doivent dans en au "
              "aux sur par pour avec sans sous que qui quoi quel quelle quels quelles ce cette ces il elle ils "
              "elles se son sa ses leur leurs ne pas plus si lorsque comme tout toute tous pendant".split()),
    "it": set("il lo la i gli le l un uno una del della dei degli delle di da dal dalla e o è sono essere ha "
              "hanno può possono deve devono in nel nella nei nelle a al alla ai alle su per con senza che chi "
              "quale quali questo questa questi queste egli ella esso essa suo sua suoi sue non se come ogni durante".split()),
}

SUFFIXES = {
    "en": ["ations", "ation", "ments", "ment", "ings", "ing", "ies", "ied", "ers", "er", "ed", "es", "s"],
    "de": ["ungen", "ung", "heiten", "heit", "keiten", "keit", "ern", "em", "en", "er", "es", "e", "s", "n"],
    "fr": ["ements", "ement", "ations", "ation", "euses", "euse", "eurs", "eur", "ions", "ion", "ees", "ee",
           "es", "e", "s", "x"],
    "it": ["azioni", "azione", "amenti", "amento", "mente", "zioni", "zione", "i", "e", "a", "o"],
}

MIN_STEM = 4
WORD = re.compile(r"[^\W\d_]+|\d+[a-z]*", re.UNICODE)


def fold(s: str) -> str:
    s = s.lower().replace("ß", "ss")
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def stem(word: str, lang: str) -> str:
    for suf in SUFFIXES.get(lang, ()):
        if word.endswith(suf) and len(word) - len(suf) >= MIN_STEM:
            return word[: -len(suf)]
    return word


def tokens(text: str, lang: str) -> list[str]:
    stop = _FOLDED_STOP.get(lang, set())
    out = []
    for w in WORD.findall(fold(text)):
        if w in stop or len(w) < 2:
            continue
        out.append(stem(w, lang))
    return out


_FOLDED_STOP = {l: {fold(w) for w in ws} for l, ws in STOP.items()}


def normalise(s: str) -> str:
    """For comparing a quoted span with the source: case, accents, spacing and
    typographic quotes do not count."""
    s = fold(s).replace("«", '"').replace("»", '"').replace("’", "'").replace("‘", "'")
    s = re.sub(r"[“”„]", '"', s)
    return re.sub(r"\s+", " ", s).strip(" .;:,")
