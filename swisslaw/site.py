"""The static site: search Swiss federal law in any official language and read
each article side by side in German, French, Italian and English.

Everything runs in the browser. The page tokenises and ranks exactly like
search.py (the stop words and suffixes are written into the page from text.py),
so a query gives the same ranking on the site as on the command line.
"""

from __future__ import annotations

import json
from pathlib import Path

from .text import MIN_STEM, STOP, SUFFIXES


def _payload(corpus: dict) -> dict:
    acts = [{"eli": a["eli"], "sr": a["sr"], "short": a["short"], "title": a["title"],
             "version": a["version"], "source": a["source"], "authoritative": a["authoritative"]}
            for a in corpus["acts"]]
    arts = []
    for a in corpus["articles"]:
        arts.append({"id": a["id"], "act": a["act"],
                     "l": {l: [e["num"], e["heading"], e["path"][-2:], e["text"]] for l, e in a["lang"].items()}})
    return {"built": corpus["built"], "acts": acts, "articles": arts}


def write(corpus: dict, out: Path, results: Path = Path("evals/results.json"),
          answers: Path = Path("evals/answers.json")) -> None:
    (out / "data").mkdir(parents=True, exist_ok=True)
    (out / "data" / "corpus.json").write_text(json.dumps(_payload(corpus), ensure_ascii=False, separators=(",", ":")),
                                               encoding="utf-8")
    extra = {}
    if results.exists():
        r = json.loads(results.read_text(encoding="utf-8"))
        extra["eval"] = {"summary": r["summary"], "translator": r.get("translator"),
                         "rows": [{k: x[k] for k in ("id", "q", "gold", "rank", "translation")} for x in r["rows"]]}
    if answers.exists():
        extra["answers"] = json.loads(answers.read_text(encoding="utf-8"))
    (out / "data" / "results.json").write_text(json.dumps(extra, ensure_ascii=False), encoding="utf-8")
    text = {"stop": {l: sorted(v) for l, v in STOP.items()}, "suffixes": SUFFIXES, "minStem": MIN_STEM}
    (out / "index.html").write_text(PAGE.replace("/*TEXT*/", json.dumps(text, ensure_ascii=False)), encoding="utf-8")
    print(out / "index.html")


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Swiss law search</title>
<meta name="description" content="Search Swiss federal law in German, French, Italian or English and read every article side by side in all four.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Schibsted+Grotesk:wght@400;500;700;800&family=Literata:opsz,wght@7..72,400;7..72,600&display=swap">
<style>
/* White paper for long reading, black type, and Swiss red only where the eye
   should land first. Each language has its own colour so a reader always knows
   which text they are in; English is grey on purpose, because it is the one
   text without legal force. */
:root {
  --paper: #FFFFFF; --ink: #000000; --soft: #5C5C5C; --hair: #E4E2DE; --wash: #F4F3F0;
  --red: #DA291C; --red-dark: #A51E14;
  --de: #1E4FA8; --fr: #0B7A55; --it: #B4500A; --en: #6E6E6E; --older: #8F5B00;
  --sans: "Schibsted Grotesk", "Helvetica Neue", Arial, sans-serif;
  --serif: "Literata", Georgia, serif;
}
* { box-sizing: border-box; }
html { background: var(--paper); color: var(--ink); }
body { margin: 0; font: 400 17px/1.5 var(--sans); }
a { color: var(--ink); text-decoration-color: var(--red); text-decoration-thickness: 2px; text-underline-offset: 3px; }
:focus-visible { outline: 3px solid var(--red); outline-offset: 2px; }
.wrap { max-width: 84rem; margin-inline: auto; padding-inline: 1.25rem; }

.hero { background: var(--red); color: #fff; }
.hero .wrap { display: grid; grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr); gap: 2rem; align-items: end; padding-block: 2.6rem 2.2rem; }
.hero h1 { font: 800 clamp(2.1rem, 5vw, 3.8rem)/1 var(--sans); letter-spacing: -0.03em; margin: 0; }
.hero p { margin: 0; font-size: 1.02rem; line-height: 1.55; max-width: 44ch; }
.hero .langline { display: flex; gap: 0.35rem; margin-top: 1rem; }
.hero .langline span { font-weight: 700; font-size: 0.85rem; background: #fff; padding: 0.15rem 0.5rem; }
.langline .de { color: var(--de); } .langline .fr { color: var(--fr); } .langline .it { color: var(--it); } .langline .en { color: var(--en); }

.searchzone { padding-block: 1.6rem 1.2rem; }
form.search { display: grid; grid-template-columns: minmax(0, 1fr) auto; border: 3px solid var(--ink); max-width: 60rem; }
form.search input { font: 400 1.3rem/1.3 var(--serif); border: 0; padding: 0.9rem 1rem; background: transparent; color: var(--ink); min-width: 0; }
form.search input:focus { outline: none; }
form.search:focus-within { border-color: var(--red); }
.langs { display: flex; }
.langs button { font: 700 0.95rem var(--sans); border: 0; border-left: 3px solid var(--ink); background: var(--paper); color: var(--ink); padding: 0 1rem; cursor: pointer; }
.langs button[data-l="de"] { --c: var(--de); } .langs button[data-l="fr"] { --c: var(--fr); }
.langs button[data-l="it"] { --c: var(--it); } .langs button[data-l="en"] { --c: var(--en); }
.langs button { color: var(--c); }
.langs button[aria-pressed="true"] { background: var(--c); color: #fff; }
.under { display: flex; flex-wrap: wrap; gap: 0.4rem 1.1rem; align-items: baseline; margin-top: 0.9rem; color: var(--soft); }
.under button.eg { font: 400 1rem var(--serif); color: var(--ink); background: none; border: 0; padding: 0; cursor: pointer; text-decoration: underline; text-decoration-color: var(--red); text-decoration-thickness: 2px; text-underline-offset: 4px; }
.acts { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 1rem; }
.acts label { font-size: 0.9rem; background: var(--wash); padding: 0.3rem 0.65rem; cursor: pointer; user-select: none; }
.acts label:has(input:checked) { background: var(--ink); color: #fff; }
.acts label:has(input:checked) span { color: #BDBDBD !important; }
.acts input { position: absolute; opacity: 0; pointer-events: none; }

.work { display: grid; grid-template-columns: minmax(15rem, 21rem) minmax(0, 1fr); gap: 2rem; align-items: start; padding-bottom: 3.5rem; }
.results { list-style: none; margin: 0; padding: 0; }
.results li button { display: block; width: 100%; text-align: left; background: none; border: 0; border-left: 6px solid transparent; padding: 0.7rem 0.8rem; cursor: pointer; color: var(--ink); font: inherit; }
.results li button:hover { background: var(--wash); }
.results li button[aria-current="true"] { background: var(--wash); border-left-color: var(--red); }
.results .ref { font-weight: 800; font-size: 1.02rem; }
.results .ref small { font-weight: 500; color: var(--soft); margin-left: 0.4rem; }
.results .what { display: block; font: 400 1rem/1.35 var(--serif); margin-top: 0.15rem; }
.empty { color: var(--soft); padding: 1rem 0.8rem; }

.reader { min-height: 20rem; }
.reader header { padding: 0 0 1rem; }
.reader h2 { font: 800 clamp(1.8rem, 3.4vw, 2.6rem)/1 var(--sans); letter-spacing: -0.02em; margin: 0; }
.reader .act { color: var(--soft); margin: 0.5rem 0 0; max-width: 70ch; }
.tabs { display: none; gap: 0; }
.tabs button { font: 700 0.95rem var(--sans); border: 0; background: var(--wash); padding: 0.55rem 1rem; cursor: pointer; }
.parallel { display: grid; grid-template-columns: repeat(var(--cols, 4), minmax(0, 1fr)); gap: 1.4rem; }
.col { border-top: 8px solid var(--c, var(--ink)); padding-top: 0.8rem; min-width: 0; }
.col[data-l="de"] { --c: var(--de); } .col[data-l="fr"] { --c: var(--fr); } .col[data-l="it"] { --c: var(--it); } .col[data-l="en"] { --c: var(--en); }
.col .lang { display: flex; flex-direction: column; gap: 0.05rem; font-size: 0.85rem; color: var(--soft); margin-bottom: 0.6rem; }
.col .lang b { color: var(--c); font-weight: 800; font-size: 1rem; }
.badge { display: inline-block; font-size: 0.82rem; font-weight: 700; padding: 0.1rem 0.5rem; color: #fff; background: var(--c); }
.badge.translation { background: var(--wash); color: var(--en); }
.badge.older { background: #FFF1CC; color: var(--older); }
.col h3 { font: 600 1.08rem/1.3 var(--serif); margin: 0 0 0.5rem; }
.col .trail { font-size: 0.82rem; color: var(--soft); margin: 0 0 0.7rem; }
.col p { font: 400 1rem/1.65 var(--serif); margin: 0 0 0.7rem; hyphens: auto; }
.col[data-l="en"] p { color: #3A3A3A; }
.col p .n { font: 800 0.8rem var(--sans); color: var(--c); vertical-align: 0.35em; margin-right: 0.25rem; }
.col.missing { color: var(--soft); font-size: 0.95rem; }
.col mark { background: #FFE58A; color: inherit; padding: 0 1px; }
.reader footer { margin-top: 1.4rem; padding-top: 1rem; border-top: 3px solid var(--ink); font-size: 0.9rem; color: var(--soft); }

.eval { background: #EAF0F7; color: var(--ink); padding-block: 3rem 3.4rem; border-top: 8px solid var(--red); }
.eval a { color: var(--ink); }
.eval h2 { font: 800 clamp(1.7rem, 3.4vw, 2.5rem)/1.05 var(--sans); letter-spacing: -0.02em; margin: 0 0 0.8rem; max-width: 22ch; }
.eval .lede { max-width: 70ch; color: #3C4450; margin: 0 0 1.8rem; }
.modes { display: grid; gap: 0.9rem; max-width: 60rem; }
.mode { display: grid; grid-template-columns: 17rem 1fr 4.5rem; gap: 1rem; align-items: center; }
.mode .bar { height: 1.6rem; background: #D3DBE6; position: relative; overflow: hidden; }
.mode .bar span { position: absolute; inset: 0 auto 0 0; background: #8E99A8; }
.mode:last-child .bar span { background: var(--red); }
.mode .bar span.k1 { background: #4A5361; }
.mode:last-child .bar span.k1 { background: var(--red-dark); }
.mode .v { font-weight: 800; font-size: 1.5rem; text-align: right; font-variant-numeric: tabular-nums; }
.key { font-size: 0.9rem; color: #3C4450; margin-top: 0.9rem; display: flex; gap: 1.4rem; flex-wrap: wrap; }
.key i { display: inline-block; width: 14px; height: 14px; vertical-align: -2px; margin-right: 0.4rem; }
.facts { display: grid; grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr)); gap: 1.6rem; margin-top: 2.4rem; max-width: 70rem; }
.facts p { margin: 0; color: #3C4450; border-top: 6px solid var(--red); padding-top: 0.8rem; }
.facts b { display: block; font: 800 1.9rem/1.1 var(--sans); color: var(--ink); margin-bottom: 0.3rem; }
details.qs { margin-top: 2.4rem; max-width: 70rem; }
details.qs summary { cursor: pointer; font-weight: 700; }
table { border-collapse: collapse; width: 100%; font-size: 0.92rem; margin-top: 0.9rem; }
th, td { text-align: left; padding: 0.5rem 0.6rem; border-bottom: 1px solid #CAD3DF; vertical-align: top; }
th { color: #4A5361; font-weight: 500; }
td.r { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
td.miss { color: var(--red-dark); }
.answers { margin-top: 2.4rem; max-width: 62rem; }
.answer { border-left: 6px solid var(--red); padding: 0.2rem 0 0.2rem 1rem; margin: 1.2rem 0; }
.answer h3 { font: 400 1.1rem/1.35 var(--serif); font-style: italic; margin: 0 0 0.5rem; }
.answer .cite { font-size: 0.88rem; color: #4A5361; }
.answer .disputed { color: var(--older); }
.page-foot { padding-block: 1.8rem 2.6rem; color: var(--soft); font-size: 0.88rem; }
.page-foot p { max-width: 80ch; margin: 0.3rem 0; }

@media (max-width: 1000px) {
  .hero .wrap { grid-template-columns: 1fr; }
  .work { grid-template-columns: 1fr; }
  .results { max-height: 21rem; overflow-y: auto; border-bottom: 3px solid var(--ink); }
  .tabs { display: flex; margin-bottom: 1rem; }
  .parallel { grid-template-columns: 1fr; }
  .col { display: none; }
  .col.on { display: block; }
  .mode { grid-template-columns: 1fr 3.6rem; }
  .mode .bar { grid-column: 1 / -1; grid-row: 2; }
}
@media (max-width: 560px) {
  form.search { grid-template-columns: 1fr; }
  .langs { border-top: 3px solid var(--ink); }
  .langs button { flex: 1; padding: 0.6rem 0; }
  .langs button:first-child { border-left: 0; }
}
@media (prefers-reduced-motion: no-preference) { .mode .bar span { transition: width 700ms ease-out; } }
</style>
</head>
<body>
<header class="hero">
  <div class="wrap">
    <h1>Swiss federal law, searched in four languages.</h1>
    <div>
      <p>Ask in German, French, Italian or English. Every article opens in all four, side by side, with the date of each version. Only German, French and Italian are legally binding, so the English text is shown in grey.</p>
      <div class="langline" aria-hidden="true"><span class="de">Deutsch</span><span class="fr">Français</span><span class="it">Italiano</span><span class="en">English</span></div>
    </div>
  </div>
</header>
<div class="wrap searchzone">
  <form class="search" role="search" id="form">
    <input id="q" type="search" autocomplete="off" spellcheck="false" aria-label="Search the law" placeholder="Kündigungsfrist Probezeit">
    <div class="langs" role="group" aria-label="Language of your search">
      <button type="button" data-l="de" aria-pressed="true">DE</button>
      <button type="button" data-l="fr" aria-pressed="false">FR</button>
      <button type="button" data-l="it" aria-pressed="false">IT</button>
      <button type="button" data-l="en" aria-pressed="false">EN</button>
    </div>
  </form>
  <div class="under" id="examples">Try
    <button class="eg" data-l="de" data-q="Kündigung während Krankheit">Kündigung während Krankheit</button>
    <button class="eg" data-l="fr" data-q="violation de la sécurité des données annonce">violation de la sécurité des données</button>
    <button class="eg" data-l="en" data-q="holiday entitlement weeks">holiday entitlement</button>
    <button class="eg" data-l="it" data-q="lavoro domenicale">lavoro domenicale</button>
  </div>
  <div class="acts" id="acts" aria-label="Acts to search"></div>
</div>

<main class="wrap work">
  <section aria-label="Results"><ol class="results" id="results"><li class="empty">Loading the law…</li></ol></section>
  <article class="reader" id="reader" aria-live="polite"></article>
</main>

<section class="eval" id="eval" hidden>
  <div class="wrap">
    <h2>Does searching in four languages find more?</h2>
    <p class="lede" id="eval-lede"></p>
    <div class="modes" id="modes"></div>
    <div class="key"><span><i style="background:#4A5361"></i>right article first (red-dark for the four-language search)</span><span><i style="background:#8E99A8"></i>right article in the top five (red for the four-language search)</span></div>
    <div class="facts" id="facts"></div>
    <details class="qs"><summary>All questions and where the right article ranked</summary><div style="overflow-x:auto"><table id="qtable"></table></div></details>
    <div class="answers" id="answers"></div>
  </div>
</section>

<footer class="wrap page-foot">
  <p>Texts from Fedlex, the official publication platform of the Swiss Confederation, read from its public data service. This site is a search tool, not legal advice; always check the current text on fedlex.admin.ch.</p>
  <p id="built"></p>
</footer>

<script>
const TEXT = /*TEXT*/;
const NAMES = {de: "Deutsch", fr: "Français", it: "Italiano", en: "English"};
const ORDER = ["de", "fr", "it", "en"];

// ---- text: the same steps as swisslaw/text.py ----
const fold = s => s.toLowerCase().replace(/ß/g, "ss").normalize("NFD").replace(/\p{Mn}/gu, "");
const STOPF = Object.fromEntries(Object.entries(TEXT.stop).map(([l, ws]) => [l, new Set(ws.map(fold))]));
const WORD = /[^\P{L}]+|\d+[a-z]*/gu;
function stem(w, l) {
  for (const s of TEXT.suffixes[l] || []) if (w.endsWith(s) && w.length - s.length >= TEXT.minStem) return w.slice(0, -s.length);
  return w;
}
function tokens(text, l) {
  const out = [], stop = STOPF[l] || new Set();
  for (const w of fold(text).match(WORD) || []) { if (stop.has(w) || w.length < 2) continue; out.push(stem(w, l)); }
  return out;
}

// ---- BM25, as swisslaw/search.py ----
const K1 = 1.2, B = 0.75, indexes = {};
function buildIndex(l) {
  const ids = [], tf = [], dl = [], df = new Map(), post = new Map();
  for (const a of DATA.articles) {
    const e = a.l[l]; if (!e) continue;
    const doc = [e[1], e[1], e[2].slice(-2).join(" "), e[3]].join(" ");
    const t = new Map(); let n = 0;
    for (const w of tokens(doc, l)) { t.set(w, (t.get(w) || 0) + 1); n++; }
    const i = ids.length; ids.push(a.id); tf.push(t); dl.push(n);
    for (const w of t.keys()) { df.set(w, (df.get(w) || 0) + 1); if (!post.has(w)) post.set(w, []); post.get(w).push(i); }
  }
  const N = ids.length, avg = dl.reduce((x, y) => x + y, 0) / N, idf = new Map();
  for (const [w, d] of df) idf.set(w, Math.log(1 + (N - d + 0.5) / (d + 0.5)));
  return {ids, tf, dl, avg, idf, post};
}
function search(q, l, k = 25) {
  const ix = indexes[l] || (indexes[l] = buildIndex(l)), score = new Map();
  for (const w of new Set(tokens(q, l))) {
    const idf = ix.idf.get(w); if (idf === undefined) continue;
    for (const i of ix.post.get(w)) {
      const f = ix.tf[i].get(w);
      score.set(i, (score.get(i) || 0) + idf * f * (K1 + 1) / (f + K1 * (1 - B + B * ix.dl[i] / ix.avg)));
    }
  }
  return [...score].sort((a, b) => b[1] - a[1] || (ix.ids[a[0]] < ix.ids[b[0]] ? -1 : 1)).map(([i]) => ix.ids[i])
    .filter(id => activeActs.has(BY[id].act)).slice(0, k);
}

// ---- page ----
let DATA, BY, ACTS, lang = "de", current = null, activeActs = new Set(), terms = [];
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));

function ref(a, l) {
  const act = ACTS[a.act], e = a.l[l] || a.l[act.authoritative];
  return `${e[0]} ${act.short[l] || act.short.de}`;
}
function highlight(html, l) {
  if (!terms.length) return html;
  return html.replace(/[\p{L}\d]+/gu, w => terms.includes(stem(fold(w), l)) && !STOPF[l]?.has(fold(w)) ? `<mark>${w}</mark>` : w);
}

function renderResults(ids) {
  const ol = $("#results");
  if (!ids.length) { ol.innerHTML = `<li class="empty">No article matches. Try other words, or search in another language.</li>`; return; }
  ol.innerHTML = ids.map(id => {
    const a = BY[id], act = ACTS[a.act], e = a.l[lang] || a.l[act.authoritative];
    return `<li><button type="button" data-id="${esc(id)}" aria-current="${id === current}"><span class="ref">${esc(e[0])}<small>${esc(act.short[lang] || act.short.de)}, SR ${esc(act.sr)}</small></span><span class="what">${esc(e[1])}</span></button></li>`;
  }).join("");
}

function renderArticle(id) {
  const a = BY[id]; if (!a) return;
  current = id;
  document.querySelectorAll(".results button").forEach(b => b.setAttribute("aria-current", b.dataset.id === id));
  const act = ACTS[a.act], newest = Math.max(...["de", "fr", "it"].filter(l => act.version[l]).map(l => +new Date(act.version[l])));
  const cols = ORDER.map(l => {
    const e = a.l[l];
    if (!e) {
      const why = act.version[l] ? "This article is not in the English version Fedlex publishes, which is older than the binding text." :
        "Fedlex publishes no English translation of this act.";
      return `<div class="col missing" data-l="${l}"><div class="lang"><b>${NAMES[l]}</b></div><p>${why}</p></div>`;
    }
    const v = act.version[l], older = +new Date(v) < newest;
    const badge = l === "en" ? `<span class="badge ${older ? "older" : "translation"}">${older ? "translation of an older version" : "translation, not binding"}</span>`
                             : `<span class="badge binding">binding</span>`;
    const paras = e[3].split("\n").map(p => {
      const m = p.match(/^(\d+[a-z]*)\s+([\s\S]*)$/);
      return m ? `<p><span class="n">${esc(m[1])}</span>${highlight(esc(m[2]), l)}</p>` : `<p>${highlight(esc(p), l)}</p>`;
    }).join("");
    return `<div class="col" data-l="${l}"><div class="lang"><b>${NAMES[l]}</b><span>in force from ${esc(v)}</span></div>
      <h3>${esc(e[0])} ${esc(e[1])}</h3>${e[2].length ? `<p class="trail">${esc(e[2].join(", "))}</p>` : ""}${badge ? `<div style="margin:-0.3rem 0 0.7rem">${badge}</div>` : ""}${paras}</div>`;
  }).join("");
  const title = act.title[lang] || act.title.de;
  $("#reader").innerHTML = `<header><h2>${esc(ref(a, lang))}</h2><p class="act">${esc(title)}, SR ${esc(act.sr)}</p></header>
    <div class="tabs" role="tablist">${ORDER.map(l => `<button type="button" role="tab" data-tab="${l}" aria-selected="${l === lang}" class="langtab">${l.toUpperCase()}</button>`).join("")}</div>
    <div class="parallel">${cols}</div>
    <footer>Source: <a href="${esc(ELI(act))}" rel="noopener">${esc(title)} on Fedlex</a>. Article ${esc(a.id.split(" ")[1].replace("art_", "").replace(/_/g, ""))} carries the same identifier in every language, which is how the columns are matched.</footer>`;
  setTab(lang);
  history.replaceState(null, "", "#" + encodeURIComponent(id));
}
const ELI = act => "https://www.fedlex.admin.ch/eli/" + act.eli + "/" + (lang === "en" && act.version.en ? "en" : lang === "en" ? "de" : lang);
function setTab(l) {
  document.querySelectorAll(".col").forEach(c => c.classList.toggle("on", c.dataset.l === l));
  document.querySelectorAll(".langtab").forEach(b => { b.setAttribute("aria-selected", b.dataset.tab === l); b.style.cssText = b.dataset.tab === l ? `background:var(--${l});color:#fff` : ""; });
}

function run() {
  const q = $("#q").value.trim();
  terms = tokens(q, lang);
  if (!q) { renderResults([]); $("#results").innerHTML = `<li class="empty">Type a question or a few words.</li>`; return; }
  const ids = search(q, lang);
  renderResults(ids);
  if (ids.length && (!current || !ids.includes(current))) renderArticle(ids[0]);
  else if (current) renderArticle(current);
}
function setLang(l) {
  lang = l;
  document.querySelectorAll(".langs button").forEach(b => b.setAttribute("aria-pressed", b.dataset.l === l));
  $("#q").placeholder = {de: "Kündigungsfrist Probezeit", fr: "délai de congé temps d'essai", it: "termine di disdetta periodo di prova", en: "notice period probation"}[l];
  run();
}

function renderEval(R) {
  const E = R.eval; if (!E) return;
  const S = E.summary, n = E.rows.length;
  $("#eval").hidden = false;
  $("#eval-lede").textContent = `${n} questions in plain English, the way people type them, each checked against the article that answers it. The same question is searched four ways: in the English translation only, and after a model (${(E.translator || "").split(":").pop()}) rewrites it in the legal language of German, French and Italian.`;
  const order = ["en", "de", "official", "all"];
  $("#modes").innerHTML = order.map(m => `<div class="mode"><span>${esc(S[m].label)}</span>
    <span class="bar" title="first: ${Math.round(100 * S[m]["hit@1"])}%, top five: ${Math.round(100 * S[m]["hit@5"])}%"><span style="width:${100 * S[m]["hit@5"]}%"></span><span class="k1" style="width:${100 * S[m]["hit@1"]}%"></span></span>
    <span class="v">${Math.round(100 * S[m]["hit@5"])}%</span></div>`).join("");
  const ne = S.no_english, c = S["all_vs_en@5"];
  $("#facts").innerHTML = `
    <p><b>${ne["found_all@5"]} of ${ne.questions} against ${ne["found_en@5"]}</b>Questions answered only by acts with no English text at all (the Labour Act, the Product Liability Act), found in the top five by the four-language search against English search.</p>
    <p><b>${c.only_all} against ${c.only_en}</b>Questions only the four-language search found in its top five, against questions only English search found. Exact McNemar test: p = ${c.p < 0.001 ? "< 0.001" : c.p.toFixed(3)}.</p>
    <p><b>${Math.round(100 * S.all.mrr) / 100} against ${Math.round(100 * S.en.mrr) / 100}</b>Mean reciprocal rank of the right article, four languages against English only. 1 would mean always first.</p>`;
  const cell = r => r ? `<td class="r">${r}</td>` : `<td class="r miss">not in top 10</td>`;
  $("#qtable").innerHTML = `<thead><tr><th>Question</th><th>Right article</th><th>English only</th><th>Four languages</th></tr></thead><tbody>` +
    E.rows.map(r => `<tr><td>${esc(r.q)}</td><td>${r.gold.map(g => `<a href="#${encodeURIComponent(g)}" data-open="${esc(g)}">${esc(BY[g] ? ref(BY[g], "en") : g)}</a>`).join(", ")}</td>${cell(r.rank.en)}${cell(r.rank.all)}</tr>`).join("") + `</tbody>`;
  if (R.answers && R.answers.items?.length) {
    const A = R.answers;
    $("#answers").innerHTML = `<h2>Answers, with every citation checked</h2>
      <p class="lede">${esc(A.note)}</p>` + A.items.map(x => `<div class="answer"><h3>${esc(x.question)}</h3><ul>${
        x.points.map(p => `<li${p.check && p.check.verdict !== "supported" ? ' class="disputed"' : ""}>${esc(p.text)} <span class="cite">${p.cites.map(c => `<a href="#${encodeURIComponent(c.article)}" data-open="${esc(c.article)}">${esc(BY[c.article] ? ref(BY[c.article], "en") : c.article)}${c.para ? " para. " + esc(c.para) : ""}</a>`).join(", ")}${p.check ? `, second model: ${esc(p.check.verdict.replace("_", " "))}` : ""}</span></li>`).join("")
      }</ul>${x.dropped?.length ? `<p class="cite">${x.dropped.length} point${x.dropped.length > 1 ? "s" : ""} removed because the quote was not in the cited paragraph.</p>` : ""}</div>`).join("");
  }
}

document.addEventListener("click", e => {
  const b = e.target.closest("[data-id]"); if (b) { renderArticle(b.dataset.id); if (innerWidth < 960) $("#reader").scrollIntoView({behavior: "smooth"}); return; }
  const l = e.target.closest(".langs button"); if (l) { setLang(l.dataset.l); return; }
  const t = e.target.closest("[data-tab]"); if (t) { setTab(t.dataset.tab); return; }
  const eg = e.target.closest(".eg"); if (eg) { $("#q").value = eg.dataset.q; current = null; setLang(eg.dataset.l); return; }
  const o = e.target.closest("[data-open]"); if (o) { e.preventDefault(); renderArticle(o.dataset.open); $("#reader").scrollIntoView({behavior: "smooth"}); }
});
$("#form").addEventListener("submit", e => { e.preventDefault(); current = null; run(); });
let timer; $("#q").addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(() => { current = null; run(); }, 180); });

Promise.all([fetch("data/corpus.json").then(r => r.json()), fetch("data/results.json").then(r => r.ok ? r.json() : {}).catch(() => ({}))])
  .then(([d, R]) => {
    DATA = d; BY = Object.fromEntries(d.articles.map(a => [a.id, a])); ACTS = Object.fromEntries(d.acts.map(a => [a.eli, a]));
    activeActs = new Set(d.acts.map(a => a.eli));
    $("#acts").innerHTML = d.acts.map(a => `<label title="${esc(a.title.en || a.title.de)}"><input type="checkbox" checked value="${esc(a.eli)}">${esc(a.short.de)}<span style="color:var(--soft)"> / ${esc(a.short.fr)}</span></label>`).join("");
    $("#acts").addEventListener("change", e => { e.target.checked ? activeActs.add(e.target.value) : activeActs.delete(e.target.value); run(); });
    $("#built").textContent = `${d.articles.length} articles from ${d.acts.length} acts, read from Fedlex on ${d.built}.`;
    renderEval(R);
    const h = decodeURIComponent(location.hash.slice(1));
    $("#q").value = "Kündigung während Krankheit"; run();
    if (BY[h]) renderArticle(h);
  })
  .catch(() => { $("#results").innerHTML = `<li class="empty">The law texts did not load. Reload the page.</li>`; });
</script>
</body>
</html>
"""
