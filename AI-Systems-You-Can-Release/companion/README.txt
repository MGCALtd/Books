AI Systems You Can Release - companion 1.0.1
20 October 2026

LOCATION
Keep these files under AI-Systems-You-Can-Release/companion/.
The exercises run offline and use only Python's standard library.
Use Python 3.12 or later. Open this companion directory and run:
  python score_fixture.py
  python verify_sample.py
  python run_exercises.py
  python verify_full.py
  python repair_lab.py
  python outbox_lab.py
  python live_harness.py
  python verify_extensions.py

Use python3 or py -3 if that selects your intended Python installation.
Check the actual interpreter version first. No command makes provider calls.

EXPECTED RESULTS
score_fixture.py: A and B both 19/20. A BLOCK; B FIXTURE_GATES_PASS;
release_authorisation is NOT_ISSUED for both.
verify_sample.py: PASS for verdict arithmetic and malformed inputs.
run_exercises.py: T1/KB-17/2; precision/recall 1; one draft after lost reply;
ten passing trials of twelve; mean 160 ms, p95 400 ms, p99 1000 ms.
verify_full.py: 20 original tests, including execution of other documented
commands; ends with OK. The extension command itself checks 11 more tests.
repair_lab.py: six local cases, before 3/6 and after 6/6; no release authority.
outbox_lab.py: PENDING/one sink row, then DELIVERED/one sink row.
live_harness.py: offline adapter test, twenty unknowns, zero provider calls.
verify_extensions.py: 11 focused repair, delegation, outbox and adapter tests.

READ
controls.py contains the original retrieval, approval, local journal and
metric mechanisms. Random approval handles locate protected binding records.
authority_lab.py illustrates per-tool admission and fixed-minute quotas using
fake delegated-token metadata. It implements neither OAuth nor an MCP server.
repair_lab.py contrasts a deliberately flawed lookup with an eligible-first
repair. This executed mechanism is separate from supplied model verdicts.
outbox_lab.py simulates a remote sink using a second local SQLite database.
The sink's atomic key check is an explicit assumption behind deduplication.
live_harness.py is an optional adapter seam. The default path stays offline;
read Appendix J before configuring any approved endpoint or paid provider.

FORMS
forms/ contains ten blank CSV forms. examples/ contains completed synthetic
A/B decisions, one finding and one handoff using those same field headers.
release_board_questions.txt is an editable question sheet from Appendix K.
Code and forms are MIT-licensed under LICENSE.txt. Book prose is separately
copyrighted; companion code printed in the book remains MIT-licensed.

INTEGRITY
SHA256SUMS.json covers every companion file except itself and Python cache
files. verify_full.py checks the complete file set and each digest. Work in a
copy when experimenting; preserve the supplied baseline. Hashes identify
bytes against this baseline, not an independently signed or trusted source.

LIMITS
Test principals are supplied by trusted code. The approval registry and quota
counters are in memory. The outbox has one intent and one worker. No provider
behaviour, deployed authentication or independent platform run is established.
See ERRATA.txt for known limits. The examples create only temporary databases.

CORRECTIONS AND DOWNLOAD AVAILABILITY
https://github.com/MGCALtd/Books/tree/main/AI-Systems-You-Can-Release/companion
https://github.com/MGCALtd/Books/issues
Identify AI Systems You Can Release and version 1.0.1 in reports.
Book-specific files belong under AI-Systems-You-Can-Release/companion/.
