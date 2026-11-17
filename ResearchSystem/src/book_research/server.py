"""Read-only MCP. Local-only HTTP; use authenticated connection before remote access."""
import json
import asyncio

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse

from .core import Catalogue, OllamaEmbeddings
from .presentation import RESEARCH_INSTRUCTIONS, STYLE_VERSION


def build_server(db_path, embeddings=None, port=8765):
    mcp = FastMCP('MGCA Book Research', host='127.0.0.1', port=port,
                  instructions=RESEARCH_INSTRUCTIONS)
    read_only = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)

    @mcp.tool(annotations=read_only)
    def search(query: str, limit: int = 8, subject: str | None = None, book_id: str | None = None) -> str:
        """Search primary book evidence, then fetch relevant hits. Synthesise a research answer with numbered references using citation.reference; keep internal locators out of the final answer. Subject filters are inferred; retry without them if needed."""
        catalogue = Catalogue(db_path, embeddings, readonly=True)
        try:
            return json.dumps(catalogue.search(query, limit, subject, book_id), ensure_ascii=False)
        finally:
            catalogue.close()

    @mcp.tool(annotations=read_only)
    def fetch(id: str, neighbours: int = 1) -> str:
        """Read source passages before citing them. Use their readable citation.reference in numbered end references. Integrate the evidence into one research answer; do not show raw paths or passage IDs. IDs come from search; no arbitrary filesystem access."""
        catalogue = Catalogue(db_path, readonly=True)
        try:
            return json.dumps(catalogue.fetch(id, neighbours), ensure_ascii=False)
        finally:
            catalogue.close()

    @mcp.tool(annotations=read_only)
    def list_books() -> str:
        """List indexed books, extraction warnings and embedding coverage. Does not expose local folder paths."""
        catalogue = Catalogue(db_path, readonly=True)
        try:
            return json.dumps(catalogue.catalogue(), ensure_ascii=False)
        finally:
            catalogue.close()

    @mcp.custom_route('/library', methods=['GET'])
    async def library_page(request: Request):
        return HTMLResponse(WEB_PAGE)

    @mcp.custom_route('/library/search', methods=['GET'])
    async def library_search(request: Request):
        query = request.query_params.get('q', '')
        try:
            return JSONResponse(json.loads(await asyncio.to_thread(search, query)))
        except (ValueError, OSError) as exc:
            return JSONResponse({'error': str(exc)}, status_code=400)

    @mcp.custom_route('/library/books', methods=['GET'])
    async def library_books(request: Request):
        return JSONResponse(json.loads(await asyncio.to_thread(list_books)))

    return mcp


def run(args):
    if not args.db.is_file():
        raise ValueError('Import books before starting the MCP server')
    from .cli import embedding_client
    embeddings = embedding_client(args)
    build_server(args.db, embeddings, args.port).run(transport=args.transport)


WEB_PAGE = '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MGCA Book Research — local pilot</title>
<style>body{font:17px system-ui;background:#f4f7fa;color:#172c40;max-width:960px;margin:40px auto;padding:20px}input{font:inherit;padding:12px;width:70%;border:1px solid #9cafc0;border-radius:8px}button{font:inherit;padding:12px;background:#12675b;color:white;border:0;border-radius:8px}article{background:white;padding:20px;margin:18px 0;border-radius:10px;box-shadow:0 2px 10px #172c4010}small{color:#496277}h1{font-size:30px}.notice{background:#e3eee9;padding:16px;border-radius:8px}pre{white-space:pre-wrap}</style>
<h1>MGCA Book Research</h1><p class="notice">Local retrieval pilot. Search returns source passages, not AI-generated answers. Tags and metadata are unreviewed. Equations and diagrams require checking against the original book.</p>
<p id="inventory">Loading catalogue…</p><form id="form"><input id="q" aria-label="Search books" value="time dilation and Lorentz transformations"><button>Search books</button></form>
<p id="status"></p><main id="results"></main><script>
const status=document.getElementById('status'), results=document.getElementById('results');
fetch('/library/books').then(r=>r.json()).then(books=>{document.getElementById('inventory').textContent=books.length+' indexed documents · '+books.reduce((n,b)=>n+b.passages,0)+' passages · '+books.reduce((n,b)=>n+b.embedded_passages,0)+' embedded passages';}).catch(()=>{document.getElementById('inventory').textContent='Catalogue unavailable';});
document.getElementById('form').onsubmit=async event=>{event.preventDefault();status.textContent='Searching…';results.replaceChildren();try{const response=await fetch('/library/search?q='+encodeURIComponent(document.getElementById('q').value));const data=await response.json();if(!response.ok)throw Error(data.error||'Search failed');status.textContent=data.mode+' · '+data.elapsed_ms+' ms · '+data.results.length+' results';for(const hit of data.results){const article=document.createElement('article');const title=document.createElement('h2');title.textContent=hit.title;const meta=document.createElement('small');meta.textContent='Location '+hit.page+' · '+hit.tags.join(', ')+' · tags unreviewed';const body=document.createElement('p');body.textContent=hit.text;const ref=document.createElement('small');ref.textContent=hit.url;article.append(title,meta,body,ref);results.append(article);}}catch(error){status.textContent=error.message;}};
</script></html>'''
