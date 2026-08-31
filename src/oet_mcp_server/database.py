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
    "SNG": "SNG", "SONG": "SNG", "SONG OF SOLOMON": "SNG", "CANTICLES": "SNG", "SOS": "SNG",
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
    "NAH": "NAH", "NAHUM": "NAH",
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
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
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
        m_dot = re.match(r'^([A-Za-z0-9]{3})[._](\d+)[:.](\d+)(?:[-–](\d+))?$', ref_str)
        if m_dot:
            b_code = self.normalize_book(m_dot.group(1))
            ch = int(m_dot.group(2))
            v_start = int(m_dot.group(3))
            v_end = int(m_dot.group(4)) if m_dot.group(4) else v_start
            return b_code, ch, v_start, ch, v_end

        m_full = re.match(
            r'^((?:[1-3]\s+)?[A-Za-z]+)\s*(\d+)(?:[:.](\d+))?(?:[-–](\d+)(?:[:.](\d+))?)?$',
            ref_str
        )
        if not m_full:
            b_code = self.normalize_book(ref_str)
            if b_code:
                return b_code, 1, 1, 999, 999
            return None, 0, 0, 0, 0

        b_name, ch1_str, v1_str, end_p1, end_p2 = m_full.groups()
        b_code = self.normalize_book(b_name)
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
        format: str = "markdown",
        show_decision_codes: bool = False
    ) -> PassageResponse:
        """
        Retrieves verses for a given scripture reference in RV, LV, parallel, or interlinear mode.
        """
        b_code, start_ch, start_v, end_ch, end_v = self.parse_reference(reference)
        if not b_code:
            raise ValueError(f"Could not recognize biblical reference: '{reference}'")

        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM books WHERE book_code = ?", (b_code,))
            book_row = cur.fetchone()
            if not book_row:
                raise ValueError(f"Book code '{b_code}' not found in database.")

            if start_ch == end_ch:
                cur.execute("""
                SELECT * FROM verses
                WHERE book_code = ? AND chapter = ? AND verse >= ? AND verse <= ?
                ORDER BY verse ASC
                """, (b_code, start_ch, start_v, end_v))
            else:
                cur.execute("""
                SELECT * FROM verses
                WHERE book_code = ? AND (
                    (chapter = ? AND verse >= ?) OR
                    (chapter > ? AND chapter < ?) OR
                    (chapter = ? AND verse <= ?)
                )
                ORDER BY chapter ASC, verse ASC
                """, (b_code, start_ch, start_v, start_ch, end_ch, end_ch, end_v))

            verse_rows = cur.fetchall()
            if not verse_rows:
                cur.execute("""
                SELECT * FROM verses WHERE book_code = ? AND chapter = ? ORDER BY verse ASC
                """, (b_code, start_ch))
                verse_rows = cur.fetchall()

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
                    WHERE book_code = ? AND chapter = ? AND verse = ?
                    ORDER BY word_seq ASC
                    """, (b_code, v["chapter"], v["verse"]))
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
                            tags=wr["tags"]
                        ))

                decisions = []
                if v["decisions_json"]:
                    try:
                        raw_decs = json.loads(v["decisions_json"])
                        for d in raw_decs:
                            decisions.append(DecisionItem(
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
                    decisions=decisions,
                    has_missing_verse=bool(v["has_missing_verse_flag"]),
                    has_poetry_parallel=bool(v["has_poetry_parallel"]),
                    has_order_swap=bool(v["has_order_swap"]),
                    notes=notes_list,
                    words=words_list
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
                cross_refs_count=total_xrefs
            )

    def compare_passage(self, reference: str) -> List[ComparisonDiffItem]:
        """
        Isolates and computes detailed translation divergencies between OET-RV and OET-LV.
        """
        passage = self.get_passage(reference, version="parallel", show_decision_codes=True)
        diff_items = []

        for v in passage.verses:
            rv_raw = v.rv_annotated or ""
            lv_raw = v.lv_annotated or ""

            added_lv = re.findall(r'\[\+?:?([^\]]+)\]', lv_raw)
            untranslated_lv = re.findall(r'\{([^}]+)\}', lv_raw)

            notes = []
            if v.has_order_swap:
                notes.append("Clause ordering was inverted (⇔) for modern discourse fluency.")
            if v.has_poetry_parallel:
                notes.append("Hebrew poetic parallelism (≈) marked in Readers' Version.")
            if v.has_missing_verse:
                notes.append("Omitted verse (◘) absent from earliest textual witnesses.")

            diff_items.append(ComparisonDiffItem(
                verse_id=v.verse_id,
                rv_text=v.rv_text or "",
                lv_text=v.lv_text or "",
                added_words_lv=added_lv,
                untranslated_words_lv=untranslated_lv,
                translation_decisions_rv=v.decisions,
                syntactic_notes=" ".join(notes) if notes else None
            ))

        return diff_items

    def lookup_word(self, word_id: str) -> Optional[Dict[str, Any]]:
        """
        Lookup a specific word link token by ID (e.g. 'JHNc1v1w5' or 'JHN_1:1w5').
        """
        cleaned_id = word_id.strip()
        m_c = re.match(r'([A-Za-z0-9]{3})c(\d+)v(\d+)w(\d+)', cleaned_id, re.IGNORECASE)
        if m_c:
            b, c, v, w = m_c.groups()
            cleaned_id = f"{b.upper()}_{c}:{v}w{w}"

        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            SELECT * FROM words WHERE word_link_id = ? OR ref_str = ?
            """, (cleaned_id, cleaned_id))
            row = cur.fetchone()
            if not row:
                return None

            data = dict(row)
            cur.execute("SELECT rv_text_clean, lv_text_clean FROM verses WHERE verse_id = ?", (f"{data['book_code']}.{data['chapter']}.{data['verse']}",))
            v_row = cur.fetchone()
            if v_row:
                data["verse_rv"] = v_row["rv_text_clean"]
                data["verse_lv"] = v_row["lv_text_clean"]

            lemma = data.get("sr_lemma") or data.get("original_lemma")
            if lemma:
                cur.execute("SELECT * FROM lexicon WHERE lemma = ? OR strongs = ?", (lemma, data.get("strongs")))
                lex = cur.fetchone()
                if lex:
                    data["lexicon"] = dict(lex)
                    if lex["gloss_distribution_json"]:
                        data["lexicon"]["gloss_distribution"] = json.loads(lex["gloss_distribution_json"])

            return data

    def search_lemma(
        self,
        lemma_or_strongs: str,
        testament: str = "all",
        limit: int = 30
    ) -> Dict[str, Any]:
        """
        Search for all occurrences of a lemma or Strong's ID across the corpus.
        """
        query = lemma_or_strongs.strip()
        testament = testament.upper()

        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            SELECT * FROM lexicon
            WHERE lemma = ? OR strongs = ? OR lemma_display = ?
            """, (query, query, query))
            lex_row = cur.fetchone()

            sql = """
            SELECT w.*, v.rv_text_clean, v.lv_text_clean, b.testament
            FROM words w
            JOIN verses v ON (w.book_code = v.book_code AND w.chapter = v.chapter AND w.verse = v.verse)
            JOIN books b ON w.book_code = b.book_code
            WHERE (w.sr_lemma = ? OR w.strongs = ? OR w.original_lemma = ? OR w.original_word = ?)
            """
            params = [query, query, query, query]
            if testament in ["OT", "NT"]:
                sql += " AND b.testament = ?"
                params.append(testament)
            sql += " ORDER BY b.canonical_order ASC, w.chapter ASC, w.verse ASC LIMIT ?"
            params.append(limit)

            cur.execute(sql, params)
            rows = cur.fetchall()

            occurrences = []
            gloss_counter = Counter()

            for r in rows:
                gloss = r["oet_gloss"] or r["vlt_gloss"] or ""
                if gloss:
                    gloss_counter[gloss] += 1
                occurrences.append({
                    "ref": f"{r['book_code']} {r['chapter']}:{r['verse']} (word {r['word_seq']})",
                    "word_link_id": r["word_link_id"],
                    "original_word": r["original_word"],
                    "morphology": r["morphology"],
                    "oet_gloss": r["oet_gloss"],
                    "rv_text": r["rv_text_clean"],
                    "lv_text": r["lv_text_clean"]
                })

            result = {
                "query": query,
                "testament_filter": testament,
                "total_found_in_sample": len(occurrences),
                "gloss_distribution_in_sample": dict(gloss_counter.most_common(10)),
                "occurrences": occurrences
            }

            if lex_row:
                result["lexicon_info"] = {
                    "lang": lex_row["lang"],
                    "lemma": lex_row["lemma"],
                    "lemma_display": lex_row["lemma_display"],
                    "strongs": lex_row["strongs"],
                    "primary_gloss": lex_row["primary_gloss"],
                    "total_canonical_occurrences": lex_row["total_occurrences"],
                    "canonical_gloss_distribution": json.loads(lex_row["gloss_distribution_json"]) if lex_row["gloss_distribution_json"] else {}
                }

            return result

    def get_lexicon_entry(self, query: str, lang: str = "auto") -> Optional[LexiconEntry]:
        """
        Retrieves a rich lexicon entry by lemma or Strong's ID.
        """
        q = query.strip()
        with self.get_connection() as conn:
            cur = conn.cursor()
            sql = "SELECT * FROM lexicon WHERE lemma = ? OR strongs = ? OR lemma_display = ?"
            params = [q, q, q]
            if lang.lower() in ["greek", "hebrew"]:
                sql += " AND lang = ?"
                params.append(lang.lower())
            cur.execute(sql, params)
            row = cur.fetchone()
            if not row:
                cur.execute("""
                SELECT l.* FROM lexicon_fts f
                JOIN lexicon l ON f.lemma_key = l.lemma_key
                WHERE lexicon_fts MATCH ? LIMIT 1
                """, (q,))
                row = cur.fetchone()
                if not row:
                    return None

            gloss_dist = json.loads(row["gloss_distribution_json"]) if row["gloss_distribution_json"] else {}
            refs = [r.strip() for r in row["first_occurrences_refs"].split(",") if r.strip()] if row["first_occurrences_refs"] else []

            return LexiconEntry(
                lemma_key=row["lemma_key"],
                lang=row["lang"],
                lemma=row["lemma"],
                lemma_display=row["lemma_display"],
                strongs=row["strongs"],
                primary_gloss=row["primary_gloss"],
                total_occurrences=row["total_occurrences"],
                gloss_distribution=gloss_dist,
                first_occurrences_refs=refs
            )

    def search_text(
        self,
        query: str,
        version: str = "both",
        testament: str = "all",
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Full-text search using FTS5 virtual table.
        """
        q = query.strip()
        version = version.lower()
        testament = testament.upper()

        with self.get_connection() as conn:
            cur = conn.cursor()
            sql = """
            SELECT v.verse_id, v.book_code, v.chapter, v.verse, v.rv_text_clean, v.lv_text_clean, b.english_name, b.testament
            FROM verses_fts f
            JOIN verses v ON f.verse_id = v.verse_id
            JOIN books b ON v.book_code = b.book_code
            WHERE verses_fts MATCH ?
            """
            params = [q]
            if testament in ["OT", "NT"]:
                sql += " AND b.testament = ?"
                params.append(testament)
            sql += " ORDER BY b.canonical_order ASC, v.chapter ASC, v.verse ASC LIMIT ?"
            params.append(limit)

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
