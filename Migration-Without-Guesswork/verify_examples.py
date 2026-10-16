"""Self-check the book's fictional examples, independent expected results and files.

Run with Python 3.12 or later from any working directory. PASS means these local
teaching checks passed; it is not acceptance of a production migration.
"""

import csv
import hashlib
import json
from pathlib import Path
import re
import shlex
import sqlite3
import subprocess
import sys
import tempfile

from learning_exercises import (
    boundary_example,
    measure,
    metric_fixture,
    snapshot_example,
)
from reconcile import fixture, reconcile
from relationship_exercises import run as relationship_run
from scale_exercise import run as scale_run
from transition_exercises import run as transition_run

HERE = Path(__file__).resolve().parent

# The public instructions and runner must describe the same exercise commands.
DOCUMENTED_COMMANDS = (
    ("reconcile.py", ("--output", "my_first_run")),
    ("learning_exercises.py", ()),
    ("transition_exercises.py", ()),
    ("scale_exercise.py", ()),
    ("relationship_exercises.py", ()),
)


def require_equal(label, actual, expected):
    """Raise an actionable mismatch even when Python runs with optimization (-O)."""
    if actual != expected:
        raise ValueError(f"{label}: expected {expected!r}; got {actual!r}")


def check_files():
    """Check every manifest entry before importing exercise inputs into a database.

    This catches missing files, newline conversion and accidental edits. A manifest
    supplied beside files is not an independent authentication or security guarantee.
    """
    manifest = json.loads((HERE / "SHA256SUMS.json").read_text(encoding="utf-8"))
    for name, expected in manifest.items():
        path = HERE / name
        if not path.is_file():
            raise ValueError(
                f"Missing companion file: {name}. Extract the whole folder."
            )
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(
                f"Checksum mismatch: {name}. Expected {expected}; got {actual}. Use a"
                " fresh download without changing line endings. Keep deliberate"
                " exercise edits in a separate copy; do not rewrite the manifest to"
                " hide them."
            )
    return len(manifest)


def check_queries():
    """Run each Q-numbered SELECT against a fresh fixture and explicit expected rows."""
    expected = json.loads((HERE / "queries_expected.json").read_text(encoding="utf-8"))
    text = (HERE / "queries.sql").read_text(encoding="utf-8")
    queries = re.findall(r"^-- (Q\d+) [^\n]+\n(.*?)(?=^-- Q\d+ |\Z)", text, re.S | re.M)
    names = [name for name, _ in queries]
    require_equal("named query sequence", names, [f"Q{i:02d}" for i in range(1, 22)])
    connection = fixture()
    try:
        for name, sql in queries:
            rows = [list(row) for row in connection.execute(sql)]
            require_equal(f"{name} result", rows, expected[name])
    finally:
        connection.close()
    return len(queries)


def check_relationships():
    """Check the inflated header sum, orphan parent and two distinct attachment defects."""
    results = relationship_run()
    require_equal(
        "six-line fixture",
        results["lines"],
        {
            "source_line_rows": 6,
            "header_total_minor": 20000,
            "joined_header_total_minor": 30000,
            "line_total_minor": 20000,
            "target_orphan_lines": [["T1", "O-999", 1]],
            "target_line_total_minor": 20000,
        },
    )
    require_equal(
        "attachment findings",
        {(item["name"], item["category"]) for item in results["attachments"]},
        {("order-101.txt", "OWNER_RELATIONSHIP"), ("order-102.txt", "CONTENT_HASH")},
    )


def check_forms():
    """Ensure A01–A11 each contain unique field names and one empty starter row."""
    templates = sorted((HERE / "templates").glob("A*.csv"))
    require_equal("form count", len(templates), 11)
    require_equal(
        "form sequence",
        [p.name[:3] for p in templates],
        [f"A{i:02d}" for i in range(1, 12)],
    )
    for template in templates:
        with template.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.reader(handle))
        if len(rows) != 2 or not rows[0] or not all(rows[0]):
            raise ValueError(f"{template.name}: expected headers and one empty row")
        require_equal(
            f"{template.name} field uniqueness", len(set(rows[0])), len(rows[0])
        )
        require_equal(f"{template.name} starter width", len(rows[1]), len(rows[0]))
        if any(rows[1]):
            raise ValueError(f"{template.name}: starter row must be empty")
    return len(templates)


def check_examples():
    """Compare book outcomes against independent constants, not regenerated answers."""
    connection = fixture()
    try:
        results = reconcile(connection)
    finally:
        connection.close()
    require_equal(
        "baseline findings",
        {(item["category"], item["order_id"]) for item in results["findings"]},
        {
            ("DUPLICATE_TARGET", "O-105"),
            ("SOURCE_ONLY", "O-104"),
            ("FIELD_CUSTOMER", "O-102"),
        },
    )
    require_equal(
        "boundary totals",
        [x["total_minor"] for x in boundary_example()],
        [20000, 22500, 23000, 18000],
    )
    require_equal("SQLite WAL reader values", snapshot_example(), [6000, 6000, 6500])
    metrics = measure(metric_fixture())
    require_equal(
        "timely-correct proportion", metrics["timely_correct_proportion"], 0.98
    )
    require_equal("successful p95", metrics["successful_p95_ms"], 100)
    require_equal("successful p99", metrics["successful_p99_ms"], 900)
    transition = transition_run()
    for variant, minutes in [
        ("planned", 65),
        ("delayed_data", 80),
        ("delayed_access", 71),
    ]:
        require_equal(
            f"{variant} forward arithmetic",
            transition[variant]["reopen"]["finish"],
            minutes,
        )
    require_equal(
        "delayed-data execution flag",
        transition["delayed_data_forward_schedule_is_executed"],
        False,
    )
    require_equal(
        "post-write minor-unit total", transition["post_write_total_minor"], 26000
    )
    scale = scale_run()
    require_equal(
        "differing scale partitions", scale["differing_partitions"], ["T1/00"]
    )
    require_equal("unique matched scale keys", scale["unique_matched_keys"], 19998)


def check_commands():
    """Run documented commands away from the source folder, retaining no output files.

    Each command uses this interpreter. A timeout prevents an accidental hang; its
    duration is a local test limit, not a migration performance requirement.
    """
    commands = DOCUMENTED_COMMANDS
    with tempfile.TemporaryDirectory(prefix="book-reader-") as directory:
        for script, args in commands:
            completed = subprocess.run(
                [sys.executable, str(HERE / script), *args],
                cwd=directory,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if completed.returncode:
                raise ValueError(
                    f"{script} exited {completed.returncode}:"
                    f" {completed.stderr.strip()}"
                )
            if not completed.stdout.strip():
                raise ValueError(f"{script} produced no reader output")
    return len(commands)


def check_readme_commands():
    """Reject mangled instructions and require every exercise command in both guides.

    Parse shell-style argument words, not a permissive substring. For example,
    'python 3 reconcile.py' must fail rather than resemble 'python3 reconcile.py'.
    The verifier itself is a documented entry point, not one of the five child CLIs.
    """
    allowed = {(name, args) for name, args in DOCUMENTED_COMMANDS}
    allowed.add(("verify_examples.py", ()))
    for name in ("README.md", "README.txt"):
        commands = set()
        for line in (HERE / name).read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not re.match(r"^(?:python3?|py)\s", stripped) or ".py" not in stripped:
                continue
            words = shlex.split(stripped)
            if words[0] == "py" and len(words) > 1 and words[1] == "-3":
                words.pop(1)
            command = (words[1], tuple(words[2:]))
            if not words[1].endswith(".py") or command not in allowed:
                raise ValueError(f"{name}: unrecognised or mangled command: {stripped}")
            commands.add(command)
        require_equal(f"{name} documented command coverage", commands, allowed)
    return len(allowed)


def main():
    """Print one JSON PASS record; give a concise actionable failure on stderr otherwise."""
    if sys.version_info < (3, 12):
        raise ValueError(
            "Python 3.12 or later is required. Run python --version first."
        )
    file_count = check_files()
    readme_command_count = check_readme_commands()
    query_count = check_queries()
    check_relationships()
    form_count = check_forms()
    check_examples()
    command_count = check_commands()
    print(
        json.dumps(
            {
                "result": "PASS",
                "manifest_files": file_count,
                "documented_CLIs": command_count,
                "documented_commands_checked": readme_command_count,
                "named_SQL_queries": query_count,
                "forms": form_count,
                "relationship_checks": "PASS",
                "python": sys.version.split()[0],
                "sqlite": sqlite3.sqlite_version,
                "scope": "local fictional exercises",
            }
        )
    )


if __name__ == "__main__":
    try:
        main()
    except (
        ValueError,
        OSError,
        sqlite3.Error,
        subprocess.TimeoutExpired,
        KeyError,
    ) as error:
        print(f"Verification failed: {error}", file=sys.stderr)
        sys.exit(1)
