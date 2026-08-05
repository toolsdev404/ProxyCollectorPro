"""Proxy Collector Pro - Export Tests"""

import unittest
import tempfile
import os
from core.database import Database
from core.models import Proxy, ExportConfig
from utils.exporter import ExportEngine


class TestExport(unittest.TestCase):
    def setUp(self):
        self.db_file = tempfile.mktemp(suffix=".db")
        self.db = Database(self.db_file)
        self.exporter = ExportEngine(self.db)

        # Insert test proxies
        for i in range(5):
            p = Proxy(
                host=f"192.168.1.{i}", port=8080,
                protocol="http", status="alive", score=50
            )
            self.db.insert_proxy(p)
        self.db._writer.flush()
        import time
        time.sleep(0.3)

    def tearDown(self):
        self.db.close()
        for ext in ["", "-wal", "-shm"]:
            f = self.db_file + ext
            if os.path.exists(f):
                os.remove(f)

    def test_txt_export(self):
        config = ExportConfig(
            format="txt",
            scheme="with_scheme",
            grouping="separate",
            output_path=tempfile.gettempdir()
        )
        result = self.exporter.export(config)
        self.assertTrue(result["success"])
        self.assertGreater(len(result["files"]), 0)


if __name__ == "__main__":
    unittest.main()
