import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from book_research.core import Catalogue


class MCPTests(unittest.TestCase):
    def test_real_stdio_protocol_search_fetch_and_readonly_tools(self):
        async def scenario(db):
            parameters = StdioServerParameters(command=sys.executable,
                args=['-m','book_research.cli','--db',str(db),'serve'])
            async with stdio_client(parameters) as (reader, writer):
                async with ClientSession(reader, writer) as session:
                    initialized = await session.initialize()
                    self.assertIn('ONE coherent', initialized.instructions)
                    tools = await session.list_tools()
                    self.assertEqual({tool.name for tool in tools.tools}, {'search','fetch','list_books'})
                    self.assertTrue(all(tool.annotations.readOnlyHint for tool in tools.tools))
                    result = await session.call_tool('search', {'query':'catalyst'})
                    self.assertFalse(result.isError)
                    data = json.loads(result.content[0].text)
                    self.assertEqual(data['research_style'], 'research-synthesis-v1')
                    self.assertIn('citation', data['results'][0])
                    ident = data['results'][0]['id']
                    fetched = await session.call_tool('fetch', {'id':ident})
                    self.assertFalse(fetched.isError)
                    self.assertIn('catalyst', fetched.content[0].text)
                    fetched_data = json.loads(fetched.content[0].text)
                    self.assertIn('reference', fetched_data['citation'])
                    invalid = await session.call_tool('fetch', {'id':'999999'})
                    self.assertTrue(invalid.isError)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'test.txt'
            source.write_text('A catalyst changes the rate of a chemical reaction.', encoding='utf-8')
            catalogue = Catalogue(root / 'test.sqlite3')
            catalogue.ingest(source)
            catalogue.close()
            asyncio.run(scenario(root / 'test.sqlite3'))
