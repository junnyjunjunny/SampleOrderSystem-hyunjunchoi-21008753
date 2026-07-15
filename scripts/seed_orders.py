import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import get_connection
from app.repository import OrderRepository, SampleRepository
from app.services import OrderService

ORDERS = [
    ("S-001", "ACME Corp", 20),
    ("S-005", "Global Semi", 10),
    ("S-010", "Nova Materials", 15),
    ("S-015", "Wafer Tech", 25),
    ("S-020", "MaskWorks", 5),
]


def seed() -> None:
    conn = get_connection()
    sample_repo = SampleRepository(conn)
    order_repo = OrderRepository(conn)
    service = OrderService(order_repo, sample_repo)

    created = []
    try:
        for sample_id, customer_name, quantity in ORDERS:
            order_id = service.receive_order(sample_id, customer_name, quantity)
            created.append(order_id)
    except KeyError as exc:
        print(f"[오류] {exc} — 먼저 `py scripts/seed_samples.py`로 시료를 시딩하세요.")
        return
    finally:
        conn.close()
    print(f"시딩 완료: 주문 {len(created)}건 접수 -> {', '.join(created)}")


if __name__ == "__main__":
    seed()
