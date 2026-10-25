import unittest

from swisslaw import answer, evaluate
from swisslaw.fedlex import parse
from swisslaw.search import Index, fuse
from swisslaw.text import normalise, tokens

AKN = '<akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0"><act><body>{}</body></act></akomaNtoso>'

ARTICLE = AKN.format("""
<chapter eId="chap_3"><num>3. Kapitel:</num><heading>Pflichten</heading>
<article eId="art_24"><num><b>Art. 24</b></num><heading>Meldung</heading>
<paragraph eId="art_24/para_1"><num>1</num><content><p> Der Verantwortliche<authorialNote><p>Fussnote, gehoert nicht zum Text.</p></authorialNote> meldet dem EDÖB so rasch als möglich.</p></content></paragraph>
<paragraph eId="art_24/para_5"><num>5</num><content><blockList><listIntroduction> Er kann verzichten, wenn:</listIntroduction>
<item><num>a. </num><p>die Information unmöglich ist; oder</p></item><item><num>b. </num><p>sie öffentlich ist.</p></item></blockList></content></paragraph>
</article>
<article eId="art_25"><num><b>Art. 25</b></num><heading></heading><paragraph><num>1</num><content><p>Aufgehoben</p></content></paragraph></article>
</chapter>""")


class Parsing(unittest.TestCase):
    def setUp(self):
        self.arts = parse(ARTICLE.encode())

    def test_article_fields_and_path(self):
        a = self.arts[0]
        self.assertEqual((a.eid, a.num, a.heading), ("art_24", "Art. 24", "Meldung"))
        self.assertEqual(a.path, ["3. Kapitel: Pflichten"])

    def test_footnotes_are_not_text(self):
        self.assertNotIn("Fussnote", self.arts[0].text)
        self.assertIn("Der Verantwortliche meldet dem EDÖB", self.arts[0].text)

    def test_lists_stay_in_their_paragraph(self):
        lines = self.arts[0].text.split("\n")
        self.assertEqual(lines[1], "5 Er kann verzichten, wenn: a. die Information unmöglich ist; oder b. sie öffentlich ist.")

    def test_repealed_articles_are_recognised(self):
        self.assertTrue(self.arts[1].repealed)
        self.assertFalse(self.arts[0].repealed)


class Text(unittest.TestCase):
    def test_plural_and_accents_meet(self):
        self.assertEqual(tokens("Kündigungen", "de"), tokens("Kündigung", "de"))
        self.assertEqual(tokens("résiliations", "fr"), tokens("résiliation", "fr"))

    def test_stop_words_go(self):
        self.assertEqual(tokens("Die Kündigung der Arbeit", "de"), tokens("Kündigung Arbeit", "de"))

    def test_quotes_compare_loosely(self):
        self.assertEqual(normalise("«Probezeit»  gilt."), normalise('"probezeit" gilt'))


CORPUS = [
    {"id": "CO art_335_b", "act": "or", "lang": {
        "de": {"num": "Art. 335b", "heading": "während der Probezeit", "path": [], "text": "1 Während der Probezeit kann das Arbeitsverhältnis mit einer Kündigungsfrist von sieben Tagen gekündigt werden."},
        "en": {"num": "Art. 335b", "heading": "During the probation period", "path": [], "text": "1 During the probation period, either party may terminate the contract at any time by giving seven days’ notice."}}},
    {"id": "EmpA art_9", "act": "arg", "lang": {
        "de": {"num": "Art. 9", "heading": "Wöchentliche Höchstarbeitszeit", "path": [], "text": "1 Die wöchentliche Höchstarbeitszeit beträgt 45 Stunden für Büropersonal."}}},
]
ACTS = {"or": {"short": {"en": "CO"}, "sr": "220", "authoritative": "de"},
        "arg": {"short": {"en": "EmpA"}, "sr": "822.11", "authoritative": "de"}}


class Search(unittest.TestCase):
    def test_article_without_english_is_only_found_in_other_languages(self):
        en, de = Index(CORPUS, "en"), Index(CORPUS, "de")
        self.assertEqual(en.n, 1)
        self.assertEqual(en.search("maximum weekly working hours"), [])
        self.assertEqual(de.search("wöchentliche Höchstarbeitszeit")[0][0], "EmpA art_9")

    def test_fusion_rewards_agreement(self):
        self.assertEqual(fuse([["a", "b"], ["b", "a"], ["b", "c"]])[0], "b")

    def test_first_hit_and_mcnemar(self):
        self.assertEqual(evaluate.first_hit(["x", "y", "g"], ["g", "h"]), 3)
        self.assertIsNone(evaluate.first_hit(["x"], ["g"]))
        # 0 against 6 discordant questions: p = 2 / 64
        self.assertAlmostEqual(evaluate.mcnemar_exact([False] * 6, [True] * 6)[2], 2 / 64)


class Grounding(unittest.TestCase):
    def test_quotes_must_be_in_the_cited_paragraph(self):
        points = [
            {"text": "Seven days' notice in the probation period.",
             "cites": [{"article": "CO art_335_b", "para": "1", "quote": "giving seven days’ notice"}]},
            {"text": "Invented rule.", "cites": [{"article": "CO art_335_b", "para": "1", "quote": "thirty days of notice apply"}]},
            {"text": "Wrong article.", "cites": [{"article": "CO art_999", "para": "1", "quote": "giving seven days’ notice"}]},
        ]
        kept, dropped = answer.ground(points, CORPUS)
        self.assertEqual([p["text"] for p in kept], ["Seven days' notice in the probation period."])
        self.assertEqual(kept[0]["cites"][0]["lang"], "en")
        self.assertEqual(len(dropped), 2)

    def test_quote_in_the_german_text_counts(self):
        kept, _ = answer.ground([{"text": "x", "cites": [{"article": "EmpA art_9", "para": "1",
                                  "quote": "Höchstarbeitszeit beträgt 45 Stunden"}]}], CORPUS)
        self.assertEqual(kept[0]["cites"][0]["lang"], "de")

    def test_paragraphs_are_split_by_number(self):
        e = {"text": "1 Erster Absatz.\n5bis Neuer Absatz."}
        self.assertEqual(answer.paragraphs(e), {"1": "Erster Absatz.", "5bis": "Neuer Absatz."})


if __name__ == "__main__":
    unittest.main()
