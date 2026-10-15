"""20,000 fictional headers. Partition hashes narrow diagnosis; keyed checks decide."""
import hashlib
import json
from collections import defaultdict
from reconcile import fixture, reconcile

def build():
    c = fixture()
    c.execute('DELETE FROM source_orders')
    c.execute('DELETE FROM target_orders')
    for tenant in range(1, 5):
        rows = [(f'T{tenant}', f'O-{n:06d}', f'C{n}',
                 'Paid', 'GBP', 1000) for n in range(1, 5001)]
        c.executemany('INSERT INTO source_orders(tenant_id,order_id,customer_id,status,currency,amount_minor) VALUES(?,?,?,?,?,?)', rows)
        c.executemany('INSERT INTO target_orders(tenant_id,order_id,customer_id,status,currency,amount_minor) VALUES(?,?,?,?,?,?)',
                      [(t,o,u,'SETTLED',cur,a) for t,o,u,s,cur,a in rows])
    for side in ['source', 'target']:
        c.execute(f'CREATE INDEX {side}_key ON {side}_orders(tenant_id,order_id)')
    c.execute("DELETE FROM target_orders WHERE tenant_id='T1' AND order_id='O-000104'")
    c.execute("INSERT INTO target_orders(tenant_id,order_id,customer_id,status,currency,amount_minor) SELECT tenant_id,order_id,customer_id,status,currency,amount_minor FROM target_orders WHERE tenant_id='T1' AND order_id='O-000105'")
    c.execute("UPDATE target_orders SET customer_id='C9' WHERE tenant_id='T1' AND order_id='O-000102'")
    return c

def partition_controls(c, side):
    """Typed JSON, length prefix, sorted canonical tuples; preserve duplicate rows.

    Canonicalisation is specific to this schema. It maps source Paid to SETTLED.
    No Unicode normalisation or trimming of actual identifiers occurs.
    """
    buckets = defaultdict(list)
    for r in c.execute(f'SELECT tenant_id,order_id,customer_id,status,currency,amount_minor FROM {side}_orders'):
        row = list(r)
        if side == 'source':
            mapped = c.execute('SELECT target_status FROM status_map WHERE source_status=?', (row[3],)).fetchone()
            if not mapped:
                raise ValueError('unmapped status')
            row[3] = mapped[0]
        part = (row[0], (int(row[1].split('-')[1]) - 1) // 500)
        buckets[part].append(tuple(row))
    controls = {}
    for part, rows in sorted(buckets.items()):
        h = hashlib.sha256()
        for row in sorted(rows):
            payload = json.dumps(row, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
            h.update(len(payload).to_bytes(8, 'big'))
            h.update(payload)
        controls[f'{part[0]}/{part[1]:02d}'] = {
            'rows': len(rows), 'total_minor': sum(row[-1] for row in rows),
            'sha256': h.hexdigest()}
    return controls

def run():
    c = build()
    s, t = partition_controls(c, 'source'), partition_controls(c, 'target')
    differences = [p for p in sorted(set(s) | set(t)) if s.get(p) != t.get(p)]
    r = reconcile(c)
    return {'rows_per_side': r['counts']['source_rows'],
            'target_rows': r['counts']['target_rows'],
            'source_total_minor': sum(x['total_minor'] for x in s.values()),
            'target_total_minor': sum(x['total_minor'] for x in t.values()),
            'partitions': len(s), 'differing_partitions': differences,
            'unique_matched_keys': r['counts']['unique_matched_keys'],
            'findings': r['findings'], 'source_partition_00': s['T1/00'],
            'target_partition_00': t['T1/00'],
            'scope': 'synthetic local headers; diagnostic scale example, not a benchmark'}

if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
