"""Print independently specified teaching results; no model calls or real users."""
from dataclasses import replace
from pathlib import Path
import json
import tempfile
from controls import (CORPUS, Principal, Policy, DraftStore, retrieve,
                      retrieval_metrics, safe_event, percentile, trial_report)


def main():
    p = Principal('T1', 'staff-1', frozenset({'KB-17', 'KB-18'}))
    docs = retrieve(p, 'monitor approval')
    identity = [(d.tenant, d.key, d.revision) for d in docs]
    metrics = retrieval_metrics(identity, [('T1', 'KB-17', 2)])
    policy = Policy()
    payload = {'equipment': 'monitor', 'reason': 'Synthetic example'}
    handle = policy.approve(p, 'OP-1', payload, expires=60)
    with tempfile.TemporaryDirectory() as directory:
        store = DraftStore(Path(directory) / 'drafts.db')
        try:
            store.save(policy, p, 'OP-1', payload, handle, now=10, lose_ack=True)
        except TimeoutError:
            pass
        # A new connection reopens accepted state, rather than trusting a reply.
        reopened = DraftStore(Path(directory) / 'drafts.db')
        draft_id = reopened.save(policy, p, 'OP-1', payload, handle, now=11)
        result = {'retrieved': identity, 'retrieval': metrics,
                  'lost_ack_rows': reopened.count(), 'retry_draft': draft_id}
    rows = [{'case': c, 'trial': t, 'passed': not (c == 'C3' and t > 1)}
            for c in ('C1', 'C2', 'C3', 'C4') for t in (1, 2, 3)]
    result['variability'] = trial_report(rows)
    timings = [100] * 18 + [400, 1000]
    result['latency_ms'] = {'mean': sum(timings)/len(timings),
                            'p95': percentile(timings, .95),
                            'p99': percentile(timings, .99)}
    result['redacted'] = safe_event({'trace_id': 'TR-1', 'decision': 'DENY',
                                     'raw_prompt': 'synthetic private text',
                                     'api_key': 'not-a-real-key'})
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
