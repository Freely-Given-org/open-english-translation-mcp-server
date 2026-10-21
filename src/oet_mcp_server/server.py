"""
src/oet_mcp_server/server.py

Model Context Protocol (MCP) Server implementation for the Open English Translation (OET).
"""

import json
from typing import Optional, Literal, Annotated
from functools import wraps
from pydantic import Field, BaseModel
from mcp.types import CallToolResult, TextContent, ToolAnnotations
from mcp.server.mcpserver import MCPServer

from .database import OETDatabase
from .models import (
    PassageResponse, LexiconEntry, WordModel, WordLookupResponse, ConcordanceResponse,
    TextSearchResponse, ComparisonResponse, DecisionsResponse, VerseDecisions,
    BookContextResponse, GuideResponse,
)

# Initialize MCPServer and DB
server = MCPServer("Open English Translation (OET) Server", instructions=(
    "Use get_oet_guide for OET conventions. Read RV and LV together and use get_book_context/get_section "
    "for context. Distinguish source text, unused variants, translator notes and your own inference. "
    "Gloss counts are OET-LV corpus evidence, not dictionary meanings or RV statistics. "
    "Follow next_offset for complete results and cite returned source references and corpus revision."))
db = OETDatabase()


OET_GUIDE = """Read OET-RV and OET-LV together. RV supplies natural English context; LV exposes
source wording, including particles, additions and awkward literal constructions.
LV word order may be adjusted for English. Literal double negatives and ellipsis must
be interpreted with the RV and source grammar, not as ordinary English. Capitalization
and editorial headings are translation conventions, not independent manuscript evidence.
Names are often transliterated differently from traditional English names; alternate names
may be supplied in parentheses. 'you all' distinguishes plural address. LV commonly retains
ancient units and figurative language while RV helps readers understand them.

The plain reading view hides annotation markup. Use show_decision_codes=True to distinguish
added English words from untranslated particles ({word}); DOM is the Hebrew direct-object
marker. Underscores, equals signs and division signs in source glosses mark joins, not
additional dictionary words. Code meanings are available at oet://formats.

Decision categories identify an editorial operation, not necessarily its reason. Cite an
actual translator note when explaining a documented rationale; label your own explanation
as inference. No annotation does not imply no interpretation. Divine-name formatting is
not evidence that a manuscript used nomina sacra.

Interlinear defaults exclude unused Greek variants. Variant rows remain available explicitly
and carry their source selection marker. Counts refer to selected source word occurrences,
not unique verses. Hebrew/Aramaic lemma statistics include prefixed forms; whole-word glosses
can contain translations of several morphemes and are not isolated stem definitions.
Dictionary definitions, etymology and manuscript witness apparatus are not supplied.

Use include_structure and get_section for paragraphs and poetry, include_alignment for
English-to-source links, and lookup_word for coded and decoded morphology. Missing links
remain missing. Use corpus provenance and per-book source notes to identify edition, draft
status and adapted material. Public website links may show a newer revision than this corpus.
"""


def evidence_tool(function):
    """Expose read-only tools with useful, recoverable input errors."""
    @wraps(function)
    def wrapped(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except ValueError as error:
            return CallToolResult(content=[TextContent(text=str(error))], isError=True)
    return server.tool(annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False,
                       idempotentHint=True, openWorldHint=False))(wrapped)


def respond(model: BaseModel, text: Optional[str] = None) -> CallToolResult:
    data = model.model_dump(exclude_none=True, exclude_defaults=True)
    if isinstance(model, LexiconEntry):
        data["count_scope"] = model.count_scope
    if isinstance(model, WordLookupResponse) and model.lexicon:
        data["lexicon"]["count_scope"] = model.lexicon.count_scope
    if text is None:
        text = json.dumps(data, ensure_ascii=False)
    elif getattr(model, "next_offset", None) is not None and f"offset={model.next_offset}" not in text:
        text += f"\n\nMore results: repeat with offset={model.next_offset} and the same filters."
    return CallToolResult(content=[TextContent(text=text)], structuredContent=data)


@server.resource("oet://guide")
def get_guide_resource() -> str:
    """Guide to reading OET evidence, conventions and limitations."""
    return OET_GUIDE


# ---------------------------------------------------------------------------
# Resources & Resource Templates
# ---------------------------------------------------------------------------

@server.resource("oet://catalog")
def get_catalog_resource() -> str:
    """Catalog of all books available in the Open English Translation with chapter counts and testaments."""
    books = db.get_catalog()
    lines = [
        "# Open English Translation (OET) Canon Catalog",
        "",
        "| Book Code | English Name | OET Name | Testament | Chapters | RV Available | LV Available |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
    ]
    for b in books:
        rv_str = "Yes" if b.rv_available else "In Progress"
        lv_str = "Yes" if b.lv_available else "In Progress"
        lines.append(f"| `{b.book_code}` | {b.english_name} | {b.oet_name} | {b.testament} | {b.chapters_count} | {rv_str} | {lv_str} |")
    return "\n".join(lines)


@server.resource("oet://metadata/rv")
def get_rv_metadata_resource() -> str:
    """Translation philosophy and design guidelines for the OET Readers' Version (OET-RV)."""
    return """# Open English Translation — Readers' Version (OET-RV)

The **OET Readers' Version (OET-RV)** is designed to be an easy-to-read, natural, modern-English translation of the Hebrew, Aramaic, and Greek Scriptures.

## Key Design Principles
1. **Thought-for-Thought Fluency**: Rather than mimicking ancient syntax, the RV rephrases clauses into natural, idiomatic modern English.
2. **Transparent Decision Tagging (`\\add`)**: Where significant translation choices occur, the source text identifies the kind of change; notes may explain its rationale:
   - `@`: **Referent Replacement** (e.g. Replacing pronoun 'he' with explicit name 'David' or 'the messenger' for context clarity when starting pericopes).
   - `≈`: **Rewording** (Rephrasing clauses or idioms into modern conversational English).
   - `#`: **Number Change** (Generalizing ancient masculine singular proverbs to gender-neutral plural sayings).
   - `%`: **Person Shift** (Flattening multi-nested direct quotes into clear indirect speech).
   - `^`: **Opposite Phrasing** (Phrasing negative constructions positively for modern comprehension).
   - `?`: **Uncertainty Marker** (Indicates translator doubt regarding original intent).
   - `!`: **Alternate (Traditional) Name** (e.g. giving the familiar name in parentheses after a distinctive OET name, as in 'Mosheh (Moses)').
3. **Hebrew Poetic Parallelism**:
   - `≈`: Synonymous parallelism (second poetic line reiterates the first).
   - `^`: Antithetic parallelism (second poetic line states the contrast).
   - `→`: Synthetic parallelism (second poetic line completes the thought).
4. **Discourse Order Swapping (`⇔`)**: Indicated when the translator inverts Hebrew/Greek clause order to match English discourse standards.
"""


@server.resource("oet://metadata/lv")
def get_lv_metadata_resource() -> str:
    """Translation philosophy and markup conventions for the OET Literal Version (OET-LV)."""
    return """# Open English Translation — Literal Version (OET-LV)

The **OET Literal Version (OET-LV)** aims for maximum formal equivalence and transparency to the underlying Hebrew/Aramaic (UHB) and Greek (SR-GNT) manuscripts.

## Key Markup Conventions
- **Added Words (`\\add`)**:
  - `+`: **Added Article** (`[the]`, `[a]`, `[some]`) required by English syntax where the original had none.
  - `=`: **Added Copula** (`[is]`, `[was]`, `[are]`) required in English nominal sentences.
  - `<`: **Added Direct Object** (`[it]`, `[him]`) for transitive English verbs.
  - `>`: **Added Implied Entity** (`[thing]`, `[one]`, `[person]`).
  - `≡`: **Elided Repetition** (re-stating omitted verbs for clarity).
  - `&`: **Added Possessive** (`[his]`, `[their]`).
- **Untranslated Words (`\\untr`)**:
  - `{word}`: Original language particles dropped in English (e.g., Greek case-markers before proper nouns, Hebrew Direct Object Marker *DOM* / *ʼēt*).
- **Divine-name formatting (`\\nd`)**:
  - Highlights divine names and titles (God, Yahweh, Jesus, Messiah).
"""


@server.resource("oet://formats")
def get_formats_resource() -> str:
    """Reference for the supported OET decision categories; consult the guide for other conventions."""
    ref_table = db.get_formats_reference()
    lines = [
        "# OET Formatting & Decision Code Reference",
        "",
        "| Code | Scope | Category | Description | Example |",
        "| :--- | :--- | :--- | :--- | :--- |"
    ]
    for r in ref_table:
        lines.append(f"| `{r['code']}` | `{r['scope']}` | {r['name']} | {r['description']} | `{r['example']}` |")
    return "\n".join(lines)


@server.resource("oet://passage/{version}/{reference}")
def get_passage_resource(version: str, reference: str) -> str:
    """Direct resource template for reading any passage in RV, LV, or parallel."""
    return format_passage_markdown(db.get_passage(reference, version=version, include_notes=True))


@server.resource("oet://word/{word_id}")
def get_word_resource(word_id: str) -> str:
    """Direct resource template for looking up a specific original word link token."""
    w = db.lookup_word(word_id)
    if not w:
        return f"Word token '{word_id}' not found."
    return format_word_markdown(w)


@server.resource("oet://lexicon/{lang}/{query}")
def get_lexicon_resource(lang: str, query: str) -> str:
    """Retrieve OET-LV corpus usage statistics for a lemma or Strong's ID."""
    entry = db.get_lexicon_entry(query, lang=lang)
    if not entry:
        return f"Lexicon entry '{query}' ({lang}) not found."
    return format_lexicon_markdown(entry)


# ---------------------------------------------------------------------------
# Formatting Helpers
# ---------------------------------------------------------------------------

def format_passage_markdown(res: PassageResponse, show_decision_codes: bool = False) -> str:
    lines = [
        f"## {res.english_name} ({res.oet_name}) — {res.reference}",
        f"*Version*: **{res.version.upper()}** | *Verses*: {res.verses_count} of {res.total_verses}",
        ""
    ]

    current_section = None
    for v in res.verses:
        if v.section_heading and v.section_heading != current_section:
            current_section = v.section_heading
            lines.append(f"### {current_section}\n")

        v_ref = f"{res.english_name} {v.chapter}:{v.verse_label}"
        def reading(version, fallback):
            if fallback is None:
                return "Unavailable: " + v.availability.get(version, "no source text")
            if v.structure and fallback == (v.rv_text if version == "RV" else v.lv_text):
                # Preserve boundaries in structure mode; annotation mode remains in fallback text.
                annotated = v.rv_annotated if version == "RV" else v.lv_annotated
                if fallback != annotated:
                    return "  \n".join(segment["text"] for segment in v.structure.get(version, []) if segment["text"]) or fallback
            return fallback
        rv_reading, lv_reading = reading("RV", v.rv_text), reading("LV", v.lv_text)
        if res.version.lower() == "parallel":
            lines.append(f"**{v_ref}**")
            lines.append(f"* **OET-RV (Readers)**: {rv_reading}")
            lines.append(f"* **OET-LV (Literal)**: {lv_reading}")
            lines.append("")
        elif res.version.lower() == "rv":
            lines.append(f"**{v_ref}** {rv_reading}")
        elif res.version.lower() == "lv":
            lines.append(f"**{v_ref}** {lv_reading}")
        elif res.version.lower() == "interlinear":
            lines.append(f"**{v_ref}**")
            lines.append(f"*RV*: {rv_reading}")
            lines.append(f"*LV*: {lv_reading}")
            if v.words:
                lines.append("\n| Word ID | Original | Lemma | Strong's | Morph | Literal Gloss | OET Gloss |")
                lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
                for w in v.words:
                    lines.append(f"| `{w.ref}`{' (unused variant)' if not w.is_selected else ''} | {w.original_word} | {w.sr_lemma or w.original_lemma} | {w.strongs or '-'} | `{w.morphology or '-'}` | {w.vlt_gloss or '-'} | {w.oet_gloss or '-'} |")
            lines.append("")

    # Append Footnotes
    all_notes = []
    for v in res.verses:
        all_notes.extend(v.notes)

    if all_notes:
        lines.append("---")
        lines.append("### Translator Footnotes & Cross-References")
        for n in all_notes:
            tag = f"[{n.source_version} {n.category}]" if n.category != "General" else f"[{n.source_version}]"
            caller = f" ({n.caller_ref})" if n.caller_ref else ""
            lines.append(f"* **{n.verse_id}**{caller} {tag}: {n.content}")

    if res.next_offset is not None:
        lines.append(f"More verses: repeat with offset={res.next_offset} and the same arguments.")
    if res.provenance:
        lines.append(f"Source: {res.provenance.get('attribution')}; {res.provenance.get('text_license')}; corpus {res.provenance.get('source_commit', '')[:12]}.")
    if res.verses:
        lines.append(f"Public passage: {res.verses[0].source_url}")
    return "\n".join(lines)


def format_word_markdown(w: dict) -> str:
    lines = [
        f"## Wordlink Token: `{w.get('ref_str')}` (#{w.get('word_link_id')})",
        "",
        f"- **Original Word**: `{w.get('original_word')}` ({w.get('original_word_clean')})",
        f"- **Lemma**: `{w.get('sr_lemma') or w.get('original_lemma')}`",
        f"- **Standard Strong's IDs**: `{', '.join(w.get('strongs_standard', []))}`",
        f"- **Source selection**: {'selected' if w.get('is_selected') else 'unused variant'} (source marker: {w.get('source_status')!r})",
        f"- **Source role code**: `{w.get('role')}`",
        f"- **Morphological Parsing**: `{w.get('morphology')}`",
        f"- **Source word-table gloss**: *{w.get('vlt_gloss') or 'Not recorded'}*",
        f"- **OET Gloss**: *{w.get('oet_gloss')}*",
        f"- **Contextual Gloss**: *{w.get('contextual_gloss') or 'Not recorded'}*",
    ]
    if w.get("grammar"):
        lines.append("- **Decoded grammar**: " + json.dumps(w["grammar"], ensure_ascii=False))
    if w.get("alignments"):
        lines.append("- **Linked English wording**: " + "; ".join(f"{a['source_version']}: {a['text']}" for a in w["alignments"]))
    if w.get("morpheme_glosses"):
        lines.append(f"- **Hebrew Morpheme Breakdown**: `{w.get('morpheme_glosses')}`")
    if w.get("tags"):
        lines.append(f"- **Theological / Domain Tags**: `{w.get('tags')}`")

    if w.get("verse_rv") or w.get("verse_lv"):
        lines.append("\n### Verse Context")
        lines.append(f"* **OET-RV**: {w.get('verse_rv')}")
        lines.append(f"* **OET-LV**: {w.get('verse_lv')}")

    if w.get("lexicon"):
        lex = w["lexicon"]
        lines.append("\n### OET-LV Corpus Usage Statistics")
        lines.append(f"- Selected Source Occurrences: **{lex.get('total_occurrences')}**")
        if lex.get("gloss_distribution"):
            lines.append("- Primary English Glosses in OET:")
            for g, c in list(lex["gloss_distribution"].items())[:6]:
                lines.append(f"  * *{g}*: {c}×")

    return "\n".join(lines)


def format_lexicon_markdown(entry: LexiconEntry) -> str:
    lines = [
        f"## Lexicon Entry: `{entry.lemma}` ({entry.lemma_display or entry.lemma})",
        f"- **Language**: {entry.lang.title()}",
        f"- **Strong's Number**: `{entry.strongs or 'N/A'}`",
        f"- **Primary OET Gloss**: **{entry.primary_gloss or 'N/A'}**",
        f"- **Selected Source Occurrences**: **{entry.total_occurrences}** (unused variants: {entry.unused_variant_occurrences})",
        entry.count_scope,
        f"- **Occurrences without a recorded gloss**: {entry.unglossed_occurrences}",
        "",
        "### Gloss Distribution Across the OET"
    ]
    for gloss, count in entry.gloss_distribution.items():
        pct = (count / entry.total_occurrences * 100) if entry.total_occurrences > 0 else 0
        lines.append(f"* **{gloss}**: {count} occurrences ({pct:.1f}%)")

    if entry.first_occurrences_refs:
        lines.append("\n### Sample Occurrences")
        lines.append(", ".join(entry.first_occurrences_refs[:20]))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------

@evidence_tool
def get_passage(
    reference: str,
    version: Literal["parallel", "rv", "lv", "interlinear"] = "parallel",
    include_notes: bool = True,
    format: Literal["markdown", "json"] = "markdown",
    show_decision_codes: bool = False,
    include_raw: bool = False,
    include_variants: bool = False,
    include_structure: bool = False,
    include_alignment: bool = False,
    limit: Annotated[int, Field(ge=1, le=100)] = 20,
    offset: Annotated[int, Field(ge=0)] = 0,
) -> Annotated[CallToolResult, PassageResponse]:
    """Read OET-RV and OET-LV with notes and corpus provenance.

    Use get_oet_guide for conventions and get_book_context/get_section for context.
    reference accepts John 1:1-5, JHN.1.1, 1Cor 13, and cross-chapter ranges.
    interlinear adds selected original-language words, lemma IDs and decoded grammar;
    include_variants adds explicitly labelled unused Greek variants. It is capped at
    10 verses per page. Follow next_offset with the same arguments for further pages.
    include_structure adds paragraph/poetry markers and section IDs. include_alignment
    adds source word links and half-open offsets into the verse ESFM; links can be
    incomplete and are not inferred. include_raw returns verse ESFM in structured data.
    Markdown is a compact reading view; structuredContent always contains typed data.
    """
    if version == "interlinear":
        limit = min(limit, 10)
    result = db.get_passage(reference, version=version, include_notes=include_notes,
        include_raw=include_raw, show_decision_codes=show_decision_codes,
        include_variants=include_variants, include_structure=include_structure,
        include_alignment=include_alignment, limit=limit, offset=offset)
    data = result.model_dump(exclude_none=True, exclude_defaults=True,
                            exclude={"verses": {"__all__": {"rv_annotated", "lv_annotated"}}})
    if version in {"rv", "lv"}:
        other = "lv" if version == "rv" else "rv"
        for verse in data["verses"]:
            verse.pop(other + "_text", None)
            verse.pop(other + "_esfm", None)
    text = json.dumps(data, ensure_ascii=False) if format == "json" else format_passage_markdown(result)
    return CallToolResult(content=[TextContent(text=text)], structuredContent=data)


@evidence_tool
def compare_translations(reference: str, limit: Annotated[int, Field(ge=1, le=100)] = 20,
                         offset: Annotated[int, Field(ge=0)] = 0) -> Annotated[CallToolResult, ComparisonResponse]:
    """Compare RV/LV explicit annotations, preserving which version made each decision.

    Category labels describe the annotation, not a documented translator rationale.
    Consult get_passage notes for explanations. This is not an exhaustive linguistic diff.
    Follow next_offset with the same reference to continue.
    """
    passage = db.get_passage(reference, show_decision_codes=True, limit=limit, offset=offset)
    comparisons = db.compare_passage(reference, passage=passage)
    result = ComparisonResponse(reference=reference, comparisons=comparisons,
                                total_verses=passage.total_verses, next_offset=passage.next_offset)
    lines = [f"## Translation Comparison & Linguistic Breakdown: {reference}"]
    for d in comparisons:
        lines += [f"### {d.verse_id}", f"* **OET-RV**: {d.rv_text}", f"* **OET-LV**: {d.lv_text}"]
        for dec in d.translation_decisions_rv:
            lines.append(f"* [RV] {dec.type}: {dec.text or dec.description or dec.code}")
        if d.added_words_lv:
            lines.append(f"* [LV] Added spans: {', '.join(d.added_words_lv)}")
        if d.untranslated_words_lv:
            lines.append(f"* [LV] Untranslated: {', '.join(d.untranslated_words_lv)}")
        if d.syntactic_notes:
            lines.append(d.syntactic_notes)
    return respond(result, "\n".join(lines))


@evidence_tool
def search_text(query: str, version: Literal["both", "rv", "lv"] = "both",
                testament: Literal["all", "OT", "NT"] = "all",
                limit: Annotated[int, Field(ge=1, le=100)] = 20,
                offset: Annotated[int, Field(ge=0)] = 0,
                book: Optional[str] = None) -> Annotated[CallToolResult, TextSearchResponse]:
    """Search English words in the requested translation, optionally filtered by book/testament.

    Unquoted words must all occur; double-quoted text is an exact phrase. Punctuation
    is accepted as literal input. FTS operators are not supported. Follow next_offset
    with the same filters to continue; total_matches is the full filtered count.
    """
    result = TextSearchResponse(**db.search_text(query, version, testament, limit, offset, book, with_metadata=True))
    lines = [f"## Search Results for '{query}' ({len(result.matches)} of {result.total_matches} matches)"]
    for match in result.matches:
        lines.append(f"### {match.reference}")
        if match.rv_text is not None:
            lines.append(f"* **RV**: {match.rv_text}")
        if match.lv_text is not None:
            lines.append(f"* **LV**: {match.lv_text}")
    return respond(result, "\n".join(lines))


@evidence_tool
def search_lemma(lemma_or_strongs: str, testament: Literal["all", "OT", "NT"] = "all",
                 limit: Annotated[int, Field(ge=1, le=100)] = 30,
                 include_variants: bool = False, book: Optional[str] = None,
                 offset: Annotated[int, Field(ge=0)] = 0,
                 sampling: Literal["representative", "canonical"] = "representative") -> Annotated[CallToolResult, ConcordanceResponse]:
    """Retrieve occurrences of a lemma or Strong's ID with scoped counts and LV glosses.

    Examples: logos, λόγος, agape, G3056, H7225, רֵאשִׁית, or a returned lemma_key.
    Hebrew prefixes are resolved through lemma components. Standard and extended
    identifiers can be explicit: strongs:G26 or strongs_ext:G260. Ambiguity is reported.
    Default samples rotate across books; canonical order supports consecutive reading.
    Counts describe selected source word occurrences, not unique verses or RV renderings.
    Full-corpus lexicon statistics are labelled separately from filtered sample counts.
    """
    result = ConcordanceResponse(**db.search_lemma(lemma_or_strongs, testament, limit,
        include_variants, book, offset, sampling))
    lines = [f"## Lemma Concordance Search: `{result.query}`",
             f"Showing {result.total_found_in_sample} of {result.total_matches} matching occurrences ({sampling}).",
             result.count_scope]
    for word in result.occurrences:
        status = "selected" if word.is_selected else "unused variant"
        lines += [f"* **{word.ref}** `{word.word_link_id}` [{status}] {word.original_word} → {word.oet_gloss}",
                  f"  RV: {word.rv_text or 'Unavailable'}", f"  LV: {word.lv_text or 'Unavailable'}"]
    return respond(result, "\n".join(lines))


@evidence_tool
def lookup_word(word_id: str) -> Annotated[CallToolResult, WordLookupResponse]:
    """Inspect a linked source word, selection status, lemma components, grammar and verse context.

    Use IDs returned by interlinear/alignment results: JHNc1v1w5, GEN_1:1w1,
    or namespaced source-table row numbers such as NT:62345 or OT:1.
    Morphology uses SR-GNT or OSHB codes; unknown codes remain marked as unknown.
    No manuscript witness apparatus or dictionary definitions are supplied.
    """
    value = db.lookup_word(word_id)
    if value is None:
        raise ValueError(f"Word {word_id!r} not found; use an ID returned by get_passage(version='interlinear').")
    word = WordModel(**dict(value, ref=value['ref_str']))
    result = WordLookupResponse(word=word, verse_rv=value.get('verse_rv'), verse_lv=value.get('verse_lv'),
        lexicon=value.get('lexicon'), lexicon_entries=value['lexicon_entries'] if len(value['lexicon_entries']) > 1 else [],
        alignments=value['alignments'], provenance=value['provenance'])
    return respond(result, format_word_markdown(value))


@evidence_tool
def get_lexicon_entry(query: str, lang: Literal["auto", "greek", "hebrew", "aramaic"] = "auto") -> Annotated[CallToolResult, LexiconEntry]:
    """Retrieve a source lemma's selected-word count and complete OET-LV gloss distribution.

    These are corpus usage statistics, not a dictionary definition, etymology or semantic
    domain. Examples: logos, G3056, H7225, רֵאשִׁית, or a returned lemma_key.
    Ambiguous identifiers return candidate keys; use search_lemma for combined occurrences.
    """
    entry = db.get_lexicon_entry(query, lang=lang)
    if entry is None:
        raise ValueError(f"No lemma entry found for {query!r} ({lang}); use a lemma or identifier from an interlinear word lookup.")
    return respond(entry, format_lexicon_markdown(entry))


@evidence_tool
def get_translation_decisions(reference: str, limit: Annotated[int, Field(ge=1, le=100)] = 20,
                              offset: Annotated[int, Field(ge=0)] = 0) -> Annotated[CallToolResult, DecisionsResponse]:
    """Read RV/LV decision categories and supporting notes, with each annotation's source version.

    Source spans are half-open character offsets into that version's verse ESFM
    (get_passage include_raw=True). Category descriptions are not passage-specific
    rationales. A missing annotation does not mean no interpretive choice was made.
    """
    passage = db.get_passage(reference, limit=limit, offset=offset)
    result = DecisionsResponse(reference=reference, total_verses=passage.total_verses,
        next_offset=passage.next_offset,
        verses=[VerseDecisions(verse_id=v.verse_id, decisions=v.decisions, notes=v.notes) for v in passage.verses])
    lines = [f"## Explicit Translation Decisions in {reference}"]
    for verse in result.verses:
        lines.append(f"### {verse.verse_id}")
        for d in verse.decisions:
            lines.append(f"* [{d.source_version}] `{d.code}` {d.type}: {d.text or d.description or ''}")
        for note in verse.notes:
            lines.append(f"* [{note.source_version} note] {note.content}")
    return respond(result, "\n".join(lines))


@evidence_tool
def get_book_context(book: str, limit: Annotated[int, Field(ge=1, le=100)] = 50,
                     offset: Annotated[int, Field(ge=0)] = 0) -> Annotated[CallToolResult, BookContextResponse]:
    """Read source declarations, introductions, superscriptions and section outlines.

    Lists stable section IDs for get_section. Includes source-file hashes, corpus revision,
    attribution and source notes (including borrowed or draft text). Pages section lists.
    """
    result = BookContextResponse(**db.get_book_context(book, limit, offset))
    return respond(result)


@evidence_tool
def get_section(section_id: str, limit: Annotated[int, Field(ge=1, le=100)] = 20,
                offset: Annotated[int, Field(ge=0)] = 0) -> Annotated[CallToolResult, PassageResponse]:
    """Read a contextual section in parallel RV/LV with paragraph/poetry structure.

    Obtain section_id from get_book_context or get_passage(include_structure=True).
    Section headings and boundaries are editorial. Follow next_offset for long sections.
    """
    result = db.get_section(section_id, limit, offset)
    return respond(result, format_passage_markdown(result))


@evidence_tool
def get_oet_guide() -> Annotated[CallToolResult, GuideResponse]:
    """Read conventions needed to interpret OET text, word counts and translation annotations."""
    return respond(GuideResponse(guidance=OET_GUIDE, source_urls=[
        'https://oet.bible/Design/LiteralVersion/', 'https://oet.bible/Design/ReadersVersion/',
        'https://hb.openscriptures.org/parsing/HebrewMorphologyCodes.html']), OET_GUIDE)


# ---------------------------------------------------------------------------
# MCP Prompts
# ---------------------------------------------------------------------------

@server.prompt()
def comparative_exegesis(passage: str) -> str:
    """Guide contextual reading using source evidence and clearly labelled inference."""
    return f"""Study {passage} using OET.
1. Read get_oet_guide and get_book_context for the book; retrieve the enclosing get_section when useful.
2. Read get_passage(reference={passage!r}, include_structure=True, show_decision_codes=True).
3. Read compare_translations and translator notes. Distinguish RV choices from LV choices.
4. Use get_passage(version='interlinear', include_alignment=True) to identify actual source word IDs;
   use lookup_word before selecting lemma keys for search_lemma. Do not guess roots from English.
5. Compare contexts using representative samples and book filters; follow next_offset for exhaustive counts.
6. Cite passage references and corpus provenance. Separate source facts, translator explanations and
   your own interpretation. Do not infer etymology, dictionary senses or manuscript support from gloss counts.
"""


@server.prompt()
def biblical_word_study(lemma_or_strongs: str) -> str:
    """Guide a corpus word study without inventing lexical definitions or etymology."""
    return f"""Study {lemma_or_strongs!r} with get_lexicon_entry and search_lemma.
Read get_oet_guide first. Resolve ambiguous IDs using returned lemma keys. Record count scope,
source selection and language. Use representative samples across books and canonical pagination
for exhaustive investigation. Read surrounding sections for examples. Gloss distributions describe
OET-LV word-table renderings, not all dictionary senses or OET-RV frequencies; Hebrew whole-word
glosses may include several morphemes. Inspect RV wording through actual word alignments and notes.
Report supported contextual observations and limitations. Etymology, independent lexical definitions
and manuscript witness claims require separately cited sources that these tools do not provide.
"""


@server.prompt()
def translation_critique(passage: str) -> str:
    """Guide an evidence-based explanation of explicit OET translation annotations."""
    return f"""Study translation choices in {passage}.
Read get_oet_guide, then get_passage(reference={passage!r}, show_decision_codes=True,
include_structure=True). Read get_translation_decisions and compare_translations. Preserve each
annotation's source_version. Consult notes for documented explanations and original-word alignments
for linguistic evidence. Category labels alone do not explain a translator's motives. Label your own
proposed explanations as inference and state when no rationale is recorded. Read the surrounding
section before drawing conclusions, and cite the passage and corpus revision.
"""
