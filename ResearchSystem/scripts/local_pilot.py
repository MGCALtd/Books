"""Run a real CPU-embedding smoke test and write measured results. No paid API."""
import json
import os
import ssl
import time
from pathlib import Path

import httpx
from huggingface_hub import set_client_factory

from book_research.core import Catalogue
from book_research.embeddings import CPUEmbeddings


def main():
    root = Path(__file__).resolve().parents[1]
    # Respect Windows trust roots; never disable certificate verification.
    set_client_factory(lambda: httpx.Client(verify=ssl.create_default_context(), follow_redirects=True, timeout=60))
    os.environ['HF_HUB_DISABLE_XET'] = '1'
    started = time.perf_counter()
    embeddings = CPUEmbeddings(root / 'data/models')
    load_seconds = time.perf_counter() - started
    catalogue = Catalogue(root / 'data/pilot.sqlite3', embeddings)
    try:
        imports = [catalogue.ingest(path) for path in sorted((root / 'samples').glob('*.txt'))]
        queries = ['What changes the speed at which chemicals transform?',
                   'How is light described in quantum theory?', 'How are traits inherited in living things?']
        checks = []
        for query, expected in zip(queries, ['chemistry', 'mixed-physics', 'biology']):
            result = catalogue.search(query, limit=3)
            top = result['results'][0]['title'] if result['results'] else None
            checks.append({'query': query, 'mode': result['mode'], 'elapsed_ms': result['elapsed_ms'],
                           'expected_top': expected, 'actual_top': top, 'passed': top == expected})
        report = {'scope': 'Three tiny synthetic fixtures. Not a book-scale or 100-book benchmark.',
                  'embedding_model': embeddings.identity(), 'model_initialisation_seconds': round(load_seconds, 3),
                  'imports': imports, 'checks': checks, 'catalogue': catalogue.catalogue()}
        reports = root / 'reports'
        reports.mkdir(exist_ok=True)
        (reports / 'cpu-pilot.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(report, indent=2))
        if not all(check['passed'] for check in checks):
            raise SystemExit(1)
    finally:
        catalogue.close()


if __name__ == '__main__':
    main()
