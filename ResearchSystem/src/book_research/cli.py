from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .core import Catalogue, OllamaEmbeddings, NeedsOCR


def main():
    parser = argparse.ArgumentParser(description='Local book research pilot; never modifies source books.')
    parser.add_argument('--db', type=Path, default=Path(os.getenv('BOOK_DB', 'data/books.sqlite3')))
    parser.add_argument('--embed', action='store_true', help='Use real local Ollama vectors; no cloud API.')
    parser.add_argument('--cpu-embed', action='store_true', help='Download/use a small CPU MiniLM model. No paid API.')
    parser.add_argument('--model-cache', type=Path, default=Path('data/models'))
    parser.add_argument('--ollama-url', default=os.getenv('OLLAMA_URL', 'http://127.0.0.1:11434'))
    parser.add_argument('--model', default=os.getenv('EMBED_MODEL', 'embeddinggemma'))
    commands = parser.add_subparsers(dest='command', required=True)
    ingest = commands.add_parser('import')
    ingest.add_argument('folder', type=Path)
    commands.add_parser('catalogue')
    commands.add_parser('vectorize')
    search = commands.add_parser('search')
    search.add_argument('query')
    search.add_argument('--subject')
    search.add_argument('--book-id')
    fetch = commands.add_parser('fetch')
    fetch.add_argument('id')
    serve = commands.add_parser('serve')
    serve.add_argument('--transport', choices=['stdio', 'streamable-http'], default='stdio')
    serve.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    if args.embed and args.cpu_embed:
        parser.error('Choose one embedding backend')
    if args.command == 'serve':
        from .server import run
        run(args)
        return
    client = embedding_client(args)
    catalogue = Catalogue(args.db, client)
    try:
        if args.command == 'import':
            if not args.folder.is_dir():
                parser.error('folder must be an existing directory')
            results = []
            for path in sorted(args.folder.rglob('*')):
                if path.is_file() and not path.is_symlink() and path.suffix.lower() in {'.txt','.md','.pdf','.epub'}:
                    try:
                        result = catalogue.ingest(path)
                    except NeedsOCR as exc:
                        result = {'status': 'needs_ocr', 'reason': str(exc)}
                    except Exception as exc:
                        result = {'status': 'failed', 'reason': str(exc), 'error_type': type(exc).__name__}
                    result['filename'] = path.name
                    results.append(result)
                    print(json.dumps(result, ensure_ascii=False))
            if any(item['status'] in {'failed','needs_ocr'} for item in results):
                raise SystemExit(2)
        elif args.command == 'vectorize':
            if not (args.embed or args.cpu_embed):
                parser.error('vectorize requires --embed or --cpu-embed')
            catalogue.vectorize_missing()
            print(json.dumps({'status': 'complete'}))
        elif args.command == 'catalogue':
            print(json.dumps(catalogue.catalogue(), ensure_ascii=False, indent=2))
        elif args.command == 'search':
            print(json.dumps(catalogue.search(args.query, subject=args.subject, book_id=args.book_id), ensure_ascii=False, indent=2))
        elif args.command == 'fetch':
            print(json.dumps(catalogue.fetch(args.id), ensure_ascii=False, indent=2))
    finally:
        catalogue.close()


def embedding_client(args):
    if args.cpu_embed:
        from .embeddings import CPUEmbeddings
        return CPUEmbeddings(args.model_cache)
    return OllamaEmbeddings(args.ollama_url, args.model) if args.embed else None


if __name__ == '__main__':
    main()
