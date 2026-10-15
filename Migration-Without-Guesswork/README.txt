Migration Without Guesswork — companion examples, revision 0.5.0

CONTENTS
reconcile.py — static CC-03/header-exercise-1 reconciliation
fixture.sql — complete fictional schema, inputs, views and status mapping
learning_exercises.py — changing data, local effects and response calculations
transition_exercises.py — cutover arithmetic, recovery data and authority model
scale_exercise.py — 20,000 synthetic headers and 40 partition controls
verify_examples.py — checksums, expected results and all documented CLI commands
LICENSE.txt — MIT licence for original code/SQL/companion documentation
SHA256 SUMS.json — individual file integrity manifest (excluding itself)

REQUIREMENTS
Use Python 3.12 or later with standard-library sqlite 3 available.
No package installation, credentials, external accounts or network calls required.
Reviewed runtime: Python 3.12.14 / SQLite 3.53.1, as reported by that interpreter.
This is an observed environment, not a recommendation to pin obsolete patches.
Python 3.12.14 and 3.14.8 are checked separately for this revision. Python 3.10/3.11 and independent Windows/macOS execution have not been checked. Always use current security patches.

RUN FROM THIS DIRECTORY
python 3 reconcile.py --output my_first_run
python 3 learning_exercises.py
python 3 transition_exercises.py
python 3 scale_exercise.py
python 3 verify_examples.py

The reconciliation output directory must not already exist. Expected baseline:
3 findings (duplicateO-105, missingO-104, wrongcustomerO-102),2 unique matched keys,
4 rows per side,20000 GBP minor units per side. Read result.json, exceptions.csv
and run_manifest.json together. The original failed fixture is deliberate.

The transition forward schedules are 65/80/71 minutes. The 80 minute variation is
not executed under the hard 55 minute decision rule. The clock-only pre-write
return limit 60 applies only while no target business work is accepted; planned
controlled writes begin 50 and end simple pre-write return. Logical states are
SOURCE/NONE/TARGET; this model does not implement distributed fencing.

Scale expected:20000 rows and 20000000 minor units on each side,40 partitions,
T1/00 different,19998 unique matched keys and 3 intentional findings. Hashing uses
mapped sorted typed JSON tuples with byte-length framing, preserving duplicates.
The local algorithm collects each partition in memory; it is not a production
streaming or capacity benchmark.

All records/results are fictional. This code is a learning aid, not production
acceptance software. Do not connect it to live customer systems. Local atomicity
is not distributed exactly-once processing. Consecutive teaching positions are
not a universal CDC position rule. Synthetic performance figures are not measured
service performance. Journal reconstruction is ordered and requires before-values;
it is not an idempotent general replay engine.

LICENSING
Original companion code, SQL and documentation: MIT, see LICENSE.txt. Keep the
copyright/licence notices in substantial redistributed copies. Book prose,
illustrations, trademarks and separate paid packs are outside this code licence.
No third-party runtime is bundled. Obtain Python/SQLite through their maintainers.

ADDITIONAL RESOURCES
queries.sql and queries_expected.json:21 named queries and exact baseline rows.
relationship_exercises.py: six lines, multiplied header total and orphan case;
attachments/: actual synthetic bytes, hashes and ownership manifest.
templates/: eleven original blank CSV forms matching Appendix A1–A11.
ERRATA.txt and VERSION_HISTORY.txt identify revision and feedback route.
Run python3 relationship_exercises.py and python3 verify_examples.py.
