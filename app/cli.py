import math
import os
from datetime import datetime, timezone

from app.models import Order, Sample
from app.repository import OrderRepository, SampleRepository
from app.services import OrderService


def clear_screen() -> None:
    os.system("cls")


def pause() -> None:
    input("\n계속하려면 Enter > ")


def paginate(items, page: int, page_size: int = 5):
    total_pages = max(1, math.ceil(len(items) / page_size))
    page = max(0, min(page, total_pages - 1))
    start = page * page_size
    return items[start : start + page_size], page, total_pages


def print_menu() -> None:
    print("\n===== S-Semi 시료 주문관리 =====")
    print("[1] 시료 관리  [2] 주문 접수  [3] 주문 승인  [4] 주문 거절")
    print("[5] 생산 시작  [6] 출고  [7] 주문 목록  [0] 종료")


def print_sample_table(samples) -> None:
    if not samples:
        print("등록된 시료가 없습니다.")
        return
    print(f"{'ID':<8}{'이름':<20}{'수율':<8}{'재고':<8}")
    for s in samples:
        print(f"{s.sample_id:<8}{s.name:<20}{s.yield_rate:<8}{s.stock:<8}")


def register_sample(sample_repo: SampleRepository) -> None:
    sample_id = input("시료 ID > ").strip()
    name = input("이름 > ").strip()
    avg_time = float(input("평균 생산시간(min/ea) > ").strip())
    yield_rate = float(input("수율(0~1) > ").strip())
    stock = int(input("초기 재고 > ").strip())
    sample_repo.create(Sample(sample_id, name, avg_time, yield_rate, stock))
    print("등록 완료.")


def search_samples(sample_repo: SampleRepository) -> None:
    field = input("검색 기준 (id/name) > ").strip().lower()
    query = input("검색어 > ").strip()
    results = sample_repo.search(field, query)
    print_sample_table(results)


def edit_or_delete_sample(sample_repo: SampleRepository) -> None:
    sample_id = input("수정/삭제할 시료 ID > ").strip()
    sample = sample_repo.get(sample_id)
    print(f"현재 값: 이름={sample.name}, 생산시간={sample.avg_production_time}, "
          f"수율={sample.yield_rate}, 재고={sample.stock}")
    action = input("[1] 수정  [2] 삭제 > ").strip()
    if action == "1":
        name = input(f"이름(엔터=유지: {sample.name}) > ").strip() or sample.name
        avg_time_raw = input(f"평균 생산시간(엔터=유지: {sample.avg_production_time}) > ").strip()
        avg_time = float(avg_time_raw) if avg_time_raw else sample.avg_production_time
        yield_rate_raw = input(f"수율(엔터=유지: {sample.yield_rate}) > ").strip()
        yield_rate = float(yield_rate_raw) if yield_rate_raw else sample.yield_rate
        stock_raw = input(f"재고(엔터=유지: {sample.stock}) > ").strip()
        stock = int(stock_raw) if stock_raw else sample.stock
        sample_repo.update(Sample(sample_id, name, avg_time, yield_rate, stock))
        print("수정 완료.")
    elif action == "2":
        sample_repo.delete(sample_id)
        print("삭제 완료.")
    else:
        raise ValueError(f"잘못된 항목: {action}")


def sample_management_menu(sample_repo: SampleRepository) -> None:
    page = 0
    while True:
        clear_screen()
        print("\n===== 시료 관리 =====")
        samples = sample_repo.list_all()
        page_items, page, total_pages = paginate(samples, page)
        print_sample_table(page_items)
        print(f"(페이지 {page + 1}/{total_pages})")
        choice = input("[N] 다음  [B] 이전  [1] 검색  [2] 등록  [3] 수정/삭제  [0] 뒤로 > ").strip().upper()
        if choice == "0":
            return
        if choice == "N":
            if page + 1 >= total_pages:
                print("마지막 페이지입니다.")
                pause()
            else:
                page += 1
            continue
        if choice == "B":
            if page == 0:
                print("첫 페이지입니다.")
                pause()
            else:
                page -= 1
            continue
        action = {
            "1": lambda: search_samples(sample_repo),
            "2": lambda: register_sample(sample_repo),
            "3": lambda: edit_or_delete_sample(sample_repo),
        }.get(choice)
        if action is None:
            print("[오류] 올바른 메뉴를 선택하세요.")
            pause()
            continue
        try:
            action()
        except (ValueError, KeyError) as exc:
            print(f"[오류] {exc}")
        pause()


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
        "1": lambda: sample_management_menu(sample_repo),
        "2": lambda: receive_order(order_repo),
        "3": lambda: approve_order(service),
        "4": lambda: reject_order(service),
        "5": lambda: start_production(service),
        "6": lambda: ship_order(service),
        "7": lambda: list_orders(order_repo),
    }
    while True:
        clear_screen()
        print_menu()
        choice = input("선택 > ").strip()
        if choice == "0":
            print("종료합니다.")
            break
        action = actions.get(choice)
        if action is None:
            print("[오류] 올바른 메뉴를 선택하세요.")
            pause()
            continue
        try:
            action()
        except (ValueError, KeyError) as exc:
            print(f"[오류] {exc}")
        if choice != "1":
            pause()
