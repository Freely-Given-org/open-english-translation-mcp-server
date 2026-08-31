"""
src/oet_mcp_server/models.py

Pydantic data models for structured MCP payloads.
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class DecisionItem(BaseModel):
    code: str = Field(description="OET decision code character, e.g. '@', '≈', '+', '=', '<', '>', '≡', '&', '*', '#', '%', '^', '?'")
    type: str = Field(description="Human readable name of the translation decision category")
    text: Optional[str] = Field(default=None, description="The English text affected by this decision")
    description: Optional[str] = Field(default=None, description="Explanation of why this decision was made")


class WordModel(BaseModel):
    word_link_id: str = Field(description="Unique wordlink reference, e.g. 'JHN_1:1w5' or 'JHNc1v1w5'")
    ref: str = Field(description="Book chapter:verse word index")
    original_word: str = Field(description="Original Greek or Hebrew surface word")
    sr_lemma: Optional[str] = Field(default=None, description="Statistical Restoration or transliterated lemma")
    original_lemma: Optional[str] = Field(default=None, description="Original language lemma")
    strongs: Optional[str] = Field(default=None, description="Strong's Concordance identifier, e.g. 'G3056' or 'H7225'")
    role: Optional[str] = Field(default=None, description="Syntactic role (Noun, Verb, Preposition, etc.)")
    morphology: Optional[str] = Field(default=None, description="Morphological parsing code")
    vlt_gloss: Optional[str] = Field(default=None, description="Literal gloss in VLT")
    oet_gloss: Optional[str] = Field(default=None, description="Primary OET rendering")
    contextual_gloss: Optional[str] = Field(default=None, description="Contextual translation in passage")
    morpheme_glosses: Optional[str] = Field(default=None, description="Detailed Hebrew morpheme breakdown")
    tags: Optional[str] = Field(default=None, description="Semantic and theological domain tags")


class NoteItem(BaseModel):
    verse_id: str
    source_version: str = Field(description="'RV' or 'LV'")
    note_type: str = Field(description="'footnote' or 'xref'")
    category: Optional[str] = Field(default=None, description="Category code like 'TD' (Translation Decision), 'TC' (Textual Criticism), 'Hist', 'Fig', 'General'")
    caller_ref: Optional[str] = Field(default=None)
    content: str


class VerseModel(BaseModel):
    verse_id: str = Field(description="Standardized verse ID, e.g. 'JHN.1.1'")
    book_code: str
    chapter: int
    verse: int
    verse_label: str
    section_heading: Optional[str] = None
    rv_text: Optional[str] = Field(default=None, description="Clean Readers' Version text")
    lv_text: Optional[str] = Field(default=None, description="Clean Literal Version text")
    rv_annotated: Optional[str] = Field(default=None, description="Readers' Version with markup decisions")
    lv_annotated: Optional[str] = Field(default=None, description="Literal Version with untranslated & added words")
    decisions: List[DecisionItem] = Field(default_factory=list)
    has_missing_verse: bool = False
    has_poetry_parallel: bool = False
    has_order_swap: bool = False
    notes: List[NoteItem] = Field(default_factory=list)
    words: List[WordModel] = Field(default_factory=list)


class PassageResponse(BaseModel):
    reference: str
    book_code: str
    english_name: str
    oet_name: str
    version: str
    verses_count: int
    verses: List[VerseModel]
    footnotes_count: int = 0
    cross_refs_count: int = 0


class LexiconEntry(BaseModel):
    lemma_key: str
    lang: str = Field(description="'greek' or 'hebrew'")
    lemma: str
    lemma_display: Optional[str] = None
    strongs: Optional[str] = None
    primary_gloss: Optional[str] = None
    total_occurrences: int
    gloss_distribution: Dict[str, int] = Field(default_factory=dict)
    first_occurrences_refs: List[str] = Field(default_factory=list)


class ComparisonDiffItem(BaseModel):
    verse_id: str
    rv_text: str
    lv_text: str
    added_words_lv: List[str] = Field(default_factory=list, description="Words added in LV (copulas, articles, objects)")
    untranslated_words_lv: List[str] = Field(default_factory=list, description="Original words left untranslated in English")
    translation_decisions_rv: List[DecisionItem] = Field(default_factory=list, description="Decisions made in RV (referents, rewordings, number changes)")
    syntactic_notes: Optional[str] = None


class CatalogBook(BaseModel):
    book_code: str
    testament: str
    canonical_order: int
    english_name: str
    oet_name: str
    abbr: str
    chapters_count: int
    rv_available: bool
    lv_available: bool
