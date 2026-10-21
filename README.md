# Open English Translation (OET) MCP Server

An official **Model Context Protocol (MCP)** server providing Large Language Models (LLMs) with high-speed, structured access to the **Open English Translation (OET)** of the Bible.

The OET design specifications are at [OET.Bible](https://OET.Bible). The OET text is available on [GitHub here](https://github.com/Freely-Given-org/OpenEnglishTranslation--OET).

---

## What the server provides

The OET Readers’ Version (RV) and Literal Version (LV) are intended to be read together.
This server supplies parallel passages, translator notes, source-word links, lemma usage
statistics, and explicit translation annotations for LLM research.

- Greek interlinears and counts exclude unused source variants by default; variants remain
  available with their original selection marker.
- Hebrew and Aramaic words link to their actual lemma components, including prefixed forms.
- Standard Strong’s identifiers are distinct from the extended identifiers in SR-GNT.
- Decisions retain their source version and affected ESFM span. Their category is not a
  passage-specific explanation; translator notes and model inference remain distinct.
- Paragraph/poetry structure, introductions, sections, source declarations, word alignments,
  and decoded morphology are available on demand.
- Every tool is read-only and returns structured data plus readable text. Searches and passages
  have bounded pages and continuation offsets.

The lexical data describes **OET-LV word-table usage**, not dictionary definitions, etymology,
manuscript witness evidence, or RV gloss frequencies. Hebrew whole-word glosses can contain
several morphemes. Read `get_oet_guide` before interpreting unfamiliar conventions.

---

## Quick Start

### Running via `uvx`

```bash
uvx oet-mcp-server
```

### Installation from Source

> **Note:** the approximately 417 MiB corpus database is a **Git-LFS** file. Without
> `git lfs pull` you get only a ~130-byte LFS pointer, and every data tool
> fails at runtime.

```bash
git clone https://github.com/Freely-Given-org/open-english-translation-mcp-server.git
cd open-english-translation-mcp-server
git lfs install && git lfs pull   # materialize the real corpus database
uv sync
uv run oet-mcp-server
```

---

## AI Client Configuration

### 1. Claude Desktop / Antigravity / Cursor

Add to your `claude_desktop_config.json` or MCP settings:

```json
{
  "mcpServers": {
    "oet-bible": {
      "command": "uvx",
      "args": ["oet-mcp-server"]
    }
  }
}
```

Or for local development:

```json
{
  "mcpServers": {
    "oet-bible": {
      "command": "uv",
      "args": [
        "--directory",
        "/srv/FreelyGiven/open-english-translation-mcp-server",
        "run",
        "oet-mcp-server"
      ]
    }
  }
}
```

---

## MCP Server Capabilities

### Tools

| Tool | Purpose | Useful options |
| :--- | :--- | :--- |
| `get_oet_guide` | Interpretation conventions and evidence limits | No arguments |
| `get_passage` | Parallel, RV, LV, or interlinear passages | `include_notes`, `show_decision_codes`, `include_structure`, `include_alignment`, `include_raw`, `include_variants`, `limit`, `offset` |
| `get_book_context` | Introductions, source notes, version declarations and section outlines | `book`, `limit`, `offset` |
| `get_section` | Read a complete contextual section in bounded pages | `section_id`, `limit`, `offset` |
| `compare_translations` | Version-specific annotation comparison | `reference`, `limit`, `offset` |
| `get_translation_decisions` | Decision categories, source spans and supporting notes | `reference`, `limit`, `offset` |
| `search_text` | English keyword/phrase matches in the requested translation | `version`, `testament`, `book`, `limit`, `offset` |
| `search_lemma` | Selected source-word counts and representative occurrences | `testament`, `book`, `include_variants`, `sampling`, `limit`, `offset` |
| `lookup_word` | Selection status, lemma components, grammar and aligned English | `word_id` |
| `get_lexicon_entry` | Complete LV gloss distribution and selected/unused/unglossed counts | `query`, `lang` (`auto`, `greek`, `hebrew`, `aramaic`) |

Examples:

```text
get_passage(reference="John 1:1", version="interlinear", include_alignment=true)
get_passage(reference="Psalm 1:1-6", include_structure=true)
get_book_context(book="John")
get_section(section_id="JHN.RV.S1")
search_lemma(lemma_or_strongs="G3056", sampling="representative")
search_lemma(lemma_or_strongs="H7225", book="Genesis", sampling="canonical")
lookup_word(word_id="GEN_1:1w1")
```

`get_passage` defaults to 20 verse records, with at most 10 in interlinear mode.
Other limits are described in each tool schema; all are capped at 100. Repeat the same
request with the returned `next_offset` to continue. Grouped source verses such as `1–3`
retain their labels and can be retrieved by requesting a verse inside the group. RV and LV
may use different groupings; unavailable matching segments are identified explicitly.

Text search treats unquoted words as AND terms and double-quoted text as an exact phrase.
Punctuation is accepted; FTS operators are not exposed. Version filters constrain the search
itself. Results include a filtered total, not just the page size.

Lemma lookup accepts original-script or source-transliterated lemmas, accent variants,
standard Strong’s IDs (`G3056`, `H7225`), and returned lemma keys. Extended Greek IDs remain
accepted when unambiguous. Disambiguate explicitly with `strongs:G260` versus
`strongs_ext:G260`. Do not infer a root from an English gloss. Ambiguous lemma lookup returns
candidate keys; concordance search can combine matching lemma entries without double-counting
source words. Representative sampling rotates across books; canonical sampling supports
consecutive traversal. Full-corpus statistics are labelled separately from filtered samples.

Word IDs include `JHN_1:1w5`, `JHNc1v1w5`, and namespaced source-table rows (`NT:62342`, `OT:1`).
Alignment spans and decision spans are half-open character offsets in the returned verse ESFM,
not in the cleaned English text. Source-table IDs are revision-specific. Links are imported
from the source; missing links are not guessed. Greek word order follows source-table positions.
Decoded grammar names its scheme and preserves unknown codes rather than guessing their meaning.

`format="markdown"` is the default passage reading view. `format="json"` changes its text
representation; both formats always return typed MCP `structuredContent` with an output schema.
Raw ESFM, structure and alignments are opt-in. Null and default optional values are omitted.
Public passage URLs may show a newer edition than the local corpus; cite its revision and hashes.

### Resources and prompts

Resources: `oet://guide`, `oet://catalog`, `oet://metadata/rv`, `oet://metadata/lv`,
`oet://formats`, `oet://passage/{version}/{reference}`, `oet://word/{word_id}`,
and `oet://lexicon/{lang}/{query}`. Resource passage reads use a bounded default page;
use the tools to continue or request detailed views.

The `comparative_exegesis`, `biblical_word_study`, and `translation_critique` prompts
start from context and source evidence. They distinguish translator notes from model
interpretation and do not request unsupported dictionary or manuscript claims.

### Corpus updates and compatibility

Version 0.2 requires MCP SDK 2.1.1 or newer within major version 2 and **corpus schema 2**.
Older corpus files are rejected with a rebuild message. The database is approximately 417 MiB
and remains a Git-LFS artifact. Build from the local OET checkout with:

```bash
uv run python scripts/build_db.py
uv run python scripts/verify_db.py
uv run pytest -q
```

The builder writes a temporary database and replaces the destination only after a successful
build and integrity check. `--output /path/to/corpus.db` builds to a different destination.
Provenance records the OET repository revision, whether source files differ from that revision,
source-file and word-table hashes, build timestamp, attribution and text licence.
Per-book declarations retain source edition and adaptation notes, including WEBBE material.

Regression scenarios cover unused variants in John 1:1, `logos` counts, prefixed Hebrew stems,
invalid ranges, version/language filters, decision attribution, recovered notes, poetry boundaries,
word alignment, grouped verses, pagination, morphology and the MCP output contract.

---

## OET Translation Decision Codes Reference

| Code | Category | Meaning | Example |
| :---: | :--- | :--- | :--- |
| `@` | Referent Replacement | Pronoun changed to explicit name | `\add @David\add*` |
| `≈` | Rewording | Rephrased for modern clarity | `\add ≈answered\add*` |
| `#` | Number Change | Singular generalized to plural | `\add #people\add*` |
| `%` | Person Shift | Direct speech flattened to indirect | `\add %that he will\add*` |
| `^` | Opposite Phrasing | Saying phrased positively | `\add ^always open\add*` |
| `+` | Added Article | Article added for English grammar | `\add +the\add*` |
| `=` | Added Copula | Helping verb ('is', 'was') added | `\add =is\add*` |
| `<` | Added Direct Object | Object added for transitive verb | `\add <it\add*` |
| `>` | Added Implied Object | Implied entity ('thing', 'person') | `\add >things\add*` |
| `≡` | Elided Repetition | Repeated elided word for clarity | `\add ≡pursued\add*` |
| `&` | Added Owner | Possessive added for naturalness | `\add &his\add*` |
| `?` | Uncertainty Marker | Translator doubt regarding intent | `\add ?in the clouds\add*` |
| `!` | Alternate Name | Familiar/traditional name added in parentheses after an OET distinctive name | `\add !(Moses)\add*` |
| `≈` *(line)* | Synonymous Parallelism | Second poetic line reiterates first | `\q1 ≈Yahweh gives comfort` |
| `^` *(line)* | Antithetic Parallelism | Second poetic line states contrast | `\q1 ^but Israel will fall` |
| `→` *(line)* | Synthetic Parallelism | Second poetic line reaches result | `\q1 →and he answered` |
| `⇔` *(verse)*| Order Swapped | Clauses inverted for English flow | `\v 10 ⇔The girls did...` |

---

## Deployment (Docker)

> **Important:** the approximately 417 MiB corpus database is stored as a **Git-LFS** file. A
> checkout without `git lfs pull` contains only a ~130-byte LFS pointer, which
> makes every data tool fail at runtime. The Dockerfile guards against this:
> `scripts/verify_db.py` runs at build time and **fails the build** if the DB
> isn't a real, queryable SQLite database.

### Recommended: use the CI-built image

The `.github/workflows/docker-publish.yml` workflow materializes the LFS data,
builds the image, and pushes it to
`ghcr.io/freely-given-org/open-english-translation-mcp-server`
as `:latest` and `:main` (on pushes to `main`) and `:v*` (on version tags).
Deploying servers then pull instead of building:

> **Before this works**, the workflow must have published at least one image
> (push to `main`, create a `v*` tag, or trigger it from the GitHub Actions
> tab). Until then `docker compose pull` fails, so use the local-build path
> below.

```bash
git clone --filter=blob:none https://github.com/Freely-Given-org/open-english-translation-mcp-server.git
cd open-english-translation-mcp-server
docker compose pull          # pulls the GHCR image
docker compose up -d         # no local build, no LFS data needed on the server
```

`OET_MCP_IMAGE` overrides the image used by `docker-compose.yml`.

### Building locally

```bash
git lfs install && git lfs pull   # materialize the real corpus DB
docker compose up -d --build
```

The container exposes a Docker healthcheck (`scripts/healthcheck.py`) that
validates the DB and that the MCP proxy is accepting connections, so
`docker inspect` / orchestrators report the deploy as unhealthy if the DB is
invalid.

---

## License

* Code: Open Source under [CC0 1.0 Universal](https://creativecommons.org/publicdomain/zero/1.0/) (see the `LICENSE` file).
* [OET Text & Datasets](https://github.com/Freely-Given-org/OpenEnglishTranslation--OET): Creative Commons Attribution-ShareAlike ([CC-BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)) by [Freely-Given.org](https://freely-given.org).
