import sqlite3

from app.models import Order, Sample


def _escape_like(query: str) -> str:
    return query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


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

    def update(self, sample: Sample) -> None:
        cursor = self.conn.execute(
            """
            UPDATE samples
            SET name = ?, avg_production_time = ?, yield_rate = ?, stock = ?
            WHERE sample_id = ?
            """,
            (sample.name, sample.avg_production_time, sample.yield_rate, sample.stock, sample.sample_id),
        )
        self.conn.commit()
        if cursor.rowcount == 0:
            raise KeyError(f"Sample not found: {sample.sample_id}")

    def delete(self, sample_id: str) -> None:
        cursor = self.conn.execute("DELETE FROM samples WHERE sample_id = ?", (sample_id,))
        self.conn.commit()
        if cursor.rowcount == 0:
            raise KeyError(f"Sample not found: {sample_id}")

    def search(self, field: str, query: str):
        try:
            column = {"id": "sample_id", "name": "name"}[field]
        except KeyError as exc:
            raise KeyError(f"Invalid search field: {field}") from exc
        rows = self.conn.execute(
            f"SELECT * FROM samples WHERE {column} LIKE ? ESCAPE '\\' COLLATE NOCASE ORDER BY sample_id",
            (f"%{_escape_like(query)}%",),
        ).fetchall()
        return [Sample.from_row(row) for row in rows]


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

    def next_order_id(self, date_str: str) -> str:
        prefix = f"O-{date_str}-"
        row = self.conn.execute(
            "SELECT order_id FROM orders WHERE order_id LIKE ? ORDER BY order_id DESC LIMIT 1",
            (f"{prefix}%",),
        ).fetchone()
        seq = int(row["order_id"].rsplit("-", 1)[1]) + 1 if row else 1
        return f"{prefix}{seq:03d}"

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

    def set_production_quantity(self, order_id: str, production_quantity: int) -> None:
        cursor = self.conn.execute(
            "UPDATE orders SET production_quantity = ? WHERE order_id = ?", (production_quantity, order_id)
        )
        self.conn.commit()
        if cursor.rowcount == 0:
            raise KeyError(f"Order not found: {order_id}")

    def set_production_started_at(self, order_id: str, started_at: str) -> None:
        cursor = self.conn.execute(
            "UPDATE orders SET production_started_at = ? WHERE order_id = ?", (started_at, order_id)
        )
        self.conn.commit()
        if cursor.rowcount == 0:
            raise KeyError(f"Order not found: {order_id}")

    def next_production_queue_seq(self) -> int:
        row = self.conn.execute("SELECT MAX(production_queue_seq) AS max_seq FROM orders").fetchone()
        return (row["max_seq"] or 0) + 1

    def set_production_queue_seq(self, order_id: str, seq: int) -> None:
        cursor = self.conn.execute(
            "UPDATE orders SET production_queue_seq = ? WHERE order_id = ?", (seq, order_id)
        )
        self.conn.commit()
        if cursor.rowcount == 0:
            raise KeyError(f"Order not found: {order_id}")
