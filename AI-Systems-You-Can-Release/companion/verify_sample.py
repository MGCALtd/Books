"""Meaningful arithmetic and input-boundary checks for the sample chapter."""
from pathlib import Path
from copy import deepcopy
import json
import re
from score_fixture import score, validate, zero_failure_upper_bound


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def rejects(rows, name):
    try:
        validate(rows)
    except ValueError:
        return
    raise AssertionError('Malformed fixture was accepted: ' + name)


def main():
    root = Path(__file__).parent
    commands = re.findall(r'^  python ([a-z_]+\.py)$', (root / 'README.txt').read_text(), flags=re.MULTILINE)
    expected = [command.split()[1] for command in json.loads((root / 'commands.json').read_text())]
    require(commands == expected, 'README commands drifted from documented executable entry points.')
    rows = json.loads((root / 'verdict_fixture.json').read_text())
    a, b = score(rows, 'A'), score(rows, 'B')
    require((a['passed'], b['passed']) == (19, 19), 'Expected equal 19/20 roll-ups.')
    require(a['fixture_decision'] == 'BLOCK' and a['reasons'] == ['tenant gate failed'], 'A must block on tenant isolation.')
    require(b['fixture_decision'] == 'FIXTURE_GATES_PASS', 'B should pass only the fixture gates.')
    require(a['release_authorisation'] == b['release_authorisation'] == 'NOT_ISSUED', 'Checker cannot authorise release.')
    changed = deepcopy(rows)
    next(row for row in changed if row['id'] == 'T02')['B'] = False
    result = score(changed, 'B')
    require(result['passed'] == 18 and result['percent'] == 90 and result['fixture_decision'] == 'BLOCK', 'Exercise must yield18/20 and block.')
    require(abs(zero_failure_upper_bound(300)*100 - 0.99360819444577121543587290481534438766390570055500) < 1e-10, 'Statistical illustration differs from independently specified expected value.')
    rejects(rows[:-1], 'missing case')
    rejects(rows + [deepcopy(rows[0])], 'duplicate ID')
    for value in [None, 'false', 0, 1]:
        bad = deepcopy(rows); bad[0]['A'] = value; rejects(bad, 'non-Boolean verdict')
    bad = deepcopy(rows); bad[0]['family'] = 'tenant'; rejects(bad, 'wrong family')
    bad = deepcopy(rows); bad[0]['id'] = 'UNKNOWN'; rejects(bad, 'unexpected case ID')
    print(json.dumps({'result':'PASS','scope':'synthetic arithmetic/validation only','checks':['README command spelling','equal scores/different gates','no release authority','exercise mutation','exact binomial illustration','missing case','duplicate ID','four invalid verdict types','wrong family','unexpected ID']}))


if __name__ == '__main__':
    main()
