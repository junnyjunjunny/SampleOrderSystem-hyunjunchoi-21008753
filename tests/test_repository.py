import sqlite3
import unittest

from app.db import SCHEMA
from app.models import Order, Sample
from app.repository import OrderRepository, SampleRepository


def make_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


class SampleRepositoryTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()
        self.repo = SampleRepository(self.conn)

    def test_create_and_get(self):
        self.repo.create(Sample("S1", "Wafer-A", 10.0, 0.95, 100))
        sample = self.repo.get("S1")
        self.assertEqual(sample.name, "Wafer-A")
        self.assertEqual(sample.stock, 100)

    def test_create_duplicate_raises(self):
        self.repo.create(Sample("S1", "Wafer-A", 10.0, 0.95, 100))
        with self.assertRaises(ValueError):
            self.repo.create(Sample("S1", "Wafer-B", 5.0, 0.9, 10))

    def test_get_missing_raises(self):
        with self.assertRaises(KeyError):
            self.repo.get("NOPE")

    def test_update_stock(self):
        self.repo.create(Sample("S1", "Wafer-A", 10.0, 0.95, 100))
        self.repo.update_stock("S1", 50)
        self.assertEqual(self.repo.get("S1").stock, 50)


class OrderRepositoryTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()
        self.sample_repo = SampleRepository(self.conn)
        self.order_repo = OrderRepository(self.conn)
        self.sample_repo.create(Sample("S1", "Wafer-A", 10.0, 0.95, 100))

    def test_create_and_get(self):
        self.order_repo.create(Order("O1", "S1", "ACME", 10, "RECEIVED", "2026-01-01T00:00:00"))
        order = self.order_repo.get("O1")
        self.assertEqual(order.status, "RECEIVED")

    def test_list_all_filters_by_status(self):
        self.order_repo.create(Order("O1", "S1", "ACME", 10, "RECEIVED", "2026-01-01T00:00:00"))
        self.order_repo.create(Order("O2", "S1", "ACME", 5, "APPROVED", "2026-01-02T00:00:00"))
        received = self.order_repo.list_all("RECEIVED")
        self.assertEqual([o.order_id for o in received], ["O1"])

    def test_update_status(self):
        self.order_repo.create(Order("O1", "S1", "ACME", 10, "RECEIVED", "2026-01-01T00:00:00"))
        self.order_repo.update_status("O1", "APPROVED")
        self.assertEqual(self.order_repo.get("O1").status, "APPROVED")


if __name__ == "__main__":
    unittest.main()
