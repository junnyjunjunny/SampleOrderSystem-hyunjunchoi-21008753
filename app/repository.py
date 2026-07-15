import sqlite3

from app.models import Order, Sample


class SampleRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(self, sample: Sample) -> None:
        try:
            self.conn.execute(
                """
                INSERT INTO samples (sample_id, name, avg_production_time, yield_rate, stock)
                VALUES (?, ?, ?, ?, ?)
                """,
                (sample.sample_id, sample.name, sample.avg_production_time, sample.yield_rate, sample.stock),
            )
            self.conn.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Sample already exists: {sample.sample_id}") from exc

    def get(self, sample_id: str) -> Sample:
        row = self.conn.execute(
            "SELECT * FROM samples WHERE sample_id = ?", (sample_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"Sample not found: {sample_id}")
        return Sample.from_row(row)

    def list_all(self):
        rows = self.conn.execute("SELECT * FROM samples ORDER BY sample_id").fetchall()
        return [Sample.from_row(row) for row in rows]

    def update_stock(self, sample_id: str, stock: int) -> None:
        cursor = self.conn.execute(
            "UPDATE samples SET stock = ? WHERE sample_id = ?", (stock, sample_id)
        )
        self.conn.commit()
        if cursor.rowcount == 0:
            raise KeyError(f"Sample not found: {sample_id}")


class OrderRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(self, order: Order) -> None:
        try:
            self.conn.execute(
                """
                INSERT INTO orders (order_id, sample_id, customer_name, quantity, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (order.order_id, order.sample_id, order.customer_name, order.quantity, order.status, order.created_at),
            )
            self.conn.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Order already exists: {order.order_id}") from exc

    def get(self, order_id: str) -> Order:
        row = self.conn.execute(
            "SELECT * FROM orders WHERE order_id = ?", (order_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"Order not found: {order_id}")
        return Order.from_row(row)

    def list_all(self, status: str | None = None):
        if status is None:
            rows = self.conn.execute("SELECT * FROM orders ORDER BY created_at").fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM orders WHERE status = ? ORDER BY created_at", (status,)
            ).fetchall()
        return [Order.from_row(row) for row in rows]

    def update_status(self, order_id: str, status: str) -> None:
        cursor = self.conn.execute(
            "UPDATE orders SET status = ? WHERE order_id = ?", (status, order_id)
        )
        self.conn.commit()
        if cursor.rowcount == 0:
            raise KeyError(f"Order not found: {order_id}")
