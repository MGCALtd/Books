"""Synthetic chapter5-8 exercises. No external actions or services."""

from copy import deepcopy
import hashlib, json, math, sqlite3, tempfile
from pathlib import Path

BASE = {
    "T1/O-101": dict(customer="C1", amount_minor=4000, currency="GBP"),
    "T1/O-102": dict(customer="C2", amount_minor=6000, currency="GBP"),
    "T1/O-104": dict(customer="C4", amount_minor=5000, currency="GBP"),
    "T1/O-105": dict(customer="C5", amount_minor=5000, currency="GBP"),
}
EVENTS = [
    dict(
        position=101,
        op="upsert",
        key="T1/O-106",
        value=dict(customer="C6", amount_minor=2500, currency="GBP"),
    ),
    dict(
        position=102,
        op="upsert",
        key="T1/O-102",
        value=dict(customer="C2", amount_minor=6500, currency="GBP"),
    ),
    dict(position=103, op="delete", key="T1/O-104"),
]


class ChangeState:
    """Small consecutive-log model for chapter 5, with positions 101–103.

    Real change-data-capture positions can be sparse or multi-part; this model
    deliberately requires consecutive integers to make missing events visible."""

    def __init__(self):
        """Copy the starting population so each instance has independent state."""
        self.state = deepcopy(BASE)
        self.applied = 100
        self.seen = {}

    def apply(self, event):
        """Apply the next event, ignore an identical repeat, and reject gaps/conflicts.

        Retain the event content as well as its position: reusing a position for different
        content must not silently succeed. A missing delete is harmless in this model.
        """
        position = event["position"]
        fingerprint = json.dumps(event, sort_keys=True)
        if position in self.seen:
            if self.seen[position] != fingerprint:
                raise ValueError("Position content conflicts with retained event")
            return "repeat"
        if position != self.applied + 1:
            raise ValueError("Gap in this consecutive teaching log")
        if event["op"] == "upsert":
            self.state[event["key"]] = deepcopy(event["value"])
        elif event["op"] == "delete":
            self.state.pop(event["key"], None)
        else:
            raise ValueError("Unsupported event")
        self.seen[position] = fingerprint
        self.applied = position
        return "applied"

    def control(self):
        """Report the applied boundary, active row count and integer minor-unit sum."""
        return dict(
            position=self.applied,
            rows=len(self.state),
            total_minor=sum((x["amount_minor"] for x in self.state.values())),
        )


def boundary_example():
    """Return controls before and after the insert, update and delete.

    Expected amounts in minor units: 20000, 22500, 23000, 18000."""
    s = ChangeState()
    observed = [s.control()]
    for event in EVENTS:
        s.apply(event)
        observed.append(s.control())
    return observed


def snapshot_example():
    """Demonstrate one SQLite WAL reader snapshot against a separate writer.

    The reader sees 6000 twice within its transaction, then 6500 after committing.
    Both connections and the temporary directory are local and disposable. This
    does not demonstrate a distributed snapshot or production CDC alignment."""
    with tempfile.TemporaryDirectory(prefix="book-snapshot-") as td:
        path = str(Path(td) / "example.sqlite")
        setup = sqlite3.connect(path)
        setup.execute("PRAGMA journal_mode=WAL")
        setup.execute("CREATE TABLE example(amount_minor INTEGER)")
        setup.execute("INSERT INTO example VALUES(6000)")
        setup.commit()
        setup.close()
        reader = sqlite3.connect(path)
        writer = sqlite3.connect(path)
        try:
            reader.execute("BEGIN")
            a = reader.execute("SELECT amount_minor FROM example").fetchone()[0]
            writer.execute("UPDATE example SET amount_minor=6500")
            writer.commit()
            b = reader.execute("SELECT amount_minor FROM example").fetchone()[0]
            reader.commit()
            c = reader.execute("SELECT amount_minor FROM example").fetchone()[0]
            return [a, b, c]
        finally:
            reader.close()
            writer.close()


def intent_database():
    """Create the local intent ledger and effect tables; caller closes the connection.

    Their writes can share one SQLite transaction. An external invoice API cannot
    be made atomic merely by copying this local arrangement."""
    c = sqlite3.connect(":memory:")
    c.executescript(
        "CREATE TABLE ledger(\n tenant TEXT,intent TEXT,fingerprint TEXT,result TEXT,\n"
        " PRIMARY KEY(tenant,intent));\n CREATE TABLE effects(\n tenant TEXT,intent"
        " TEXT,order_id TEXT,customer TEXT,\n currency TEXT,amount_minor"
        " INTEGER,UNIQUE(tenant,intent));"
    )
    return c


INTENT = dict(
    tenant="T1",
    intent="INV-102",
    order_id="O-102",
    customer="C2",
    currency="GBP",
    amount_minor=6000,
)


def handle_intent(c, payload, fail_after_effect=False):
    """Retain one local effect and result for a tenant-scoped invoice intent.

    An identical repeat returns the retained result; changed content under the
    same identity raises ValueError. The optional fault is injected after the effect
    insert and before ledger completion, so the transaction must roll both back.
    Only the exact documented payload fields and positive integer minor units pass."""
    required = ["tenant", "intent", "order_id", "customer", "currency", "amount_minor"]
    if set(payload) != set(required):
        raise ValueError("Unexpected or missing payload field")
    if any(
        (
            not isinstance(payload[x], str) or not payload[x].strip()
            for x in required[:-1]
        )
    ):
        raise ValueError("Required identifier missing")
    if type(payload["amount_minor"]) is not int or payload["amount_minor"] <= 0:
        raise ValueError("Positive integer minor amount required")
    fingerprint = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    try:
        # The effect and ledger are local tables sharing this transaction.
        c.execute("BEGIN")
        old = c.execute(
            "SELECT fingerprint,result FROM ledger WHERE tenant=? AND intent=?",
            (payload["tenant"], payload["intent"]),
        ).fetchone()
        if old:
            if old[0] != fingerprint:
                raise ValueError("Conflicting payload for retained intent")
            c.commit()
            return dict(state="repeat", result=old[1])
        c.execute(
            "INSERT INTO effects VALUES(?,?,?,?,?,?)",
            tuple((payload[x] for x in required)),
        )
        if fail_after_effect:
            raise RuntimeError("Injected local failure")
        retained = "SIMULATED-" + payload["intent"]
        c.execute(
            "INSERT INTO ledger VALUES(?,?,?,?)",
            (payload["tenant"], payload["intent"], fingerprint, retained),
        )
        c.commit()
        return dict(state="completed", result=retained)
    except Exception:
        c.rollback()
        raise


def nearest_rank(values, p):
    """Return the nearest-rank quantile at probability p in (0, 1].

    Sort n values and select one-based rank ceil(p*n). This is the book’s declared
    convention, not interpolation; different tools can report different percentiles."""
    if (
        not values
        or type(p) not in (int, float)
        or not math.isfinite(p)
        or not 0 < p <= 1
    ):
        raise ValueError("Nonempty values and 0 < p <= 1 required")
    return sorted(values)[math.ceil(p * len(values)) - 1]


def metric_fixture():
    """Return 100 fictional client attempts, including a slow success and timeout."""
    return [
        dict(id=i, correct=True, duration_ms=100, timeout=False) for i in range(1, 99)
    ] + [
        dict(id=99, correct=True, duration_ms=900, timeout=False),
        dict(id=100, correct=False, duration_ms=2000, timeout=True),
    ]


def measure(records, limit_ms=500):
    """Separate all-attempt outcomes from successful-completion latency.

    Timeouts stay in the success/timely-correct denominators but do not enter
    successful latency percentiles. Durations and the timely limit are milliseconds.
    When there are no successes, successful latency values are None, not zero."""
    if (
        type(limit_ms) not in (int, float)
        or not math.isfinite(limit_ms)
        or limit_ms < 0
    ):
        raise ValueError("limit_ms must be finite non-negative milliseconds")
    if not records:
        raise ValueError("No attempts")
    ids = [r["id"] for r in records]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate attempt ID")
    if any(
        (
            type(r["correct"]) is not bool or type(r["timeout"]) is not bool
            for r in records
        )
    ):
        raise ValueError("Boolean outcome flags required")
    if any(
        (
            type(r["duration_ms"]) not in [int, float]
            or not math.isfinite(r["duration_ms"])
            or r["duration_ms"] < 0
            for r in records
        )
    ):
        raise ValueError("Invalid duration")
    if any((r["correct"] and r["timeout"] for r in records)):
        raise ValueError("Timeout cannot be a correct completion")
    # Keep timeout outcomes in the attempt denominator, outside successful latency.
    success = [r["duration_ms"] for r in records if r["correct"] and (not r["timeout"])]
    timely = sum(
        (
            r["correct"] and (not r["timeout"]) and (r["duration_ms"] <= limit_ms)
            for r in records
        )
    )
    n = len(records)
    return dict(
        attempts=n,
        successes=len(success),
        timeouts=sum((r["timeout"] for r in records)),
        timely_correct=timely,
        timely_correct_proportion=timely / n,
        success_proportion=len(success) / n,
        successful_mean_ms=sum(success) / len(success) if success else None,
        successful_p95_ms=nearest_rank(success, 0.95) if success else None,
        successful_p99_ms=nearest_rank(success, 0.99) if success else None,
        scope="Synthetic client attempts, successful-latency population separate",
    )


def closure_gate(item):
    """Return the next evidence state for a fictional exception record.

    A deployed fix alone is insufficient: closure needs a passing retest, coverage
    reference and reviewer. Accepted exceptions need the listed decision fields.
    This validates record completeness, not the authority or truth of its contents."""
    if not item.get("original_evidence"):
        return "evidence incomplete"
    if item.get("accepted_exception"):
        required = [
            "decision_owner",
            "population",
            "consequence",
            "mitigation",
            "operating_owner",
            "review_condition",
            "decision_reference",
        ]
        return (
            "accepted exception"
            if all((item.get(x) for x in required))
            else "evidence incomplete"
        )
    if not item.get("correction_reference"):
        return "investigating"
    if item.get("retest_passed") is False:
        return "retest failed"
    if item.get("retest_passed") is not True:
        return "awaiting retest"
    if not all(
        (
            item.get(x)
            for x in ["retest_reference", "affected_population_reference", "reviewer"]
        )
    ):
        return "evidence incomplete"
    return "closed by verified correction"


def main():
    """Run the independent chapter 5–8 examples and print JSON for comparison."""
    c = intent_database()
    first = handle_intent(c, deepcopy(INTENT))
    second = handle_intent(c, deepcopy(INTENT))
    result = dict(
        boundary=boundary_example(),
        snapshot=snapshot_example(),
        idempotency=dict(
            first=first,
            second=second,
            effects=c.execute("SELECT COUNT(*) FROM effects").fetchone()[0],
        ),
        metrics=measure(metric_fixture()),
        recovery_minutes=sum([2, 3, 8, 4, 6]),
        sqlite_version=sqlite3.sqlite_version,
        scope="Synthetic local exercises only",
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
