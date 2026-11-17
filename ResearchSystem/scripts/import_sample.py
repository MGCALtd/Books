"""Import a bounded sample from a user-selected folder, preserving originals."""
import argparse
import json
import os
import sys
import time
from pathlib import Path

from book_research.core import Catalogue, NeedsOCR


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--folder', type=Path, required=True)
    parser.add_argument('--limit', type=int, default=5)
    parser.add_argument('--cpu-embed', action='store_true')
    args = parser.parse_args()
    if not 1 <= args.limit <= 20:
        parser.error('Choose between 1 and 20 books for the initial sample.')
    root = Path(__file__).resolve().parents[1]
    # Probe with scandir so access denial is not misreported as a missing folder.
    try:
        with os.scandir(args.folder):
            pass
    except OSError as exc:
        print(f'Cannot read {args.folder}: {exc}', file=sys.stderr, flush=True)
        return 2
    os.environ.setdefault('HF_HOME', str(root / 'data/hf-home'))
    os.environ.setdefault('HF_XET_CACHE', str(root / 'data/hf-xet'))
    os.environ.setdefault('HF_HUB_DISABLE_XET', '1')
    embeddings = None
    if args.cpu_embed:
        from book_research.embeddings import CPUEmbeddings
        print('Loading local CPU embedding model...', flush=True)
        embeddings = CPUEmbeddings(root / 'data/models')
    catalogue = Catalogue(root / 'data/real-books.sqlite3', embeddings)
    records = []
    started = time.perf_counter()
    try:
        for directory, _, filenames in os.walk(args.folder, followlinks=False,
                onerror=lambda error: print(f'Folder skipped: {error}', file=sys.stderr, flush=True)):
            for name in sorted(filenames):
                path = Path(directory) / name
                if path.is_symlink() or path.suffix.lower() not in {'.pdf','.epub','.txt','.md'}:
                    continue
                print(f'Processing {len(records)+1}/{args.limit}: {name}', flush=True)
                try:
                    result = catalogue.ingest(path)
                except NeedsOCR as exc:
                    result = {'status':'needs_ocr','reason':str(exc)}
                except Exception as exc:
                    result = {'status':'failed','error_type':type(exc).__name__,'reason':str(exc)}
                result['filename'] = name
                records.append(result)
                print(json.dumps(result, ensure_ascii=False), flush=True)
                if len(records) >= args.limit:
                    break
            if len(records) >= args.limit:
                break
        report = {'source':str(args.folder),'seconds':round(time.perf_counter()-started,3),
                  'attempted':len(records),'results':records,'catalogue':catalogue.catalogue(),
                  'scope':'First supported files encountered, not a representative subject sample.'}
        destination = root / 'reports/real-book-sample.json'
        destination.parent.mkdir(exist_ok=True)
        destination.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(f'Report: {destination}',flush=True)
        print(f'Database: {root / "data/real-books.sqlite3"}',flush=True)
        return 0 if records and all(row['status'] in {'imported','duplicate'} for row in records) else 2
    finally:
        catalogue.close()


if __name__ == '__main__':
    raise SystemExit(main())
