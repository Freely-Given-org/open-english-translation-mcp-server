#!/usr/bin/env python3
"""
scripts/build_db.py

Builds the complete SQLite database (oet_corpus.db) from:
- OET-RV ESFM files (/srv/FreelyGiven/OpenEnglishTranslation--OET/translatedTexts/ReadersVersion/)
- OET-LV ESFM files (/srv/FreelyGiven/OpenEnglishTranslation--OET/derivedTexts/auto_edited_VLT_ESFM/ and auto_edited_OT_ESFM/)
- OET-LV NT Word Table TSV
- OET-LV OT Word Table TSV
"""

import os
import sys
import re
import csv
import json
import sqlite3
import glob
from pathlib import Path
from collections import defaultdict, Counter

WORKSPACE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = WORKSPACE_DIR / "src" / "oet_mcp_server" / "data"
DB_PATH = DB_DIR / "oet_corpus.db"

OET_REPO = Path("/srv/FreelyGiven/OpenEnglishTranslation--OET")
RV_DIR = OET_REPO / "translatedTexts" / "ReadersVersion"
LV_NT_DIR = OET_REPO / "derivedTexts" / "auto_edited_VLT_ESFM"
LV_OT_DIR = OET_REPO / "derivedTexts" / "auto_edited_OT_ESFM"

NT_TSV_PATH = RV_DIR / "OET-LV_NT_word_table.tsv"
OT_TSV_PATH = RV_DIR / "OET-LV_OT_word_table.tsv"

# Canon book definitions & metadata
BOOK_NAMES = {
    # OT
    "GEN": ("Genesis", "Genesis", "OT", 1),
    "EXO": ("Exodus", "Exodus", "OT", 2),
    "LEV": ("Leviticus", "Leviticus", "OT", 3),
    "NUM": ("Numbers", "Numbers", "OT", 4),
    "DEU": ("Deuteronomy", "Deuteronomy", "OT", 5),
    "JOS": ("Joshua", "Yehoshua", "OT", 6),
    "JDG": ("Judges", "Judges", "OT", 7),
    "RUT": ("Ruth", "Ruth", "OT", 8),
    "SA1": ("1 Samuel", "1 Shemuel", "OT", 9),
    "SA2": ("2 Samuel", "2 Shemuel", "OT", 10),
    "KI1": ("1 Kings", "1 Kings", "OT", 11),
    "KI2": ("2 Kings", "2 Kings", "OT", 12),
    "CH1": ("1 Chronicles", "1 Chronicles", "OT", 13),
    "CH2": ("2 Chronicles", "2 Chronicles", "OT", 14),
    "EZR": ("Ezra", "Ezra", "OT", 15),
    "NEH": ("Nehemiah", "Nehemiah", "OT", 16),
    "EST": ("Esther", "Esther", "OT", 17),
    "JOB": ("Job", "Iyyov", "OT", 18),
    "PSA": ("Psalms", "Songs", "OT", 19),
    "PRO": ("Proverbs", "Proverbs", "OT", 20),
    "ECC": ("Ecclesiastes", "Ecclesiastes", "OT", 21),
    "SNG": ("Song of Solomon", "Song of Solomon", "OT", 22),
    "ISA": ("Isaiah", "Yeshayah", "OT", 23),
    "JER": ("Jeremiah", "Yermeyah", "OT", 24),
    "LAM": ("Lamentations", "Lamentations", "OT", 25),
    "EZE": ("Ezekiel", "Yehezkel", "OT", 26),
    "DAN": ("Daniel", "Daniel", "OT", 27),
    "HOS": ("Hosea", "Hosea", "OT", 28),
    "JOL": ("Joel", "Yoel", "OT", 29),
    "AMO": ("Amos", "Amots", "OT", 30),
    "OBA": ("Obadiah", "Ovadyah", "OT", 31),
    "JNA": ("Jonah", "Yonah", "OT", 32),
    "MIC": ("Micah", "Mikah", "OT", 33),
    "NAH": ("Nahum", "Nahum", "OT", 34),
    "HAB": ("Habakkuk", "Havakkuk", "OT", 35),
    "ZEP": ("Zephaniah", "Tsefanyah", "OT", 36),
    "HAG": ("Haggai", "Haggai", "OT", 37),
    "ZEC": ("Zechariah", "Zekaryah", "OT", 38),
    "MAL": ("Malachi", "Malaki", "OT", 39),
    # NT
    "MAT": ("Matthew", "Matthew", "NT", 40),
    "MRK": ("Mark", "Mark", "NT", 41),
    "LUK": ("Luke", "Luke", "NT", 42),
    "JHN": ("John", "Yohan", "NT", 43),
    "ACT": ("Acts", "Acts", "NT", 44),
    "ROM": ("Romans", "Romans", "NT", 45),
    "CO1": ("1 Corinthians", "1 Corinthians", "NT", 46),
    "CO2": ("2 Corinthians", "2 Corinthians", "NT", 47),
    "GAL": ("Galatians", "Galatians", "NT", 48),
    "EPH": ("Ephesians", "Ephesians", "NT", 49),
    "PHP": ("Philippians", "Philippians", "NT", 50),
    "COL": ("Colossians", "Colossians", "NT", 51),
    "TH1": ("1 Thessalonians", "1 Thessalonians", "NT", 52),
    "TH2": ("2 Thessalonians", "2 Thessalonians", "NT", 53),
    "TI1": ("1 Timothy", "1 Timothy", "NT", 54),
    "TI2": ("2 Timothy", "2 Timothy", "NT", 55),
    "TIT": ("Titus", "Titus", "NT", 56),
    "PHM": ("Philemon", "Philemon", "NT", 57),
    "HEB": ("Hebrews", "Hebrews", "NT", 58),
    "JAM": ("James", "Yacob", "NT", 59),
    "PE1": ("1 Peter", "1 Peter", "NT", 60),
    "PE2": ("2 Peter", "2 Peter", "NT", 61),
    "JN1": ("1 John", "1 Yohan", "NT", 62),
    "JN2": ("2 John", "2 Yohan", "NT", 63),
    "JN3": ("3 John", "3 Yohan", "NT", 64),
    "JDE": ("Jude", "Yudas", "NT", 65),
    "REV": ("Revelation", "Revelation", "NT", 66),
}

# Deuterocanonical books, which the OET publishes with the Hebrew Scriptures. They are
# numbered after the 66 canonical books so that the canonical ordering stays stable, and
# they are Readers' Version only (no Louis Irvin translation exists yet).
DEUTEROCANONICAL_NAMES = {
    "TOB": ("Tobit", "Tobit", "OT", 67),
    "JDT": ("Judith", "Judith", "OT", 68),
    "ESG": ("Esther (Greek)", "Esther (Greek)", "OT", 69),
    "ES1": ("1 Esdras", "1 Esdras", "OT", 70),
    "ES2": ("2 Esdras", "2 Esdras", "OT", 71),
    "DAG": ("Daniel (Greek)", "Daniel (Greek)", "OT", 72),
    "BAR": ("Baruch", "Baruch", "OT", 73),
    "MAN": ("Prayer of Manasses", "Prayer of Manasses", "OT", 74),
    "PS2": ("Psalm 151", "Psalm 151", "OT", 75),
    "WIS": ("Wisdom of Solomon", "Wisdom of Solomon", "OT", 76),
    "SIR": ("Sirach", "Sirach", "OT", 77),
    "MA1": ("1 Maccabees", "1 Maccabees", "OT", 78),
    "MA2": ("2 Maccabees", "2 Maccabees", "OT", 79),
    "MA3": ("3 Maccabees", "3 Maccabees", "OT", 80),
    "MA4": ("4 Maccabees", "4 Maccabees", "OT", 81),
}

ALL_BOOKS = {**BOOK_NAMES, **DEUTEROCANONICAL_NAMES}

# Add standard translation decision formats
DECISION_FORMATS = [
    ("+", "add_tag", "Added Article", "Added article ('a', 'the', 'some') for English grammatical sense", r"\add +the\add*"),
    ("=", "add_tag", "Added Copula", "Added copula ('is', 'was', 'are') required by English grammar", r"\add =is\add*"),
    ("<", "add_tag", "Added Direct Object", "Added direct object required by transitive English verb", r"\add <it\add*"),
    (">", "add_tag", "Added Implied Object/Person", "Added implied entity ('thing', 'one', 'person')", r"\add >things\add*"),
    ("≡", "add_tag", "Elided Repetition", "Repeated something elided in original for readability", r"\add ≡pursued\add*"),
    ("&", "add_tag", "Added Owner/Possessive", "Added possessive pronoun ('his', 'their')", r"\add &his\add*"),
    ("@", "add_tag", "Referent Replacement", "Replaced pronoun with specific name/referent", r"\add @Adam\add*"),
    ("*", "add_tag", "Name to Pronoun", "Replaced name with pronoun for fluency", r"\add *he\add*"),
    ("#", "add_tag", "Number Change", "Changed number (e.g. singular proverb generalized to plural)", r"\add #people\add*"),
    ("%", "add_tag", "Person / Direct Speech Shift", "Changed person (e.g. direct speech to indirect)", r"\add %that he will\add*"),
    ("^", "add_tag", "Saying to Opposite", "Changed saying to positive/opposite for natural flow", r"\add ^always open\add*"),
    ("≈", "add_tag", "Rewording", "Reworded word/phrase/clause for modern clarity", r"\add ≈answered\add*"),
    ("?", "add_tag", "Doubt / Uncertainty", "Translator uncertain of original intent (can precede other codes)", r"\add ?in the clouds\add*"),
    ("!", "add_tag", "Alternate (Traditional) Name", "Added the familiar/traditional name of a person or place in parentheses after the OET distinctive name", r"\add !(Moses)\add*"),
    ("≈", "line_start", "Synonymous Parallelism", "Second line of Hebrew poetic doublet repeating thought", r"\q1 ≈Yahweh gives comfort"),
    ("^", "line_start", "Antithetic Parallelism", "Second line of Hebrew poetic doublet stating contrast", r"\q1 ^but Israel will fall"),
    ("→", "line_start", "Synthetic Parallelism", "Second line of Hebrew poetic doublet reaching conclusion", r"\q1 →and he answered"),
    ("⇔", "verse_start", "Order Swapped", "Swapped first and second halves of verse for English naturalness", r"\v 10 ⇔The girls did..."),
]

# The decision codes that may follow "\add " to introduce an \add span, e.g. "\add !(Moses)\add*"
ADD_CODES = "+=<>≡&@*#%^≈?!"
# A span is written "\add ...\add*", or "\+add ...\+add*" when nested inside another marker.
# The whitespace around the code belongs to the opening marker, so it is consumed rather than
# rendered: "\add !/Jericho\add*" yields "/Jericho", not " /Jericho".
ADD_SPAN_RE = (
    r'\\(?P<escape>\+?)add(?!\*)\s*'
    r'(?P<code>[' + re.escape(ADD_CODES) + r']*)'
    r'\s*(?P<text>.*?)'
    r'\\(?P=escape)add\*'
)

# A verse continues onto following lines, each introduced by a line marker such as
# "\q1", "\q2", "\p", "\m" or "\li1". The marker is stripped and the rest of the line is
# joined onto the verse.
# Poetry (\q1, \q2, \qa), paragraph (\p, \m, \mi, \pi, \pc), list (\li1), speaker (\sp)
# and stanza (\b) lines continue the current verse, so they are joined onto it. The marker is
# kept in the raw text and stripped from the rendered text here.
LINE_MARKER_RE = re.compile(
    r'\\(?:qa\d*|q\d*|pi\d*|li\d*|ms\d*|mr\d*|nb|pc|sp|mi|m|p|b)(?:\s+|$)'
)
# Section headings are numbered ("\s1", "\s2", ...), so match the number generally.
SECTION_RE = re.compile(r'\\s\d*\s')
# A parallelism decision is written on the marker itself: "\q1 ≈…", "\q1 →…", "\v 10 ⇔…".
# The symbol records a decision (it is stored in the decisions table) but is not text, so
# it is dropped from the rendered text along with the marker. "\add ≈…" is unaffected because
# a single letter does not match the three-letter "\add".
LINE_DECISION_SYMBOL_RE = re.compile(r'\\[a-zA-Z]\d*\s*[≈^→⇔]\s*')
# A decision at the start of a verse is written after the "\v" marker, which parsing removes.
VERSE_DECISION_SYMBOL_RE = re.compile(r'^[≈^→⇔]\s*')
# A decision symbol sometimes stands on its own in the middle of a line, with no marker at
# all ("on the day of his raging ≈anger"). It is still a decision rather than text.
INLINE_DECISION_RE = re.compile(r'[≈^→⇔]')


def strip_inline_decision(m: "re.Match") -> str:
    """Drop a standalone decision symbol, keeping the code of an "\add" span.

    The code of an "\add" span has to survive until the span is annotated, so a symbol that
    belongs to an "\add" marker is left in place here and removed with the marker.
    """
    if re.search(r'\\(?:\+?)add\s*$', m.string[:m.start()]):
        return m.group(0)
    return " "
LINE_DECISION_RE = re.compile(r'\\(?:q\d?|v\s+\d+)\s*([≈^→⇔])')
LINE_DECISION_TYPES = {
    "≈": ("synonymous_parallelism", "Synonymous Parallelism"),
    "^": ("antithetic_parallelism", "Antithetic Parallelism"),
    "→": ("synthetic_parallelism", "Synthetic Parallelism"),
    "⇔": ("order_swapped", "Order Swapped"),
}


# Character formatting and editorial markers that carry no meaning for a plain-text
# reader: the tags are dropped and the inner text kept, the same way "\em" and "\bd" are
# already handled. "\z" notes are numbered to match their section ("\z1"), and the number
# is optional. A "+" prefix marks an alternative rendering of a format ("\+nd spirit"), so
# the opener and closer must agree on it. Any attribute list after a "|" is publishing
# metadata and is dropped, as in "\jmp later|link-href="#C12V3"\jmp*".
FORMAT_SPAN_RE = re.compile(
    r'\\(?P<plus>\+)?(?P<tag>it|bdit|bd|bk|em|nd|sc|wh|wj|sup|sig|qs|jmp|z|zr)\d*'
    r'(?P<oword>[a-zA-Z]*)(?P<space>\s*)'
    r'(?P<text>.*?)'
    r'(?:\|[^\\]*)?'
    r'\\(?P=plus)?(?P=tag)\d*(?P<suffix>[a-zA-Z]+)?\*',
    re.DOTALL,
)
# Some "\z" notes are never closed in the source, so the bare opener has to go too.
# "\z1hilite" glues the same word onto the marker (see unwrap_format_span); an unclosed
# version of it can survive when it sits inside another unclosed note, so allow the word.
BARE_Z_RE = re.compile(r'\\zr?\d*[a-zA-Z]*\s+')
# Figure blocks are captions plus image and copyright metadata, of no use in a text corpus.
FIG_BLOCK_RE = re.compile(r'\\fig\b.*?\\fig\*', re.DOTALL)
# "\d" holds performance directions ("For the musical director, ...") rather than text.
DESC_BLOCK_RE = re.compile(r'\\d\s+[^\\]*')
# Footnotes, in either shape: "\f + \fr 1:1 \ft text\f*", and "\f + \fr 1:1 \fqa Name,\f*"
# where the note content sits inline rather than in a "\ft" part.
FOOTNOTE_BLOCK_RE = re.compile(r'\\f\s*\+\s*\\fr\b.*?\\f\*', re.DOTALL)


def add_space_if_attached(m: "re.Match", replacement: str) -> str:
    """Restore a word boundary that a marker hid from the reader.

    A span can be written directly against the text on either side of it: "When he\\add
    ≈makes thunder\\add*" or "how\\add*\\nd Messiah\\nd*". Removing the marker without a
    space would run the two words together, so one is added back. Spans that continue a
    word keep their attachment instead: the OET writes those as a code-less "\\add" ("his
    servant\\add s\\add*"), and emphasis markers such as "\\sup" wrap part of a word.
    Trailing spaces are harmless because the caller normalizes whitespace afterwards.
    """
    if not m.start():
        return replacement
    previous = m.string[m.start() - 1]
    if previous == "*" or (previous.isalpha() and replacement[:1].isalpha()):
        return " " + replacement
    return replacement


def unwrap_format_span(m: "re.Match") -> str:
    """Keep the text of a character-formatting span and drop its marker and attributes.

    The OET sometimes writes a note as "\\z2hilite text\\z2hilite*", repeating the same word
    on both sides of the note. A word that appears on both sides of the marker belongs to
    the marker rather than the text, so it is dropped; letters that only follow the opener
    are ordinary text and are kept.
    """
    text, oword, suffix = m.group("text"), m.group("oword"), m.group("suffix")
    if not oword or oword == suffix:
        return text
    return oword + m.group("space") + text


def unwrap_all_format_spans(text: str) -> str:
    """Unwrap character-formatting spans, including ones nested inside another span."""
    for _ in range(10):
        unwrapped = FORMAT_SPAN_RE.sub(unwrap_format_span, text)
        if unwrapped == text:
            break
        text = unwrapped
    return text


def clean_esfm_text(text: str) -> str:
    """Strip ESFM tags to produce clean, natural English reading text."""
    # Remove the parallelism symbols of line decisions, which are metadata rather than text
    text = LINE_DECISION_SYMBOL_RE.sub(' ', text)
    text = VERSE_DECISION_SYMBOL_RE.sub(' ', text)
    text = INLINE_DECISION_RE.sub(strip_inline_decision, text)
    # Remove footnotes, cross-refs and figure blocks
    text = FOOTNOTE_BLOCK_RE.sub(' ', text)
    text = re.sub(r'\\x\s*\+\s*\\xo.*?\\xt\s*(.*?)\\x\*', ' ', text)
    text = FIG_BLOCK_RE.sub(' ', text)
    # Remove \add markers and their code characters. A span without a decision code is a
    # fragment of the surrounding word ("servant\add s\add*"), so it stays attached.
    def unwrap_add(m):
        if not m.group("code").strip():
            return m.group("text")
        return add_space_if_attached(m, m.group("text"))

    text = re.sub(ADD_SPAN_RE, unwrap_add, text)
    # Remove \untr markers (in LV, untranslated words like 'the', 'DOM')
    text = re.sub(r'\\untr\s*(.*?)\\untr\*', lambda m: add_space_if_attached(m, m.group(1)), text)
    # Remove \nd, \wj, \em, \bd markers
    text = re.sub(r'\\nd\s*(.*?)\\nd\*', lambda m: add_space_if_attached(m, m.group(1)), text)
    text = re.sub(r'\\wj\s*(.*?)\\wj\*', lambda m: add_space_if_attached(m, m.group(1)), text)
    text = re.sub(r'\\em\s*(.*?)\\em\*', lambda m: add_space_if_attached(m, m.group(1)), text)
    # Remove figure blocks, performance directions and character formatting, keeping text
    text = DESC_BLOCK_RE.sub(' ', text)
    text = unwrap_all_format_spans(text)
    text = BARE_Z_RE.sub(' ', text)
    # Remove verse-continuation line markers (\q1, \p, \li1, ...)
    text = LINE_MARKER_RE.sub(' ', text)
    # Remove word link pipes: word¦12345 -> word
    text = re.sub(r'¦\d+', '', text)
    # Remove underscores connecting multi-word glosses: in_order_that -> in order that
    text = text.replace('_', ' ')
    # Normalize spaces and punctuation
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def annotate_esfm_text(text: str, version: str = "RV") -> str:
    """Format ESFM text with human-readable markdown annotations showing translation decisions."""
    # Drop the parallelism symbols of line decisions; the decision itself is in the
    # decisions table, and wrapping a whole poetry line in brackets would bury the text
    text = LINE_DECISION_SYMBOL_RE.sub(' ', text)
    text = VERSE_DECISION_SYMBOL_RE.sub(' ', text)
    text = INLINE_DECISION_RE.sub(strip_inline_decision, text)
    # Strip footnotes, cross refs and figure blocks from inline text
    text = FOOTNOTE_BLOCK_RE.sub(' ', text)
    text = re.sub(r'\\x\s*\+\s*\\xo.*?\\xt\s*(.*?)\\x\*', ' ', text)
    text = FIG_BLOCK_RE.sub(' ', text)

    # Process \add with decision symbols
    def replace_add(m):
        code = m.group("code").strip()
        inner = m.group("text").strip()
        if not code:
            # a code-less span continues the surrounding word, so it stays attached
            return f"[{inner}]"
        return add_space_if_attached(m, f"[{code}:{inner}]")

    text = re.sub(ADD_SPAN_RE, replace_add, text)
    # Process \untr
    text = re.sub(r'\\untr\s*(.*?)\\untr\*', lambda m: add_space_if_attached(m, '{' + m.group(1) + '}'), text)
    # Strip word link IDs
    text = re.sub(r'¦\d+', '', text)
    text = re.sub(r'\\nd\s*(.*?)\\nd\*', lambda m: add_space_if_attached(m, m.group(1)), text)
    text = re.sub(r'\\wj\s*(.*?)\\wj\*', lambda m: add_space_if_attached(m, m.group(1)), text)
    text = re.sub(r'\\em\s*(.*?)\\em\*', lambda m: add_space_if_attached(m, m.group(1)), text)
    # Drop character formatting and editorial markers, keeping their text
    text = DESC_BLOCK_RE.sub(' ', text)
    text = unwrap_all_format_spans(text)
    text = BARE_Z_RE.sub(' ', text)
    text = LINE_MARKER_RE.sub(' ', text)
    text = text.replace('_', ' ')
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_decisions(raw_text: str) -> list:
    """Extract all explicit translation decisions encoded via \\add and line markers."""
    decisions = []
    # Check start markers
    if raw_text.startswith("⇔"):
        decisions.append({
            "code": "⇔",
            "type": "order_swapped",
            "description": "Clause order inverted for natural English discourse"
        })
    if "≈" in raw_text[:3]:
        decisions.append({
            "code": "≈",
            "type": "synonymous_parallelism",
            "description": "Hebrew poetic synonymous parallelism"
        })
    if "^" in raw_text[:3]:
        decisions.append({
            "code": "^",
            "type": "antithetic_parallelism",
            "description": "Hebrew poetic antithetic parallelism"
        })

    # Parallelism decisions written on a line marker: "\q1 ≈…", "\q1 →…", "\v 10 ⇔…"
    for m in LINE_DECISION_RE.finditer(raw_text):
        kind, description = LINE_DECISION_TYPES[m.group(1)]
        decisions.append({
            "code": m.group(1),
            "type": kind,
            "description": description
        })

    # Find all \add occurrences
    for m in re.finditer(ADD_SPAN_RE, raw_text):
        code = m.group("code").strip()
        content = re.sub(r'¦\d+', '', m.group("text")).replace('_', ' ').strip()
        code_desc = {
            "+": "Added Article",
            "=": "Added Copula",
            "<": "Added Direct Object",
            ">": "Added Implied Object/Person",
            "≡": "Elided Repetition",
            "&": "Added Owner/Possessive",
            "@": "Referent Replacement (Pronoun -> Name)",
            "*": "Name to Pronoun",
            "#": "Number Change",
            "%": "Person / Direct Speech Shift",
            "^": "Saying to Opposite",
            "≈": "Rewording for Modern Fluency",
            "?": "Uncertain / Probable Reading",
            "!": "Alternate (Traditional) Name"
        }.get(code, "Added Information")
        decisions.append({
            "code": code,
            "type": code_desc,
            "text": content
        })
    return decisions


def parse_esfm_file(filepath: Path, version: str):
    """
    Parses an ESFM file and returns:
    - book_meta: dict
    - verses: list
    - notes: list
    """
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # The filename carries the canonical OET book code (CH1, EZE, JAM, JDE, ...), which is
    # what BOOK_NAMES and the word tables use. The in-file "\id" marker spells some of the
    # same books differently (1CH, EZK, JAS, JUD, ...), so only use it as a fallback.
    book_code = filepath.stem
    prefix = f"OET-{version}_"
    if book_code.startswith(prefix):
        book_code = book_code[len(prefix):]
    else:
        m_id = re.search(r'\\id\s+([A-Za-z0-9]{3})', content)
        if m_id:
            book_code = m_id.group(1).upper()

    book_meta = {
        "book_code": book_code,
        "title": None,
        "toc1": None,
        "toc2": None,
        "toc3": None,
    }

    verses = []
    notes = []
    current_chapter = 0
    current_section = None
    lines = content.splitlines()

    # A verse's text can span several source lines: the first begins with "\v N" and the
    # rest continue it as poetry ("\q1", "\q2"), paragraph ("\p", "\m", "\mi"), or list
    # ("\li1") lines. Those lines have to be joined onto the verse, otherwise most of the
    # poetic books (Psalms, Proverbs 10-31, Song of Songs, ...) keep only their first line.
    pending_verse = None  # (verse label, list of text fragments)

    def flush_verse():
        """Finalize the verse being accumulated, if any."""
        nonlocal pending_verse
        if pending_verse is None:
            return
        v_num_str, fragments = pending_verse
        pending_verse = None
        v_text_raw = " ".join(f for f in fragments if f).strip()

        v_clean_num = re.split(r'[-–,]', v_num_str)[0]
        try:
            verse_num = int(v_clean_num)
        except ValueError:
            verse_num = 1

        verse_id = f"{book_code}.{current_chapter}.{v_num_str}"

        # Extract footnotes
        for fn in re.finditer(r'\\f\s*\+\s*\\fr\s*(.*?)\\ft\s*(.*?)\\f\*', v_text_raw):
            fr = fn.group(1).strip()
            ft = fn.group(2).strip()
            category = "General"
            if ft.startswith("TD:"):
                category = "TD"
            elif ft.startswith("TC:"):
                category = "TC"
            elif ft.startswith("Hist:"):
                category = "Hist"
            elif ft.startswith("Fig:"):
                category = "Fig"
            notes.append((verse_id, version, "footnote", category, fr, ft))

        # Extract cross-references
        for xr in re.finditer(r'\\x\s*\+\s*\\xo\s*(.*?)\\xt\s*(.*?)\\x\*', v_text_raw):
            xo = xr.group(1).strip()
            xt = xr.group(2).strip()
            notes.append((verse_id, version, "xref", "General", xo, xt))

        clean = clean_esfm_text(v_text_raw)
        annotated = annotate_esfm_text(v_text_raw, version)
        decisions = extract_decisions(v_text_raw)
        has_missing = 1 if "◘" in v_text_raw else 0
        has_parallel = 1 if any(p in v_text_raw for p in ["≈", "→"]) else 0
        has_swap = 1 if "⇔" in v_text_raw else 0

        verses.append({
            "verse_id": verse_id,
            "book_code": book_code,
            "chapter": current_chapter,
            "verse": verse_num,
            "verse_label": v_num_str,
            "raw": v_text_raw,
            "clean": clean,
            "annotated": annotated,
            "decisions": decisions,
            "has_missing": has_missing,
            "has_parallel": has_parallel,
            "has_swap": has_swap,
            "section": current_section
        })

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith(r'\toc1 '):
            book_meta["toc1"] = line[6:].strip()
        elif line.startswith(r'\toc2 '):
            book_meta["toc2"] = line[6:].strip()
        elif line.startswith(r'\toc3 '):
            book_meta["toc3"] = line[6:].strip()
        elif line.startswith(r'\h '):
            book_meta["title"] = line[3:].strip()
        elif line.startswith(r'\c '):
            flush_verse()
            c_str = line[3:].split()[0]
            try:
                current_chapter = int(c_str)
            except ValueError:
                pass
        elif SECTION_RE.match(line):
            flush_verse()
            parts = line.split(maxsplit=1)
            current_section = parts[1].strip() if len(parts) > 1 else None
        elif line.startswith(r'\v '):
            flush_verse()
            parts = line[3:].split(maxsplit=1)
            if not parts:
                continue
            pending_verse = (parts[0], [parts[1] if len(parts) > 1 else ""])
        elif pending_verse is not None:
            # A continuation line of the verse being accumulated. Poetry (\q1, \q2),
            # paragraph (\p, \m) and list (\li1) lines belong to the verse above them, so
            # the line is joined on with its marker intact; the text helpers strip it.
            if line.startswith(r'\b') or line.startswith(r'\rem'):
                continue
            pending_verse[1].append(line)

    flush_verse()

    return book_meta, verses, notes


def create_schema(conn: sqlite3.Connection):
    """Creates the SQLite tables and indices."""
    cur = conn.cursor()
    
    cur.executescript("""
    DROP TABLE IF EXISTS books;
    DROP TABLE IF EXISTS sections;
    DROP TABLE IF EXISTS verses;
    DROP TABLE IF EXISTS words;
    DROP TABLE IF EXISTS lexicon;
    DROP TABLE IF EXISTS notes_and_xrefs;
    DROP TABLE IF EXISTS formats_reference;
    DROP TABLE IF EXISTS verses_fts;
    DROP TABLE IF EXISTS lexicon_fts;

    CREATE TABLE books (
        book_code TEXT PRIMARY KEY,
        testament TEXT NOT NULL,
        canonical_order INTEGER,
        english_name TEXT NOT NULL,
        oet_name TEXT,
        abbr TEXT,
        chapters_count INTEGER DEFAULT 0,
        sections_count INTEGER DEFAULT 0,
        rv_available INTEGER DEFAULT 0,
        lv_available INTEGER DEFAULT 0
    );

    CREATE TABLE sections (
        section_id TEXT PRIMARY KEY,
        book_code TEXT NOT NULL,
        chapter INTEGER,
        start_verse INTEGER,
        end_verse INTEGER,
        heading TEXT NOT NULL,
        FOREIGN KEY(book_code) REFERENCES books(book_code)
    );

    CREATE TABLE verses (
        verse_id TEXT PRIMARY KEY,
        book_code TEXT NOT NULL,
        chapter INTEGER NOT NULL,
        verse INTEGER NOT NULL,
        verse_label TEXT NOT NULL,
        rv_text_raw TEXT,
        rv_text_clean TEXT,
        rv_text_annotated TEXT,
        lv_text_raw TEXT,
        lv_text_clean TEXT,
        lv_text_annotated TEXT,
        has_missing_verse_flag INTEGER DEFAULT 0,
        has_poetry_parallel INTEGER DEFAULT 0,
        has_order_swap INTEGER DEFAULT 0,
        decisions_json TEXT,
        section_heading TEXT,
        FOREIGN KEY(book_code) REFERENCES books(book_code)
    );

    CREATE INDEX idx_verses_bcv ON verses(book_code, chapter, verse);

    CREATE TABLE words (
        word_link_id TEXT PRIMARY KEY,
        word_num INTEGER,
        book_code TEXT NOT NULL,
        chapter INTEGER NOT NULL,
        verse INTEGER NOT NULL,
        word_seq INTEGER NOT NULL,
        ref_str TEXT NOT NULL,
        original_word TEXT,
        original_word_clean TEXT,
        sr_lemma TEXT,
        original_lemma TEXT,
        strongs TEXT,
        role TEXT,
        morphology TEXT,
        vlt_gloss TEXT,
        oet_gloss TEXT,
        contextual_gloss TEXT,
        morpheme_glosses TEXT,
        tags TEXT
    );

    CREATE INDEX idx_words_ref ON words(book_code, chapter, verse);
    CREATE INDEX idx_words_strongs ON words(strongs);
    CREATE INDEX idx_words_sr_lemma ON words(sr_lemma);
    CREATE INDEX idx_words_orig_lemma ON words(original_lemma);

    CREATE TABLE lexicon (
        lemma_key TEXT PRIMARY KEY,
        lang TEXT NOT NULL,
        lemma TEXT NOT NULL,
        lemma_display TEXT,
        strongs TEXT,
        primary_gloss TEXT,
        total_occurrences INTEGER DEFAULT 0,
        gloss_distribution_json TEXT,
        first_occurrences_refs TEXT
    );

    CREATE INDEX idx_lexicon_strongs ON lexicon(strongs);
    CREATE INDEX idx_lexicon_lemma ON lexicon(lemma);

    CREATE TABLE notes_and_xrefs (
        note_id INTEGER PRIMARY KEY AUTOINCREMENT,
        verse_id TEXT NOT NULL,
        source_version TEXT NOT NULL,
        note_type TEXT NOT NULL,
        category TEXT,
        caller_ref TEXT,
        content TEXT NOT NULL,
        FOREIGN KEY(verse_id) REFERENCES verses(verse_id)
    );

    CREATE INDEX idx_notes_verse ON notes_and_xrefs(verse_id);

    CREATE TABLE formats_reference (
        code TEXT NOT NULL,
        scope TEXT NOT NULL,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        example TEXT,
        PRIMARY KEY(code, scope)
    );

    CREATE VIRTUAL TABLE verses_fts USING fts5(
        verse_id,
        book_code,
        chapter UNINDEXED,
        verse UNINDEXED,
        rv_text_clean,
        lv_text_clean,
        content='verses',
        content_rowid='rowid'
    );

    CREATE VIRTUAL TABLE lexicon_fts USING fts5(
        lemma_key,
        lang UNINDEXED,
        lemma,
        lemma_display,
        strongs,
        primary_gloss,
        content='lexicon',
        content_rowid='rowid'
    );
    """)
    conn.commit()


def populate_formats_reference(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.executemany(
        "INSERT INTO formats_reference (code, scope, name, description, example) VALUES (?, ?, ?, ?, ?)",
        DECISION_FORMATS
    )
    conn.commit()


def ingest_word_tables(conn: sqlite3.Connection):
    """Ingests NT and OT TSV word tables and compiles lexicon statistics."""
    cur = conn.cursor()
    print("Ingesting NT Word Table TSV...")
    
    words_data = []
    lexicon_stats = defaultdict(lambda: {
        "lang": "greek",
        "lemma": "",
        "lemma_display": "",
        "strongs": "",
        "glosses": Counter(),
        "refs": []
    })

    if NT_TSV_PATH.exists():
        with open(NT_TSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                ref = row.get("Ref", "")
                m = re.match(r'([A-Z0-9]{3})_(\d+):(\d+)w(\d+)', ref)
                if not m:
                    continue
                book, ch, v, w_seq = m.groups()
                greek_word = row.get("GreekWord", "")
                sr_lemma = row.get("SRLemma", "")
                greek_lemma = row.get("GreekLemma", "")
                vlt_gloss = row.get("VLTGlossWords", "")
                oet_gloss = row.get("OETGlossWords", "")
                strongs_ext = row.get("StrongsExt", "")
                strongs = f"G{strongs_ext}" if strongs_ext and not strongs_ext.startswith("G") else strongs_ext
                role = row.get("Role", "")
                morph = row.get("Morphology", "")
                tags = row.get("Tags", "")

                word_link_id = ref
                words_data.append((
                    word_link_id,
                    None,
                    book,
                    int(ch),
                    int(v),
                    int(w_seq),
                    ref,
                    greek_word,
                    greek_word,
                    sr_lemma,
                    greek_lemma,
                    strongs,
                    role,
                    morph,
                    vlt_gloss,
                    oet_gloss,
                    oet_gloss,
                    None,
                    tags
                ))

                l_key = f"grk:{sr_lemma or strongs}"
                st = lexicon_stats[l_key]
                st["lang"] = "greek"
                st["lemma"] = sr_lemma
                st["lemma_display"] = greek_lemma
                st["strongs"] = strongs
                if oet_gloss:
                    clean_g = clean_esfm_text(oet_gloss).lower()
                    if clean_g:
                        st["glosses"][clean_g] += 1
                if len(st["refs"]) < 50:
                    st["refs"].append(f"{book} {ch}:{v}")

    print(f"Loaded {len(words_data)} NT words. Ingesting OT Word Table TSV...")

    if OT_TSV_PATH.exists():
        with open(OT_TSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                ref = row.get("Ref", "")
                m = re.match(r'([A-Z0-9]{3})_(\d+):(\d+)w(\d+)', ref)
                if not m:
                    continue
                book, ch, v, w_seq = m.groups()
                heb_word = row.get("Word", "")
                heb_clean = row.get("NoCantillations", "")
                strongs_val = row.get("Strongs", "")
                strongs = f"H{strongs_val}" if strongs_val and not strongs_val.startswith("H") else strongs_val
                morph = row.get("Morphology", "")
                morph_glosses = row.get("MorphemeGlosses", "")
                word_gloss = row.get("WordGloss", "")
                ctx_gloss = row.get("ContextualWordGloss", "")
                role = row.get("Role", "")
                tags = row.get("Tags", "")

                word_link_id = ref
                words_data.append((
                    word_link_id,
                    None,
                    book,
                    int(ch),
                    int(v),
                    int(w_seq),
                    ref,
                    heb_word,
                    heb_clean,
                    strongs_val,
                    heb_clean,
                    strongs,
                    role,
                    morph,
                    word_gloss,
                    ctx_gloss or word_gloss,
                    ctx_gloss,
                    morph_glosses,
                    tags
                ))

                l_key = f"heb:{strongs or heb_clean}"
                st = lexicon_stats[l_key]
                st["lang"] = "hebrew"
                st["lemma"] = strongs_val
                st["lemma_display"] = heb_clean
                st["strongs"] = strongs
                if word_gloss:
                    clean_g = clean_esfm_text(word_gloss).lower()
                    if clean_g:
                        st["glosses"][clean_g] += 1
                if len(st["refs"]) < 50:
                    st["refs"].append(f"{book} {ch}:{v}")

    print(f"Total words collected: {len(words_data)}. Inserting into SQLite...")

    cur.executemany("""
    INSERT INTO words (
        word_link_id, word_num, book_code, chapter, verse, word_seq, ref_str,
        original_word, original_word_clean, sr_lemma, original_lemma, strongs,
        role, morphology, vlt_gloss, oet_gloss, contextual_gloss, morpheme_glosses, tags
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, words_data)
    conn.commit()

    print(f"Compiling {len(lexicon_stats)} lexicon entries...")
    lex_rows = []
    lex_fts_rows = []
    for l_key, st in lexicon_stats.items():
        total_occ = sum(st["glosses"].values())
        top_gloss = st["glosses"].most_common(1)[0][0] if st["glosses"] else ""
        gloss_json = json.dumps(dict(st["glosses"].most_common(10)), ensure_ascii=False)
        refs_str = ", ".join(st["refs"])
        glosses_list = ", ".join(st["glosses"].keys())
        
        lex_rows.append((
            l_key,
            st["lang"],
            st["lemma"],
            st["lemma_display"],
            st["strongs"],
            top_gloss,
            total_occ,
            gloss_json,
            refs_str
        ))

        lex_fts_rows.append((
            l_key,
            st["lang"],
            st["lemma"],
            st["lemma_display"],
            st["strongs"],
            top_gloss,
            glosses_list
        ))

    cur.executemany("""
    INSERT INTO lexicon (
        lemma_key, lang, lemma, lemma_display, strongs, primary_gloss,
        total_occurrences, gloss_distribution_json, first_occurrences_refs
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, lex_rows)

    cur.execute("""
    INSERT INTO lexicon_fts (rowid, lemma_key, lang, lemma, lemma_display, strongs, primary_gloss)
    SELECT rowid, lemma_key, lang, lemma, lemma_display, strongs, primary_gloss FROM lexicon;
    """)
    conn.commit()
    print("Lexicon and words ingested successfully.")


def ingest_bibles(conn: sqlite3.Connection):
    """Ingests OET-RV and OET-LV ESFM files and populates books, verses, notes, and sections."""
    cur = conn.cursor()
    print("Ingesting OET-RV and OET-LV ESFM files...")

    rv_files = list(RV_DIR.glob("OET-RV_*.ESFM"))
    lv_files = list(LV_NT_DIR.glob("OET-LV_*.ESFM")) + list(LV_OT_DIR.glob("OET-LV_*.ESFM"))

    rv_verses_by_ref = {}
    lv_verses_by_ref = {}
    all_notes = []
    book_stats = defaultdict(lambda: {"rv_chapters": set(), "lv_chapters": set(), "rv_verses": 0, "lv_verses": 0, "sections": 0, "oet_name": None})

    print(f"Found {len(rv_files)} RV files and {len(lv_files)} LV files.")

    for r_file in rv_files:
        b_meta, v_list, n_list = parse_esfm_file(r_file, "RV")
        b_code = b_meta["book_code"]
        if b_meta["title"]:
            book_stats[b_code]["oet_name"] = b_meta["title"]
        for v in v_list:
            rv_verses_by_ref[v["verse_id"]] = v
            book_stats[b_code]["rv_chapters"].add(v["chapter"])
            book_stats[b_code]["rv_verses"] += 1
        all_notes.extend(n_list)

    for l_file in lv_files:
        b_meta, v_list, n_list = parse_esfm_file(l_file, "LV")
        b_code = b_meta["book_code"]
        for v in v_list:
            lv_verses_by_ref[v["verse_id"]] = v
            book_stats[b_code]["lv_chapters"].add(v["chapter"])
            book_stats[b_code]["lv_verses"] += 1
        all_notes.extend(n_list)

    # Insert Books
    book_rows = []
    for b_code, (eng_name, def_oet, testm, canon_ord) in ALL_BOOKS.items():
        st = book_stats[b_code]
        oet_name = st["oet_name"] or def_oet
        ch_count = max(len(st["rv_chapters"]), len(st["lv_chapters"]), 1)
        rv_avail = 1 if st["rv_verses"] > 0 else 0
        lv_avail = 1 if st["lv_verses"] > 0 else 0
        book_rows.append((
            b_code,
            testm,
            canon_ord,
            eng_name,
            oet_name,
            eng_name[:3],
            ch_count,
            st["sections"],
            rv_avail,
            lv_avail
        ))

    cur.executemany("""
    INSERT INTO books (
        book_code, testament, canonical_order, english_name, oet_name,
        abbr, chapters_count, sections_count, rv_available, lv_available
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, book_rows)
    conn.commit()

    # Merge verses
    all_verse_ids = set(rv_verses_by_ref.keys()) | set(lv_verses_by_ref.keys())
    print(f"Merging and inserting {len(all_verse_ids)} unique verses...")

    verse_rows = []
    fts_rows = []

    for v_id in sorted(all_verse_ids):
        rv_v = rv_verses_by_ref.get(v_id)
        lv_v = lv_verses_by_ref.get(v_id)
        sample_v = rv_v or lv_v
        book_code = sample_v["book_code"]
        chapter = sample_v["chapter"]
        verse_num = sample_v["verse"]
        v_label = sample_v["verse_label"]

        rv_raw = rv_v["raw"] if rv_v else None
        rv_clean = rv_v["clean"] if rv_v else None
        rv_annotated = rv_v["annotated"] if rv_v else None

        lv_raw = lv_v["raw"] if lv_v else None
        lv_clean = lv_v["clean"] if lv_v else None
        lv_annotated = lv_v["annotated"] if lv_v else None

        has_missing = 1 if ((rv_v and rv_v["has_missing"]) or (lv_v and lv_v["has_missing"])) else 0
        has_parallel = 1 if ((rv_v and rv_v["has_parallel"]) or (lv_v and lv_v["has_parallel"])) else 0
        has_swap = 1 if ((rv_v and rv_v["has_swap"]) or (lv_v and lv_v["has_swap"])) else 0

        # Combine decisions
        decisions = []
        if rv_v and rv_v["decisions"]:
            decisions.extend(rv_v["decisions"])
        if lv_v and lv_v["decisions"]:
            decisions.extend(lv_v["decisions"])
        dec_json = json.dumps(decisions, ensure_ascii=False) if decisions else None

        section = rv_v["section"] if rv_v and rv_v["section"] else (lv_v["section"] if lv_v else None)

        verse_rows.append((
            v_id,
            book_code,
            chapter,
            verse_num,
            v_label,
            rv_raw,
            rv_clean,
            rv_annotated,
            lv_raw,
            lv_clean,
            lv_annotated,
            has_missing,
            has_parallel,
            has_swap,
            dec_json,
            section
        ))

    cur.executemany("""
    INSERT INTO verses (
        verse_id, book_code, chapter, verse, verse_label,
        rv_text_raw, rv_text_clean, rv_text_annotated,
        lv_text_raw, lv_text_clean, lv_text_annotated,
        has_missing_verse_flag, has_poetry_parallel, has_order_swap,
        decisions_json, section_heading
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, verse_rows)

    cur.execute("""
    INSERT INTO verses_fts (rowid, verse_id, book_code, chapter, verse, rv_text_clean, lv_text_clean)
    SELECT rowid, verse_id, book_code, chapter, verse, rv_text_clean, lv_text_clean FROM verses;
    """)
    conn.commit()

    # Insert notes
    print(f"Inserting {len(all_notes)} footnotes and cross-references...")
    cur.executemany("""
    INSERT INTO notes_and_xrefs (
        verse_id, source_version, note_type, category, caller_ref, content
    ) VALUES (?, ?, ?, ?, ?, ?)
    """, all_notes)
    conn.commit()
    print("Scripture verses and notes ingested successfully.")


def main():
    DB_DIR.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        print(f"Removing existing database at {DB_PATH}")
        DB_PATH.unlink()

    print(f"Building SQLite database at {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")

    create_schema(conn)
    populate_formats_reference(conn)
    ingest_word_tables(conn)
    ingest_bibles(conn)

    print("Optimizing SQLite database...")
    conn.execute("PRAGMA optimize;")
    conn.commit()
    conn.close()

    db_size_mb = DB_PATH.stat().st_size / (1024 * 1024)
    print(f"Database build complete! Final size: {db_size_mb:.2f} MB")


if __name__ == "__main__":
    main()
