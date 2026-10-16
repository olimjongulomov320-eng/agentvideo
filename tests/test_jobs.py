# -*- coding: utf-8 -*-
"""Tests: job store — states, dedupe, cancellation, limits, recovery."""
import os
import shutil
import tempfile
import unittest

from agent_system.jobs import ACTIVE_STATES, JobStore, new_job_id


class TestJobStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="jobs_test_")
        self.store = JobStore(os.path.join(self.tmp, "jobs.sqlite3"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_create_and_get(self):
        jid = self.store.create(1, "motion", "uz", "Firm A", 140, 1)
        job = self.store.get(jid)
        self.assertEqual(job["status"], "queued")
        self.assertEqual(job["style"], "motion")
        self.assertEqual(job["user_id"], 1)

    def test_unknown_style_rejected(self):
        with self.assertRaises(ValueError):
            self.store.create(1, "claymation", "en")

    def test_status_transitions_and_progress(self):
        jid = self.store.create(1, "motion", "en")
        for state in ("researching", "awaiting_approval", "rendering", "completed"):
            self.store.set_status(jid, state, "at %s" % state, 50)
        self.assertEqual(self.store.get(jid)["status"], "completed")
        self.assertEqual(self.store.get(jid)["progress"], 50)

    def test_invalid_status_rejected(self):
        jid = self.store.create(1, "motion", "en")
        with self.assertRaises(ValueError):
            self.store.set_status(jid, "exploded")

    def test_cancel_freezes_terminal_jobs(self):
        jid = self.store.create(1, "motion", "en")
        self.store.set_status(jid, "completed")
        self.assertFalse(self.store.request_cancel(jid))
        self.assertEqual(self.store.get(jid)["status"], "completed")

    def test_cancel_active_job(self):
        jid = self.store.create(1, "motion", "en")
        self.store.set_status(jid, "rendering")
        self.assertTrue(self.store.request_cancel(jid))
        self.assertTrue(self.store.is_cancelled(jid))

    def test_duplicate_update_detection(self):
        self.assertTrue(self.store.mark_update(5550, "J1"))
        self.assertFalse(self.store.mark_update(5550, "J1"))
        self.assertTrue(self.store.seen_update(5550))

    def test_distinct_updates_both_accepted(self):
        self.assertTrue(self.store.mark_update(1))
        self.assertTrue(self.store.mark_update(2))

    def test_active_count_and_rendering_count(self):
        a = self.store.create(1, "motion", "en")
        b = self.store.create(1, "motion", "en")
        c = self.store.create(1, "motion", "en")
        self.store.set_status(a, "rendering")
        self.store.set_status(b, "researching")
        self.store.set_status(c, "completed")
        self.assertEqual(self.store.active_count(), 2)
        self.assertEqual(self.store.rendering_count(), 1)

    def test_concurrency_limit_is_observable(self):
        limit = 1
        j1 = self.store.create(1, "motion", "en")
        self.store.set_status(j1, "rendering")
        self.assertGreaterEqual(self.store.active_count(), limit)

    def test_find_active_for_user(self):
        j1 = self.store.create(7, "motion", "en")
        self.store.set_status(j1, "researching")
        self.assertEqual(self.store.find_active_for_user(7)["id"], j1)
        self.store.set_status(j1, "completed")
        self.assertIsNone(self.store.find_active_for_user(7))

    def test_list_for_user_only_returns_own_jobs(self):
        self.store.create(7, "motion", "en")
        self.store.create(8, "motion", "en")
        self.assertEqual(len(self.store.list_for_user(7)), 1)

    def test_recover_interrupted_marks_failed(self):
        a = self.store.create(1, "motion", "en")
        b = self.store.create(1, "motion", "en")
        self.store.set_status(a, "rendering")
        self.store.set_status(b, "researching")
        recovered = self.store.recover_interrupted()
        self.assertEqual(sorted(recovered), sorted([a, b]))
        self.assertEqual(self.store.get(a)["status"], "failed")
        self.assertIn("restart", self.store.get(a)["error"])

    def test_fail_records_redacted_error(self):
        from agent_system import security
        token = "1234567890:AAFakeBotTokenValueForTesting_abc"
        security.register_secret(token)
        jid = self.store.create(1, "motion", "en")
        self.store.fail(jid, "boom with %s inside" % token)
        self.assertNotIn(token, self.store.get(jid)["error"])

    def test_events_are_logged(self):
        jid = self.store.create(1, "motion", "en")
        self.store.log_event(jid, "note", "hello")
        kinds = [e["kind"] for e in self.store.events(jid)]
        self.assertIn("created", kinds)
        self.assertIn("note", kinds)

    def test_job_ids_are_unique_and_short(self):
        ids = {new_job_id() for _ in range(300)}
        self.assertEqual(len(ids), 300)
        self.assertTrue(all(len(i) == 9 and i.startswith("J") for i in ids))

    def test_persistence_across_store_instances(self):
        jid = self.store.create(1, "motion", "en")
        store2 = JobStore(os.path.join(self.tmp, "jobs.sqlite3"))
        self.assertEqual(store2.get(jid)["id"], jid)

    def test_cleanup_old_keeps_recent(self):
        jid = self.store.create(1, "motion", "en")
        self.store.set_status(jid, "completed")
        self.assertEqual(self.store.cleanup_old(keep_days=1), 0)


if __name__ == "__main__":
    unittest.main()
