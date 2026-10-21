"""
src/oet_mcp_server/models.py

Pydantic data models for structured MCP payloads.
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class DecisionItem(BaseModel):
    source_version: Optional[Literal["RV", "LV"]] = None
    source_span: Optional[List[int]] = Field(default=None, description="Half-open character offsets in this version's verse ESFM")
    code: str = Field(description="OET decision code character, e.g. '@', '≈', '+', '=', '<', '>', '≡', '&', '*', '#', '%', '^', '?', '!'")
    type: str = Field(description="Human readable name of the translation decision category")
    text: Optional[str] = Field(default=None, description="The English text affected by this decision")
    description: Optional[str] = Field(default=None, description="Meaning of the annotation category, not a passage-specific translator rationale")


class WordModel(BaseModel):
    word_link_id: str = Field(description="Unique wordlink reference, e.g. 'JHN_1:1w5' or 'JHNc1v1w5'")
    ref: str = Field(description="Book chapter:verse word index")
    original_word: str = Field(description="Original Greek or Hebrew surface word")
    sr_lemma: Optional[str] = Field(default=None, description="Statistical Restoration or transliterated lemma")
    original_lemma: Optional[str] = Field(default=None, description="Original language lemma")
    strongs: Optional[str] = Field(default=None, description="Legacy source identifier; use strongs_standard for standard dictionary IDs")
    role: Optional[str] = Field(default=None, description="Syntactic role (Noun, Verb, Preposition, etc.)")
    morphology: Optional[str] = Field(default=None, description="Morphological parsing code")
    vlt_gloss: Optional[str] = Field(default=None, description="Literal gloss in VLT")
    oet_gloss: Optional[str] = Field(default=None, description="Primary OET rendering")
    contextual_gloss: Optional[str] = Field(default=None, description="Contextual translation in passage")
    morpheme_glosses: Optional[str] = Field(default=None, description="Detailed Hebrew morpheme breakdown")
    tags: Optional[str] = Field(default=None, description="Semantic and theological domain tags")
    lang: str
    source_status: str
    is_selected: bool
    strongs_standard: List[str] = Field(default_factory=list)
    source_strongs: Optional[str] = None
    lemmas: List[Dict[str, Any]] = Field(default_factory=list)
    grammar: Dict[str, Any] = Field(default_factory=dict)


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
    rv_esfm: Optional[str] = Field(default=None, description="Raw OET-RV ESFM source, only when include_raw is set")
    lv_esfm: Optional[str] = Field(default=None, description="Raw OET-LV ESFM source, only when include_raw is set")
    decisions: List[DecisionItem] = Field(default_factory=list)
    has_missing_verse: bool = False
    has_poetry_parallel: bool = False
    has_order_swap: bool = False
    notes: List[NoteItem] = Field(default_factory=list)
    words: List[WordModel] = Field(default_factory=list)
    structure: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    alignments: List[Dict[str, Any]] = Field(default_factory=list)
    availability: Dict[str, str] = Field(default_factory=dict)
    source_url: Optional[str] = None


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
    total_verses: int = 0
    offset: int = 0
    next_offset: Optional[int] = None
    provenance: Dict[str, Any] = Field(default_factory=dict)


class LexiconEntry(BaseModel):
    lemma_key: str
    lang: str = Field(description="'greek', 'hebrew', or 'aramaic'")
    lemma: str
    lemma_display: Optional[str] = None
    strongs: Optional[str] = None
    primary_gloss: Optional[str] = None
    total_occurrences: int
    gloss_distribution: Dict[str, int] = Field(default_factory=dict)
    first_occurrences_refs: List[str] = Field(default_factory=list)
    strongs_ids: List[str] = Field(default_factory=list)
    count_scope: str = "Selected source word occurrences; OET-LV word-table glosses, not RV renderings"
    unused_variant_occurrences: int = 0
    unglossed_occurrences: int = 0


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


class WordLookupResponse(BaseModel):
    word: WordModel
    verse_rv: Optional[str] = None
    verse_lv: Optional[str] = None
    lexicon: Optional[LexiconEntry] = None
    lexicon_entries: List[LexiconEntry] = Field(default_factory=list)
    alignments: List[Dict[str, Any]] = Field(default_factory=list)
    provenance: Dict[str, Any] = Field(default_factory=dict)


class WordOccurrence(BaseModel):
    ref: str
    word_link_id: str
    original_word: str
    morphology: Optional[str] = None
    oet_gloss: Optional[str] = None
    is_selected: bool
    source_status: str
    rv_text: Optional[str] = None
    lv_text: Optional[str] = None


class ConcordanceResponse(BaseModel):
    query: str
    testament_filter: str
    book: Optional[str] = None
    include_variants: bool
    sampling: str
    offset: int
    count_scope: str
    total_matches: int
    total_found_in_sample: int
    next_offset: Optional[int] = None
    gloss_distribution_in_sample: Dict[str, int]
    occurrences: List[WordOccurrence]
    resolved_lemma_keys: List[str]
    lexicon_info: Optional[Dict[str, Any]] = None


class TextMatch(BaseModel):
    verse_id: str
    reference: str
    book_code: str
    testament: str
    rv_text: Optional[str] = None
    lv_text: Optional[str] = None


class TextSearchResponse(BaseModel):
    query: str
    version: str
    testament: str
    matches: List[TextMatch]
    offset: int
    next_offset: Optional[int] = None
    total_matches: int


class ComparisonResponse(BaseModel):
    reference: str
    comparisons: List[ComparisonDiffItem]
    total_verses: int
    next_offset: Optional[int] = None


class VerseDecisions(BaseModel):
    verse_id: str
    decisions: List[DecisionItem]
    notes: List[NoteItem] = Field(default_factory=list)


class DecisionsResponse(BaseModel):
    reference: str
    verses: List[VerseDecisions]
    total_verses: int
    next_offset: Optional[int] = None


class BookContextResponse(BaseModel):
    book_code: str
    sources: Dict[str, Any]
    sections: List[Dict[str, Any]]
    total_sections: int
    next_offset: Optional[int] = None
    provenance: Dict[str, Any]


class GuideResponse(BaseModel):
    guidance: str
    source_urls: List[str]
