import sqlite3
import unittest
from datetime import datetime, timedelta, timezone

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
        self.service.decide("O2", approve=True)  # -> PRODUCTION (재고 20 < 100, 부족분 80, 수율 0.95 -> 실생산량 85)
        self.assertEqual(self.order_repo.get("O2").production_quantity, 85)
        self.service.complete_production("O2")
        self.assertEqual(self.order_repo.get("O2").status, "CONFIRMED")
        self.assertEqual(self.sample_repo.get("S1").stock, 105)  # 20 + 85(production_quantity), not order.quantity(100)

    def test_complete_production_without_production_status_raises(self):
        with self.assertRaises(ValueError):
            self.service.complete_production("O1")  # 아직 RECEIVED

    def test_confirmed_then_ship_deducts_stock(self):
        self.service.decide("O1", approve=True)  # -> CONFIRMED (재고 20 >= 10)
        self.service.ship("O1")
        self.assertEqual(self.order_repo.get("O1").status, "RELEASE")
        self.assertEqual(self.sample_repo.get("S1").stock, 10)

    def test_ship_without_confirmation_raises(self):
        with self.assertRaises(ValueError):
            self.service.ship("O1")  # 아직 RECEIVED


class OrderServiceProductionLineTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()
        self.sample_repo = SampleRepository(self.conn)
        self.order_repo = OrderRepository(self.conn)
        self.service = OrderService(self.order_repo, self.sample_repo)
        # avg_production_time=2.0, yield_rate=1.0 -> production_quantity == shortage, total_minutes == shortage * 2
        self.sample_repo.create(Sample("S1", "Wafer-A", 2.0, 1.0, 0))

    def test_decide_immediately_starts_production_when_line_idle(self):
        order_id = self.service.receive_order("S1", "ACME", 10)
        self.service.decide(order_id, approve=True)  # -> PRODUCTION, production_quantity=10, total=20min
        order = self.order_repo.get(order_id)
        self.assertIsNotNone(order.production_started_at)

    def test_advance_does_not_complete_before_elapsed_time(self):
        order_id = self.service.receive_order("S1", "ACME", 10)
        self.service.decide(order_id, approve=True)
        self.service.advance_production_line()
        self.assertEqual(self.order_repo.get(order_id).status, "PRODUCTION")

    def test_advance_completes_after_elapsed_time(self):
        order_id = self.service.receive_order("S1", "ACME", 10)
        self.service.decide(order_id, approve=True)  # production_quantity=10, total=20min
        started = datetime.now(timezone.utc) - timedelta(minutes=21)
        self.order_repo.set_production_started_at(order_id, started.isoformat())
        self.service.advance_production_line()
        order = self.order_repo.get(order_id)
        self.assertEqual(order.status, "CONFIRMED")
        self.assertEqual(self.sample_repo.get("S1").stock, 10)

    def test_advance_starts_next_waiting_order_after_current_completes(self):
        order_a = self.service.receive_order("S1", "ACME", 10)
        self.service.decide(order_a, approve=True)  # starts immediately (line idle)
        order_b = self.service.receive_order("S1", "ACME", 5)
        self.service.decide(order_b, approve=True)  # waits (line busy with A)
        self.assertIsNone(self.order_repo.get(order_b).production_started_at)

        started = datetime.now(timezone.utc) - timedelta(minutes=21)
        self.order_repo.set_production_started_at(order_a, started.isoformat())
        self.service.advance_production_line()

        self.assertEqual(self.order_repo.get(order_a).status, "CONFIRMED")
        self.assertIsNotNone(self.order_repo.get(order_b).production_started_at)
        self.assertEqual(self.order_repo.get(order_b).status, "PRODUCTION")

    def test_waiting_queue_orders_by_decision_time_not_receipt_time(self):
        # OA received first (earliest created_at) but decided last
        self.order_repo.create(Order("OA", "S1", "ACME", 10, "RECEIVED", "2020-01-01T00:00:00"))
        # OC received in the middle
        self.order_repo.create(Order("OC", "S1", "ACME", 10, "RECEIVED", "2020-06-01T00:00:00"))
        # OB received last (latest created_at) but decided first
        self.order_repo.create(Order("OB", "S1", "ACME", 10, "RECEIVED", "2020-12-01T00:00:00"))

        self.service.decide("OB", approve=True)  # line idle -> becomes current immediately
        self.service.decide("OC", approve=True)  # queued 2nd
        self.service.decide("OA", approve=True)  # queued 3rd, despite earliest created_at

        started = datetime.now(timezone.utc) - timedelta(minutes=21)
        self.order_repo.set_production_started_at("OB", started.isoformat())
        self.service.advance_production_line()  # OB completes, next in FIFO (by decision time) should start

        self.assertEqual(self.order_repo.get("OB").status, "CONFIRMED")
        self.assertIsNotNone(self.order_repo.get("OC").production_started_at)
        self.assertIsNone(self.order_repo.get("OA").production_started_at)

    def test_advance_backfills_legacy_order_missing_production_quantity(self):
        self.order_repo.create(Order("O-LEGACY", "S1", "ACME", 15, "PRODUCTION", "2026-01-01T00:00:00"))
        self.service.advance_production_line()
        order = self.order_repo.get("O-LEGACY")
        self.assertEqual(order.production_quantity, 15)  # shortage=15-0=15, yield=1.0 -> 15
        self.assertIsNotNone(order.production_started_at)


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
