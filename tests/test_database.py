"""
tests/test_database.py

Unit tests for OETDatabase and query engine.
"""

import pytest
from oet_mcp_server.database import OETDatabase


@pytest.fixture
def db():
    return OETDatabase()


def test_book_normalization(db):
    assert db.normalize_book("John") == "JHN"
    assert db.normalize_book("Yohan") == "JHN"
    assert db.normalize_book("jhn") == "JHN"
    assert db.normalize_book("Genesis") == "GEN"
    assert db.normalize_book("1 Samuel") == "SA1"
    assert db.normalize_book("1Sam") == "SA1"
    assert db.normalize_book("SA1") == "SA1"
    assert db.normalize_book("Revelation") == "REV"


def test_parse_reference(db):
    assert db.parse_reference("John 1:1") == ("JHN", 1, 1, 1, 1)
    assert db.parse_reference("John 1:1-18") == ("JHN", 1, 1, 1, 18)
    assert db.parse_reference("John 1") == ("JHN", 1, 1, 1, 999)
    assert db.parse_reference("JHN.1.1") == ("JHN", 1, 1, 1, 1)
    assert db.parse_reference("GEN 1:1-5") == ("GEN", 1, 1, 1, 5)
    assert db.parse_reference("1 Sam 2:3") == ("SA1", 2, 3, 2, 3)


def test_get_passage_parallel(db):
    res = db.get_passage("John 1:1-3", version="parallel", include_notes=True)
    assert res.book_code == "JHN"
    assert res.verses_count == 3
    v1 = res.verses[0]
    assert v1.verse_label == "1"
    assert "In the beginning was the message" in v1.rv_text
    assert "In the beginning was the message" in v1.lv_text
    assert res.footnotes_count >= 1


def test_get_passage_interlinear(db):
    res = db.get_passage("John 1:1", version="interlinear", include_words=True)
    assert res.verses_count == 1
    v1 = res.verses[0]
    assert len(v1.words) > 0
    w1 = v1.words[0]
    assert w1.original_word == "Ἐν"
    assert w1.sr_lemma == "en"


def test_compare_passage(db):
    diffs = db.compare_passage("John 1:1-3")
    assert len(diffs) == 3
    assert any(len(d.added_words_lv) > 0 for d in diffs)
    assert any(len(d.translation_decisions_rv) > 0 for d in diffs)


def test_lookup_word_greek(db):
    w = db.lookup_word("JHN_1:1w5")
    assert w is not None
    assert w["original_word"] == "λόγος"
    assert w["sr_lemma"] == "logos"
    assert w["strongs"] == "G30560"
    assert "message" in w["oet_gloss"].lower()
    assert "lexicon" in w


def test_lookup_word_hebrew(db):
    w = db.lookup_word("GEN_1:1w1")
    assert w is not None
    assert "רֵאשִׁית" in w["original_word_clean"] or "רֵאשִׁ֖ית" in w["original_word"]
    assert "H7225" in w["strongs"] or "7225" in w["strongs"]


def test_search_lemma(db):
    res = db.search_lemma("logos", limit=10)
    assert res["query"] == "logos"
    assert res["lexicon_info"]["total_canonical_occurrences"] > 100
    assert len(res["occurrences"]) > 0


def test_search_text(db):
    res = db.search_text('"true light"', version="both", limit=5)
    assert len(res) >= 1
    assert any("John 1:9" in r["reference"] for r in res)


def test_get_catalog(db):
    cat = db.get_catalog()
    assert len(cat) >= 66
    jhn = next((b for b in cat if b.book_code == "JHN"), None)
    assert jhn is not None
    assert jhn.english_name == "John"
    assert jhn.rv_available is True
    assert jhn.lv_available is True


def test_every_catalog_book_resolves_to_verses(db):
    # Books are stored under the canonical OET code, so all 66 must be reachable
    missing = [b.book_code for b in db.get_catalog() if not db.get_passage(b.book_code).verses]
    assert missing == []


@pytest.mark.parametrize("ref,code", [
    ("1 Chronicles 1:1", "CH1"),
    ("1CH.1.1", "CH1"),
    ("1 Corinthians 13:4", "CO1"),
    ("2CO.13.4", "CO2"),
    ("James 1:1", "JAM"),
    ("Ezekiel 1:1", "EZE"),
    ("Jude 1", "JDE"),
    ("1 Peter 1:1", "PE1"),
    ("1 John 1:1", "JN1"),
    ("2 Timothy 3:16", "TI2"),
])
def test_numbered_books_are_reachable(db, ref, code):
    passage = db.get_passage(ref)
    assert passage.book_code == code
    assert passage.verses


@pytest.mark.parametrize("code", ["CH1", "SA1", "KI2", "CO1", "EZE", "JAM", "JDE", "JN3", "PE2", "TH1", "TI2"])
def test_bare_canonical_codes_resolve(db, code):
    assert db.get_passage(code).verses


DEUTEROCANONICAL_CODES = [
    "TOB", "JDT", "ESG", "ES1", "ES2", "DAG", "BAR", "MAN",
    "PS2", "WIS", "SIR", "MA1", "MA2", "MA3", "MA4",
]


def test_deuterocanonical_books_are_cataloged(db):
    cat = db.get_catalog()
    codes = [b.book_code for b in cat]
    assert codes[:66] == [b.book_code for b in cat if b.canonical_order <= 66]
    assert set(DEUTEROCANONICAL_CODES) <= set(codes)
    # They follow the canonical books, keeping the canonical ordering stable
    assert codes[66:] == DEUTEROCANONICAL_CODES

    tob = next(b for b in cat if b.book_code == "TOB")
    assert tob.english_name == "Tobit"
    assert tob.testament == "OT"
    assert tob.rv_available is True
    assert tob.lv_available is False  # Readers' Version only so far


@pytest.mark.parametrize("code", DEUTEROCANONICAL_CODES)
def test_deuterocanonical_books_are_reachable(db, code):
    assert db.normalize_book(code) == code
    passage = db.get_passage(f"{code}.1.1")
    assert passage.book_code == code
    assert passage.verses
    assert passage.verses[0].rv_text


@pytest.mark.parametrize("name,code", [
    ("Tobit", "TOB"),
    ("Judith", "JDT"),
    ("1 Esdras 1:1", "ES1"),
    ("2 Esdras 1:1", "ES2"),
    ("Additions to Esther", "ESG"),
    ("4 Maccabees 1:1", "MA4"),
    ("PS2", "PS2"),
    ("1 Maccabees", "MA1"),
    ("Ecclesiasticus", "SIR"),
])
def test_deuterocanonical_aliases(db, name, code):
    assert db.get_passage(name).book_code == code


def test_bare_code_wins_over_book_plus_chapter(db):
    # "PS2" is Psalm 151, not Psalms 2; writing "Psalm 2" or "Ps 2" still means Psalms 2
    assert db.get_passage("PS2").book_code == "PS2"
    assert db.get_passage("Psalm 2").book_code == "PSA"
    assert db.get_passage("Ps 2").verses[0].verse_id == "PSA.2.1"


def test_judith_is_not_confused_with_jude(db):
    assert db.normalize_book("Judith") == "JDT"
    assert db.normalize_book("JUD") == "JDE"


def test_every_verse_belongs_to_a_catalogued_book(db):
    with db.get_connection() as conn:
        orphans = conn.execute(
            "SELECT count(*) FROM verses v "
            "LEFT JOIN books b ON v.book_code = b.book_code "
            "WHERE b.book_code IS NULL"
        ).fetchone()[0]
    assert orphans == 0


def test_get_formats_reference(db):
    refs = db.get_formats_reference()
    assert len(refs) >= 10
    codes = {r["code"] for r in refs}
    assert "@" in codes
    assert "≈" in codes
    assert "+" in codes
    assert "=" in codes
    assert "!" in codes


def test_multi_line_verses_are_complete(db):
    # Poetry continues a verse onto \q lines; those lines must not be dropped
    psa231 = db.get_passage("Psalms 23:1").verses[0]
    assert psa231.rv_text.endswith("anything.")
    assert psa231.rv_text.startswith("Yahweh is my shepherd")

    psa11 = db.get_passage("Psalms 1:1").verses[0]
    assert psa11.rv_text.startswith("A person will reap the benefits")
    assert "scoffers" in psa11.rv_text


def test_no_marker_survives_in_any_clean_text(db):
    # char(92) is a backslash: no USFM marker may survive in any rendered column
    with db.get_connection() as conn:
        leaks = conn.execute(
            "SELECT count(*) FROM verses WHERE "
            + " OR ".join(
                f"instr({col}, char(92)) > 0"
                for col in (
                    "rv_text_clean", "lv_text_clean",
                    "rv_text_annotated", "lv_text_annotated",
                )
            )
        ).fetchone()[0]
    assert leaks == 0


def test_lv_name_alternation_has_no_marker(db):
    # The LV writes OET distinctive names as "English/(OET-name)" and used to mark the
    # raised ayin of those names with a "\sup" marker
    lv = db.get_passage("Acts 1:6").verses[0].lv_text
    assert "Israaʸl/(Yisrāʼēl)" in lv


def test_raw_esfm_is_opt_in(db):
    plain = db.get_passage("1 Kings 16:34").verses[0]
    assert plain.rv_esfm is None

    raw = db.get_passage("1 Kings 16:34", include_raw=True).verses[0]
    assert r"\add !(Jericho)\add*" in raw.rv_esfm
    assert r"\q" in db.get_passage("Psalms 1:1", include_raw=True).verses[0].rv_esfm
