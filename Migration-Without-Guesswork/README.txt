Migration Without Guesswork — companion 0.7.1

START WITH README.md: complete setup, reading path, expected results, safe exercises,
SQLite CLI instructions, templates, troubleshooting, licence and evidence limits.
A Markdown viewer is optional: README.md is readable plain text.

Quick start (inside this extracted folder):
  python --version
  python verify_examples.py
Use Python 3.12 or later with standard-library sqlite3. If your command is python3,
substitute it. No pip packages, network calls, credentials or paid accounts are used.

Individual commands:
  python reconcile.py --output my_first_run
  python learning_exercises.py
  python transition_exercises.py
  python scale_exercise.py
  python relationship_exercises.py

reconcile.py creates result.json, exceptions.csv and run_manifest.json in a NEW
output directory. The other exercise commands print JSON. Input files are found
relative to the script folder, not the working directory.

Expected baseline: 3 findings and 2 unique matched keys despite equal GBP200.00
controls. Full exact query expectations are in queries_expected.json and the book.
Run the original copy's verifier before making an experimental copy. Intentional
edits should fail byte checks; do not regenerate the manifest to conceal them.

Original Python, SQL, templates and companion documentation: MIT, LICENSE.txt.
Book prose, illustrations and separate paid products are not covered by this licence.
Synthetic local exercises only. These scripts are not a production migration tool.
Corrections: ERRATA.txt / VERSION_HISTORY.txt in this same book folder.
Use the book-specific GitHub Issues route documented in ERRATA.txt.

Archive inventory: SHA256SUMS.json lists all 31 content files and excludes itself.
Repository-only .gitattributes is not included in the companion ZIP.
