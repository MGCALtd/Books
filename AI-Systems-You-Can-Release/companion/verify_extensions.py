"""Executable checks for the new repair, delegation, outbox and adapter labs."""
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from controls import Principal, Policy
from authority_lab import Gateway, Delegation
from repair_lab import run as repair_run
from outbox_lab import Outbox, FakeSink, run as outbox_run
from live_harness import run as harness_run, self_test


class ExtensionChecks(unittest.TestCase):
    def setUp(self):
        self.p = Principal('T1', 'staff-1', frozenset({'KB-17'}))
        self.payload = {'equipment': 'monitor', 'reason': 'Synthetic example'}
        self.token = Delegation('T1', 'staff-1', 'service-desk',
                                frozenset({'policy.read', 'draft.write'}), 600)

    def test_random_handle_and_collision_does_not_overwrite(self):
        policy = Policy()
        with patch('controls.secrets.token_urlsafe', side_effect=['first', 'first', 'second']) as rng:
            a = policy.approve(self.p, 'OP-1', self.payload, 60)
            b = policy.approve(self.p, 'OP-2', self.payload, 60)
        self.assertEqual((a, b), ('first', 'second'))
        self.assertEqual([c.args for c in rng.call_args_list], [(32,), (32,), (32,)])
        self.assertEqual(policy.approvals[a][2], 'OP-1')

    def test_new_handles_still_bind_operation_and_expiry(self):
        policy = Policy()
        h = policy.approve(self.p, 'OP-1', self.payload, 60)
        self.assertRegex(h, r'^[A-Za-z0-9_-]{43}$')
        with self.assertRaises(PermissionError):
            policy.allow(self.p, 'save_draft', 'T1', 'OP-2', self.payload, h, 10)
        with self.assertRaises(PermissionError):
            policy.allow(self.p, 'save_draft', 'T1', 'OP-1', self.payload, h, 60)

    def test_repair_observes_defect_and_keeps_positive_routes(self):
        r = repair_run()
        self.assertEqual((r['before_passes'], r['after_passes']), (3, 6))
        crossed = r['cases'][0]
        self.assertEqual(crossed['before'], [('T2', 'KB-17', 1)])
        self.assertEqual(crossed['after'], [])
        self.assertEqual(r['release_authorisation'], 'NOT_ISSUED')

    def test_delegation_cannot_lend_broader_service_authority(self):
        variations = [replace(self.token, tenant='T2'),
                      replace(self.token, subject='staff-2'),
                      replace(self.token, audience='unrelated-api'),
                      replace(self.token, scopes=frozenset({'policy.read'})),
                      replace(self.token, expires=10)]
        for token in variations:
            with self.subTest(token=token), self.assertRaises(PermissionError):
                Gateway().admit(self.p, token, 'save_draft', 'T1', 10)
        self.assertEqual(Gateway().admit(self.p, self.token, 'save_draft', 'T1', 10), 'draft.write')

    def test_tool_allowlist_cross_tenant_and_withdrawal(self):
        for tool, tenant, p in [('submit_request', 'T1', self.p),
                                ('read_policy', 'T2', self.p),
                                ('save_draft', 'T1', replace(self.p, can_save=False))]:
            with self.subTest(tool=tool, tenant=tenant), self.assertRaises(PermissionError):
                Gateway().admit(p, self.token, tool, tenant, 10)

    def test_rate_scope_and_fixed_window_limit(self):
        g = Gateway()
        g.admit(self.p, self.token, 'read_policy', 'T1', 58)
        g.admit(self.p, self.token, 'read_policy', 'T1', 59)
        with self.assertRaises(PermissionError):
            g.admit(self.p, self.token, 'read_policy', 'T1', 59.5)
        g.admit(self.p, self.token, 'read_policy', 'T1', 60)
        g.admit(self.p, self.token, 'save_draft', 'T1', 60)

    def test_outbox_reopens_after_sink_commit_and_lost_reply(self):
        self.assertEqual(outbox_run(), {
            'after_lost_reply': {'local_state': 'PENDING', 'sink_rows': 1},
            'after_retry': {'local_state': 'DELIVERED', 'sink_rows': 1},
            'kind': 'LOCAL_REMOTE_SINK_SIMULATION'})

    def test_outbox_and_sink_reject_changed_payload(self):
        with tempfile.TemporaryDirectory() as temp:
            outbox, sink = Outbox(Path(temp)/'l.db'), FakeSink(Path(temp)/'r.db')
            outbox.enqueue('T1', 'staff-1', 'OP', {'a': 'original'})
            with self.assertRaises(ValueError):
                outbox.enqueue('T1', 'staff-1', 'OP', {'a': 'changed'})
            outbox.deliver(sink)
            with self.assertRaises(ValueError):
                sink.accept('T1', 'staff-1', 'OP', '{"a":"changed"}')
            self.assertEqual(sink.count(), 1)

    def test_adapter_default_unknowns_and_no_provider_calls(self):
        self.assertEqual(self_test()['provider_calls'], 0)
        self.assertEqual(self_test()['unknown'], 20)

    def test_adapter_errors_remain_unknown_not_false_or_pass(self):
        r = harness_run(lambda c: {}, lambda c, r: True)
        self.assertEqual(len(r['observations']), 20)
        self.assertTrue(all(x['passed'] is None and x['error_type'] == 'ValueError'
                            for x in r['observations']))

    def test_corrected_chapter_eleven_intersection(self):
        timely = [True]*17 + [False]*3
        correct = [True]*16 + [False] + [True]*3
        self.assertEqual(sum(t and c for t, c in zip(timely, correct)), 16)
        self.assertEqual(sum(t and c for t, c in zip(timely, correct))/20, .8)
        self.assertEqual(460/16, 28.75)


if __name__ == '__main__':
    unittest.main(verbosity=2)
