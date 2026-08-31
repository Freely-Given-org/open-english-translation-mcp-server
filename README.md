# Open English Translation (OET) MCP Server

An official **Model Context Protocol (MCP)** server providing Large Language Models (LLMs) with high-speed, structured access to the **Open English Translation (OET)** of the Bible.

---

## What Makes the OET Different?

1. **Dual-Stream Parallel Translation**:
   * **Readers' Version (OET-RV)**: Natural, idiomatic, thought-for-thought modern English designed for macro-level discourse comprehension and fluency.
   * **Literal Version (OET-LV)**: Transparent, hyper-literal formal equivalence showing every added copula, article, transitive direct object, and untranslated particle.
2. **Word-Level Lexical Graph & Interlinear**:
   * Every word token is cross-linked via TSV datasets to Hebrew/Aramaic (`UHB`) and Greek (`SR-GNT`) dictionary entries, lemmas, Strong's numbers, morphological tags, and canonical gloss distributions.
3. **Explicit Translation Decision Tags (`\add`)**:
   * Encodes the exact reason for every addition or divergence (`@` for referent replacements, `≈` for rewordings, `#` for number changes, `%` for speech shifts, `^` for opposite phrasing, `?` for uncertainty, `≈`/`^`/`→` for Hebrew poetic parallelism, and `⇔` for clause re-ordering).

---

## Quick Start

### Running via `uvx`

```bash
uvx oet-mcp-server
```

### Installation from Source

```bash
git clone https://github.com/Freely-Given-org/open-english-translation-mcp-server.git
cd open-english-translation-mcp-server
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

### 1. Resources & Resource Templates

| URI Pattern | Description |
| :--- | :--- |
| `oet://catalog` | Lists all 66+ biblical books, chapter counts, testaments, and translation status. |
| `oet://metadata/rv` | Translation philosophy and `\add` decision encoding guide for OET-RV. |
| `oet://metadata/lv` | Markup guide for OET-LV (added copulas, untranslated particles, direct objects). |
| `oet://formats` | Complete specification of OET encoding formats and special character codes. |
| `oet://passage/{version}/{reference}` | Direct reading URI for any passage (`parallel`, `rv`, `lv`, `interlinear`). |
| `oet://word/{word_id}` | Lookup a specific word link token (e.g. `JHNc1v1w5`, `MAT_1:1w1`). |
| `oet://lexicon/{lang}/{query}` | Dictionary definition and canonical gloss distribution for a lemma or Strong's ID. |

---

### 2. Tools

#### `get_passage`
Retrieve scripture in parallel side-by-side, readers, literal, or interlinear table view.
* **Arguments**:
  * `reference` (*string*, required): e.g. `"John 1:1-5"`, `"Rom 8:28"`, `"Gen 1:1"`.
  * `version` (*string*): `"parallel"`, `"rv"`, `"lv"`, or `"interlinear"`.
  * `include_notes` (*bool*): Attach translator footnotes (`TD:`, `TC:`) and cross-references.
  * `format` (*string*): `"markdown"` or `"json"`.
  * `show_decision_codes` (*bool*): Reveal inline decision tags (`[@referent]`, `[≈rewording]`).

#### `compare_translations`
Calculates a granular comparative breakdown between OET-RV and OET-LV for a passage.
* **Arguments**:
  * `reference` (*string*, required): e.g. `"John 1:1-3"`, `"Romans 1:16-17"`.

#### `search_text`
High-speed full-text search across RV and LV using SQLite FTS5.
* **Arguments**:
  * `query` (*string*, required): e.g. `"true light"`, `"covenant"`.
  * `version` (*string*): `"both"`, `"rv"`, or `"lv"`.
  * `testament` (*string*): `"all"`, `"OT"`, or `"NT"`.
  * `limit` (*int*): Max results (default 20).

#### `search_lemma`
Concordance lookup showing how an original Hebrew/Greek root or Strong's ID is translated across the entire Bible.
* **Arguments**:
  * `lemma_or_strongs` (*string*, required): e.g. `"logos"`, `"G3056"`, `"bereshit"`, `"H7225"`.
  * `testament` (*string*): `"all"`, `"OT"`, `"NT"`.
  * `limit` (*int*): Max sample occurrences.

#### `lookup_word`
Drill down into a specific original word link token with complete grammatical parsing and manuscript collations.
* **Arguments**:
  * `word_id` (*string*, required): e.g. `"JHNc1v1w5"`, `"MAT_1:1w1"`.

#### `get_lexicon_entry`
Retrieve dictionary definition, semantic domain, and canonical distribution for a lemma or Strong's ID.
* **Arguments**:
  * `query` (*string*, required): Lemma or Strong's ID.
  * `lang` (*string*): `"auto"`, `"greek"`, `"hebrew"`.

#### `get_translation_decisions`
Isolates all explicit `\add` decision codes in a passage.
* **Arguments**:
  * `reference` (*string*, required): e.g. `"John 1:1-18"`.

---

### 3. MCP Prompts

* **`comparative_exegesis`**: Guided prompt leading an AI through rigorous exegesis (macro discourse in RV, micro syntax in LV, and root word studies).
* **`biblical_word_study`**: Guided prompt performing a complete biblical word study across genres and testaments.
* **`translation_critique`**: Guided prompt analyzing why modern dynamic translations diverge from literal syntax in difficult verses.

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
| `≈` *(line)* | Synonymous Parallelism | Second poetic line reiterates first | `\q1 ≈Yahweh gives comfort` |
| `^` *(line)* | Antithetic Parallelism | Second poetic line states contrast | `\q1 ^but Israel will fall` |
| `→` *(line)* | Synthetic Parallelism | Second poetic line reaches result | `\q1 →and he answered` |
| `⇔` *(verse)*| Order Swapped | Clauses inverted for English flow | `\v 10 ⇔The girls did...` |

---

## License

* Code: Open Source under the MIT / GPL-3.0 License.
* OET Text & Datasets: Creative Commons Attribution-ShareAlike ([CC-BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)) by [Freely-Given.org](https://freely-given.org).
