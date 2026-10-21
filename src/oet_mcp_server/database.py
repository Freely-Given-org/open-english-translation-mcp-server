"""
src/oet_mcp_server/database.py

SQLite connection management and query engine for the Open English Translation (OET).
"""

import os
import re
import json
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager
from collections import Counter

from .grammar import decode_morphology
from .lexical import SCHEMA_VERSION, normalize_alias

from .models import (
    VerseModel,
    PassageResponse,
    WordModel,
    NoteItem,
    LexiconEntry,
    ComparisonDiffItem,
    DecisionItem,
    CatalogBook,
)

# Standard default DB location
DEFAULT_DB_PATH = Path(__file__).resolve().parent / "data" / "oet_corpus.db"

# Canonical mappings for standard & alternate book names
BOOK_ALIASES = {
    # OT
    "GEN": "GEN", "GENESIS": "GEN", "GN": "GEN",
    "EXO": "EXO", "EXODUS": "EXO", "EX": "EXO",
    "LEV": "LEV", "LEVITICUS": "LEV", "LV": "LEV",
    "NUM": "NUM", "NUMBERS": "NUM", "NM": "NUM",
    "DEU": "DEU", "DEUTERONOMY": "DEU", "DT": "DEU",
    "JOS": "JOS", "JOSHUA": "JOS", "YEHOSHUA": "JOS",
    "JDG": "JDG", "JUDGES": "JDG", "JG": "JDG",
    "RUT": "RUT", "RUTH": "RUT",
    "SA1": "SA1", "1SAM": "SA1", "1SAMUEL": "SA1", "1 SAM": "SA1", "1 SAMUEL": "SA1", "1 SHEMUEL": "SA1", "1SA": "SA1",
    "SA2": "SA2", "2SAM": "SA2", "2SAMUEL": "SA2", "2 SAM": "SA2", "2 SAMUEL": "SA2", "2 SHEMUEL": "SA2", "2SA": "SA2",
    "KI1": "KI1", "1KI": "KI1", "1KINGS": "KI1", "1 KI": "KI1", "1 KINGS": "KI1", "1KGS": "KI1",
    "KI2": "KI2", "2KI": "KI2", "2KINGS": "KI2", "2 KI": "KI2", "2 KINGS": "KI2", "2KGS": "KI2",
    "CH1": "CH1", "1CH": "CH1", "1CHRONICLES": "CH1", "1 CHR": "CH1", "1 CHRONICLES": "CH1",
    "CH2": "CH2", "2CH": "CH2", "2CHRONICLES": "CH2", "2 CHR": "CH2", "2 CHRONICLES": "CH2",
    "EZR": "EZR", "EZRA": "EZR",
    "NEH": "NEH", "NEHEMIAH": "NEH",
    "EST": "EST", "ESTHER": "EST",
    "JOB": "JOB", "IYYOV": "JOB",
    "PSA": "PSA", "PSALMS": "PSA", "PSALM": "PSA", "PS": "PSA", "SONGS": "PSA",
    "PRO": "PRO", "PROVERBS": "PRO", "PR": "PRO", "PROV": "PRO",
    "ECC": "ECC", "ECCLESIASTES": "ECC", "QOH": "ECC",
    "SONG OF SONGS": "SNG", "SONGOFSONGS": "SNG", "SNG": "SNG", "SONG": "SNG", "SONG OF SOLOMON": "SNG", "CANTICLES": "SNG", "SOS": "SNG",
    "ISA": "ISA", "ISAIAH": "ISA", "YESHAYAH": "ISA", "IS": "ISA",
    "JER": "JER", "JEREMIAH": "JER", "YERMEYAH": "JER", "JR": "JER",
    "LAM": "LAM", "LAMENTATIONS": "LAM", "LM": "LAM",
    "EZE": "EZE", "EZEKIEL": "EZE", "YEHEZKEL": "EZE", "EZK": "EZE",
    "DAN": "DAN", "DANIEL": "DAN", "DN": "DAN",
    "HOS": "HOS", "HOSEA": "HOS",
    "JOL": "JOL", "JOEL": "JOL", "YOEL": "JOL", "JL": "JOL",
    "AMO": "AMO", "AMOS": "AMO", "AMOTS": "AMO", "AM": "AMO",
    "OBA": "OBA", "OBADIAH": "OBA", "OVADYAH": "OBA", "OB": "OBA",
    "JNA": "JNA", "JONAH": "JNA", "YONAH": "JNA", "JON": "JNA", "YNA": "JNA",
    "MIC": "MIC", "MICAH": "MIC", "MIKAH": "MIC", "MC": "MIC",
    "NAH": "NAH", "NAHUM": "NAH", "NAM": "NAH",
    "HAB": "HAB", "HABAKKUK": "HAB", "HAVAKKUK": "HAB", "HB": "HAB",
    "ZEP": "ZEP", "ZEPHANIAH": "ZEP", "TSEFANYAH": "ZEP", "ZP": "ZEP",
    "HAG": "HAG", "HAGGAI": "HAG", "HG": "HAG",
    "ZEC": "ZEC", "ZECHARIAH": "ZEC", "ZEKARYAH": "ZEC", "ZC": "ZEC",
    "MAL": "MAL", "MALACHI": "MAL", "MALAKI": "MAL", "ML": "MAL",
    # NT
    "MAT": "MAT", "MATTHEW": "MAT", "MT": "MAT", "MATT": "MAT",
    "MRK": "MRK", "MARK": "MRK", "MK": "MRK",
    "LUK": "LUK", "LUKE": "LUK", "LK": "LUK",
    "JHN": "JHN", "JOHN": "JHN", "YOHAN": "JHN", "JN": "JHN", "YHN": "JHN",
    "ACT": "ACT", "ACTS": "ACT", "AC": "ACT",
    "ROM": "ROM", "ROMANS": "ROM", "RM": "ROM",
    "CO1": "CO1", "1COR": "CO1", "1CORINTHIANS": "CO1", "1 COR": "CO1", "1 CORINTHIANS": "CO1", "1CO": "CO1",
    "CO2": "CO2", "2COR": "CO2", "2CORINTHIANS": "CO2", "2 COR": "CO2", "2 CORINTHIANS": "CO2", "2CO": "CO2",
    "GAL": "GAL", "GALATIANS": "GAL", "GL": "GAL",
    "EPH": "EPH", "EPHESIANS": "EPH", "EP": "EPH",
    "PHP": "PHP", "PHILIPPIANS": "PHP", "PHIL": "PHP",
    "COL": "COL", "COLOSSIANS": "COL", "CL": "COL",
    "TH1": "TH1", "1THESS": "TH1", "1THESSALONIANS": "TH1", "1 TH": "TH1", "1 THESSALONIANS": "TH1", "1TH": "TH1",
    "TH2": "TH2", "2THESS": "TH2", "2THESSALONIANS": "TH2", "2 TH": "TH2", "2 THESSALONIANS": "TH2", "2TH": "TH2",
    "TI1": "TI1", "1TIM": "TI1", "1TIMOTHY": "TI1", "1 TIM": "TI1", "1 TIMOTHY": "TI1", "1TI": "TI1",
    "TI2": "TI2", "2TIM": "TI2", "2TIMOTHY": "TI2", "2 TIM": "TI2", "2 TIMOTHY": "TI2", "2TI": "TI2",
    "TIT": "TIT", "TITUS": "TIT", "TT": "TIT",
    "PHM": "PHM", "PHILEMON": "PHM", "PHLM": "PHM",
    "HEB": "HEB", "HEBREWS": "HEB", "HB": "HEB",
    "JAM": "JAM", "JAMES": "JAM", "YACOB": "JAM", "JAS": "JAM", "YAC": "JAM",
    "PE1": "PE1", "1PET": "PE1", "1PETER": "PE1", "1 PET": "PE1", "1 PETER": "PE1", "1PE": "PE1",
    "PE2": "PE2", "2PET": "PE2", "2PETER": "PE2", "2 PET": "PE2", "2 PETER": "PE2", "2PE": "PE2",
    "JN1": "JN1", "1JOHN": "JN1", "1YOHAN": "JN1", "1 JN": "JN1", "1 JOHN": "JN1", "1 YHN": "JN1", "1YHN": "JN1",
    "JN2": "JN2", "2JOHN": "JN2", "2YOHAN": "JN2", "2 JN": "JN2", "2 JOHN": "JN2", "2 YHN": "JN2", "2YHN": "JN2",
    "JN3": "JN3", "3JOHN": "JN3", "3YOHAN": "JN3", "3 JN": "JN3", "3 JOHN": "JN3", "3 YHN": "JN3", "3YHN": "JN3",
    "JDE": "JDE", "JUDE": "JDE", "YUDAS": "JDE", "JUD": "JDE", "YUD": "JDE",
    "REV": "REV", "REVELATION": "REV", "APOCALYPSE": "REV", "RV": "REV",
    # Deuterocanonical (apocrypha). "JUD" is deliberately not reused for Judith,
    # since it already resolves to Jude.
    "TOB": "TOB", "TOBIT": "TOB", "TB": "TOB",
    "JDT": "JDT", "JUDITH": "JDT", "JUTH": "JDT",
    "ESG": "ESG", "ESTHERGREEK": "ESG", "ADDITIONSTOESTHER": "ESG", "ADDITIONS TO ESTHER": "ESG",
    "ES1": "ES1", "1ESDRAS": "ES1", "1ESD": "ES1", "ESD1": "ES1", "1 ESDRAS": "ES1",
    "ES2": "ES2", "2ESDRAS": "ES2", "2ESD": "ES2", "ESD2": "ES2", "2 ESDRAS": "ES2",
    "DAG": "DAG", "DANIELGREEK": "DAG", "ADDITIONSTODANIEL": "DAG", "SUSANNA": "DAG",
    "BELANDTHEDRAGON": "DAG", "BEL AND THE DRAGON": "DAG", "ADDITIONS TO DANIEL": "DAG",
    "BAR": "BAR", "BARUCH": "BAR", "BR": "BAR",
    "MAN": "MAN", "PRAYEROFMANASSES": "MAN", "PRAYER OF MANASSES": "MAN",
    "PS2": "PS2", "PSALM151": "PS2", "PSALM 151": "PS2",
    "WIS": "WIS", "WISDOMOFSOLOMON": "WIS", "WISDOM": "WIS", "WISDOM OF SOLOMON": "WIS",
    "SIR": "SIR", "SIRACH": "SIR", "ECCLESIASTICUS": "SIR",
    "MA1": "MA1", "1MACCABEES": "MA1", "1MAC": "MA1", "MACC1": "MA1", "1 MACCABEES": "MA1",
    "MA2": "MA2", "2MACCABEES": "MA2", "2MAC": "MA2", "MACC2": "MA2", "2 MACCABEES": "MA2",
    "MA3": "MA3", "3MACCABEES": "MA3", "3MAC": "MA3", "MACC3": "MA3", "3 MACCABEES": "MA3",
    "MA4": "MA4", "4MACCABEES": "MA4", "4MAC": "MA4", "MACC4": "MA4", "4 MACCABEES": "MA4",
}


class OETDatabase:
    """Thread-safe SQLite database manager for OET."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"OET database not found at {self.db_path}. "
                f"Please run 'python3 scripts/build_db.py' to generate it."
            )

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(f"{self.db_path.resolve().as_uri()}?mode=ro", uri=True, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        if conn.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
            conn.close()
            raise RuntimeError("Corpus schema is outdated. Rebuild with scripts/build_db.py.")
        try:
            yield conn
        finally:
            conn.close()

    def normalize_book(self, book_str: str) -> Optional[str]:
        """Normalize any book name/abbreviation into standard 3-letter uppercase code."""
        cleaned = re.sub(r'[^A-Za-z0-9]', '', book_str).upper()
        if cleaned in BOOK_ALIASES:
            return BOOK_ALIASES[cleaned]
        spaced = re.sub(r'\s+', ' ', book_str).strip().upper()
        if spaced in BOOK_ALIASES:
            return BOOK_ALIASES[spaced]
        return None

    def parse_reference(self, ref_str: str) -> Tuple[Optional[str], int, int, int, int]:
        """
        Parse reference string into (book_code, start_chapter, start_verse, end_chapter, end_verse).
        """
        ref_str = ref_str.strip()
        whole = self.normalize_book(ref_str)
        if whole and (not re.search(r"\s\d", ref_str) or ref_str.upper() in BOOK_ALIASES):
            return whole, 1, 1, 999, 999
        m_dot = re.match(r'^([A-Za-z0-9]{3})[._](\d+)[:.](\d+)(?:[-–](\d+))?$', ref_str)
        if m_dot:
            b_code = self.normalize_book(m_dot.group(1))
            ch = int(m_dot.group(2))
            v_start = int(m_dot.group(3))
            v_end = int(m_dot.group(4)) if m_dot.group(4) else v_start
            return b_code, ch, v_start, ch, v_end

        m_full = re.match(
            r'^(.+?)\s*(\d+)(?:[:.](\d+))?(?:[-–](\d+)(?:[:.](\d+))?)?$',
            ref_str
        )
        if not m_full:
            b_code = self.normalize_book(ref_str)
            if b_code:
                return b_code, 1, 1, 999, 999
            return None, 0, 0, 0, 0

        b_name, ch1_str, v1_str, end_p1, end_p2 = m_full.groups()
        # A bare canonical code such as "SA1" or "PS2" also matches the "book + chapter"
        # shape (as "SA" + chapter 1, or "PS" + chapter 2). When the whole string names a
        # different book, read it as a book and return the whole of it.
        if re.fullmatch(r'[A-Za-z0-9]{3}', ref_str):
            whole_code = self.normalize_book(ref_str)
            if whole_code and whole_code != self.normalize_book(b_name):
                return whole_code, 1, 1, 999, 999
        b_code = self.normalize_book(b_name) or self.normalize_book(ref_str)
        if not b_code:
            return None, 0, 0, 0, 0

        start_ch = int(ch1_str)
        if v1_str is None:
            if end_p1 is None:
                return b_code, start_ch, 1, start_ch, 999
            else:
                end_ch = int(end_p1)
                return b_code, start_ch, 1, end_ch, 999

        start_v = int(v1_str)
        if end_p1 is None:
            return b_code, start_ch, start_v, start_ch, start_v

        if end_p2 is None:
            end_v = int(end_p1)
            return b_code, start_ch, start_v, start_ch, end_v
        else:
            end_ch = int(end_p1)
            end_v = int(end_p2)
            return b_code, start_ch, start_v, end_ch, end_v

    def get_passage(
        self,
        reference: str,
        version: str = "parallel",
        include_notes: bool = True,
        include_words: bool = False,
        include_raw: bool = False,
        format: str = "markdown",
        show_decision_codes: bool = False,
        include_variants: bool = False,
        include_structure: bool = False,
        include_alignment: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> PassageResponse:
        """
        Retrieves verses for a given scripture reference in RV, LV, parallel, or interlinear mode.

        With include_raw, each verse also carries the original ESFM markup in rv_esfm /
        lv_esfm; the default response carries only the cleaned and annotated text.
        """
        self._validate_page(limit, offset)
        b_code, start_ch, start_v, end_ch, end_v = self.parse_reference(reference)
        if not b_code:
            raise ValueError(f"Could not recognize biblical reference: '{reference}'")

        if min(start_ch, start_v, end_ch, end_v) < 1 or (start_ch, start_v) > (end_ch, end_v):
            raise ValueError("Reference must use positive chapter/verse numbers and an ascending range.")
        if version not in {"rv", "lv", "parallel", "interlinear"}:
            raise ValueError("version must be rv, lv, parallel, or interlinear")
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM books WHERE book_code = ?", (b_code,))
            book_row = cur.fetchone()
            if not book_row:
                raise ValueError(f"Book code '{b_code}' not found in database.")

            if not self.normalize_book(reference):
                verse_specified = bool(re.search(r"[:.]\d+", reference))
                for chapter, verse in ((start_ch, start_v), (end_ch, end_v)):
                    bounds = cur.execute("SELECT min(verse), max(verse_end) FROM verses WHERE book_code=? AND chapter=?",
                                         (b_code, chapter)).fetchone()
                    if bounds[0] is None or (verse_specified and not bounds[0] <= verse <= bounds[1]):
                        raise ValueError(f"Reference endpoint {b_code} {chapter}:{verse} is unavailable; check chapter and verse bounds.")

            if start_ch == end_ch:
                cur.execute("""
                SELECT * FROM verses
                WHERE book_code = ? AND chapter = ? AND verse_end >= ? AND verse <= ?
                ORDER BY verse ASC, verse_end ASC, verse_id ASC
                """, (b_code, start_ch, start_v, end_v))
            else:
                cur.execute("""
                SELECT * FROM verses
                WHERE book_code = ? AND (
                    (chapter = ? AND verse_end >= ?) OR
                    (chapter > ? AND chapter < ?) OR
                    (chapter = ? AND verse <= ?)
                )
                ORDER BY chapter ASC, verse ASC, verse_end ASC, verse_id ASC
                """, (b_code, start_ch, start_v, start_ch, end_ch, end_ch, end_v))

            verse_rows = cur.fetchall()
            if not verse_rows:
                raise ValueError(f"No verses available for '{reference}'. No substitute passage was returned.")

            total_verses = len(verse_rows)
            verse_rows = verse_rows[offset:offset + limit]
            provenance = self._provenance(conn)
            sources = {r["source_version"]: json.loads(r["metadata_json"]) for r in conn.execute("SELECT * FROM book_metadata WHERE book_code=?", (b_code,))}
            provenance["book_sources"] = {version: {k: m[k] for k in ("source_file", "sha256", "source_declaration", "source_notes")} for version, m in sources.items()}
            verses_list = []
            total_footnotes = 0
            total_xrefs = 0

            for v in verse_rows:
                v_id = v["verse_id"]
                notes_list = []
                if include_notes:
                    cur.execute("SELECT * FROM notes_and_xrefs WHERE verse_id = ?", (v_id,))
                    for nr in cur.fetchall():
                        n_item = NoteItem(
                            verse_id=nr["verse_id"],
                            source_version=nr["source_version"],
                            note_type=nr["note_type"],
                            category=nr["category"],
                            caller_ref=nr["caller_ref"],
                            content=nr["content"]
                        )
                        notes_list.append(n_item)
                        if nr["note_type"] == "footnote":
                            total_footnotes += 1
                        elif nr["note_type"] == "xref":
                            total_xrefs += 1

                words_list = []
                if include_words or version.lower() == "interlinear":
                    cur.execute("""
                    SELECT * FROM words
                    WHERE book_code = ? AND chapter = ? AND verse = ? AND (is_selected = 1 OR ?)
                    ORDER BY word_seq ASC
                    """, (b_code, v["chapter"], v["verse"], include_variants))
                    for wr in cur.fetchall():
                        words_list.append(WordModel(
                            word_link_id=wr["word_link_id"],
                            ref=wr["ref_str"],
                            original_word=wr["original_word"] or "",
                            sr_lemma=wr["sr_lemma"],
                            original_lemma=wr["original_lemma"],
                            strongs=wr["strongs"],
                            role=wr["role"],
                            morphology=wr["morphology"],
                            vlt_gloss=wr["vlt_gloss"],
                            oet_gloss=wr["oet_gloss"],
                            contextual_gloss=wr["contextual_gloss"],
                            morpheme_glosses=wr["morpheme_glosses"],
                            tags=wr["tags"],
                            lang=wr["lang"], source_status=wr["source_status"],
                            is_selected=bool(wr["is_selected"]), source_strongs=wr["source_strongs"],
                            strongs_standard=json.loads(wr["strongs_standard_json"]),
                            lemmas=self._word_lemmas(conn, wr["word_link_id"]),
                            grammar=decode_morphology(wr["morphology"], wr["lang"], wr["role"])
                        ))

                decisions = []
                if v["decisions_json"]:
                    try:
                        raw_decs = json.loads(v["decisions_json"])
                        for d in raw_decs:
                            decisions.append(DecisionItem(
                                source_version=d.get("source_version"),
                                source_span=d.get("source_span"),
                                code=d.get("code", ""),
                                type=d.get("type", "Added Information"),
                                text=d.get("text"),
                                description=d.get("description")
                            ))
                    except Exception:
                        pass

                rv_txt = v["rv_text_annotated"] if show_decision_codes else v["rv_text_clean"]
                lv_txt = v["lv_text_annotated"] if show_decision_codes else v["lv_text_clean"]

                verses_list.append(VerseModel(
                    verse_id=v_id,
                    book_code=b_code,
                    chapter=v["chapter"],
                    verse=v["verse"],
                    verse_label=v["verse_label"],
                    section_heading=v["section_heading"],
                    rv_text=rv_txt,
                    lv_text=lv_txt,
                    rv_annotated=v["rv_text_annotated"],
                    lv_annotated=v["lv_text_annotated"],
                    rv_esfm=v["rv_text_raw"] if include_raw else None,
                    lv_esfm=v["lv_text_raw"] if include_raw else None,
                    decisions=decisions,
                    has_missing_verse=bool(v["has_missing_verse_flag"]),
                    has_poetry_parallel=bool(v["has_poetry_parallel"]),
                    has_order_swap=bool(v["has_order_swap"]),
                    notes=notes_list,
                    words=words_list,
                    structure=json.loads(v["structure_json"]) if include_structure else {},
                    alignments=[dict(r) for r in conn.execute("SELECT source_version,word_link_id,word_num,text,source_start,source_end FROM word_alignments WHERE verse_id=? ORDER BY source_version,source_start", (v_id,))] if include_alignment else [],
                    availability={ver: ("available" if v[f"{ver.lower()}_text_clean"] is not None else ("no matching source segment; check other verse groupings" if ver in sources else "version not available for this book")) for ver in ("RV", "LV")},
                    source_url=f"https://freely-given.org/OBD/par/{b_code}/C{v['chapter']}V{v['verse']}.htm"
                ))

            return PassageResponse(
                reference=reference,
                book_code=b_code,
                english_name=book_row["english_name"],
                oet_name=book_row["oet_name"] or book_row["english_name"],
                version=version,
                verses_count=len(verses_list),
                verses=verses_list,
                footnotes_count=total_footnotes,
                cross_refs_count=total_xrefs,
                total_verses=total_verses, offset=offset,
                next_offset=offset + len(verse_rows) if offset + len(verse_rows) < total_verses else None,
                provenance=provenance
            )

    def compare_passage(self, reference: str, passage: Optional[PassageResponse] = None) -> List[ComparisonDiffItem]:
        """
        Isolates and computes detailed translation divergencies between OET-RV and OET-LV.
        """
        passage = passage or self.get_passage(reference, version="parallel", show_decision_codes=True)
        diff_items = []

        for v in passage.verses:
            rv_raw = v.rv_annotated or ""
            lv_raw = v.lv_annotated or ""

            added_lv = re.findall(r'\[(?:[+=<>≡&@*#%^≈?!]*:)?([^\]]+)\]', lv_raw)
            untranslated_lv = re.findall(r'\{([^}]+)\}', lv_raw)

            notes = []
            if v.has_order_swap:
                notes.append("Clause ordering was inverted (⇔) for modern discourse fluency.")
            if v.has_poetry_parallel:
                notes.append("Hebrew poetic parallelism (≈) marked in Readers' Version.")
            if v.has_missing_verse:
                notes.append("The source marks omitted text (◘); consult the translator notes for its textual basis.")

            diff_items.append(ComparisonDiffItem(
                verse_id=v.verse_id,
                rv_text=v.rv_text or "",
                lv_text=v.lv_text or "",
                added_words_lv=added_lv,
                untranslated_words_lv=untranslated_lv,
                translation_decisions_rv=[d for d in v.decisions if d.source_version == "RV"],
                syntactic_notes=" ".join(notes) if notes else None
            ))

        return diff_items

    def lookup_word(self, word_id: str) -> Optional[Dict[str, Any]]:
        """
        Lookup a specific word link token by ID (e.g. 'JHNc1v1w5' or 'JHN_1:1w5').
        """
        cleaned_id = word_id.strip()
        m_c = re.fullmatch(r'([A-Za-z0-9]{3})c(\d+)v(\d+)w(\d+)', cleaned_id, re.IGNORECASE)
        if m_c:
            b, c, v, w = m_c.groups()
            cleaned_id = f"{b.upper()}_{c}:{v}w{w}"

        with self.get_connection() as conn:
            numeric = re.fullmatch(r"(NT|OT):(\d+)", cleaned_id, re.IGNORECASE)
            if numeric:
                row = conn.execute("SELECT word_link_id FROM words WHERE word_num=? AND (lang='greek')=?", (int(numeric[2]), numeric[1].upper() == "NT")).fetchone()
                if not row:
                    return None
                cleaned_id = row[0]
            cur = conn.cursor()
            cur.execute("""
            SELECT * FROM words WHERE word_link_id = ? OR ref_str = ?
            """, (cleaned_id, cleaned_id))
            row = cur.fetchone()
            if not row:
                return None

            data = dict(row)
            data["strongs_standard"] = json.loads(data.pop("strongs_standard_json"))
            data["is_selected"] = bool(data["is_selected"])
            data["lemmas"] = self._word_lemmas(conn, data["word_link_id"])
            data["grammar"] = decode_morphology(data["morphology"], data["lang"], data["role"])
            data["alignments"] = [dict(r) for r in conn.execute("SELECT verse_id,source_version,text,source_start,source_end FROM word_alignments WHERE word_link_id=? ORDER BY source_version,source_start", (data["word_link_id"],))]
            data["provenance"] = self._provenance(conn)
            cur.execute("SELECT rv_text_clean, lv_text_clean FROM verses WHERE verse_id = ?", (f"{data['book_code']}.{data['chapter']}.{data['verse']}",))
            v_row = cur.fetchone()
            if v_row:
                data["verse_rv"] = v_row["rv_text_clean"]
                data["verse_lv"] = v_row["lv_text_clean"]

            lexical = [lemma for lemma in data["lemmas"] if lemma["strongs"]] or data["lemmas"]
            data["lexicon_entries"] = [self._lexicon_model(conn.execute("SELECT * FROM lexicon WHERE lemma_key=?", (key,)).fetchone()).model_dump()
                                       for key in dict.fromkeys(lemma["lemma_key"] for lemma in lexical)]
            if len(data["lexicon_entries"]) == 1:
                data["lexicon"] = data["lexicon_entries"][0]

            return data

    @staticmethod
    def _word_lemmas(conn, word_id):
        return [dict(r) for r in conn.execute("""
            SELECT wl.position, l.lemma_key, l.lemma, l.lang, wl.strongs
            FROM word_lemmas wl JOIN lexicon l USING(lemma_key)
            WHERE wl.word_link_id=? ORDER BY wl.position
        """, (word_id,))]

    @staticmethod
    def _resolve_lemmas(conn, query, lang="auto"):
        q = normalize_alias(query)
        kind = None
        for prefix in ("strongs_ext:", "strongs:"):
            if q.startswith(prefix):
                kind, q = prefix[:-1], q[len(prefix):]
                break
        rows = conn.execute("""SELECT DISTINCT l.lemma_key, a.kind FROM lexicon_aliases a
                               JOIN lexicon l USING(lemma_key)
                               WHERE a.alias=? AND (?='auto' OR l.lang=?)
                               AND (? IS NULL OR a.kind=?)""", (q, lang, lang, kind, kind)).fetchall()
        by_kind = {}
        for r in rows:
            by_kind.setdefault(r["kind"], set()).add(r["lemma_key"])
        if kind is None and "strongs" in by_kind and "strongs_ext" in by_kind and by_kind["strongs"] != by_kind["strongs_ext"]:
            raise ValueError(f"Ambiguous identifier {query!r}; use strongs:{query} for the standard number or strongs_ext:{query} for the SR-GNT identifier.")
        return sorted({r["lemma_key"] for r in rows})

    @staticmethod
    def _lexicon_model(row):
        return LexiconEntry(
            lemma_key=row["lemma_key"], lang=row["lang"], lemma=row["lemma"],
            lemma_display=row["lemma_display"], strongs=row["strongs"],
            strongs_ids=json.loads(row["strongs_ids_json"]), primary_gloss=row["primary_gloss"],
            total_occurrences=row["total_occurrences"],
            unused_variant_occurrences=row["unused_variant_occurrences"],
            unglossed_occurrences=row["total_occurrences"] - sum(json.loads(row["gloss_distribution_json"]).values()),
            gloss_distribution=json.loads(row["gloss_distribution_json"]),
            first_occurrences_refs=row["first_occurrences_refs"].split(", ") if row["first_occurrences_refs"] else [])

    def search_lemma(self, lemma_or_strongs: str, testament: str = "all", limit: int = 30,
                     include_variants: bool = False, book: Optional[str] = None,
                     offset: int = 0, sampling: str = "representative") -> Dict[str, Any]:
        """Retrieve scoped word occurrences, with exact totals and bounded samples."""
        self._validate_page(limit, offset)
        if testament.upper() not in {"ALL", "OT", "NT"}:
            raise ValueError("testament must be all, OT, or NT")
        if sampling not in {"representative", "canonical"}:
            raise ValueError("sampling must be representative or canonical")
        code = self.normalize_book(book) if book else None
        if book and not code:
            raise ValueError(f"Unknown book: {book}")
        with self.get_connection() as conn:
            keys = self._resolve_lemmas(conn, lemma_or_strongs)
            result = dict(query=lemma_or_strongs, testament_filter=testament.upper(), book=code,
                          include_variants=include_variants, sampling=sampling, offset=offset,
                          count_scope="Matching source word occurrences; glosses are from OET-LV word tables, not RV",
                          total_matches=0, total_found_in_sample=0, next_offset=None,
                          gloss_distribution_in_sample={}, occurrences=[], resolved_lemma_keys=keys)
            if not keys:
                return result
            placeholders = ",".join("?" for _ in keys)
            sql = f"""SELECT w.*, b.canonical_order FROM words w JOIN books b USING(book_code)
                      WHERE EXISTS (SELECT 1 FROM word_lemmas wl WHERE wl.word_link_id=w.word_link_id
                                    AND wl.lemma_key IN ({placeholders}))
                      AND (w.is_selected=1 OR ?) AND (?='ALL' OR b.testament=?)
                      AND (? IS NULL OR w.book_code=?)"""
            params = [*keys, include_variants, testament.upper(), testament.upper(), code, code]
            result["total_matches"] = conn.execute(f"SELECT count(*) FROM ({sql})", params).fetchone()[0]
            # Round-robin across books gives broad coverage; canonical order is available for exhaustive paging.
            order = "canonical_order, chapter, verse, word_seq"
            if sampling == "representative":
                sql = f"SELECT *, row_number() OVER (PARTITION BY book_code ORDER BY chapter,verse,word_seq) AS book_position FROM ({sql})"
                order = "book_position, " + order
            rows = conn.execute(sql + f" ORDER BY {order} LIMIT ? OFFSET ?", [*params, limit, offset]).fetchall()
            counter = Counter()
            for row in rows:
                context = conn.execute("SELECT rv_text_clean,lv_text_clean FROM verses WHERE book_code=? AND chapter=? AND verse=? ORDER BY verse_id LIMIT 1",
                                       (row["book_code"],row["chapter"],row["verse"])).fetchone()
                counter[row["oet_gloss"] or ""] += 1
                result["occurrences"].append(dict(ref=f"{row['book_code']} {row['chapter']}:{row['verse']} (word {row['word_seq']})",
                    word_link_id=row["word_link_id"], original_word=row["original_word"], morphology=row["morphology"],
                    oet_gloss=row["oet_gloss"], is_selected=bool(row["is_selected"]), source_status=row["source_status"],
                    rv_text=context[0] if context else None, lv_text=context[1] if context else None))
            result["total_found_in_sample"] = len(rows)
            result["gloss_distribution_in_sample"] = dict(counter)
            if offset + len(rows) < result["total_matches"]:
                result["next_offset"] = offset + len(rows)
            if len(keys) == 1:
                lex = self._lexicon_model(conn.execute("SELECT * FROM lexicon WHERE lemma_key=?", (keys[0],)).fetchone())
                result["lexicon_info"] = dict(lang=lex.lang, lemma=lex.lemma, lemma_display=lex.lemma_display,
                    strongs=lex.strongs, primary_gloss=lex.primary_gloss,
                    total_canonical_occurrences=lex.total_occurrences,
                    unused_variant_occurrences=lex.unused_variant_occurrences,
                    canonical_gloss_distribution=lex.gloss_distribution,
                    count_scope=lex.count_scope + "; entire corpus, independent of search filters")
            return result

    def get_lexicon_entry(self, query: str, lang: str = "auto") -> Optional[LexiconEntry]:
        if lang not in {"auto", "greek", "hebrew", "aramaic"}:
            raise ValueError("lang must be auto, greek, hebrew, or aramaic")
        with self.get_connection() as conn:
            keys = self._resolve_lemmas(conn, query, lang)
            if not keys:
                return None
            if len(keys) > 1:
                raise ValueError(f"Multiple lemma entries match {query!r}; use a lemma key: {', '.join(keys)}. search_lemma can retrieve their combined occurrences.")
            return self._lexicon_model(conn.execute("SELECT * FROM lexicon WHERE lemma_key=?", (keys[0],)).fetchone())

    @staticmethod
    def _validate_page(limit, offset=0):
        if not 1 <= limit <= 100 or offset < 0:
            raise ValueError("limit must be 1–100 and offset must be nonnegative")

    def search_text(
        self,
        query: str,
        version: str = "both",
        testament: str = "all",
        limit: int = 20,
        offset: int = 0,
        book: Optional[str] = None,
        with_metadata: bool = False
    ) -> Any:
        """
        Full-text search using FTS5 virtual table.
        """
        self._validate_page(limit, offset)
        q = query.strip()
        if not q:
            raise ValueError("Provide a word or quoted phrase to search.")
        # Treat user input as words/phrases, not executable FTS syntax.
        terms = re.findall(r'"([^"\n]+)"|([^\s"]+)', q)
        q = " AND ".join('"' + (phrase or word).replace('"', '""') + '"' for phrase, word in terms)
        if not q:
            raise ValueError("Provide a word or quoted phrase to search.")
        version = version.lower()
        if version not in {"both", "rv", "lv"}:
            raise ValueError("version must be both, rv, or lv")
        columns = "{rv_text_clean lv_text_clean}" if version == "both" else version + "_text_clean"
        q = f"{columns} : ({q})"
        code = self.normalize_book(book) if book else None
        if book and not code:
            raise ValueError(f"Unknown book: {book}")
        testament = testament.upper()
        if testament not in {"ALL", "OT", "NT"}:
            raise ValueError("testament must be all, OT, or NT")

        with self.get_connection() as conn:
            cur = conn.cursor()
            sql = """
            SELECT v.verse_id, v.book_code, v.chapter, v.verse, v.rv_text_clean, v.lv_text_clean, b.english_name, b.testament
            FROM verses_fts f
            JOIN verses v ON f.rowid = v.rowid
            JOIN books b ON v.book_code = b.book_code
            WHERE verses_fts MATCH ?
            """
            params = [q]
            if testament in ["OT", "NT"]:
                sql += " AND b.testament = ?"
                params.append(testament)
            if code:
                sql += " AND b.book_code = ?"
                params.append(code)
            total = conn.execute(f"SELECT count(*) FROM ({sql})", params).fetchone()[0] if with_metadata else None
            sql += " ORDER BY b.canonical_order ASC, v.chapter ASC, v.verse ASC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cur.execute(sql, params)
            rows = cur.fetchall()

            results = []
            for r in rows:
                item = {
                    "verse_id": r["verse_id"],
                    "reference": f"{r['english_name']} {r['chapter']}:{r['verse']}",
                    "book_code": r["book_code"],
                    "testament": r["testament"],
                }
                if version in ["both", "rv"]:
                    item["rv_text"] = r["rv_text_clean"]
                if version in ["both", "lv"]:
                    item["lv_text"] = r["lv_text_clean"]
                results.append(item)

            if with_metadata:
                return dict(query=query, version=version, testament=testament, matches=results,
                            offset=offset, total_matches=total,
                            next_offset=offset+len(results) if offset+len(results)<total else None)
            return results

    def get_translation_decisions(self, reference: str) -> List[Dict[str, Any]]:
        """
        Extracts all explicitly tagged translation decisions in a reference.
        """
        passage = self.get_passage(reference, version="parallel", show_decision_codes=True)
        results = []
        for v in passage.verses:
            if v.decisions:
                results.append({
                    "verse_id": v.verse_id,
                    "reference": f"{passage.english_name} {v.chapter}:{v.verse}",
                    "rv_text": v.rv_text,
                    "decisions": [d.model_dump() for d in v.decisions]
                })
        return results

    @staticmethod
    def _provenance(conn):
        return {r["key"]: json.loads(r["value"]) for r in conn.execute("SELECT * FROM corpus_metadata")}

    def get_book_context(self, book: str, limit: int = 50, offset: int = 0):
        self._validate_page(limit, offset)
        code = self.normalize_book(book)
        if not code:
            raise ValueError(f"Unknown book: {book}")
        with self.get_connection() as conn:
            sources = {r["source_version"]: json.loads(r["metadata_json"]) for r in conn.execute("SELECT * FROM book_metadata WHERE book_code=?", (code,))}
            total = conn.execute("SELECT count(*) FROM sections WHERE book_code=?", (code,)).fetchone()[0]
            sections = [dict(r) for r in conn.execute("SELECT * FROM sections WHERE book_code=? ORDER BY source_version,chapter,start_verse LIMIT ? OFFSET ?", (code,limit,offset))]
            return dict(book_code=code, sources=sources, sections=sections, total_sections=total,
                        next_offset=offset+len(sections) if offset+len(sections)<total else None,
                        provenance=self._provenance(conn))

    def get_section(self, section_id: str, limit: int = 50, offset: int = 0):
        with self.get_connection() as conn:
            section = conn.execute("SELECT * FROM sections WHERE section_id=?", (section_id,)).fetchone()
            if not section:
                raise ValueError("Unknown section ID; use get_book_context to list available sections.")
            ref = f"{section['book_code']} {section['chapter']}:{section['start_verse']}-{section['end_chapter']}:{section['end_verse']}"
        return self.get_passage(ref, include_structure=True, limit=limit, offset=offset)

    def get_catalog(self) -> List[CatalogBook]:
        """
        Returns full list of available biblical books and translation status.
        """
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM books ORDER BY canonical_order ASC")
            return [
                CatalogBook(
                    book_code=r["book_code"],
                    testament=r["testament"],
                    canonical_order=r["canonical_order"],
                    english_name=r["english_name"],
                    oet_name=r["oet_name"] or r["english_name"],
                    abbr=r["abbr"] or r["english_name"][:3],
                    chapters_count=r["chapters_count"],
                    rv_available=bool(r["rv_available"]),
                    lv_available=bool(r["lv_available"])
                )
                for r in cur.fetchall()
            ]

    def get_formats_reference(self) -> List[Dict[str, str]]:
        """
        Returns the reference documentation table for OET markup and decision tags.
        """
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM formats_reference ORDER BY scope ASC, code ASC")
            return [dict(r) for r in cur.fetchall()]
