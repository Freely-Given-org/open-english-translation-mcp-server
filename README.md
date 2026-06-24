# open-english-translation-mcp-server
MCP Server to make the Open English Translation of the Bible (OET) easily available to LLMs

### Prompt

My (open source) Open English Translaton of the Bible (OET.Bible) has a "Readers' Version" and a "Literal Version" side by side, with all words linked by a word number to their Hebrew and Greek original words. Explain how a MCP could make this info easily accessible to LLMs.

### Gemini's response

To make a side-by-side, word-linked dataset like the Open English Translation (OET) seamlessly accessible to Large Language Models, you want to shift from treating the Bible as flat text to treating it as a graph-relational database.

An MCP (Model Context Protocol) Server acts as the perfect interface because it allows the LLM to dynamically fetch exactly the context it needs (e.g., just the underlying Greek root of a specific word or a comparison of a single verse) rather than choking the model's context window with thousands of lines of unnecessary text.

Here is a structural breakdown of how you can organize your OET data into the three core pillars of MCP—Resources, Resource Templates, and Tools—to make it instantly navigable for an AI agent.

1. Resources: Exposing the Parallel Text
Resources are static or semi-static entry points that the LLM can read like open files. You can expose your individual translation versions here.

oet://catalog: Returns an overview of books, chapter counts, and available versions (literal, readers).

oet://literal/metadata and oet://readers/metadata: Provides the translation philosophy for each version. This is critical because when an LLM understands why the Literal version chose a rigid structure over the Readers' fluid layout, its commentary becomes vastly more accurate.

2. Resource Templates: Dynamic Lookups
Resource templates use URI patterns to let the LLM request granular chunks of the parallel text on demand.

Instead of passing entire chapters, the LLM can query specific structural addresses:

oet://{version}/{book}/{chapter}: Allows the model to pull just the text it needs to answer a user's query.

oet://lexicon/{word_number}: Maps directly to your Hebrew/Greek dictionary definitions, grammatical parsing, and Strong’s alignment.

When the LLM reads a template like oet://parallel/Gen/1/1, your MCP server can return a beautifully structured payload (like JSON or Markdown) displaying the alignment:

JSON
{
  "reference": "Genesis 1:1",
  "alignment": [
    {
      "word_number": "H7225",
      "original": "בְּרֵאשִׁ֖ית",
      "literal": "In the beginning",
      "readers": "In the beginning"
    },
    {
      "word_number": "H1254",
      "original": "בָּרָ֣א",
      "literal": "created",
      "readers": "created"
    },
    {
      "word_number": "H430",
      "original": "אֱלֹהִ֑ים",
      "literal": "God",
      "readers": "God"
    }
  ]
}
3. Tools: Enabling Analytical Action
Tools are executable Python or Rust functions that the LLM can actively call to perform calculations, scans, or transformations across the OET components. This is where the magic happens for your cross-linked data.

Tool A: find_word_occurrences(word_number: str)
Instead of the LLM guessing where else a Hebrew or Greek word appears, this tool queries your database and returns a list of every verse utilizing that exact word_number.

AI Benefit: If a user asks, "How does the OET translate 'Logos' outside of the Gospel of John?", the LLM can call this tool to see every rendering in both the Literal and Readers' versions instantly.

Tool B: compare_translation_diffs(book: str, chapter: int, verse: int)
This tool can isolate rows where the divergence between the Literal and Readers' text crosses a certain linguistic threshold.

AI Benefit: The LLM can automatically flag significant translation choices and proactively explain to the user: "Notice that in the Literal version it uses word X to match the Hebrew syntax, but the Readers' version transforms it into phrase Y for natural flow."

Tool C: get_translation_notes(word_number: str, context_verse: str)
If your dataset includes translator annotations or alignment justifications, this tool serves them up right when the model spots a complex translation knot.

How the LLM Experiences Your OET Data Loop
When a user asks an MCP-enabled LLM: "Why does the Readers' version of Romans 1:17 use 'faith' differently than the Literal version?", the model executes a seamless chain of thoughts behind the scenes:

1. LLM detects it needs OET context ──> Calls template `oet://parallel/Rom/1/17`
2. Server responds with both versions and the underlying Greek word numbers.
3. LLM spots the word number for "faith/faithfulness" (G4102).
4. LLM calls tool `find_word_occurrences("G4102")` to see the broader translation patterns.
5. LLM synthesizes a deep, highly precise textual commentary without ever hallucinating the verses.

By publishing this setup as an open package (like a PyPI package built via your uv/Maturin workflows), any researcher or developer running an MCP-compliant application can hook your entire interconnected translation ecosystem straight into their AI workspace.

### Prompt

Is there a preferred name for the GitHub repo?

### Response

When structuring an open-source Model Context Protocol (MCP) server for a project with multiple repositories like yours under the Freely-Given-org umbrella, there are two distinct naming conventions to consider depending on where it lives:

If you decide to isolate the MCP server code into its own repository (which makes it easier to track issues, manage uv/Maturin workflows, and target the official MCP registry), the preferred, community-standard naming scheme is lowercase, hyphenated, appending -mcp-server:

open-english-translation-mcp-server

Why? The MCP developer community uses this pattern (e.g., sqlite-mcp-server, postgres-mcp-server) because it makes the purpose of the repository immediately scannable on GitHub and mirrors the naming structure required if you register it globally.

For the PyPI Package Name

Regardless of which GitHub structure you choose, when you publish the package to PyPI so LLMs can execute it via uvx, the preferred package name is:

Bash
oet-mcp-server
This keeps the CLI command incredibly clean for users attaching it to their local tools:
uvx oet-mcp-server


