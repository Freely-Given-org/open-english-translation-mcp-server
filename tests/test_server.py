"""
tests/test_server.py

Integration tests for FastMCP Server primitives, resources, tools, and prompts.
"""

import pytest
import asyncio
from oet_mcp_server.server import server, db


@pytest.mark.asyncio
async def test_server_resources():
    # Test catalog resource
    cat_res = await server.read_resource("oet://catalog")
    assert len(cat_res) == 1
    assert "Open English Translation (OET) Canon Catalog" in cat_res[0].content

    # Test metadata resources
    rv_meta = await server.read_resource("oet://metadata/rv")
    assert "Readers' Version" in rv_meta[0].content
    assert "Referent Replacement" in rv_meta[0].content

    lv_meta = await server.read_resource("oet://metadata/lv")
    assert "Literal Version" in lv_meta[0].content
    assert "Added Copula" in lv_meta[0].content

    formats_res = await server.read_resource("oet://formats")
    assert "Formatting & Decision Code Reference" in formats_res[0].content

    # Test passage resource template
    p_res = await server.read_resource("oet://passage/parallel/John 1:1")
    assert "John (Yohan)" in p_res[0].content
    assert "OET-RV (Readers)" in p_res[0].content
    assert "OET-LV (Literal)" in p_res[0].content


@pytest.mark.asyncio
async def test_server_tools_get_passage():
    # Parallel markdown
    res = await server.call_tool("get_passage", {"reference": "John 1:1-2", "version": "parallel"})
    text = res.content[0].text
    assert "John (Yohan)" in text
    assert "OET-RV (Readers)" in text
    assert "OET-LV (Literal)" in text

    # JSON format
    res_json = await server.call_tool("get_passage", {"reference": "John 1:1", "format": "json"})
    text_json = res_json.content[0].text
    assert '"book_code": "JHN"' in text_json


@pytest.mark.asyncio
async def test_server_tools_comparison():
    res = await server.call_tool("compare_translations", {"reference": "John 1:1-3"})
    text = res.content[0].text
    assert "Translation Comparison & Linguistic Breakdown" in text
    assert "JHN.1.1" in text


@pytest.mark.asyncio
async def test_server_tools_search():
    res = await server.call_tool("search_text", {"query": "message God", "limit": 5})
    text = res.content[0].text
    assert "Search Results for 'message God'" in text


@pytest.mark.asyncio
async def test_server_tools_lemma_and_lexicon():
    res_lem = await server.call_tool("search_lemma", {"lemma_or_strongs": "logos", "limit": 5})
    text_lem = res_lem.content[0].text
    assert "Lemma Concordance Search: `logos`" in text_lem

    res_lex = await server.call_tool("get_lexicon_entry", {"query": "logos"})
    text_lex = res_lex.content[0].text
    assert "Lexicon Entry: `logos`" in text_lex


@pytest.mark.asyncio
async def test_server_prompts():
    prompts = await server.list_prompts()
    prompt_names = [p.name for p in prompts]
    assert "comparative_exegesis" in prompt_names
    assert "biblical_word_study" in prompt_names
    assert "translation_critique" in prompt_names

    p_val = await server.get_prompt("comparative_exegesis", {"passage": "Romans 1:16-17"})
    assert len(p_val.messages) > 0
    p_text = str(p_val.messages[0].content)
    assert "Romans 1:16-17" in p_text
