from datetime import datetime, timezone

from app.models import Order, Sample
from app.repository import OrderRepository, SampleRepository
from app.services import OrderService


def print_menu() -> None:
    print("\n===== S-Semi 시료 주문관리 =====")
    print("[1] 시료 등록  [2] 시료 조회  [3] 주문 접수  [4] 주문 승인")
    print("[5] 주문 거절  [6] 생산 시작  [7] 출고  [8] 주문 목록  [0] 종료")


def register_sample(sample_repo: SampleRepository) -> None:
    sample_id = input("시료 ID > ").strip()
    name = input("이름 > ").strip()
    avg_time = float(input("평균 생산시간(min/ea) > ").strip())
    yield_rate = float(input("수율(0~1) > ").strip())
    stock = int(input("초기 재고 > ").strip())
    sample_repo.create(Sample(sample_id, name, avg_time, yield_rate, stock))
    print("등록 완료.")


def list_samples(sample_repo: SampleRepository) -> None:
    samples = sample_repo.list_all()
    if not samples:
        print("등록된 시료가 없습니다.")
        return
    print(f"{'ID':<8}{'이름':<20}{'수율':<8}{'재고':<8}")
    for s in samples:
        print(f"{s.sample_id:<8}{s.name:<20}{s.yield_rate:<8}{s.stock:<8}")


def receive_order(order_repo: OrderRepository) -> None:
    order_id = input("주문 ID > ").strip()
    sample_id = input("시료 ID > ").strip()
    customer_name = input("고객명 > ").strip()
    quantity = int(input("수량 > ").strip())
    order_repo.create(
        Order(
            order_id=order_id,
            sample_id=sample_id,
            customer_name=customer_name,
            quantity=quantity,
            status="RECEIVED",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
    )
    print("주문 접수 완료.")


def approve_order(service: OrderService) -> None:
    order_id = input("승인할 주문 ID > ").strip()
    service.approve(order_id)
    print("승인 완료.")


def reject_order(service: OrderService) -> None:
    order_id = input("거절할 주문 ID > ").strip()
    service.reject(order_id)
    print("거절 완료.")


def start_production(service: OrderService) -> None:
    order_id = input("생산 시작할 주문 ID > ").strip()
    service.start_production(order_id)
    print("생산 시작 처리 완료.")


def ship_order(service: OrderService) -> None:
    order_id = input("출고할 주문 ID > ").strip()
    service.ship(order_id)
    print("출고 완료.")


def list_orders(order_repo: OrderRepository) -> None:
    status = input("상태 필터(엔터=전체) > ").strip() or None
    orders = order_repo.list_all(status)
    if not orders:
        print("조회된 주문이 없습니다.")
        return
    print(f"{'ID':<8}{'시료ID':<8}{'고객':<12}{'수량':<6}{'상태':<14}")
    for o in orders:
        print(f"{o.order_id:<8}{o.sample_id:<8}{o.customer_name:<12}{o.quantity:<6}{o.status:<14}")


def run(sample_repo: SampleRepository, order_repo: OrderRepository, service: OrderService) -> None:
    actions = {
        "1": lambda: register_sample(sample_repo),
        "2": lambda: list_samples(sample_repo),
        "3": lambda: receive_order(order_repo),
        "4": lambda: approve_order(service),
        "5": lambda: reject_order(service),
        "6": lambda: start_production(service),
        "7": lambda: ship_order(service),
        "8": lambda: list_orders(order_repo),
    }
    while True:
        print_menu()
        choice = input("선택 > ").strip()
        if choice == "0":
            print("종료합니다.")
            break
        action = actions.get(choice)
        if action is None:
            print("[오류] 올바른 메뉴를 선택하세요.")
            continue
        try:
            action()
        except (ValueError, KeyError) as exc:
            print(f"[오류] {exc}")
