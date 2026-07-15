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


class SampleModelTest(unittest.TestCase):
    def test_negative_or_zero_production_time_raises(self):
        with self.assertRaises(ValueError):
            Sample("S1", "Wafer-A", 0, 0.95, 100)

    def test_yield_rate_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            Sample("S1", "Wafer-A", 10.0, 1.5, 100)

    def test_negative_stock_raises(self):
        with self.assertRaises(ValueError):
            Sample("S1", "Wafer-A", 10.0, 0.95, -1)

    def test_yield_rate_boundary_values_are_valid(self):
        Sample("S1", "Wafer-A", 10.0, 0.0, 100)
        Sample("S2", "Wafer-B", 10.0, 1.0, 100)

    def test_stock_zero_is_valid(self):
        Sample("S1", "Wafer-A", 10.0, 0.95, 0)


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

    def test_search_by_name_case_insensitive_partial_match(self):
        self.repo.create(Sample("S1", "Wafer-A", 10.0, 0.95, 100))
        self.repo.create(Sample("S2", "Chip-B", 5.0, 0.9, 10))
        results = self.repo.search("name", "wafer")
        self.assertEqual([s.sample_id for s in results], ["S1"])

    def test_search_by_id_case_insensitive_partial_match(self):
        self.repo.create(Sample("Wafer-1", "A", 10.0, 0.95, 100))
        self.repo.create(Sample("Chip-2", "B", 5.0, 0.9, 10))
        results = self.repo.search("id", "wafer")
        self.assertEqual([s.sample_id for s in results], ["Wafer-1"])

    def test_search_with_no_match_returns_empty_list(self):
        self.repo.create(Sample("S1", "Wafer-A", 10.0, 0.95, 100))
        self.assertEqual(self.repo.search("name", "nope"), [])

    def test_search_invalid_field_raises_key_error(self):
        with self.assertRaises(KeyError):
            self.repo.search("bogus", "wafer")

    def test_search_empty_query_returns_all(self):
        self.repo.create(Sample("S1", "Wafer-A", 10.0, 0.95, 100))
        self.repo.create(Sample("S2", "Chip-B", 5.0, 0.9, 10))
        results = self.repo.search("name", "")
        self.assertEqual([s.sample_id for s in results], ["S1", "S2"])

    def test_search_escapes_like_wildcards(self):
        self.repo.create(Sample("S1", "100%_ok", 10.0, 0.95, 100))
        self.repo.create(Sample("S2", "100Xok", 5.0, 0.9, 10))
        results = self.repo.search("name", "%_")
        self.assertEqual([s.sample_id for s in results], ["S1"])

    def test_update_modifies_fields_except_id(self):
        self.repo.create(Sample("S1", "Wafer-A", 10.0, 0.95, 100))
        self.repo.update(Sample("S1", "Wafer-A2", 20.0, 0.5, 30))
        updated = self.repo.get("S1")
        self.assertEqual(updated.name, "Wafer-A2")
        self.assertEqual(updated.avg_production_time, 20.0)
        self.assertEqual(updated.yield_rate, 0.5)
        self.assertEqual(updated.stock, 30)

    def test_update_missing_raises_key_error(self):
        with self.assertRaises(KeyError):
            self.repo.update(Sample("NOPE", "X", 1.0, 0.5, 1))

    def test_delete_removes_sample(self):
        self.repo.create(Sample("S1", "Wafer-A", 10.0, 0.95, 100))
        self.repo.delete("S1")
        with self.assertRaises(KeyError):
            self.repo.get("S1")

    def test_delete_missing_raises_key_error(self):
        with self.assertRaises(KeyError):
            self.repo.delete("NOPE")


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

    def test_next_order_id_starts_at_001_for_new_date(self):
        self.assertEqual(self.order_repo.next_order_id("20260715"), "O-20260715-001")

    def test_next_order_id_increments_for_same_date(self):
        self.order_repo.create(Order("O-20260715-001", "S1", "ACME", 1, "RECEIVED", "2026-07-15T00:00:00"))
        self.assertEqual(self.order_repo.next_order_id("20260715"), "O-20260715-002")

    def test_next_order_id_is_independent_per_date(self):
        self.order_repo.create(Order("O-20260715-001", "S1", "ACME", 1, "RECEIVED", "2026-07-15T00:00:00"))
        self.assertEqual(self.order_repo.next_order_id("20260716"), "O-20260716-001")


if __name__ == "__main__":
    unittest.main()
