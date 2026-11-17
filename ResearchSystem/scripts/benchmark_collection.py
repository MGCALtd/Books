"""Measure retrieval on the locally imported collection; reports stay out of Git."""
import html
import json
import os
import statistics
from pathlib import Path

from book_research.core import Catalogue


def main():
    root = Path(__file__).resolve().parents[1]
    os.environ.setdefault('HF_HOME', str(root / 'data/hf-home'))
    os.environ.setdefault('HF_XET_CACHE', str(root / 'data/hf-xet'))
    os.environ.setdefault('HF_HUB_DISABLE_XET', '1')
    from book_research.embeddings import CPUEmbeddings
    encoder = CPUEmbeddings(root / 'data/models')
    path = root / 'data/real-books.sqlite3'
    catalogue = Catalogue(path, encoder, readonly=True)
    cases = [
        ('Time dilation, Lorentz transformations and simultaneity', ['relativity','tensor']),
        ('Covariant and contravariant tensor indices and coordinate transformations', ['tensor','relativity']),
        ('Nuclear binding energy, nucleons and the nuclear shell model', ['nuclear','particle']),
        ('Commutators, quantum uncertainty and the Schrodinger equation', ['quantum','solvay']),
        ('Projectile motion: horizontal range, launch angle and gravitational acceleration', ['classical','fundamentals','solved']),
        ('Dark matter and the expansion of the universe', ['astrophysics']),
    ]
    checks = []
    try:
        books = catalogue.catalogue()
        for query, expected_terms in cases:
            result = catalogue.search(query, limit=5)
            results = result['results']
            # This is only a filename-based smoke check, not a correctness evaluation.
            expected_found = any(any(term in (hit['title'] + ' ' + next(
                (book['filename'] for book in books if book['id'] == hit['book_id']), '')).casefold()
                for term in expected_terms) for hit in results)
            checks.append({'query':query,'elapsed_ms':result['elapsed_ms'],'mode':result['mode'],
                           'expected_subject_source_in_top5':expected_found,'results':results})
            print(json.dumps({'query':query,'elapsed_ms':result['elapsed_ms'],
                              'top_sources':[hit['title'] for hit in results[:3]],
                              'expected_subject_source_in_top5':expected_found}), flush=True)
        report = {'scope':'Real uploaded books; filename-based retrieval smoke checks, not scientific validation.',
                  'embedding_model':encoder.identity(),'database_bytes':path.stat().st_size,
                  'book_count':len(books),'page_or_section_count':sum(b['page_count'] for b in books),
                  'passages':sum(b['passages'] for b in books),'embedded_passages':sum(b['embedded_passages'] for b in books),
                  'median_retrieval_ms':round(statistics.median(c['elapsed_ms'] for c in checks),2),
                  'books':books,'checks':checks}
        destination = root / 'reports/real-book-retrieval.json'
        destination.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        rows = ''.join('<tr><td>'+html.escape(b['filename'])+'</td><td>'+str(b['page_count'])+'</td><td>'+
                       str(b.get('indexed_locations','?'))+'</td><td>'+str(b['passages'])+'</td><td>'+
                       str(b['embedded_passages'])+'</td></tr>' for b in books)
        sections = ''
        for check in checks:
            sections += '<section><h2>'+html.escape(check['query'])+'</h2><p>'+str(check['elapsed_ms'])+' ms · '+check['mode']+'</p>'
            for hit in check['results'][:3]:
                sections += ('<article><h3>'+html.escape(hit['title'])+'</h3><p>PDF page / EPUB section '+str(hit['page'])+
                             ' · label '+html.escape(hit['page_label'])+'</p><p>'+html.escape(hit['text'][:700])+'</p></article>')
            sections += '</section>'
        page = '<!doctype html><html lang="en"><meta charset="utf-8"><title>Real-book retrieval test</title><style>body{font:17px system-ui;max-width:1100px;margin:35px auto;padding:20px;background:#f5f8fa;color:#183145}section,article{padding:18px;background:white;margin:15px 0;border-radius:8px}table{border-collapse:collapse;width:100%}td,th{padding:10px;border-bottom:1px solid #ccd7df;text-align:left}</style><h1>Real-book retrieval test</h1><p>Local CPU embeddings and SQLite pilot. Source excerpts are evidence for checking retrieval, not generated scientific answers. Printed page numbers and extraction accuracy require verification.</p><p>'+str(report['book_count'])+' books · '+str(report['passages'])+' passages · median retrieval '+str(report['median_retrieval_ms'])+' ms</p><table><tr><th>Book</th><th>Pages/sections</th><th>Locations with text</th><th>Passages</th><th>Embedded</th></tr>'+rows+'</table>'+sections+'</html>'
        (root / 'reports/Real_Book_Test_Report.html').write_text(page,encoding='utf-8')
        print(json.dumps({key:report[key] for key in ['book_count','page_or_section_count','passages','embedded_passages','database_bytes','median_retrieval_ms']}),flush=True)
    finally:
        catalogue.close()


if __name__ == '__main__':
    main()
