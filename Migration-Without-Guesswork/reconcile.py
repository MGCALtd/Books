"""Original book teaching example. Local synthetic headers only; no services."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

HERE = Path(__file__).resolve().parent


def fixture():
    """Create an isolated in-memory SQLite fixture and return its open connection.

    The caller owns the connection. Each call starts from fixture.sql; edits to one
    exercise cannot contaminate another. No production database is opened."""
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript((HERE / "fixture.sql").read_text(encoding="utf-8"))
    return connection


def reconcile(connection):
    """Compare the supplied fixture connection in independent evidence layers.

    Validate keys and required values before comparing unique matched headers.
    Duplicate keys remain findings and are excluded from field comparisons. Totals
    are diagnostic controls, not acceptance: the baseline has equal totals and
    three intentional defects. Return counts, controls and ordered findings."""
    findings = []

    def add(category, side, tenant, order, field="", source="", target="", row_id=None):
        """Append one finding using the common CSV/JSON field names.

        A row_id identifies a staging row, not the business identity. Blank source or
        target values mean that side is not relevant to the finding."""
        findings.append(
            dict(
                category=category,
                side=side,
                tenant_id=tenant,
                order_id=order,
                field=field,
                source_value=source,
                target_value=target,
                row_id=row_id,
            )
        )

    # First separate valid keys from duplicate/missing-key evidence.
    valid = (
        "typeof(tenant_id)='text' AND trim(tenant_id,char(9,10,11,12,13,32))<>'' AND"
        " typeof(order_id)='text' AND trim(order_id,char(9,10,11,12,13,32))<>''"
    )
    counts = {}
    for side in ["source", "target"]:
        table = side + "_orders"
        counts[side + "_rows"] = connection.execute(
            "SELECT COUNT(*) FROM " + table
        ).fetchone()[0]
        counts[side + "_distinct_valid_keys"] = connection.execute(
            "SELECT COUNT(*) FROM (SELECT tenant_id,order_id FROM "
            + table
            + " WHERE "
            + valid
            + " GROUP BY tenant_id,order_id)"
        ).fetchone()[0]
        for row in connection.execute(
            "SELECT * FROM " + table + " WHERE NOT (" + valid + ")"
        ):
            add(
                "INVALID_KEY",
                side,
                row["tenant_id"],
                row["order_id"],
                row_id=row["row_id"],
            )
        for row in connection.execute(
            "SELECT tenant_id,order_id,COUNT(*) AS n FROM "
            + table
            + " WHERE "
            + valid
            + " GROUP BY tenant_id,order_id HAVING COUNT(*)>1"
        ):
            add(
                "DUPLICATE_" + side.upper(),
                side,
                row["tenant_id"],
                row["order_id"],
                target=str(row["n"]) if side == "target" else "",
                source=str(row["n"]) if side == "source" else "",
            )
        for row in connection.execute("SELECT * FROM " + table):
            for field in ["customer_id", "currency", "amount_minor"]:
                value = row[field]
                if value is None or (
                    isinstance(value, str) and (not value.strip("\t\n\x0b\x0c\r "))
                ):
                    add(
                        "REQUIRED_VALUE",
                        side,
                        row["tenant_id"],
                        row["order_id"],
                        field,
                        row_id=row["row_id"],
                    )
            if (
                row["amount_minor"] is not None
                and connection.execute(
                    "SELECT typeof(amount_minor) FROM " + table + " WHERE row_id=?",
                    (row["row_id"],),
                ).fetchone()[0]
                != "integer"
            ):
                add(
                    "INVALID_AMOUNT_TYPE",
                    side,
                    row["tenant_id"],
                    row["order_id"],
                    "amount_minor",
                    row_id=row["row_id"],
                )
            if side == "source":
                mapped = connection.execute(
                    "SELECT 1 FROM status_map WHERE source_status=?", (row["status"],)
                ).fetchone()
            else:
                mapped = connection.execute(
                    "SELECT 1 FROM status_map WHERE target_status=?", (row["status"],)
                ).fetchone()
            if not mapped:
                add(
                    "UNMAPPED_STATUS",
                    side,
                    row["tenant_id"],
                    row["order_id"],
                    "status",
                    row_id=row["row_id"],
                )
    for side, other in [("source", "target"), ("target", "source")]:
        sql = (
            f"SELECT DISTINCT s.tenant_id,s.order_id FROM {side}_orders s\n   WHERE"
            " typeof(s.tenant_id)='text' AND"
            " trim(s.tenant_id,char(9,10,11,12,13,32))<>''\n     AND"
            " typeof(s.order_id)='text' AND"
            " trim(s.order_id,char(9,10,11,12,13,32))<>''\n     AND NOT EXISTS (SELECT"
            f" 1 FROM {other}_orders t\n       WHERE t.tenant_id=s.tenant_id AND"
            " t.order_id=s.order_id)"
        )
        for row in connection.execute(sql):
            add(side.upper() + "_ONLY", side, row["tenant_id"], row["order_id"])
    # Field comparisons use unique keys only: never hide multiplicity with a join.
    base = (
        " FROM source_unique s JOIN target_unique t\n          ON"
        " t.tenant_id=s.tenant_id AND t.order_id=s.order_id "
    )
    counts["unique_matched_keys"] = connection.execute(
        "SELECT COUNT(*)" + base
    ).fetchone()[0]
    for field, category in [
        ("customer_id", "FIELD_CUSTOMER"),
        ("currency", "FIELD_CURRENCY"),
        ("amount_minor", "FIELD_AMOUNT"),
    ]:
        guard = ""
        if field == "amount_minor":
            guard = (
                " AND typeof(s.amount_minor)='integer' AND"
                " typeof(t.amount_minor)='integer' AND s.currency=t.currency AND"
                " s.currency IS NOT NULL AND"
                " trim(s.currency,char(9,10,11,12,13,32))<>''"
            )
        sql = (
            f"SELECT s.tenant_id,s.order_id,s.{field} AS a,t.{field} AS b"
            + base
            + f" WHERE s.{field} IS NOT t.{field}"
            + guard
        )
        for row in connection.execute(sql):
            add(
                category,
                "both",
                row["tenant_id"],
                row["order_id"],
                field,
                row["a"],
                row["b"],
            )
    sql = (
        "SELECT s.tenant_id,s.order_id,m.target_status AS a,t.status AS b"
        + base
        + " JOIN status_map m ON m.source_status=s.status WHERE m.target_status IS NOT"
        " t.status"
    )
    for row in connection.execute(sql):
        add(
            "FIELD_STATUS",
            "both",
            row["tenant_id"],
            row["order_id"],
            "status",
            row["a"],
            row["b"],
        )
    # Stable ordering makes saved runs and reader comparisons reproducible.
    findings.sort(
        key=lambda row: tuple(
            (
                "" if row[k] is None else str(row[k])
                for k in [
                    "category",
                    "side",
                    "tenant_id",
                    "order_id",
                    "field",
                    "row_id",
                ]
            )
        )
    )
    # Totals include all integer-valued rows, including duplicates; equality is insufficient.
    controls = {}
    for side in ["source", "target"]:
        controls[side] = [
            dict(row)
            for row in connection.execute(
                "SELECT tenant_id,currency,COUNT(*) AS rows,SUM(amount_minor) AS"
                " total_minor FROM "
                + side
                + "_orders WHERE typeof(amount_minor)='integer' GROUP BY"
                " tenant_id,currency ORDER BY tenant_id,currency"
            )
        ]
    return dict(
        contract="CC-03/header-exercise-1",
        counts=counts,
        controls=controls,
        findings=findings,
        scope="Static synthetic order headers only",
        not_examined=[
            "live-state alignment",
            "line items",
            "attachments",
            "permissions",
            "workflow",
            "recovery",
        ],
    )


def main():
    """Write a new local run directory and print a concise result summary.

    Existing output directories are refused so earlier evidence is not overwritten.
    The run manifest identifies the interpreter, SQLite and the exact input/code bytes.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="order_reconciliation_run")
    arguments = parser.parse_args()
    output_directory = Path(arguments.output)
    if output_directory.exists():
        parser.error("Output directory already exists; choose a new directory.")
    connection = fixture()
    result = reconcile(connection)
    output_directory.mkdir(parents=True)
    (output_directory / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    with (output_directory / "exceptions.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        fields = [
            "category",
            "side",
            "tenant_id",
            "order_id",
            "field",
            "source_value",
            "target_value",
            "row_id",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(result["findings"])
    manifest = {
        "python": sys.version.split()[0],
        "sqlite": sqlite3.sqlite_version,
        "fixture_sha256": (
            hashlib.sha256((HERE / "fixture.sql").read_bytes()).hexdigest()
        ),
        "query_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    (output_directory / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    print(
        f"{len(result['findings'])} findings; {result['counts']['unique_matched_keys']}"
        " unique matched keys."
    )


if __name__ == "__main__":
    main()
