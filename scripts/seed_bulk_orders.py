import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import get_connection
from app.repository import OrderRepository, SampleRepository
from app.services import OrderService

CUSTOMERS = [
    "ACME Corp", "Global Semi", "Nova Materials", "Wafer Tech", "MaskWorks",
    "Orion Electronics", "Delta Chip", "Vertex Labs", "Quantum Foundry", "Apex Systems",
]

SAMPLE_IDS = [f"S-{i:03d}" for i in range(1, 24)]

COUNT = 100


def seed() -> None:
    conn = get_connection()
    sample_repo = SampleRepository(conn)
    order_repo = OrderRepository(conn)
    service = OrderService(order_repo, sample_repo)

    created = []
    try:
        for i in range(COUNT):
            sample_id = SAMPLE_IDS[i % len(SAMPLE_IDS)]
            customer_name = CUSTOMERS[i % len(CUSTOMERS)]
            quantity = 5 + (i * 7) % 120
            order_id = service.receive_order(sample_id, customer_name, quantity)
            created.append(order_id)
    except KeyError as exc:
        print(f"[오류] {exc} — 먼저 `py scripts/seed_samples.py`로 시료를 시딩하세요.")
        return
    finally:
        conn.close()
    print(f"시딩 완료: 주문 {len(created)}건 접수 (전부 RESERVED, [3] 주문 승인/거절에서 확인 가능)")
    print(f"주문번호 범위: {created[0]} ~ {created[-1]}")


if __name__ == "__main__":
    seed()
