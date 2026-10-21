"""Exercise the published MCP contract through a real stdio client connection."""
import asyncio
import sys
from pathlib import Path

import pytest
from jsonschema import validate
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@pytest.mark.asyncio
async def test_stdio_research_workflow_and_error_recovery():
    async def workflow():
        params = StdioServerParameters(command=sys.executable, args=['-m', 'oet_mcp_server'],
                                       cwd=Path(__file__).resolve().parents[1])
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                initialized = await session.initialize()
                assert 'get_oet_guide' in initialized.instructions
                listed = await session.list_tools()
                schemas = {t.name: t.output_schema for t in listed.tools}
                cases = {
                    'get_oet_guide': {},
                    'get_passage': {'reference': 'John 1:1', 'version': 'interlinear'},
                    'get_book_context': {'book': 'John'},
                    'get_section': {'section_id': 'JHN.RV.S1'},
                    'compare_translations': {'reference': 'John 1:1'},
                    'get_translation_decisions': {'reference': 'John 1:1'},
                    'search_text': {'query': 'DOM', 'version': 'rv'},
                    'search_lemma': {'lemma_or_strongs': 'G3056'},
                    'lookup_word': {'word_id': 'GEN_1:1w1'},
                    'get_lexicon_entry': {'query': 'H7225'},
                }
                for name, args in cases.items():
                    result = await session.call_tool(name, args)
                    assert not result.is_error, (name, result)
                    validate(result.structured_content, schemas[name])
                    assert result.content
                bad_reference = await session.call_tool('get_passage', {'reference': 'John 1:999'})
                assert bad_reference.is_error
                assert 'endpoint' in bad_reference.content[0].text
                bad_limit = await session.call_tool('search_text', {'query': 'God', 'limit': -1})
                assert bad_limit.is_error
                good = await session.call_tool('get_passage', {'reference': 'John 1:1'})
                assert not good.is_error
    await asyncio.wait_for(workflow(), timeout=30)
