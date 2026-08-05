"""Proxy Collector Pro - Scheduler Tests"""

import unittest
from engine.scheduler import FairScheduler
from core.models import ValidationJob, Proxy


class TestScheduler(unittest.TestCase):
    def setUp(self):
        self.scheduler = FairScheduler()
        self.scheduler.set_targets(10, 10, 10, 10, 40)

    def test_add_job(self):
        proxy = Proxy(
            host="1.2.3.4", port=8080, protocol="http"
        )
        job = ValidationJob(proxy=proxy, protocol="http", endpoint="")
        self.assertTrue(self.scheduler.add_job(job))

    def test_deduplication(self):
        proxy = Proxy(
            host="1.2.3.4", port=8080, protocol="http"
        )
        job1 = ValidationJob(proxy=proxy, protocol="http")
        job2 = ValidationJob(proxy=proxy, protocol="http")

        self.assertTrue(self.scheduler.add_job(job1))
        self.assertFalse(self.scheduler.add_job(job2))

    def test_target_reached(self):
        self.scheduler.mark_success("http")
        self.assertFalse(
            self.scheduler.is_target_reached("http")
        )

        for _ in range(10):
            self.scheduler.mark_success("http")

        self.assertTrue(
            self.scheduler.is_target_reached("http")
        )


if __name__ == "__main__":
    unittest.main()
