"""Durable intent and deduplicating remote-sink SIMULATION in two databases.

No messages leave this machine; no remote API or exactly-once network claim.
The sink's atomic key check is an explicit assumption, not an outbox property.
"""
import json
from pathlib import Path
import sqlite3
import tempfile
from controls import canonical


class Outbox:
    def __init__(self, path):
        self.path = str(path)
        with sqlite3.connect(self.path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS intent ('
                       'tenant TEXT, subject TEXT, operation TEXT, payload TEXT NOT NULL,'
                       'state TEXT NOT NULL, PRIMARY KEY(tenant,subject,operation))')

    def enqueue(self, tenant, subject, operation, payload):
        """Caller supplies already authorised synthetic intent, not model text."""
        encoded = canonical(payload)
        with sqlite3.connect(self.path) as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT payload FROM intent WHERE tenant=? AND subject=? '
                             'AND operation=?', (tenant, subject, operation)).fetchone()
            if row and row[0] != encoded:
                raise ValueError('intent key conflict')
            db.execute('INSERT OR IGNORE INTO intent VALUES(?,?,?,?,?)',
                       (tenant, subject, operation, encoded, 'PENDING'))

    def row(self):
        with sqlite3.connect(self.path) as db:
            rows = db.execute('SELECT tenant,subject,operation,payload,state FROM intent').fetchall()
        if len(rows) != 1:
            raise ValueError('this small lab requires exactly one intent')
        return rows[0]

    def deliver(self, sink, lose_ack=False):
        tenant, subject, operation, payload, state = self.row()
        if state == 'DELIVERED':
            return 'DELIVERED'
        # The sink commits separately. A timeout here leaves local PENDING
        # even when the sink has accepted the effect. Reconcile the same key.
        sink.accept(tenant, subject, operation, payload, lose_ack)
        with sqlite3.connect(self.path) as db:
            db.execute('UPDATE intent SET state=? WHERE tenant=? AND subject=? AND operation=?',
                       ('DELIVERED', tenant, subject, operation))
        return 'DELIVERED'


class FakeSink:
    def __init__(self, path):
        self.path = str(path)
        with sqlite3.connect(self.path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS effects ('
                       'tenant TEXT, subject TEXT, operation TEXT, payload TEXT NOT NULL,'
                       'PRIMARY KEY(tenant,subject,operation))')

    def accept(self, tenant, subject, operation, encoded, lose_ack=False):
        with sqlite3.connect(self.path) as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT payload FROM effects WHERE tenant=? AND subject=? '
                             'AND operation=?', (tenant, subject, operation)).fetchone()
            if row and row[0] != encoded:
                raise ValueError('sink key conflict')
            db.execute('INSERT OR IGNORE INTO effects VALUES(?,?,?,?)',
                       (tenant, subject, operation, encoded))
        if lose_ack:
            raise TimeoutError('sink committed; reply lost')

    def count(self):
        with sqlite3.connect(self.path) as db:
            return db.execute('SELECT COUNT(*) FROM effects').fetchone()[0]


def run():
    with tempfile.TemporaryDirectory() as temp:
        local, remote = Path(temp)/'local.db', Path(temp)/'sink.db'
        outbox, sink = Outbox(local), FakeSink(remote)
        outbox.enqueue('T1', 'staff-1', 'OP-REMOTE-1', {'draft_reference': 'D-EXAMPLE'})
        try:
            outbox.deliver(sink, lose_ack=True)
        except TimeoutError:
            pass
        before = {'local_state': outbox.row()[4], 'sink_rows': sink.count()}
        Outbox(local).deliver(FakeSink(remote))
        return {'after_lost_reply': before,
                'after_retry': {'local_state': Outbox(local).row()[4],
                                'sink_rows': FakeSink(remote).count()},
                'kind': 'LOCAL_REMOTE_SINK_SIMULATION'}


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
