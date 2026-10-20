"""Regression checks with explicit independent expectations and failure cases.

Run from any directory. Temporary SQLite files are deleted on completion.
Assertions use unittest methods, so Python -O does not disable them.
No dependency installation, API key, network request or paid service required.
"""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from controls import (CORPUS, Principal, Policy, DraftStore, retrieve,
                      retrieval_metrics, safe_event, percentile, trial_report)

ROOT = Path(__file__).resolve().parent


class MechanismChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'drafts.db'
        self.p = Principal('T1', 'staff-1', frozenset({'KB-17', 'KB-18'}))
        self.policy = Policy()
        self.payload = {'equipment': 'monitor', 'reason': 'Synthetic example'}
        self.handle = self.policy.approve(self.p, 'OP-1', self.payload, 60)
        self.store = DraftStore(self.path)

    def allow(self, **changes):
        args = dict(principal=self.p, action='save_draft', tenant='T1',
                    operation='OP-1', payload=self.payload,
                    handle=self.handle, now=10)
        args.update(changes)
        return self.policy.allow(**args)

    def save(self, **changes):
        args = dict(policy=self.policy, principal=self.p, operation='OP-1',
                    payload=self.payload, handle=self.handle, now=10)
        args.update(changes)
        return self.store.save(**args)

    def test_retrieval_exact_identity_and_stale_revision(self):
        docs = retrieve(self.p, 'monitor approval')
        self.assertEqual([(d.tenant, d.key, d.revision) for d in docs],
                         [('T1', 'KB-17', 2)])
        self.assertNotIn(CORPUS[0], docs)
        self.assertNotIn(CORPUS[2], docs)

    def test_retrieval_revoked_and_other_tenant(self):
        self.assertEqual(retrieve(replace(self.p, allowed_docs=frozenset()),
                                  'monitor'), [])
        other = replace(self.p, tenant='T2')
        self.assertEqual([d.text for d in retrieve(other, 'monitor')],
                         ['Monitor requests require finance approval.'])

    def test_poison_reaches_context_but_submission_denied(self):
        granted = replace(self.p, allowed_docs=frozenset({'KB-99'}))
        docs = retrieve(granted, 'monitor')
        self.assertEqual(len(docs), 1)
        self.assertIn('Ignore rules', docs[0].text)
        with self.assertRaises(PermissionError):
            self.allow(principal=granted, action='submit_request')
        self.assertEqual(self.store.count(), 0)

    def test_empty_and_unique_retrieval_metrics(self):
        got = retrieval_metrics(['a', 'a', 'b', 'x'], ['a', 'b'])
        self.assertEqual(got, {'hits': 2, 'returned': 3, 'relevant': 2,
                               'precision': 2/3, 'recall': 1})
        self.assertEqual(retrieval_metrics([], ['a'])['recall'], 0)
        self.assertIsNone(retrieval_metrics([], ['a'])['precision'])
        self.assertIsNone(retrieval_metrics(['x'], [])['recall'])

    def test_approval_happy_path(self):
        self.assertIsNone(self.allow())
        self.assertTrue(self.save().startswith('D-'))
        self.assertEqual(self.store.count(), 1)

    def test_approval_binding_and_expiry(self):
        variations = [dict(tenant='T2'), dict(action='submit_request'),
                      dict(operation='OP-2'), dict(handle='forged'),
                      dict(payload=dict(self.payload, equipment='keyboard')),
                      dict(principal=replace(self.p, subject='staff-2')),
                      dict(principal=replace(self.p, can_save=False)),
                      dict(now=60), dict(now=61)]
        for changes in variations:
            with self.subTest(changes=changes), self.assertRaises(PermissionError):
                self.allow(**changes)
        self.assertEqual(self.store.count(), 0)

    def test_policy_revision_invalidates_approval(self):
        self.policy.revision = 'P2'
        with self.assertRaises(PermissionError):
            self.save()
        self.assertEqual(self.store.count(), 0)

    def test_payload_rejects_ambiguity(self):
        bad = [dict(self.payload, destination='outsider.invalid'),
               dict(self.payload, equipment='server'),
               dict(self.payload, reason='\t\r\n'),
               dict(self.payload, reason='x'*201),
               dict(self.payload, reason=None), {'equipment': 'monitor'}]
        for payload in bad:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                self.allow(payload=payload)

    def test_nonfinite_time_rejected(self):
        for value in [float('nan'), float('inf'), True]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.allow(now=value)

    def test_lost_ack_reopens_single_effect(self):
        with self.assertRaises(TimeoutError):
            self.save(lose_ack=True)
        self.store = DraftStore(self.path)
        first = self.save(now=11)
        second = self.save(now=12)
        self.assertEqual(first, second)
        self.assertEqual(self.store.count(), 1)

    def test_before_commit_rolls_back(self):
        with self.assertRaises(RuntimeError):
            self.save(fail_before_commit=True)
        self.assertEqual(DraftStore(self.path).count(), 0)
        self.save(now=11)
        self.assertEqual(self.store.count(), 1)

    def test_changed_payload_conflicts_even_with_new_approval(self):
        self.save()
        changed = dict(self.payload, reason='Changed intent')
        handle = self.policy.approve(self.p, 'OP-1', changed, 60)
        with self.assertRaisesRegex(ValueError, 'idempotency conflict'):
            self.save(payload=changed, handle=handle)
        self.assertEqual(self.store.count(), 1)
        con = sqlite3.connect(self.path)
        try:
            stored = json.loads(con.execute('SELECT payload FROM drafts').fetchone()[0])
        finally:
            con.close()
        self.assertEqual(stored, self.payload)

    def test_operation_scope_separates_subject_and_tenant(self):
        ids = {self.save()}
        for p in [replace(self.p, subject='staff-2'), replace(self.p, tenant='T2')]:
            handle = self.policy.approve(p, 'OP-1', self.payload, 60)
            ids.add(self.save(principal=p, handle=handle))
        self.assertEqual(len(ids), 3)
        self.assertEqual(self.store.count(), 3)

    def test_retry_rechecks_current_capability(self):
        self.save()
        with self.assertRaises(PermissionError):
            self.save(principal=replace(self.p, can_save=False))
        self.assertEqual(self.store.count(), 1)

    def test_trace_projection_and_its_content_limit(self):
        raw = {'trace_id': 'TR-1', 'decision': 'DENY', 'api_key': 'fake',
               'raw_prompt': 'private synthetic text', 'draft_id': 12}
        self.assertEqual(safe_event(raw), {'trace_id': 'TR-1', 'decision': 'DENY'})
        # Documents a limitation; this toy projection is NOT a complete DLP tool.
        self.assertEqual(safe_event({'decision': 'arbitrary text'})['decision'],
                         'arbitrary text')

    def test_variability_unknown_and_duplicate_trials(self):
        rows = [{'case': c, 'trial': t, 'passed': not(c == 'C3' and t > 1)}
                for c in ('C1', 'C2', 'C3', 'C4') for t in (1, 2, 3)]
        self.assertEqual(len({(r['case'], r['trial']) for r in rows}), 12)
        self.assertEqual(trial_report(rows), {'passed_trials': 10, 'trials': 12,
                         'unknown': 0, 'all_observed_trials_pass_cases': 3, 'cases': 4})
        rows[8]['passed'] = None
        self.assertEqual(trial_report(rows)['unknown'], 1)
        self.assertEqual(trial_report(rows)['passed_trials'], 10)
        with self.assertRaises(ValueError):
            trial_report(rows + [rows[0]])

    def test_graders_and_budget_arithmetic(self):
        j1 = [True, True, True, False, False, True]
        j2 = [True, False, True, False, True, True]
        truth = [True, False, True, False, True, True]
        self.assertEqual(sum(a == b for a, b in zip(j1, j2)), 4)
        self.assertEqual(sum(a == b for a, b in zip(j1, truth)), 4)
        self.assertEqual(sum(a == b for a, b in zip(j2, truth)), 6)
        self.assertEqual((400 + 4*3*5)/16, 28.75)
        self.assertEqual(1000 - 20, 980)
        self.assertAlmostEqual(16/(16+98)*100, 14.035087719298245)

    def test_nearest_rank_latency(self):
        times = [100]*18 + [400, 1000]
        self.assertEqual(sum(times)/len(times), 160)
        self.assertEqual(percentile(times, .95), 400)
        self.assertEqual(percentile(times, .99), 1000)

    def test_readme_commands_and_all_documented_entry_points(self):
        expected = json.loads((ROOT/'commands.json').read_text())
        found = re.findall(r'^  (python [a-z_]+\.py)$',
                           (ROOT/'README.txt').read_text(), re.MULTILINE)
        self.assertEqual(found, expected)
        # Do not recursively run this verifier from inside itself.
        for command in expected:
            if command.endswith('verify_full.py'):
                continue
            completed = subprocess.run([sys.executable, '-O', str(ROOT/command.split()[1])],
                                       cwd=self.temp.name, text=True, capture_output=True,
                                       timeout=30)
            self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_shipping_manifest(self):
        manifest = json.loads((ROOT/'SHA256SUMS.json').read_text())
        shipped = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*')
                   if p.is_file() and '__pycache__' not in p.parts
                   and p.name != 'SHA256SUMS.json'}
        self.assertEqual(set(manifest), shipped)
        for name, expected in manifest.items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),
                             expected, name)


if __name__ == '__main__':
    unittest.main(verbosity=2)
