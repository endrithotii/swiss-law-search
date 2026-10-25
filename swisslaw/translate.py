"""Turn one question into the three official languages of federal law.

The model is asked for the words the statute itself would use, not a literal
translation: "trial period" should become "Probezeit" / "temps d'essai" /
"periodo di prova", because that is what the Code of Obligations says.
Translations are cached on disk, so evaluations are repeatable and free to rerun.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

SYSTEM = """You translate a question about Swiss federal law into German, French and Italian.
Use the legal terms Swiss federal statutes use in each language, not loose everyday words,
and keep the question short. Do not answer the question.
Reply with JSON only: {"de": "...", "fr": "...", "it": "...", "en": "..."}
where "en" is the question in plain English (unchanged if it is already English)."""


class Translator:
    def __init__(self, model, cache_path: Path):
        self.model = model
        self.path = cache_path
        self.cache: dict = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}

    def key(self, question: str) -> str:
        h = hashlib.sha256((self.model.name + "\n" + SYSTEM + "\n" + question).encode()).hexdigest()[:16]
        return f"{self.model.name}:{h}"

    def __call__(self, question: str) -> dict[str, str]:
        k = self.key(question)
        if k not in self.cache:
            out = self.model.complete_json(SYSTEM, question)
            self.cache[k] = {"q": question, **{l: str(out.get(l) or "").strip() for l in ("de", "fr", "it", "en")}}
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.cache, ensure_ascii=False, indent=1), encoding="utf-8")
        t = self.cache[k]
        return {l: t[l] for l in ("de", "fr", "it", "en") if t.get(l)}
