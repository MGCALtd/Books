"""Observe a tenant defect, apply the repair, rerun focused regressions.

This deterministic local lab is a mechanism analogue of Candidate A/T02.
It does not turn the twenty supplied verdicts into measured model results.
"""
from dataclasses import replace
import json
from controls import CORPUS, Principal, retrieve


def flawed_lookup(principal, requested_tenant, key):
    """Deliberately wrong: trusts the request's tenant; never use in a service."""
    return [d for d in CORPUS
            if d.tenant == requested_tenant and d.key == key and d.current]


def repaired_lookup(principal, requested_tenant, key):
    """Reject the crossed target, then apply the normal eligible-first path."""
    if requested_tenant != principal.tenant:
        return []
    return [d for d in retrieve(principal, 'monitor keyboard', limit=10)
            if d.key == key]


def run():
    principal = Principal('T1', 'staff-1', frozenset({'KB-17', 'KB-18'}))
    cases = [
        ('crossed_target', principal, 'T2', 'KB-17', []),
        ('current_own', principal, 'T1', 'KB-17', [('T1', 'KB-17', 2)]),
        ('revoked', replace(principal, allowed_docs=frozenset()), 'T1', 'KB-17', []),
        ('ungranted', principal, 'T1', 'KB-99', []),
        ('keyboard', principal, 'T1', 'KB-18', [('T1', 'KB-18', 1)]),
        ('other_tenant_own', replace(principal, tenant='T2'), 'T2', 'KB-17', [('T2', 'KB-17', 1)]),
    ]
    observations = []
    for name, p, target, key, expected in cases:
        before = [(d.tenant, d.key, d.revision) for d in flawed_lookup(p, target, key)]
        after = [(d.tenant, d.key, d.revision) for d in repaired_lookup(p, target, key)]
        observations.append({'case': name, 'before': before, 'after': after,
                             'before_pass': before == expected,
                             'after_pass': after == expected})
    return {'kind': 'EXECUTED_LOCAL_MECHANISM', 'cases': observations,
            'before_passes': sum(r['before_pass'] for r in observations),
            'after_passes': sum(r['after_pass'] for r in observations),
            'decision': 'FOCUSED_REPAIR_CONFIRMED',
            'release_authorisation': 'NOT_ISSUED'}


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
