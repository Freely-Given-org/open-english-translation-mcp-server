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
    ("≈", "line_start", "Synonymous Parallelism", "Second line of Hebrew poetic doublet repeating thought", r"\q1 ≈Yahweh gives comfort"),
    ("^", "line_start", "Antithetic Parallelism", "Second line of Hebrew poetic doublet stating contrast", r"\q1 ^but Israel will fall"),
    ("→", "line_start", "Synthetic Parallelism", "Second line of Hebrew poetic doublet reaching conclusion", r"\q1 →and he answered"),
    ("⇔", "verse_start", "Order Swapped", "Swapped first and second halves of verse for English naturalness", r"\v 10 ⇔The girls did..."),
]


def clean_esfm_text(text: str) -> str:
    """Strip ESFM tags to produce clean, natural English reading text."""
    # Remove footnotes and cross-refs
    text = re.sub(r'\\f\s*\+\s*\\fr.*?\\ft\s*(.*?)\\f\*', '', text)
    text = re.sub(r'\\x\s*\+\s*\\xo.*?\\xt\s*(.*?)\\x\*', '', text)
    # Remove \add markers and their code characters
    text = re.sub(r'\\add\s*([+=<>≡&@*#%^≈\?]*)(.*?)\\add\*', r'\2', text)
    # Remove \untr markers (in LV, untranslated words like 'the', 'DOM')
    text = re.sub(r'\\untr\s*(.*?)\\untr\*', r'\1', text)
    # Remove \nd, \wj, \em, \bd markers
    text = re.sub(r'\\nd\s*(.*?)\\nd\*', r'\1', text)
    text = re.sub(r'\\wj\s*(.*?)\\wj\*', r'\1', text)
    text = re.sub(r'\\em\s*(.*?)\\em\*', r'\1', text)
    text = re.sub(r'\\bd\s*(.*?)\\bd\*', r'\1', text)
    # Remove word link pipes: word¦12345 -> word
    text = re.sub(r'¦\d+', '', text)
    # Remove underscores connecting multi-word glosses: in_order_that -> in order that
    text = text.replace('_', ' ')
    # Normalize spaces and punctuation
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def annotate_esfm_text(text: str, version: str = "RV") -> str:
    """Format ESFM text with human-readable markdown annotations showing translation decisions."""
    # Strip footnotes and cross refs from inline text
    text = re.sub(r'\\f\s*\+\s*\\fr.*?\\ft\s*(.*?)\\f\*', '', text)
    text = re.sub(r'\\x\s*\+\s*\\xo.*?\\xt\s*(.*?)\\x\*', '', text)
    
    # Process \add with decision symbols
    def replace_add(m):
        code = m.group(1).strip()
        inner = m.group(2).strip()
        if not code:
            return f"[{inner}]"
        return f"[{code}:{inner}]"

    text = re.sub(r'\\add\s*([+=<>≡&@*#%^≈\?]*)(.*?)\\add\*', replace_add, text)
    # Process \untr
    text = re.sub(r'\\untr\s*(.*?)\\untr\*', r'{\1}', text)
    # Strip word link IDs
    text = re.sub(r'¦\d+', '', text)
    text = re.sub(r'\\nd\s*(.*?)\\nd\*', r'\1', text)
    text = re.sub(r'\\wj\s*(.*?)\\wj\*', r'\1', text)
    text = re.sub(r'\\em\s*(.*?)\\em\*', r'\1', text)
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

    # Find all \add occurrences
    for m in re.finditer(r'\\add\s*([+=<>≡&@*#%^≈\?]*)(.*?)\\add\*', raw_text):
        code = m.group(1).strip()
        content = re.sub(r'¦\d+', '', m.group(2)).replace('_', ' ').strip()
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
            "?": "Uncertain / Probable Reading"
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

    book_code = None
    m_id = re.search(r'\\id\s+([A-Z0-9]{3})', content)
    if m_id:
        book_code = m_id.group(1)
    else:
        fname = filepath.stem
        book_code = fname.replace(f"OET-{version}_", "")

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
            c_str = line[3:].split()[0]
            try:
                current_chapter = int(c_str)
            except ValueError:
                pass
        elif line.startswith(r'\s1 ') or line.startswith(r'\s '):
            heading = line.split(maxsplit=1)[1].strip()
            current_section = heading
        elif line.startswith(r'\v '):
            parts = line[3:].split(maxsplit=1)
            if not parts:
                continue
            v_num_str = parts[0]
            v_text_raw = parts[1] if len(parts) > 1 else ""

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
        rv_text,
        lv_text
    );

    CREATE VIRTUAL TABLE lexicon_fts USING fts5(
        lemma_key,
        lang UNINDEXED,
        lemma,
        lemma_display,
        strongs,
        primary_gloss,
        glosses
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

    cur.executemany("""
    INSERT INTO lexicon_fts (
        lemma_key, lang, lemma, lemma_display, strongs, primary_gloss, glosses
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, lex_fts_rows)
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
    for b_code, (eng_name, def_oet, testm, canon_ord) in BOOK_NAMES.items():
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

        fts_rows.append((
            v_id,
            book_code,
            chapter,
            verse_num,
            rv_clean or "",
            lv_clean or ""
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

    cur.executemany("""
    INSERT INTO verses_fts (
        verse_id, book_code, chapter, verse, rv_text, lv_text
    ) VALUES (?, ?, ?, ?, ?, ?)
    """, fts_rows)
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
