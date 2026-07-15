import sqlite3
import unittest
from datetime import datetime, timedelta, timezone

from app.db import SCHEMA
from app.models import Order, Sample
from app.repository import OrderRepository, SampleRepository
from app.services import OrderService, stock_status


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
        self.order_repo.create(Order("O1", "S1", "ACME", 10, "RESERVED", "2026-01-01T00:00:00"))

    def test_decide_approve_with_sufficient_stock_confirms(self):
        status = self.service.decide("O1", approve=True)
        self.assertEqual(status, "CONFIRMED")
        self.assertEqual(self.order_repo.get("O1").status, "CONFIRMED")

    def test_decide_confirms_and_deducts_stock_immediately(self):
        self.service.decide("O1", approve=True)  # 재고 20 >= 주문 10 -> 즉시 CONFIRMED
        self.assertEqual(self.sample_repo.get("S1").stock, 10)  # 20 - 10, 출고 전에 이미 차감됨

    def test_decide_approve_with_insufficient_stock_moves_to_production(self):
        self.order_repo.create(Order("O2", "S1", "ACME", 100, "RESERVED", "2026-01-01T00:00:00"))
        status = self.service.decide("O2", approve=True)
        self.assertEqual(status, "PRODUCING")
        self.assertEqual(self.order_repo.get("O2").status, "PRODUCING")

    def test_decide_reject_moves_to_rejected(self):
        status = self.service.decide("O1", approve=False)
        self.assertEqual(status, "REJECTED")
        self.assertEqual(self.order_repo.get("O1").status, "REJECTED")

    def test_decide_missing_order_raises(self):
        with self.assertRaises(KeyError):
            self.service.decide("NOPE", approve=True)

    def test_decide_on_production_order_raises(self):
        self.order_repo.create(Order("O2", "S1", "ACME", 100, "RESERVED", "2026-01-01T00:00:00"))
        self.service.decide("O2", approve=True)  # -> PRODUCING (재고 20 < 100)
        self.sample_repo.update_stock("S1", 200)  # 재고가 나중에 충분해지더라도
        with self.assertRaises(ValueError):
            self.service.decide("O2", approve=True)  # decide()로 다시 결정할 수 없음 (complete_production만 가능)

    def test_decide_already_decided_raises(self):
        self.service.decide("O1", approve=False)
        with self.assertRaises(ValueError):
            self.service.decide("O1", approve=True)

    def test_complete_production_confirms_and_settles_stock(self):
        self.order_repo.create(Order("O2", "S1", "ACME", 100, "RESERVED", "2026-01-01T00:00:00"))
        self.service.decide("O2", approve=True)  # -> PRODUCING (재고 20 < 100, 부족분 80, 수율 0.95 -> 실생산량 85)
        self.assertEqual(self.order_repo.get("O2").production_quantity, 85)
        self.service.complete_production("O2")
        self.assertEqual(self.order_repo.get("O2").status, "CONFIRMED")
        # 20 + 85(production_quantity, 보충) - 100(quantity, 이 주문 소비분) = 5
        self.assertEqual(self.sample_repo.get("S1").stock, 5)

    def test_complete_production_without_production_status_raises(self):
        with self.assertRaises(ValueError):
            self.service.complete_production("O1")  # 아직 RESERVED

    def test_ship_does_not_change_stock(self):
        self.service.decide("O1", approve=True)  # -> CONFIRMED, 재고 20 -> 10로 이미 차감됨
        self.service.ship("O1")
        self.assertEqual(self.order_repo.get("O1").status, "RELEASE")
        self.assertEqual(self.sample_repo.get("S1").stock, 10)  # 출고는 재고를 건드리지 않음

    def test_ship_without_confirmation_raises(self):
        with self.assertRaises(ValueError):
            self.service.ship("O1")  # 아직 RESERVED


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
        self.service.decide(order_id, approve=True)  # -> PRODUCING, production_quantity=10, total=20min
        order = self.order_repo.get(order_id)
        self.assertIsNotNone(order.production_started_at)

    def test_advance_does_not_complete_before_elapsed_time(self):
        order_id = self.service.receive_order("S1", "ACME", 10)
        self.service.decide(order_id, approve=True)
        self.service.advance_production_line()
        self.assertEqual(self.order_repo.get(order_id).status, "PRODUCING")

    def test_advance_completes_after_elapsed_time(self):
        order_id = self.service.receive_order("S1", "ACME", 10)
        self.service.decide(order_id, approve=True)  # production_quantity=10, total=20min
        started = datetime.now(timezone.utc) - timedelta(minutes=21)
        self.order_repo.set_production_started_at(order_id, started.isoformat())
        self.service.advance_production_line()
        order = self.order_repo.get(order_id)
        self.assertEqual(order.status, "CONFIRMED")
        self.assertEqual(self.sample_repo.get("S1").stock, 0)  # 0 + 10(production_quantity) - 10(quantity) = 0

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
        self.assertEqual(self.order_repo.get(order_b).status, "PRODUCING")

    def test_waiting_queue_orders_by_decision_time_not_receipt_time(self):
        # OA received first (earliest created_at) but decided last
        self.order_repo.create(Order("OA", "S1", "ACME", 10, "RESERVED", "2020-01-01T00:00:00"))
        # OC received in the middle
        self.order_repo.create(Order("OC", "S1", "ACME", 10, "RESERVED", "2020-06-01T00:00:00"))
        # OB received last (latest created_at) but decided first
        self.order_repo.create(Order("OB", "S1", "ACME", 10, "RESERVED", "2020-12-01T00:00:00"))

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
        self.order_repo.create(Order("O-LEGACY", "S1", "ACME", 15, "PRODUCING", "2026-01-01T00:00:00"))
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
        self.assertEqual(order.status, "RESERVED")
        self.assertEqual(order.sample_id, "S1")
        self.assertEqual(order.quantity, 5)

    def test_receive_order_with_missing_sample_raises(self):
        with self.assertRaises(KeyError):
            self.service.receive_order("NOPE", "ACME", 5)

    def test_receive_order_with_zero_quantity_raises(self):
        with self.assertRaises(ValueError):
            self.service.receive_order("S1", "ACME", 0)


class StockStatusTest(unittest.TestCase):
    def test_stock_above_pending_quantity_is_abundant(self):
        self.assertEqual(stock_status(stock=100, pending_quantity=40), "여유")

    def test_stock_below_pending_quantity_is_low(self):
        self.assertEqual(stock_status(stock=30, pending_quantity=100), "부족")

    def test_zero_stock_is_depleted_even_without_pending_orders(self):
        self.assertEqual(stock_status(stock=0, pending_quantity=0), "고갈")

    def test_stock_with_no_pending_orders_is_abundant(self):
        self.assertEqual(stock_status(stock=5, pending_quantity=0), "여유")


class OrderServicePendingOrderQuantityTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()
        self.sample_repo = SampleRepository(self.conn)
        self.order_repo = OrderRepository(self.conn)
        self.service = OrderService(self.order_repo, self.sample_repo)
        self.sample_repo.create(Sample("S1", "Wafer-A", 10.0, 0.95, 20))
        self.sample_repo.create(Sample("S2", "Wafer-B", 10.0, 0.95, 20))

    def test_sums_reserved_and_producing_quantities_for_the_sample(self):
        self.order_repo.create(Order("O1", "S1", "ACME", 10, "RESERVED", "2026-01-01T00:00:00"))
        self.order_repo.create(Order("O2", "S1", "ACME", 5, "PRODUCING", "2026-01-01T00:00:00"))
        self.order_repo.create(Order("O3", "S1", "ACME", 999, "RELEASE", "2026-01-01T00:00:00"))
        self.order_repo.create(Order("O4", "S2", "ACME", 7, "RESERVED", "2026-01-01T00:00:00"))
        self.assertEqual(self.service.pending_order_quantity("S1"), 15)

    def test_no_pending_orders_returns_zero(self):
        self.assertEqual(self.service.pending_order_quantity("S1"), 0)


if __name__ == "__main__":
    unittest.main()
