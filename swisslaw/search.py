"""BM25 per language, and reciprocal rank fusion across languages.

An article is indexed once per language it exists in. A question asked in
English is translated into German, French and Italian (see translate.py); each
version is run against its own language's index, and the rankings are fused.
That way an act Fedlex never translated into English can still be found from an
English question, and a German legal term the English translation renders
loosely still matches.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict

from .text import tokens

K1, B = 1.2, 0.75
RRF_K = 60


def document(entry: dict) -> str:
    # The heading says what the article is about in a few words, so it counts twice.
    return " ".join([entry["heading"], entry["heading"], " ".join(entry["path"][-2:]), entry["text"]])


class Index:
    def __init__(self, articles: list[dict], lang: str):
        self.lang = lang
        self.ids: list[str] = []
        self.tf: list[Counter] = []
        df: Counter = Counter()
        for a in articles:
            entry = a["lang"].get(lang)
            if not entry:
                continue
            t = Counter(tokens(document(entry), lang))
            self.ids.append(a["id"])
            self.tf.append(t)
            df.update(t.keys())
        self.n = len(self.ids)
        self.dl = [sum(t.values()) for t in self.tf]
        self.avgdl = sum(self.dl) / self.n if self.n else 0.0
        self.idf = {w: math.log(1 + (self.n - d + 0.5) / (d + 0.5)) for w, d in df.items()}
        self.postings: dict[str, list[int]] = defaultdict(list)
        for i, t in enumerate(self.tf):
            for w in t:
                self.postings[w].append(i)

    def search(self, query: str, k: int = 10) -> list[tuple[str, float]]:
        q = tokens(query, self.lang)
        scores: dict[int, float] = defaultdict(float)
        for w in set(q):
            idf = self.idf.get(w)
            if idf is None:
                continue
            for i in self.postings[w]:
                f = self.tf[i][w]
                scores[i] += idf * f * (K1 + 1) / (f + K1 * (1 - B + B * self.dl[i] / self.avgdl))
        best = sorted(scores.items(), key=lambda x: (-x[1], self.ids[x[0]]))[:k]
        return [(self.ids[i], s) for i, s in best]


def fuse(rankings: list[list[str]], k: int = 10) -> list[str]:
    """Reciprocal rank fusion: an article ranked high in several languages wins."""
    score: dict[str, float] = defaultdict(float)
    for ranking in rankings:
        for rank, doc in enumerate(ranking):
            score[doc] += 1 / (RRF_K + rank + 1)
    return [d for d, _ in sorted(score.items(), key=lambda x: (-x[1], x[0]))[:k]]


class Searcher:
    def __init__(self, corpus: dict, langs=("de", "fr", "it", "en")):
        self.by_id = {a["id"]: a for a in corpus["articles"]}
        self.index = {l: Index(corpus["articles"], l) for l in langs}

    def one(self, query: str, lang: str, k: int = 10) -> list[str]:
        return [d for d, _ in self.index[lang].search(query, k)]

    def multi(self, queries: dict[str, str], k: int = 10, depth: int = 30) -> list[str]:
        """queries: {"de": ..., "fr": ..., "it": ..., "en": ...}; any subset."""
        return fuse([self.one(q, l, depth) for l, q in queries.items() if l in self.index and q], k)
