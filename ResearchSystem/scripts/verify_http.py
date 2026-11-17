"""Verify the running local UI and actual HTTP MCP transport."""
import asyncio
import json
from pathlib import Path

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def main():
    base = 'http://127.0.0.1:8765'
    async with httpx.AsyncClient(trust_env=False) as client:
        ui = await client.get(base + '/library')
        ui.raise_for_status()
        assert 'MGCA Book Research' in ui.text
        result = await client.get(base + '/library/search', params={'q':'What changes the speed at which chemicals transform?'})
        result.raise_for_status()
        data = result.json()
        assert data['mode'] == 'hybrid'
        assert data['results'][0]['title'] == 'chemistry'
        invalid = await client.get(base + '/library/search', params={'q':''})
        assert invalid.status_code == 400
    async with streamablehttp_client(base + '/mcp') as (reader, writer, _):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert {tool.name for tool in tools.tools} == {'search','fetch','list_books'}
            result = await session.call_tool('search', {'query':'inherited traits'})
            assert not result.isError
            result_data = json.loads(result.content[0].text)
            assert result_data['results'][0]['title'] == 'biology'
    report = {'ui_http': 'passed', 'hybrid_search': 'passed', 'empty_query_validation':'passed',
              'streamable_http_mcp_handshake_and_search':'passed', 'retrieval_ms':data['elapsed_ms'],
              'scope':'Local synthetic fixtures; no ChatGPT account connection yet.'}
    path = Path(__file__).resolve().parents[1] / 'reports/http-pilot.json'
    path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
