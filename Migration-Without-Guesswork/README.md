# Migration Without Guesswork — companion 0.7.1

Original fictional teaching examples and blank evidence forms by Alexander Marinov (MGCA).
All material for this book stays inside `Migration-Without-Guesswork/` in this repository.

## Start here

1. Download the repository ZIP from GitHub’s **Code → Download ZIP**, then extract it completely. Open the extracted `Migration-Without-Guesswork` folder. Running a file inside a ZIP viewer is insufficient.
2. Install a current supported Python **3.12 or later**, with its standard-library `sqlite3` module. No pip packages, cloud accounts, API keys, paid services or network access are needed by these scripts.
3. Open a terminal in this folder. Run `python --version`, then `python verify_examples.py`. On systems where Python is named `python3`, substitute `python3` in every command. On Windows, `py -3` is another option if it selects a supported version.
4. Look for one JSON record containing `"result": "PASS"`. The reported runtime and SQLite versions are the ones actually used. A PASS validates these local examples, not a real migration.

If you need to run from another working directory, give the absolute script path, quoted if it contains spaces. The programs locate their fixture files beside the scripts.

Quick verification command:

```sh
python verify_examples.py
```

## Choose a reading path

| Book topic | Read / run | What to notice |
|---|---|---|
| Chapter 4 / Appendices D, G | `fixture.sql`, `queries.sql`, `reconcile.py` | Equal GBP200.00 controls hide three defects; only two keys are unique and matched. |
| Chapters 5–8 | `learning_exercises.py` | Boundaries, a WAL snapshot, retained intent, correct denominators and exception closure. |
| Chapters 9–13 | `transition_exercises.py` | Independent prerequisites, 50/55/60 bounds, preserved accepted work and authority states. |
| Appendix E | `scale_exercise.py` | 20,000 headers, 40 partitions, the same three known defects. |
| Appendix H | `relationship_exercises.py` | Header/line multiplication, orphan line, changed bytes and wrong owner. |
| Appendix A | `templates/A01_…csv` through `A11_…csv` | Blank forms for your own evidence, with no invented approvals. |

Read module/function docstrings and comments before changing a rule. The examples intentionally stay small and explicit. SQLite syntax is explained in the book’s dialect box; copying it to another engine requires semantic checks.

## Run individually and interpret results

```sh
python reconcile.py --output my_first_run
python learning_exercises.py
python transition_exercises.py
python scale_exercise.py
python relationship_exercises.py
```

Only `reconcile.py` retains reader output. Its new directory contains `result.json`, `exceptions.csv` and `run_manifest.json`. It prints **3 findings; 2 unique matched keys.** Keep the three files together. It refuses to overwrite an existing directory: choose `my_second_run` next time.

The other commands print JSON to the terminal. Values ending in `_minor` are integer minor units: GBP200.00 is `20000`, not `200.0`.

Expected landmarks:

- Baseline: duplicate target O-105, missing target O-104, wrong customer O-102 (C2 versus C9). Totals both `20000`.
- Boundary totals: `20000 → 22500 → 23000 → 18000`. SQLite WAL reader values: `[6000, 6000, 6500]`.
- Metrics: timely-correct `0.98`, successful p95 `100` ms and p99 `900` ms. Timeouts remain in the attempt denominator.
- Planned completion `65` minutes; delayed-access completion `71`. Delayed-data arithmetic gives `80`, **but that forward run is hypothetical**: it misses the minute-55 decision cutoff. First accepted target work at minute50 ends the planned simple return; minute60 is only a clock bound while NONE still holds.
- Recovery population: `6` rows and `26000` minor units, preserving later accepted work.
- Scale: `20000` rows each side, `20000000` minor units, `19998` unique matched keys, differing partition `T1/00`.
- Six lines: header control `20000`, deliberately inflated joined-header total `30000`, orphan `T1/O-999/1` despite unchanged line total.
- Attachments: order-101 has an owner relationship defect; order-102 has a byte-content defect. Owner metadata is not a live permission test.

## Use the SQL by itself

With the optional SQLite command-line program, open a **new disposable database**:

```sh
sqlite3 teaching.sqlite
.read fixture.sql
.read queries.sql
.quit
```

The `.read` commands belong inside the SQLite prompt. Do not rerun the fixture into the same database: it deliberately creates named tables and views. Start a new file for a new attempt. The Python verification route needs no separate SQLite CLI installation.

`queries_expected.json` lists exact rows for Q01–Q21; the book’s Appendix G provides the human-readable table. `[]` means no findings for that query, not that the entire migration passed. Keep comparisons independent: totals, membership, multiplicity, fields, relationships and external outcomes answer different questions.

## Try a safe change

Make a separate copy for experiments. In its `fixture.sql`, correct O-102’s target customer from C9 to C2 and run `reconcile.py` with a fresh output directory. The field finding disappears; the missing and duplicate key findings remain. Then compare that evidence with the original copy.

`verify_examples.py` checks the **unmodified release** against fixed expectations and byte hashes. It should fail on your edited copy. Do not change the expected outputs or checksum manifest merely to make a deliberate defect pass.

## Forms and troubleshooting

Each CSV template has a header and one blank starter row. Save a separate working copy, retain the headers, use one record per row, and record real evidence/owners/decisions. Template headers are explained in `templates/README.txt`. A filled form is not proof that a check ran or an owner approved it.

| Symptom | What to do |
|---|---|
| `python` is not found | Check your Python installation; try `python3` or a supported `py -3`. |
| Missing `sqlite3` module | Use a Python distribution that includes standard-library SQLite support. |
| Missing companion file | Extract the complete book folder; preserve its subdirectories. |
| Checksum mismatch | Use a fresh unedited download. Check newline/encoding changes by your editor. Keep exercises in another copy. |
| Output directory already exists | Use a new `--output` name; earlier evidence is deliberately retained. |
| SQL says table/view already exists | Start a new disposable database rather than rerunning the fixture over it. |
| Expected versus actual mismatch | Read the named check and values; record Python/SQLite versions and revision when reporting an issue. |

## Licence, scope and corrections

Original companion Python, SQL, documentation and CSV templates are MIT licensed; see `LICENSE.txt`. The book prose, diagrams, trademarks and separately sold products are outside that licence.

These examples use synthetic local data and make no remote calls. They do not implement real write fencing, production CDC, live invoice APIs, access control or disaster recovery. Apply the book’s contracts and your approved engineering process before adapting any method.

See `ERRATA.txt` and `VERSION_HISTORY.txt` in this folder. Report corrections through the GitHub Issues page linked from ERRATA.txt. Include the book name, revision, command, expected/actual output and runtime versions; remove sensitive business data. `SHA256SUMS.json` detects accidental divergence, not authenticated substitution.

Archive inventory: SHA256SUMS.json lists all 31 content files and excludes itself.
Repository-only .gitattributes is not included in the companion ZIP.
