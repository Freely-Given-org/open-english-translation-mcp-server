"""
tests/test_build_db.py

Unit tests for the ESFM parsing helpers used by scripts/build_db.py.
"""

import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import build_db  # noqa: E402
from build_db import (  # noqa: E402
    parse_esfm_file,
    DECISION_FORMATS,
    annotate_esfm_text,
    clean_esfm_text,
    extract_decisions,
)


@pytest.mark.parametrize("book_code", ["LAO", "ZZZ"])
def test_build_validates_before_replacing_database(tmp_path, monkeypatch, book_code):
    source = tmp_path / "source"
    source.mkdir()
    (source / f"OET-RV_{book_code}.ESFM").write_text(
        f"\\id {book_code}\n\\h Test book\n\\c 1\n\\v 1 A word¦1.\n", encoding="utf-8"
    )
    for name in ("nt.tsv", "ot.tsv", "OET-LV_OT_lemma_table.tsv"):
        (source / name).write_text("fixture\n", encoding="utf-8")
    monkeypatch.setattr(build_db, "OET_REPO", source)
    monkeypatch.setattr(build_db, "RV_DIR", source)
    monkeypatch.setattr(build_db, "LV_NT_DIR", source / "empty_nt")
    monkeypatch.setattr(build_db, "LV_OT_DIR", source / "empty_ot")
    monkeypatch.setattr(build_db, "NT_TSV_PATH", source / "nt.tsv")
    monkeypatch.setattr(build_db, "OT_TSV_PATH", source / "ot.tsv")

    def ingest_fixture_words(conn):
        # This unrelated Greek word reuses the source row number in the RV text.
        conn.execute("""INSERT INTO words (
            word_link_id, word_num, book_code, chapter, verse, word_seq, ref_str,
            lang, source_status, is_selected, strongs_standard_json
        ) VALUES ('JHN_1:1w1', 1, 'JHN', 1, 1, 1, 'JHN_1:1w1',
                  'greek', 'selected', 1, '[]')""")

    monkeypatch.setattr(build_db, "ingest_word_tables", ingest_fixture_words)
    monkeypatch.setattr(subprocess, "run", lambda args, **kwargs:
                        subprocess.CompletedProcess(args, 0, stdout="test-revision\n"))
    output = tmp_path / "corpus.db"
    previous = b"previous corpus contents"
    output.write_bytes(previous)
    monkeypatch.setattr(sys, "argv", ["build_db.py", "--output", str(output)])

    if book_code == "ZZZ":
        with pytest.raises(RuntimeError, match="existing database was not replaced"):
            build_db.main()
        assert output.read_bytes() == previous
    else:
        build_db.main()
        assert build_db.verify_db(output)
        with sqlite3.connect(output) as conn:
            assert conn.execute("SELECT count(*) FROM verses WHERE book_code='LAO'").fetchone()[0] == 1
            assert conn.execute("SELECT word_num, word_link_id FROM word_alignments").fetchall() == [(1, None)]
    assert not list(tmp_path.glob("oet-build-*.db"))


def test_add_alternate_name_is_a_known_code():
    assert "!" in "".join(code for code, scope, *_ in DECISION_FORMATS if scope == "add_tag")


def test_alternate_name_code_is_stripped_from_clean_text():
    raw = r"Amram's¦189723 children were Miryam \add !(Miriam)\add*, and Mosheh \add !(Moses)\add*."
    assert clean_esfm_text(raw) == "Amram's children were Miryam (Miriam), and Mosheh (Moses)."


def test_alternate_name_code_is_annotated():
    raw = r"Mosheh \add !(Moses)\add* led them"
    assert annotate_esfm_text(raw) == "Mosheh [!:(Moses)] led them"


def test_alternate_name_decision_is_extracted():
    raw = r"Shaul¦189723 \add !(Saul)\add* \add reigned\add*"
    decisions = extract_decisions(raw)
    assert decisions[0] == {
        "code": "!",
        "type": "Alternate (Traditional) Name",
        "text": "(Saul)",
    }
    assert decisions[1]["text"] == "reigned"


def test_alternate_name_handles_word_numbers():
    raw = r"a city¦87672 in Shomron¦87675 \add !(Samaria¦87675)\add*"
    assert clean_esfm_text(raw) == "a city in Shomron (Samaria)"
    assert extract_decisions(raw)[0]["text"] == "(Samaria)"


def test_escaped_add_span_is_handled():
    raw = r"wait for the promise \+add !(Jerusalem)\+add* now"
    assert clean_esfm_text(raw) == "wait for the promise (Jerusalem) now"
    assert extract_decisions(raw)[0]["code"] == "!"


def test_other_codes_still_parsed():
    assert clean_esfm_text(r"\add #people\add*") == "people"
    assert annotate_esfm_text(r"\add #people\add*") == "[#:people]"
    assert extract_decisions(r"\add #people\add*")[0]["type"] == "Number Change"


def test_exclamation_mark_inside_span_is_kept():
    raw = r"He said \add ≈What!\add* loudly"
    assert clean_esfm_text(raw) == "He said What! loudly"
    assert extract_decisions(raw)[0]["text"] == "What!"


def test_marker_whitespace_is_not_rendered():
    # The spaces inside the opening marker belong to the marker, not the output
    assert clean_esfm_text(r"Yeriho¦172624\add !/Jericho\add*)") == "Yeriho/Jericho)"
    assert clean_esfm_text(r"Yakov \add  !(Jacob)\add* , his twin") == "Yakov (Jacob) , his twin"
    assert clean_esfm_text(r"Yakov \add ≈  Ishmael\add* had a son") == "Yakov Ishmael had a son"
    assert annotate_esfm_text(r"Yeriho\add !/Jericho\add*") == "Yeriho[!:/Jericho]"
    assert extract_decisions(r"Yeriho\add !/Jericho\add*")[0]["text"] == "/Jericho"


def test_trailing_add_marker_is_not_read_as_a_span():
    # An unbalanced closing marker must not be mistaken for a span opener
    assert extract_decisions(r"bare text\add*") == []
    assert extract_decisions(r"bare text\+add*") == []


# --- Verse assembly -----------------------------------------------------------

POETRY_VERSE = """\\id PSA - test
\\h Songs
\\c 1
\\s1 Wicked and godly roads
\\p
\\v 1 \\z1 A person will reap the benefits
\\q2 if they don't take advice¦243189 from wicked¦243190 people,
\\q2 and don't stand¦243194 \\add ≈around where\\add* sinners¦243192.
\\b
\\q1
\\v 2 Yahweh is my shepherd¦254068.
"""


def _write_esfm(tmp_path, body):
    path = tmp_path / "OET-RV_PSA.ESFM"
    path.write_text(body, encoding="utf-8")
    return path


def test_verse_keeps_its_continuation_lines(tmp_path):
    meta, verses, _ = parse_esfm_file(_write_esfm(tmp_path, POETRY_VERSE), "RV")
    assert meta["book_code"] == "PSA"
    assert [v["verse_id"] for v in verses] == ["PSA.1.1", "PSA.1.2"]
    first = verses[0]
    # The \q2 lines are part of verse 1, and the \z1 note marker is not rendered
    assert first["clean"] == (
        "A person will reap the benefits if they don't take advice from wicked people, "
        "and don't stand around where sinners."
    )
    assert "\\q" not in first["clean"]
    # The line marker stays in the raw text, which is what the ESFM source looks like
    assert "\\q2" in first["raw"]


def test_continuation_lines_contribute_their_decisions(tmp_path):
    _, verses, _ = parse_esfm_file(_write_esfm(tmp_path, POETRY_VERSE), "RV")
    decisions = verses[0]["decisions"]
    assert [d["text"] for d in decisions if d["code"] == "≈"] == ["around where"]
    # Rewording inside an add span does not assert a poetic parallelism relation.
    assert verses[0]["has_parallel"] == 0


def test_last_verse_is_flushed_at_end_of_file(tmp_path):
    body = "\\id PSA - test\n\\h Songs\n\\c 23\n\\v 1 Yahweh is my shepherd¦254068:\n\\q1 he will not lack¦254070 anything¦254075.\n"
    _, verses, _ = parse_esfm_file(_write_esfm(tmp_path, body), "RV")
    assert len(verses) == 1
    assert verses[0]["clean"] == "Yahweh is my shepherd: he will not lack anything."


def test_chapter_marker_flushes_the_open_verse(tmp_path):
    body = "\\id PSA - test\n\\h Songs\n\\c 1\n\\v 1 first line\n\\q2 continued\n\\c 2\n\\v 5 second chapter\n"
    _, verses, _ = parse_esfm_file(_write_esfm(tmp_path, body), "RV")
    assert [v["verse_id"] for v in verses] == ["PSA.1.1", "PSA.2.5"]
    assert verses[0]["clean"] == "first line continued"


# --- Character formatting and editorial markers --------------------------------

def test_italic_and_bold_markers_are_unwrapped():
    assert clean_esfm_text(r"seize Peter during the \it Flat Bread Celebration\it*.") == \
        "seize Peter during the Flat Bread Celebration."
    assert clean_esfm_text(r"\bdit Yeshua the messiah and son of God\bdit*") == \
        "Yeshua the messiah and son of God"
    assert clean_esfm_text(r"\bd Weighed\bd*: deficient") == "Weighed: deficient"


def test_superscript_marker_is_unwrapped():
    # The LV marks the raised ayin of an OET name with \sup
    assert clean_esfm_text(r"_Israaʸl/(Yisrā\sup ʼēl\sup*)_") == "Israaʸl/(Yisrāʼēl)"


def test_jump_link_keeps_its_text_and_drops_attributes():
    assert clean_esfm_text(r'\jmp later|link-href="#C12V3"\jmp* poured oil') == "later poured oil"


def test_signature_and_note_markers_keep_their_text():
    assert clean_esfm_text(r"\sig I, Paul, am greeting you.\sig*") == "I, Paul, am greeting you."
    assert clean_esfm_text(r"as they deserve \qs (Instrumental break.)\qs*") == "as they deserve (Instrumental break.)"


def test_unclosed_z_note_marker_is_removed():
    # "\z1" notes are left unclosed in the source and wrap the whole verse
    assert clean_esfm_text(r"\z1 A person will reap the benefits") == "A person will reap the benefits"
    assert clean_esfm_text(r"and \z2his arrow flew\z2*") == "and his arrow flew"


def test_figure_block_is_removed():
    raw = r'\fig Yeshua was immersed.|src="images/x.jpg" size="col"\fig*\add ≈Then one day\add*'
    assert clean_esfm_text(raw) == "Then one day"


def test_footnote_blocks_are_removed_in_both_shapes():
    assert clean_esfm_text(r"a word\f + \fr 1:1 \ft A note.\f* next") == "a word next"
    assert clean_esfm_text(r"the sons of\f + \fr 5:10 \fqa Arah.\f* Ares") == "the sons of Ares"
    assert clean_esfm_text(r"kept\f + \fr 5:10 \fqa Arah.\f*") == "kept"


def test_no_marker_survives_clean_text():
    raw = (r'\z1 line one\q2 line two\it italic\it* \bdit bold\bd*\sup ʼēl\sup* '
           r'\jmp later|link-href="#x"\jmp* \sig sign-off\sig* \qs (note.)\qs* \bd plain\bd*')
    for out in (clean_esfm_text(raw), annotate_esfm_text(raw)):
        assert "\\" not in out


def test_line_parallelism_decisions_are_extracted():
    decisions = extract_decisions(r"first line\q1 ≈second line\q1\q1 →third line")
    codes = {d["code"] for d in decisions}
    assert {"≈", "→"} <= codes
    types = {d["type"] for d in decisions}
    assert "synonymous_parallelism" in types
    assert "synthetic_parallelism" in types


def test_removed_marker_does_not_join_two_words():
    # A footnote or marker written between two words must not run them together
    assert clean_esfm_text(r"take his\f + \fr 7:9 \ft a note\f* staff") == "take his staff"
    assert clean_esfm_text(r"When he\add ≈makes thunder\add* rose") == "When he makes thunder rose"
    assert clean_esfm_text(r"preach \add about how\add*\nd Messiah\nd* rose") == "preach about how Messiah rose"

def test_word_fragment_add_stays_attached():
    # A span with no decision code is a fragment of the word it touches
    assert clean_esfm_text(r"his servant\add s\add* ran") == "his servants ran"
    assert clean_esfm_text(r"David\add 's family\add* left") == "David's family left"
    assert clean_esfm_text(r"been \add re\add*born in God") == "been reborn in God"


def test_standalone_decision_symbol_is_dropped():
    # "≈" can stand alone with no marker at all, mid-line
    assert clean_esfm_text(r"the day of his raging ≈anger.") == "the day of his raging anger."
    assert clean_esfm_text(r"\q1 ≈because he rose") == "because he rose"
    # but the code of an \add span is kept, so the annotation can show it
    assert clean_esfm_text(r"\add ≈So\add* I came") == "So I came"
    assert annotate_esfm_text(r"\add ≈So\add* I came") == "[≈:So] I came"


def test_plus_prefixed_format_is_unwrapped():
    # A "+" prefix marks an alternative rendering of a format
    assert clean_esfm_text(r"the holy \+nd spirit\+nd* came") == "the holy spirit came"
    assert clean_esfm_text(r"God has \+em not\+em* lied") == "God has not lied"


def test_poetry_line_markers_are_removed():
    # Every line marker that can continue a verse is stripped, but its text is kept
    for raw, expected in (
        (r"one \q1 two \q2 three", "one two three"),
        (r"one \p two", "one two"),
        (r"one \li1 two", "one two"),
        (r"one \qa two", "one two"),
        (r"one \pi1 two", "one two"),
        (r"one \sp Yirmeyah", "one Yirmeyah"),
        (r"one \m two", "one two"),
    ):
        assert clean_esfm_text(raw) == expected, raw
