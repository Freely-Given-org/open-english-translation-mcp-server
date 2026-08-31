"""
src/oet_mcp_server/server.py

Model Context Protocol (MCP) Server implementation for the Open English Translation (OET).
"""

import json
from typing import Optional, Literal
from mcp.server.mcpserver import MCPServer

from .database import OETDatabase
from .models import PassageResponse, LexiconEntry, ComparisonDiffItem

# Initialize MCPServer and DB
server = MCPServer("Open English Translation (OET) Server")
db = OETDatabase()


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
2. **Transparent Decision Tagging (`\\add`)**: Where significant translation choices occur, the source text encodes the rationale:
   - `@`: **Referent Replacement** (e.g. Replacing pronoun 'he' with explicit name 'David' or 'the messenger' for context clarity when starting pericopes).
   - `≈`: **Rewording** (Rephrasing clauses or idioms into modern conversational English).
   - `#`: **Number Change** (Generalizing ancient masculine singular proverbs to gender-neutral plural sayings).
   - `%`: **Person Shift** (Flattening multi-nested direct quotes into clear indirect speech).
   - `^`: **Opposite Phrasing** (Phrasing negative constructions positively for modern comprehension).
   - `?`: **Uncertainty Marker** (Indicates translator doubt regarding original intent).
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
- **Nomina Sacra (`\\nd`)**:
  - Highlights divine names and titles (God, Yahweh, Jesus, Messiah).
"""


@server.resource("oet://formats")
def get_formats_resource() -> str:
    """Complete specification of OET encoding formats, special character codes, and markup tags."""
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
    """Direct resource template for retrieving dictionary definitions for a lemma or Strong's ID."""
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
        f"*Version*: **{res.version.upper()}** | *Verses*: {res.verses_count}",
        ""
    ]

    current_section = None
    for v in res.verses:
        if v.section_heading and v.section_heading != current_section:
            current_section = v.section_heading
            lines.append(f"### {current_section}\n")

        v_ref = f"{res.english_name} {v.chapter}:{v.verse}"
        if res.version.lower() == "parallel":
            lines.append(f"**{v_ref}**")
            lines.append(f"* **OET-RV (Readers)**: {v.rv_text}")
            lines.append(f"* **OET-LV (Literal)**: {v.lv_text}")
            lines.append("")
        elif res.version.lower() == "rv":
            lines.append(f"**{v.verse_label}** {v.rv_text}")
        elif res.version.lower() == "lv":
            lines.append(f"**{v.verse_label}** {v.lv_text}")
        elif res.version.lower() == "interlinear":
            lines.append(f"**{v_ref}**")
            lines.append(f"*RV*: {v.rv_text}")
            lines.append(f"*LV*: {v.lv_text}")
            if v.words:
                lines.append("\n| Seq | Original | Lemma | Strong's | Morph | Literal Gloss | OET Gloss |")
                lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
                for w in v.words:
                    lines.append(f"| {w.ref.split('w')[-1]} | {w.original_word} | {w.sr_lemma or w.original_lemma} | {w.strongs or '-'} | `{w.morphology or '-'}` | {w.vlt_gloss or '-'} | {w.oet_gloss or '-'} |")
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

    return "\n".join(lines)


def format_word_markdown(w: dict) -> str:
    lines = [
        f"## Wordlink Token: `{w.get('ref_str')}` (#{w.get('word_link_id')})",
        "",
        f"- **Original Word**: `{w.get('original_word')}` ({w.get('original_word_clean')})",
        f"- **Lemma**: `{w.get('sr_lemma') or w.get('original_lemma')}`",
        f"- **Strong's Number**: `{w.get('strongs')}`",
        f"- **Part of Speech / Role**: `{w.get('role')}`",
        f"- **Morphological Parsing**: `{w.get('morphology')}`",
        f"- **Literal Gloss (VLT)**: *{w.get('vlt_gloss')}*",
        f"- **OET Gloss**: *{w.get('oet_gloss')}*",
        f"- **Contextual Gloss**: *{w.get('contextual_gloss')}*",
    ]
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
        lines.append("\n### Canonical Usage Statistics")
        lines.append(f"- Total Canonical Occurrences: **{lex.get('total_occurrences')}**")
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
        f"- **Total Biblical Occurrences**: **{entry.total_occurrences}**",
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

@server.tool()
def get_passage(
    reference: str,
    version: Literal["parallel", "rv", "lv", "interlinear"] = "parallel",
    include_notes: bool = True,
    format: Literal["markdown", "json"] = "markdown",
    show_decision_codes: bool = False
) -> str:
    """
    Retrieve Scripture from the Open English Translation (OET).
    
    Supports:
    - 'parallel': Side-by-side comparison of Readers' Version (OET-RV) and Literal Version (OET-LV).
    - 'rv': Easy-to-read Readers' Version.
    - 'lv': Hyper-literal, grammatically transparent Literal Version.
    - 'interlinear': Token-level table with original Greek/Hebrew, transliterated lemmas, Strong's numbers, morphology, and glosses.
    
    Args:
        reference: Standard reference (e.g. 'John 1:1-5', 'Rom 8:28', 'Gen 1:1-3', 'JHN.1.1').
        version: Translation view ('parallel', 'rv', 'lv', 'interlinear').
        include_notes: Whether to attach translator footnotes and cross-references.
        format: Output format ('markdown' or 'json').
        show_decision_codes: If true, reveals inline decision codes (e.g. [@referent], [≈rewording], [+the]).
    """
    res = db.get_passage(
        reference=reference,
        version=version,
        include_notes=include_notes,
        format=format,
        show_decision_codes=show_decision_codes
    )
    if format == "json":
        return res.model_dump_json(indent=2)
    return format_passage_markdown(res, show_decision_codes=show_decision_codes)


@server.tool()
def compare_translations(reference: str) -> str:
    """
    Isolates and computes detailed translation divergencies between OET-RV and OET-LV for a passage.
    
    Identifies:
    - Added words in LV (copulas, articles, direct objects).
    - Untranslated original language particles (Greek articles before proper names, Hebrew DOM).
    - Explicit RV translation decisions (referents substituted for pronouns, rewordings, number changes).
    - Poetic parallelism (≈) and clause inversions (⇔).
    
    Args:
        reference: Scripture reference (e.g. 'John 1:1-3', 'Romans 1:16-17').
    """
    diffs = db.compare_passage(reference)
    lines = [
        f"## Translation Comparison & Linguistic Breakdown: {reference}",
        ""
    ]
    for d in diffs:
        lines.append(f"### {d.verse_id}")
        lines.append(f"* **OET-RV (Readers)**: {d.rv_text}")
        lines.append(f"* **OET-LV (Literal)**: {d.lv_text}")
        
        details = []
        if d.added_words_lv:
            details.append(f"  * **Words Added in LV for Grammar**: {', '.join(f'`{w}`' for w in d.added_words_lv)}")
        if d.untranslated_words_lv:
            details.append(f"  * **Original Particles Untranslated in LV**: {', '.join(f'`{w}`' for w in d.untranslated_words_lv)}")
        if d.translation_decisions_rv:
            dec_strs = [f"**{dec.type}** (`{dec.code}`): \"{dec.text}\"" for dec in d.translation_decisions_rv]
            details.append(f"  * **RV Translation Decisions**: {'; '.join(dec_strs)}")
        if d.syntactic_notes:
            details.append(f"  * **Syntactic Structure**: {d.syntactic_notes}")
            
        if details:
            lines.append("\n".join(details))
        lines.append("")
        
    return "\n".join(lines)


@server.tool()
def search_text(
    query: str,
    version: Literal["both", "rv", "lv"] = "both",
    testament: Literal["all", "OT", "NT"] = "all",
    limit: int = 20
) -> str:
    """
    High-speed full-text search across the Open English Translation using SQLite FTS5.
    
    Args:
        query: Search keywords or exact phrase (e.g. 'true light', 'messenger God', 'covenant').
        version: Search in 'rv', 'lv', or 'both'.
        testament: Filter by 'all', 'OT', or 'NT'.
        limit: Maximum number of verse matches (default: 20).
    """
    results = db.search_text(query=query, version=version, testament=testament, limit=limit)
    if not results:
        return f"No matches found for query '{query}'."
        
    lines = [
        f"## Search Results for '{query}' ({len(results)} matches)",
        ""
    ]
    for r in results:
        lines.append(f"### {r['reference']} [{r['testament']}]")
        if "rv_text" in r:
            lines.append(f"* **RV**: {r['rv_text']}")
        if "lv_text" in r:
            lines.append(f"* **LV**: {r['lv_text']}")
        lines.append("")
        
    return "\n".join(lines)


@server.tool()
def search_lemma(
    lemma_or_strongs: str,
    testament: Literal["all", "OT", "NT"] = "all",
    limit: int = 30
) -> str:
    """
    Find all biblical occurrences of an original Hebrew/Greek root or Strong's number.
    Returns the exact gloss frequency distribution across both OET-RV and OET-LV.
    
    Args:
        lemma_or_strongs: Lemma (e.g. 'logos', 'agape', 'bereshit') or Strong's ID ('G3056', 'H7225').
        testament: 'all', 'OT', or 'NT'.
        limit: Max occurrences to return (default: 30).
    """
    res = db.search_lemma(lemma_or_strongs, testament=testament, limit=limit)
    lines = [
        f"## Lemma Concordance Search: `{res['query']}`",
        ""
    ]
    if "lexicon_info" in res:
        lex = res["lexicon_info"]
        lines.append(f"- **Original Lemma**: `{lex['lemma']}` ({lex['lemma_display']})")
        lines.append(f"- **Language**: {lex['lang'].title()} | **Strong's**: `{lex['strongs']}`")
        lines.append(f"- **Primary OET Gloss**: *{lex['primary_gloss']}*")
        lines.append(f"- **Total Canonical Occurrences**: **{lex['total_canonical_occurrences']}**")
        lines.append("\n### Canonical Gloss Distribution in OET")
        for g, c in lex.get("canonical_gloss_distribution", {}).items():
            lines.append(f"* *{g}*: {c}×")
        lines.append("")
        
    lines.append(f"### Sample Occurrences (Showing {res['total_found_in_sample']})")
    for occ in res["occurrences"]:
        lines.append(f"**{occ['ref']}** — `{occ['original_word']}` ({occ['morphology']}) $\\rightarrow$ *{occ['oet_gloss']}*")
        lines.append(f"* *RV*: {occ['rv_text']}")
        lines.append(f"* *LV*: {occ['lv_text']}\n")
        
    return "\n".join(lines)


@server.tool()
def lookup_word(word_id: str) -> str:
    """
    Drill down into a specific original word link token (e.g. 'JHNc1v1w5' or 'JHN_1:1w5').
    Returns complete grammatical parsing, SR-GNT / UHB collation, Strong's number, and gloss.
    
    Args:
        word_id: Token ID (e.g. 'JHNc1v1w5', 'MAT_1:1w1', 'GEN_1:1w1').
    """
    w = db.lookup_word(word_id)
    if not w:
        return f"Word token '{word_id}' not found."
    return format_word_markdown(w)


@server.tool()
def get_lexicon_entry(query: str, lang: Literal["auto", "greek", "hebrew"] = "auto") -> str:
    """
    Retrieve full lexicon definition, semantic range, and distribution statistics for a lemma or Strong's ID.
    
    Args:
        query: Greek/Hebrew lemma or Strong's ID (e.g. 'G3056', 'logos', 'H7225', 'shalom').
        lang: Language filter ('auto', 'greek', 'hebrew').
    """
    entry = db.get_lexicon_entry(query, lang=lang)
    if not entry:
        return f"No lexicon entry found for '{query}'."
    return format_lexicon_markdown(entry)


@server.tool()
def get_translation_decisions(reference: str) -> str:
    """
    Extract all explicit translator decision annotations (\\add tags, referents, rewordings) in a passage.
    
    Args:
        reference: Scripture reference (e.g. 'John 1:1-18', 'Romans 1:1-7').
    """
    decisions = db.get_translation_decisions(reference)
    if not decisions:
        return f"No explicit \\add decision tags recorded in {reference}."
        
    lines = [
        f"## Explicit Translation Decisions in {reference}",
        ""
    ]
    for d in decisions:
        lines.append(f"### {d['reference']}")
        lines.append(f"**Annotated RV**: {d['rv_text']}")
        lines.append("**Decisions Applied**:")
        for dec in d["decisions"]:
            lines.append(f"* `{dec['code']}` **{dec['type']}**: \"{dec['text']}\"")
        lines.append("")
        
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# MCP Prompts
# ---------------------------------------------------------------------------

@server.prompt()
def comparative_exegesis(passage: str) -> str:
    """
    Guides the AI through a rigorous comparative exegesis using the OET parallel text and lexical tools.
    """
    return f"""You are conducting an in-depth biblical exegesis of {passage} using the Open English Translation (OET).

Follow this step-by-step exegetical procedure:
1. Call `get_passage(reference="{passage}", version="parallel")` to examine the Readers' Version (OET-RV) and Literal Version (OET-LV) side by side.
2. Analyze the macro-level discourse, paragraph structure, and poetic parallelism using the **OET-RV**.
3. Analyze the micro-level grammatical syntax, added copulas/articles, and untranslated particles using the **OET-LV**.
4. Call `compare_translations(reference="{passage}")` to isolate explicit translation decisions (referent substitutions, rewordings, number changes).
5. Identify 2–3 central theological keywords in the passage and call `search_lemma` to inspect their original Greek/Hebrew roots, Strong's numbers, and canonical gloss distributions.
6. Synthesize your exegetical findings into a balanced, scholarly commentary explaining both the theological flow and the underlying linguistic mechanics.
"""


@server.prompt()
def biblical_word_study(lemma_or_strongs: str) -> str:
    """
    Guides the AI through a comprehensive biblical word study across the OET canon.
    """
    return f"""You are conducting a thorough biblical word study on `{lemma_or_strongs}` using the Open English Translation (OET).

Follow these steps:
1. Call `get_lexicon_entry(query="{lemma_or_strongs}")` to retrieve the lexical definition, semantic range, Strong's number, and total occurrences.
2. Call `search_lemma(lemma_or_strongs="{lemma_or_strongs}", limit=30)` to inspect how the term is translated across different biblical books and genres.
3. Note how the OET-RV translates the term in narrative vs poetic vs epistolary contexts.
4. Contrast the literal rendering (OET-LV) with the contextual dynamic choices (OET-RV).
5. Produce a structured word study report detailing:
   - Root Etymology & Lexical Range
   - Statistical Distribution of English Glosses in the OET
   - Contextual Nuances Across Canon
   - Exegetical and Practical Significance.
"""


@server.prompt()
def translation_critique(passage: str) -> str:
    """
    Guides the AI in analyzing why modern dynamic translations diverge from literal syntax for a challenging passage.
    """
    return f"""You are analyzing the translation choices and linguistic divergence in {passage} using the Open English Translation.

Follow these steps:
1. Call `get_passage(reference="{passage}", version="parallel", show_decision_codes=True)` to inspect the annotated text.
2. Call `compare_translations(reference="{passage}")` to list every added word, copula, untranslated particle, and referent substitution.
3. Review any translator footnotes (`TD:` translation difficulty notes).
4. Explain why the literal Hebrew/Greek word order or structure would be awkward or misleading in modern English.
5. Explain the linguistic rationale behind each specific decision tag (`@` referent, `≈` rewording, `#` number change, `%` person shift).
"""
