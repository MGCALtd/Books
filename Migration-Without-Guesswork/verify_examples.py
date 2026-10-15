"""Reader verification of the supplied local examples and file checksums."""
from pathlib import Path
import hashlib, json, sqlite3, sys, tempfile, subprocess, re, csv
from reconcile import fixture, reconcile
from transition_exercises import run as transition_run
from learning_exercises import boundary_example, snapshot_example
from scale_exercise import run as scale_run
from relationship_exercises import run as relationship_run

def main():
    here = Path(__file__).resolve().parent
    manifest = json.loads((here / 'SHA256SUMS.json').read_text())
    for name, expected in manifest.items():
        actual = hashlib.sha256((here / name).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError('Checksum mismatch: ' + name)
    expected = json.loads((here / 'queries_expected.json').read_text())
    conn = fixture()
    parts = re.findall('-- (Q\\d+) [^\\n]+\\n(.*?;)', (here / 'queries.sql').read_text(), re.S)
    if not len(parts) == 21:
        raise ValueError('Expected result mismatch')
    for name, sql in parts:
        if not [list(row) for row in conn.execute(sql)] == expected[name]:
            raise ValueError(name)
    rel = relationship_run()
    if not rel['lines'] == {'source_line_rows': 6, 'header_total_minor': 20000, 'joined_header_total_minor': 30000, 'line_total_minor': 20000, 'target_orphan_lines': [['T1', 'O-999', 1]], 'target_line_total_minor': 20000}:
        raise ValueError('Expected result mismatch')
    if not {(x['name'], x['category']) for x in rel['attachments']} == {('order-101.txt', 'OWNER_RELATIONSHIP'), ('order-102.txt', 'CONTENT_HASH')}:
        raise ValueError('Expected result mismatch')
    templates = list((here / 'templates').glob('A*.csv'))
    if not len(templates) == 11:
        raise ValueError('Expected result mismatch')
    for template in templates:
        with template.open(newline='') as f:
            rows = list(csv.reader(f))
        if not (len(rows) == 2 and len(rows[0]) == len(rows[1]) and (not any(rows[1]))):
            raise ValueError(template.name)
    r = reconcile(fixture())
    if not {(x['category'], x['order_id']) for x in r['findings']} == {('DUPLICATE_TARGET', 'O-105'), ('SOURCE_ONLY', 'O-104'), ('FIELD_CUSTOMER', 'O-102')}:
        raise ValueError('Expected result mismatch')
    if not [x['total_minor'] for x in boundary_example()] == [20000, 22500, 23000, 18000]:
        raise ValueError('Expected result mismatch')
    tr = transition_run()
    if not tr['planned']['reopen']['finish'] == 65:
        raise ValueError('Expected result mismatch')
    if not (tr['delayed_data']['reopen']['finish'] == 80 and (not tr['delayed_data_forward_schedule_is_executed'])):
        raise ValueError('Expected result mismatch')
    if not tr['delayed_access']['reopen']['finish'] == 71:
        raise ValueError('Expected result mismatch')
    if not tr['post_write_total_minor'] == 26000:
        raise ValueError('Expected result mismatch')
    s = scale_run()
    if not (s['differing_partitions'] == ['T1/00'] and s['unique_matched_keys'] == 19998):
        raise ValueError('Expected result mismatch')
    with tempfile.TemporaryDirectory(prefix='book-reader-') as td:
        for script, args in [('reconcile.py', ['--output', 'reader_run']), ('learning_exercises.py', []), ('transition_exercises.py', []), ('scale_exercise.py', []), ('relationship_exercises.py', [])]:
            subprocess.run([sys.executable, str(here / script), *args], cwd=td, check=True, capture_output=True, text=True)
    print(json.dumps({'result': 'PASS', 'manifest_files': len(manifest), 'documented_CLIs': 5, 'named_SQL_queries': 21, 'relationship_checks': 'PASS', 'python': sys.version.split()[0], 'sqlite': sqlite3.sqlite_version, 'scope': 'local fictional exercises'}))
if __name__ == '__main__':
    main()
