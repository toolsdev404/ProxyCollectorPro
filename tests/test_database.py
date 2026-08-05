"""Proxy Collector Pro - Database Tests"""

import unittest
import os
import tempfile
import time
from core.database import Database
from core.models import Proxy, Source


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.db_file = tempfile.mktemp(suffix=".db")
        self.db = Database(self.db_file)

    def tearDown(self):
        self.db.close()
        for ext in ["", "-wal", "-shm"]:
            f = self.db_file + ext
            if os.path.exists(f):
                os.remove(f)

    def test_insert_proxy(self):
        proxy = Proxy(
            host="127.0.0.1", port=8080,
            protocol="http", source="test"
        )
        self.db.insert_proxy(proxy)
        self.db._writer.flush()
        time.sleep(0.3)

        result = self.db.get_proxy_by_endpoint(
            "127.0.0.1", 8080, "http"
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.host, "127.0.0.1")

    def test_insert_source(self):
        source = Source(
            name="TestSource",
            url="http://example.com",
            protocol="http"
        )
        self.db.insert_source(source)
        self.db._writer.flush()
        time.sleep(0.3)

        sources = self.db.get_all_sources()
        self.assertTrue(
            any(s.name == "TestSource" for s in sources)
        )

    def test_stats(self):
        stats = self.db.get_stats()
        self.assertIn("total", stats)
        self.assertIn("alive", stats)


if __name__ == "__main__":
    unittest.main()
