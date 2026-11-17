"""Verify real-book retrieval through the MCP stdio protocol, locally."""
import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    root = Path(__file__).resolve().parents[1]
    environment = dict(os.environ)
    environment.update(HF_HOME=str(root / 'data/hf-home'),
                       HF_XET_CACHE=str(root / 'data/hf-xet'), HF_HUB_DISABLE_XET='1')
    parameters = StdioServerParameters(command=sys.executable,
        args=['-m','book_research.cli','--db',str(root / 'data/real-books.sqlite3'),
              '--cpu-embed','serve'], env=environment)
    async with stdio_client(parameters) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert {tool.name for tool in tools.tools} == {'search','fetch','list_books'}
            assert all(tool.annotations.readOnlyHint for tool in tools.tools)
            inventory = await session.call_tool('list_books', {})
            assert not inventory.isError
            books = json.loads(inventory.content[0].text)
            assert books and all(book['passages'] == book['embedded_passages'] for book in books)
            response = await session.call_tool('search', {'query':'Time dilation and Lorentz transformations','limit':3})
            assert not response.isError
            results = json.loads(response.content[0].text)
            assert results['mode'] == 'hybrid' and results['results']
            hit = results['results'][0]
            response = await session.call_tool('fetch', {'id':hit['id'],'neighbours':1})
            assert not response.isError
            fetched = json.loads(response.content[0].text)
            assert any(str(item['id']) == hit['id'] for item in fetched['content'])
            report = {'status':'passed','transport':'stdio','tools':[tool.name for tool in tools.tools],
                      'books':len(books),'retrieval_ms':results['elapsed_ms'],
                      'top_title':hit['title'],'top_location':hit['page'],
                      'fetched_passages':len(fetched['content']),
                      'scope':'Real local book database. No external ChatGPT connection tested.'}
            (root / 'reports/real-book-mcp.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            print(json.dumps(report),flush=True)


if __name__ == '__main__':
    asyncio.run(main())
