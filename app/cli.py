import math
import os

from app.models import Sample
from app.repository import OrderRepository, SampleRepository
from app.services import OrderService


def clear_screen() -> None:
    os.system("cls")
    os.system("")  # enable ANSI escape processing on Windows consoles


def pause() -> None:
    input("\n계속하려면 Enter > ")


def paginate(items, page: int, page_size: int = 5):
    total_pages = max(1, math.ceil(len(items) / page_size))
    page = max(0, min(page, total_pages - 1))
    start = page * page_size
    return items[start : start + page_size], page, total_pages


def print_menu() -> None:
    print("\n===== S-Semi 시료 주문관리 =====")
    print("[1] 시료 관리  [2] 시료 주문  [3] 주문 승인/거절  [4] 생산 완료")
    print("[5] 출고  [6] 주문 목록  [0] 종료")


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


def receive_order(service: OrderService) -> None:
    sample_id = input("시료 ID > ").strip()
    customer_name = input("고객명 > ").strip()
    quantity = int(input("수량 > ").strip())
    order_id = service.receive_order(sample_id, customer_name, quantity)
    print(f"주문 접수가 완료되었습니다. 주문번호: {order_id}")


def order_reception_menu(service: OrderService) -> None:
    while True:
        clear_screen()
        print("\n===== 시료 주문 =====")
        choice = input("[1] 주문 접수  [0] 뒤로 > ").strip()
        if choice == "0":
            return
        if choice != "1":
            print("[오류] 올바른 메뉴를 선택하세요.")
            pause()
            continue
        try:
            receive_order(service)
        except (ValueError, KeyError) as exc:
            print(f"[오류] {exc}")
        pause()


def print_order_approval_table(orders, sample_repo: SampleRepository) -> None:
    if not orders:
        print("승인/거절 대기 중인 주문이 없습니다.")
        return
    print(f"{'번호':<4}{'주문번호':<14}{'고객':<12}{'시료':<20}{'수량':<6}{'상태':<10}")
    for i, o in enumerate(orders, start=1):
        try:
            sample_name = sample_repo.get(o.sample_id).name
        except KeyError:
            sample_name = "(삭제된 시료)"
        print(f"{i:<4}{o.order_id:<14}{o.customer_name:<12}{sample_name:<20}{o.quantity:<6}{o.status:<10}")


def decide_selected_order(sample_repo: SampleRepository, service: OrderService, order) -> bool:
    sample = sample_repo.get(order.sample_id)
    shortage = sample.stock - order.quantity
    shortage_display = f"\033[91m{shortage}\033[0m" if shortage < 0 else str(shortage)
    print(f"시료={sample.name}, 현재 재고={sample.stock}, 주문 수량={order.quantity}, 부족분={shortage_display}")
    decision = input("[Y] 승인  [N] 주문 거절  [0] 뒤로 > ").strip().upper()
    if decision == "Y":
        new_status = service.decide(order.order_id, approve=True)
        if new_status == "PRODUCTION":
            print("재고 부족: 생산 필요(PRODUCTION) 상태로 변경되었습니다.")
        else:
            print("승인 완료(CONFIRMED).")
    elif decision == "N":
        service.decide(order.order_id, approve=False)
        print("거절 완료(REJECTED).")
    elif decision == "0":
        return False
    else:
        raise ValueError(f"잘못된 항목: {decision}")
    return True


def order_approval_menu(sample_repo: SampleRepository, order_repo: OrderRepository, service: OrderService) -> None:
    page = 0
    while True:
        clear_screen()
        print("\n===== 주문 승인/거절 =====")
        orders = order_repo.list_all("RECEIVED")
        page_items, page, total_pages = paginate(orders, page)
        print_order_approval_table(page_items, sample_repo)
        print(f"(페이지 {page + 1}/{total_pages})")
        choice = input("[N] 다음  [B] 이전  번호 입력(승인/거절)  [0] 뒤로 > ").strip().upper()
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
        try:
            if not choice.isdigit():
                raise ValueError(f"잘못된 입력입니다: {choice}")
            index = int(choice)
            if not 1 <= index <= len(page_items):
                raise ValueError(f"올바른 번호를 입력하세요 (1~{len(page_items)})")
            decided = decide_selected_order(sample_repo, service, page_items[index - 1])
        except (ValueError, KeyError) as exc:
            print(f"[오류] {exc}")
            pause()
            continue
        if decided:
            pause()


def complete_production_order(service: OrderService) -> None:
    order_id = input("생산 완료 처리할 주문번호 > ").strip()
    service.complete_production(order_id)
    print("생산 완료 처리되었습니다.")


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
        "2": lambda: order_reception_menu(service),
        "3": lambda: order_approval_menu(sample_repo, order_repo, service),
        "4": lambda: complete_production_order(service),
        "5": lambda: ship_order(service),
        "6": lambda: list_orders(order_repo),
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
        if choice not in ("1", "2", "3"):
            pause()
