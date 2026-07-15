import sqlite3
import unittest

from app.db import SCHEMA
from app.models import Order, Sample
from app.repository import OrderRepository, SampleRepository
from app.services import OrderService


def make_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


class OrderServiceTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()
        self.sample_repo = SampleRepository(self.conn)
        self.order_repo = OrderRepository(self.conn)
        self.service = OrderService(self.order_repo, self.sample_repo)
        self.sample_repo.create(Sample("S1", "Wafer-A", 10.0, 0.95, 20))
        self.order_repo.create(Order("O1", "S1", "ACME", 10, "RECEIVED", "2026-01-01T00:00:00"))

    def test_approve_then_ship_deducts_stock(self):
        self.service.approve("O1")
        self.service.start_production("O1")
        self.service.ship("O1")
        self.assertEqual(self.order_repo.get("O1").status, "SHIPPED")
        self.assertEqual(self.sample_repo.get("S1").stock, 10)

    def test_approve_with_insufficient_stock_raises(self):
        self.order_repo.create(Order("O2", "S1", "ACME", 100, "RECEIVED", "2026-01-01T00:00:00"))
        with self.assertRaises(ValueError):
            self.service.approve("O2")

    def test_reject_then_approve_raises(self):
        self.service.reject("O1")
        with self.assertRaises(ValueError):
            self.service.approve("O1")

    def test_ship_without_production_raises(self):
        self.service.approve("O1")
        with self.assertRaises(ValueError):
            self.service.ship("O1")


if __name__ == "__main__":
    unittest.main()
