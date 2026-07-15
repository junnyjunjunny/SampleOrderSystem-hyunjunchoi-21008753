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

    def test_decide_approve_with_sufficient_stock_confirms(self):
        status = self.service.decide("O1", approve=True)
        self.assertEqual(status, "CONFIRMED")
        self.assertEqual(self.order_repo.get("O1").status, "CONFIRMED")

    def test_decide_approve_with_insufficient_stock_moves_to_production(self):
        self.order_repo.create(Order("O2", "S1", "ACME", 100, "RECEIVED", "2026-01-01T00:00:00"))
        status = self.service.decide("O2", approve=True)
        self.assertEqual(status, "PRODUCTION")
        self.assertEqual(self.order_repo.get("O2").status, "PRODUCTION")

    def test_decide_reject_moves_to_rejected(self):
        status = self.service.decide("O1", approve=False)
        self.assertEqual(status, "REJECTED")
        self.assertEqual(self.order_repo.get("O1").status, "REJECTED")

    def test_decide_missing_order_raises(self):
        with self.assertRaises(KeyError):
            self.service.decide("NOPE", approve=True)

    def test_decide_on_production_order_raises(self):
        self.order_repo.create(Order("O2", "S1", "ACME", 100, "RECEIVED", "2026-01-01T00:00:00"))
        self.service.decide("O2", approve=True)  # -> PRODUCTION (재고 20 < 100)
        self.sample_repo.update_stock("S1", 200)  # 재고가 나중에 충분해지더라도
        with self.assertRaises(ValueError):
            self.service.decide("O2", approve=True)  # decide()로 다시 결정할 수 없음 (complete_production만 가능)

    def test_decide_already_decided_raises(self):
        self.service.decide("O1", approve=False)
        with self.assertRaises(ValueError):
            self.service.decide("O1", approve=True)

    def test_complete_production_confirms_and_restocks(self):
        self.order_repo.create(Order("O2", "S1", "ACME", 100, "RECEIVED", "2026-01-01T00:00:00"))
        self.service.decide("O2", approve=True)  # -> PRODUCTION (재고 20 < 100)
        self.service.complete_production("O2")
        self.assertEqual(self.order_repo.get("O2").status, "CONFIRMED")
        self.assertEqual(self.sample_repo.get("S1").stock, 120)

    def test_complete_production_without_production_status_raises(self):
        with self.assertRaises(ValueError):
            self.service.complete_production("O1")  # 아직 RECEIVED

    def test_confirmed_then_ship_deducts_stock(self):
        self.service.decide("O1", approve=True)  # -> CONFIRMED (재고 20 >= 10)
        self.service.ship("O1")
        self.assertEqual(self.order_repo.get("O1").status, "SHIPPED")
        self.assertEqual(self.sample_repo.get("S1").stock, 10)

    def test_ship_without_confirmation_raises(self):
        with self.assertRaises(ValueError):
            self.service.ship("O1")  # 아직 RECEIVED


class OrderServiceReceiveOrderTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()
        self.sample_repo = SampleRepository(self.conn)
        self.order_repo = OrderRepository(self.conn)
        self.service = OrderService(self.order_repo, self.sample_repo)
        self.sample_repo.create(Sample("S1", "Wafer-A", 10.0, 0.95, 20))

    def test_receive_order_generates_order_id_and_status_received(self):
        order_id = self.service.receive_order("S1", "ACME", 5)
        order = self.order_repo.get(order_id)
        self.assertEqual(order.status, "RECEIVED")
        self.assertEqual(order.sample_id, "S1")
        self.assertEqual(order.quantity, 5)

    def test_receive_order_with_missing_sample_raises(self):
        with self.assertRaises(KeyError):
            self.service.receive_order("NOPE", "ACME", 5)

    def test_receive_order_with_zero_quantity_raises(self):
        with self.assertRaises(ValueError):
            self.service.receive_order("S1", "ACME", 0)


if __name__ == "__main__":
    unittest.main()
