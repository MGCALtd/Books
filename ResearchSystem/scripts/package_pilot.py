"""Create a readable test report and a source-only deliverable archive."""
import html
import json
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
report = json.loads((root / 'reports/cpu-pilot.json').read_text(encoding='utf-8'))
tests = (root / 'reports/unit-tests.txt').read_text(encoding='utf-8-sig')
rows = ''.join('<tr><td>'+html.escape(check['query'])+'</td><td>'+html.escape(check['actual_top'])+
               '</td><td>'+str(check['elapsed_ms'])+' ms</td><td>'+('Passed' if check['passed'] else 'Failed')+'</td></tr>'
               for check in report['checks'])
samples = ''.join('<article><h3>'+html.escape(path.name)+'</h3><p>'+html.escape(path.read_text(encoding='utf-8'))+'</p></article>'
                  for path in sorted((root / 'samples').glob('*.txt')))
page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MGCA book research — initial test evidence</title><style>body{font:17px system-ui;color:#173248;background:#f5f8fa;max-width:1100px;margin:35px auto;padding:24px}h1{font-size:32px}article,section{background:white;padding:22px;margin:18px 0;border-radius:10px}table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:12px;border-bottom:1px solid #dce4e9}pre{white-space:pre-wrap;font-size:13px}.note{background:#fff1cc;padding:18px;border-radius:8px}p{line-height:1.6}</style>
<h1>MGCA book research: initial PC test</h1><p>17 November 2026 · Prototype v0.1.0</p>
<p class="note"><strong>Scope:</strong> Three short synthetic text documents. Your personal books have not been imported. This is a functionality test, not a 1,000-page or 100-book performance benchmark.</p>
<section><h2>What was run</h2><p>Local SQLite FTS5 catalogue, real MiniLM CPU embeddings, hybrid keyword/vector retrieval and read-only MCP. Twelve automated tests passed, including PDF extraction, EPUB spine order, deduplication, cross-subject tags, page provenance, model mismatch protection and an actual MCP stdio client/server exchange.</p>
<p>The localhost browser connection timed out during verification and the test server was stopped. The web page is implemented but browser access is not verified. ChatGPT account connection and PostgreSQL deployment are pending.</p>
<p>Code location: <code>book-research/src/book_research</code>. Test source: <code>book-research/tests</code>. Local database: <code>book-research/data/pilot.sqlite3</code> (81,920 bytes at this test).</p></section>
<section><h2>Measured semantic retrieval</h2><p>Real model: sentence-transformers/all-MiniLM-L6-v2, 384 dimensions, CPU. First model initialisation/download took '''+str(report['model_initialisation_seconds'])+''' seconds. These retrieval measurements cover only the tiny sample collection.</p>
<table><thead><tr><th>Question</th><th>Top source</th><th>Retrieval</th><th>Result</th></tr></thead><tbody>'''+rows+'''</tbody></table></section>
<section><h2>Exactly which documents were used</h2>'''+samples+'''</section>
<section><h2>Automated test output</h2><pre>'''+html.escape(tests)+'''</pre></section>
<section><h2>Next input needed</h2><p>The exact local or NAS folder path for a small set of your real books. Sources will be read without moving or editing them. A suitable private GitHub repository also needs choosing; the public MGCALtd/Books repository was not modified.</p></section></html>'''
(root / 'reports/Initial_Test_Report.html').write_text(page, encoding='utf-8')
output = root.parent / 'outputs'
output.mkdir(exist_ok=True)
archive = output / 'MGCA_Book_Research_Pilot_2026-11-17.zip'
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if not path.is_file() or any(part in {'data','.venv','__pycache__'} or part.endswith('.egg-info') for part in relative.parts):
            continue
        bundle.write(path, 'book-research/' + relative.as_posix())
print(json.dumps({'archive':str(archive),'size_bytes':archive.stat().st_size,'report':str(root / 'reports/Initial_Test_Report.html')}))
