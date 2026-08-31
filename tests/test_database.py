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


def test_get_formats_reference(db):
    refs = db.get_formats_reference()
    assert len(refs) >= 10
    codes = {r["code"] for r in refs}
    assert "@" in codes
    assert "≈" in codes
    assert "+" in codes
    assert "=" in codes
