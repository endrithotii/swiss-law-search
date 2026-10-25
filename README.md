# swiss-law-search

Search Swiss federal law in German, French, Italian or English, and read every article in all four side by side.

Swiss federal law is binding in German, French and Italian only. The English texts are translations without legal force, Fedlex does not translate every act, and where it does, the translation can lag behind. A search that only reads English misses those acts entirely and can quote a superseded text. This project searches the binding texts too, lines the four languages up article by article, and shows the version date of each.

## What it does

- **Corpus.** Seven acts people need at work, read from Fedlex, the Confederation's publication platform, through its public SPARQL endpoint and Akoma Ntoso XML: the Data Protection Act and Ordinance, the Code of Obligations, the Labour Act, the Gender Equality Act, the Unfair Competition Act and the Product Liability Act. 1,795 articles.
- **Alignment.** Fedlex gives an article the same identifier in every language (`art_335_b`), so the columns are matched by identifier, never by position or guesswork. Footnotes are removed; repealed articles are skipped.
- **Search.** BM25 per language with light stemming. A question is rewritten by a model into the legal vocabulary of German, French and Italian; each version is searched in its own language and the rankings are fused (reciprocal rank fusion).
- **Answers.** One model answers from the retrieved articles only. Each point must cite an article, a paragraph and a quote. Code drops any citation whose quote is not in that paragraph; a model from a different family then reads each point next to its cited text and accepts, partly accepts or rejects it.
- **Site.** A static page that searches in the browser with the same tokeniser and ranking as the Python code, and shows each article in four columns with "binding", "translation" and "translation of an older version" marked.

## What the data showed

Building the corpus on 25 October 2026:

| Act | SR | Binding texts in force from | English text |
|---|---|---|---|
| Data Protection Act | 235.1 | 2025-07-07 | same version |
| Data Protection Ordinance | 235.11 | 2025-12-01 | same version |
| Code of Obligations | 220 | 2026-10-01 | **2026-01-01**, older |
| Labour Act | 822.11 | 2023-09-01 | **none** |
| Gender Equality Act | 151.1 | 2020-07-01 | same version |
| Unfair Competition Act | 241 | 2025-01-01 | same version |
| Product Liability Act | 221.112.944 | 2010-07-01 | **none** |

The retrieval evaluation is in `evals/`; its results are added here when the run completes.

## Use it

Python 3.10 or newer, standard library only.

```bash
python -m swisslaw build                                   # download the acts, write data/corpus.json
python -m swisslaw search "Kündigung Krankheit" --lang de  # no model needed
export GROQ_API_KEY=...                                    # free tier is enough
python -m swisslaw ask "Can I be fired while I am off sick?"
python -m swisslaw evaluate                                # retrieval evaluation
python -m swisslaw answers                                 # checked answers for the site
python -m swisslaw site                                    # static site in site/
```

Models are given as `provider:model` (`groq:`, `gemini:`, `openai:`, `anthropic:`, `ollama:`). The writer and the checker must come from different model families; the command refuses otherwise. Translations and answers are cached, and a run that reaches a provider's daily limit stops cleanly and resumes where it stopped.

## Tests

```bash
python -m unittest discover -s tests
```

Parsing (footnotes, lists, repealed articles), tokenising, search, rank fusion, the McNemar test, and citation grounding.

## Limits

- Not legal advice. Statutes are only part of the law: ordinances, collective labour agreements, cantonal law and case law are not here.
- 40 questions detect large differences, not small ones. The gold articles were chosen by hand; a lawyer might add others.
- BM25 with suffix stripping does not split German compounds, so "Kündigungsfrist" does not match "Frist".
- The answers are checked for grounding, not for completeness: a point can be correct and still leave out an exception in another article.
