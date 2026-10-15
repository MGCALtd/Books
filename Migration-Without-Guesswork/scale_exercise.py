"""20,000 fictional headers. Partition hashes narrow diagnosis; keyed checks decide."""

import hashlib
import json
from collections import defaultdict
from reconcile import fixture, reconcile


def build():
    """Create 20,000 synthetic headers per side and inject the three baseline defects.

    Use four tenants with 5,000 orders each and integer amount 1000. Missing O-000104
    and duplicated O-000105 cancel in the total; O-000102 has the wrong customer.
    Indexes keep this local exercise usable; these timings are not a benchmark."""
    connection = fixture()
    connection.execute("DELETE FROM source_orders")
    connection.execute("DELETE FROM target_orders")
    for tenant in range(1, 5):
        rows = [
            (f"T{tenant}", f"O-{n:06d}", f"C{n}", "Paid", "GBP", 1000)
            for n in range(1, 5001)
        ]
        connection.executemany(
            "INSERT INTO"
            " source_orders(tenant_id,order_id,customer_id,status,currency,amount_minor)"
            " VALUES(?,?,?,?,?,?)",
            rows,
        )
        connection.executemany(
            "INSERT INTO"
            " target_orders(tenant_id,order_id,customer_id,status,currency,amount_minor)"
            " VALUES(?,?,?,?,?,?)",
            [(t, o, u, "SETTLED", cur, a) for t, o, u, s, cur, a in rows],
        )
    for side in ["source", "target"]:
        connection.execute(
            f"CREATE INDEX {side}_key ON {side}_orders(tenant_id,order_id)"
        )
    connection.execute(
        "DELETE FROM target_orders WHERE tenant_id='T1' AND order_id='O-000104'"
    )
    connection.execute(
        "INSERT INTO"
        " target_orders(tenant_id,order_id,customer_id,status,currency,amount_minor)"
        " SELECT tenant_id,order_id,customer_id,status,currency,amount_minor FROM"
        " target_orders WHERE tenant_id='T1' AND order_id='O-000105'"
    )
    connection.execute(
        "UPDATE target_orders SET customer_id='C9' WHERE tenant_id='T1' AND"
        " order_id='O-000102'"
    )
    return connection


def partition_controls(connection, side):
    """Return count, amount total and canonical SHA-256 for each tenant/block.

    Only source or target is accepted as a table selector. Each 500-order block
    retains duplicates and sorts canonical row tuples, so insertion order is irrelevant.
    Map source statuses before comparison. Typed UTF-8 JSON and an eight-byte
    big-endian length prefix make row boundaries explicit. Do not trim or normalise
    business identifiers. This schema-specific method is not a universal hash contract.
    """
    if side not in {"source", "target"}:
        raise ValueError("side must be 'source' or 'target'")
    buckets = defaultdict(list)
    for row in connection.execute(
        "SELECT tenant_id,order_id,customer_id,status,currency,amount_minor FROM"
        f" {side}_orders"
    ):
        row = list(row)
        if side == "source":
            mapped = connection.execute(
                "SELECT target_status FROM status_map WHERE source_status=?", (row[3],)
            ).fetchone()
            if not mapped:
                raise ValueError("unmapped status")
            row[3] = mapped[0]
        part = (row[0], (int(row[1].split("-")[1]) - 1) // 500)
        buckets[part].append(tuple(row))
    controls = {}
    for part, rows in sorted(buckets.items()):
        digest = hashlib.sha256()
        for row in sorted(rows):
            payload = json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode(
                "utf-8"
            )
            # Frame each row before hashing so concatenated bytes remain unambiguous.
            digest.update(len(payload).to_bytes(8, "big"))
            digest.update(payload)
        controls[f"{part[0]}/{part[1]:02d}"] = {
            "rows": len(rows),
            "total_minor": sum((row[-1] for row in rows)),
            "sha256": digest.hexdigest(),
        }
    return controls


def run():
    """Compare partition controls, then retain the decisive keyed reconciliation.

    The expected differing partition is T1/00. Hash agreement is diagnostic evidence
    under this contract; the example still reports missing, duplicate and wrong-field keys.
    """
    connection = build()
    s, t = (
        partition_controls(connection, "source"),
        partition_controls(connection, "target"),
    )
    differences = [p for p in sorted(set(s) | set(t)) if s.get(p) != t.get(p)]
    row = reconcile(connection)
    return {
        "rows_per_side": row["counts"]["source_rows"],
        "target_rows": row["counts"]["target_rows"],
        "source_total_minor": sum((x["total_minor"] for x in s.values())),
        "target_total_minor": sum((x["total_minor"] for x in t.values())),
        "partitions": len(s),
        "differing_partitions": differences,
        "unique_matched_keys": row["counts"]["unique_matched_keys"],
        "findings": row["findings"],
        "source_partition_00": s["T1/00"],
        "target_partition_00": t["T1/00"],
        "scope": "synthetic local headers; diagnostic scale example, not a benchmark",
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
