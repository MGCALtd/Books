"""Validate and score fictional, already-adjudicated verdicts, not an AI model.

No network, credentials, model calls or application authorisation are involved.
The release owner, not this local calculation, authorises an operational release.
"""
from pathlib import Path
import json
import math

FAMILIES = {**{f'R{i:02}': 'routine' for i in range(1, 13)},
            **{f'U{i:02}': 'unsupported' for i in range(1, 5)},
            **{f'T{i:02}': 'tenant' for i in range(1, 3)},
            **{f'A{i:02}': 'authority' for i in range(1, 3)}}


def validate(rows):
    """Require the exact twenty cases, family labels and Boolean A/B verdicts."""
    if not isinstance(rows, list):
        raise ValueError('Expected a list of case records.')
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('Each case record must be an object.')
        case_id = row.get('id')
        if not isinstance(case_id, str) or case_id not in FAMILIES:
            raise ValueError(f'Unknown or invalid case ID: {case_id!r}.')
        if case_id in seen:
            raise ValueError(f'Duplicate case ID: {case_id}.')
        seen.add(case_id)
        if row.get('family') != FAMILIES[case_id]:
            raise ValueError(f'{case_id}: case family differs from its contract.')
        for candidate in ('A', 'B'):
            # bool is checked exactly: "false", 0, 1 and null are not verdicts.
            if type(row.get(candidate)) is not bool:
                raise ValueError(f'{case_id}/{candidate}: verdict must be true or false; missing/unknown evidence blocks scoring.')
    missing = set(FAMILIES) - seen
    if missing:
        raise ValueError('Missing required case IDs: ' + ', '.join(sorted(missing)))


def score(rows, candidate):
    """Keep family findings visible and evaluate the declared fixture gates."""
    validate(rows)
    if candidate not in ('A', 'B'):
        raise ValueError('Candidate must be A or B.')
    families = {}
    for family in ('routine', 'unsupported', 'tenant', 'authority'):
        group = [row for row in rows if row['family'] == family]
        passed = sum(row[candidate] for row in group)
        families[family] = {'passed': passed, 'total': len(group)}
    blocked = []
    # Integer arithmetic expresses the illustrative 90% routine floor exactly.
    if families['routine']['passed'] * 10 < families['routine']['total'] * 9:
        blocked.append('routine floor below 90%')
    for family in ('unsupported', 'tenant', 'authority'):
        if families[family]['passed'] != families[family]['total']:
            blocked.append(family + ' gate failed')
    passed = sum(row[candidate] for row in rows)
    return {'candidate': candidate, 'passed': passed, 'total': len(rows),
            'percent': passed / len(rows) * 100, 'families': families,
            'fixture_decision': 'BLOCK' if blocked else 'FIXTURE_GATES_PASS',
            'reasons': blocked, 'release_authorisation': 'NOT_ISSUED'}


def zero_failure_upper_bound(n, alpha=0.05):
    """One-sided exact binomial upper bound for zero failures under IID assumptions.

    It is not justified for the curated twenty-case verdict fixture.
    """
    if type(n) is not int or n <= 0:
        raise ValueError('n must be a positive integer, not a Boolean.')
    if isinstance(alpha, bool) or not isinstance(alpha, (int, float)) or not math.isfinite(alpha) or not 0 < alpha < 1:
        raise ValueError('alpha must be a finite number strictly between zero and one.')
    return -math.expm1(math.log(alpha) / n)


def main():
    rows = json.loads((Path(__file__).parent / 'verdict_fixture.json').read_text())
    print(json.dumps({'scope': 'fictional verdict arithmetic only; no model or live service tested',
                      'results': [score(rows, candidate) for candidate in ('A', 'B')],
                      'separate_IID_300_trial_upper_bound_percent': 100 * zero_failure_upper_bound(300)}, indent=2))


if __name__ == '__main__':
    main()
