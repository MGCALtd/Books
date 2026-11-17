# MGCA personal book research — initial PC pilot

Repository: `https://github.com/MGCALtd/Books`, branch `book-research-pilot`.
This project lives in `ResearchSystem/`, alongside existing companion projects.
Open `ResearchSystem/book-research.code-workspace` in VS Code. Local Python
environment: `ResearchSystem/.venv`. VS Code tasks run tests and import samples;
the debugger configuration starts the local MCP/search service.

Local catalogue and read-only MCP service for an unsorted collection. Source books
are never moved or edited. No OpenAI/Azure API calls or paid services are made.

## What works in this version

- Recursive PDF, TXT, Markdown and EPUB import with SHA-256 deduplication.
- PDF page index and embedded page labels retained; printed-page verification is
  explicitly NOT claimed. EPUB locations use spine sections.
- Mixed-subject, passage-level heuristic tags, marked unreviewed. No trained
  classifier or tag editing interface yet.
- Keyword retrieval via SQLite FTS5; optional REAL semantic vectors via an
  already installed Ollama embedding model or optional FastEmbed CPU model,
  fused by reciprocal rank.
- Read-only MCP `search`, `fetch`, and `list_books`, with bounded results.
- Local browser search page at `/library` when using Streamable HTTP.
- Restartable vector generation, model digest/dimension checks, source warnings.

## Important status

SQLite is the initial PC backend. Its optional vector path scans stored vectors;
it is not the PostgreSQL/HNSW production implementation or proof of performance
at 125,000 passages. `sql/postgres.sql` prepares that schema, but the PostgreSQL
application adapter and migration still need implementation and integration tests.
No reranker, automatic OCR, trained subject classifier, page-image retrieval,
background watcher or external ChatGPT connection is implemented yet.

## Run locally

Use Python 3.11+ and a project-local virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\book-research.exe import samples
.\.venv\Scripts\book-research.exe search "catalyst reaction"
.\.venv\Scripts\book-research.exe catalogue
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Set `BOOK_DB` to choose another database. Configuration environment variables
are read from the process environment; `.env.example` is not loaded automatically.

For real embeddings, install Ollama and your selected embedding model separately,
then enable the embedding path explicitly:

```powershell
.\.venv\Scripts\book-research.exe --embed import samples
.\.venv\Scripts\book-research.exe --embed search "catalyst reaction"
```

The embedding service is local by default (`127.0.0.1:11434`). `--ollama-url`
can target your own server. Inputs are not silently truncated; oversized chunks
must be reduced. Switching model digest requires rebuilding vectors in a new DB.
Unchanged books are not imported again. Changed files become separate versions;
there is no automatic superseding/removal policy yet.

For the optional CPU model, install `.[cpu-embeddings]`, then use `--cpu-embed`
instead of `--embed`. The first run downloads MiniLM weights (no inference fee).
The model is intended as an English-language pilot, not the final multilingual
scientific embedding choice. It uses 384-dimensional vectors, while the separate
PostgreSQL design currently specifies 768: choose a model and migrate explicitly.
If your environment restricts home-directory writes, set `HF_HOME` and
`HF_XET_CACHE` to writable project-local folders BEFORE starting Python. Set
`HF_HUB_DISABLE_XET=1` before Python startup to use standard HTTP downloads.

## Read-only MCP

```powershell
.\.venv\Scripts\book-research.exe serve --transport stdio
.\.venv\Scripts\book-research.exe serve --transport streamable-http --port 8765
```

HTTP binds ONLY to 127.0.0.1. It is a local test endpoint, not remotely accessible
from ChatGPT. Do not expose it with port forwarding. Before connecting ChatGPT,
verify account support and configure an authenticated private connection/tunnel.
Returned `book://` URIs are source identifiers, not public document URLs.
No source documents or credentials belong in GitHub. Local book paths are kept
inside the database and are not returned by MCP tools.

## Initial acceptance checks

Use synthetic fixtures first. Then import 10–20 authorised real books and check
known-answer retrieval, duplicate handling, page provenance and subject overlap.
Review scan warnings; text extraction alone does not preserve equations/diagrams.
Measure import time and retrieval latency on real documents before extrapolating.

## Next deployment information needed

1. Exact local/NAS path containing initial test books (read-only source).
2. Existing local Ollama endpoint/model, or permission to install a chosen model.
3. Later: chosen Proxmox VM, database credentials and backup destination.
