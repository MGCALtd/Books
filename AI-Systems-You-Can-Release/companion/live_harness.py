"""Optional adapter seam; offline by default. No provider results in this book.

Edit call_model() and grade() for an approved endpoint and reviewed rubric.
Only --live invokes the adapter; that may send data and incur provider fees.
The bundled self-test uses a fake adapter and no network or credentials.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parent


def call_model(case):
    """Replace with your approved SDK/endpoint. Never embed a secret here.

    Return {'answer': str, 'evidence': [controlled reference IDs],
            'accepted_effects': [authoritative reference IDs]}.
    Apply your own timeout, step and spending limits in this adapter.
    """
    raise NotImplementedError('No endpoint configured; no call was made')


def grade(case, response):
    """Replace with a versioned, calibrated grader. Unknown is the default.

    An answer alone cannot grade tenant isolation or accepted effects. Fetch
    the required controlled trace/state observations before returning a bool.
    """
    return None


def run(adapter, grader):
    cases = json.loads((ROOT/'verdict_fixture.json').read_text())
    observations = []
    for case in cases:
        start = time.perf_counter()
        try:
            response = adapter(case)
            if type(response) is not dict or type(response.get('answer')) is not str:
                raise ValueError('adapter response needs a text answer')
            passed = grader(case, response)
            if passed is not None and type(passed) is not bool:
                raise ValueError('grader must return bool or None')
            # No raw response retained by default. A hash alone cannot later
            # reconstruct evidence; use a controlled store when required.
            fingerprint = hashlib.sha256(json.dumps(response, sort_keys=True).encode()).hexdigest()
            error = None
        except Exception as exc:
            passed, fingerprint, error = None, None, type(exc).__name__
        observations.append({'id': case['id'], 'family': case['family'],
                             'passed': passed, 'elapsed_ms': round((time.perf_counter()-start)*1000, 3),
                             'response_sha256': fingerprint, 'error_type': error})
    # Same case IDs/families as the verdict fixture. Unknown rows are retained
    # separately; score_fixture.py deliberately rejects incomplete verdicts.
    return {'schema': 'book-evaluation-1', 'observations': observations,
            'release_authorisation': 'NOT_ISSUED'}


def self_test():
    result = run(lambda case: {'answer': 'Synthetic adapter reply'}, lambda c, r: None)
    if len(result['observations']) != 20 or any(r['passed'] is not None for r in result['observations']):
        raise RuntimeError('offline adapter contract failed')
    return {'result': 'PASS', 'mode': 'OFFLINE_ADAPTER_TEST', 'unknown': 20,
            'provider_calls': 0, 'release_authorisation': 'NOT_ISSUED'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='invoke your edited adapter; may incur fees')
    args = parser.parse_args()
    if args.live:
        raise SystemExit('Edit the case inputs, adapter, grader and approved budgets first; '
                         'then explicitly invoke run(call_model, grade). No endpoint is bundled.')
    print(json.dumps(self_test(), indent=2))
