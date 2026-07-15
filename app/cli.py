import math
import msvcrt
import os
import time
from datetime import datetime, timedelta, timezone

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


GREEN = "\033[92m"
ORANGE = "\033[38;5;208m"
RED = "\033[91m"
HEADER_BG = "\033[44m\033[97m"
RESET = "\033[0m"


def _visible_len(text) -> int:
    text = str(text)
    length = 0
    in_escape = False
    for ch in text:
        if ch == "\033":
            in_escape = True
            continue
        if in_escape:
            if ch == "m":
                in_escape = False
            continue
        length += 1
    return length


def _pad_cell(value, width: int) -> str:
    text = str(value)
    pad = max(0, width - _visible_len(text))
    return text + " " * pad


def print_table(headers, rows, widths) -> None:
    def border(left, mid, right):
        return left + mid.join("─" * (w + 2) for w in widths) + right

    def format_row(cells):
        return "│" + "│".join(f" {_pad_cell(c, w)} " for c, w in zip(cells, widths)) + "│"

    print(border("┌", "┬", "┐"))
    print(f"{HEADER_BG}{format_row(headers)}{RESET}")
    print(border("├", "┼", "┤"))
    for row in rows:
        print(format_row(row))
    print(border("└", "┴", "┘"))


def print_menu() -> None:
    print("\n===== S-Semi 시료 주문관리 =====")
    print("[1] 시료 관리  [2] 시료 주문  [3] 주문 승인/거절  [4] 모니터링")
    print("[5] 생산 라인 조회  [6] 출고 처리  [0] 종료")


def print_sample_table(samples) -> None:
    if not samples:
        print("등록된 시료가 없습니다.")
        return
    headers = ["ID", "이름", "수율", "재고", "생산시간(sec/ea)"]
    widths = [8, 20, 6, 6, 14]
    rows = [
        [s.sample_id, s.name, s.yield_rate, s.stock, f"{s.avg_production_time * 60:.2f}"]
        for s in samples
    ]
    print_table(headers, rows, widths)


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
    headers = ["번호", "주문번호", "고객", "시료", "수량", "상태"]
    widths = [4, 14, 12, 20, 6, 10]
    rows = []
    for i, o in enumerate(orders, start=1):
        try:
            sample_name = sample_repo.get(o.sample_id).name
        except KeyError:
            sample_name = "(삭제된 시료)"
        rows.append([i, o.order_id, o.customer_name, sample_name, o.quantity, o.status])
    print_table(headers, rows, widths)


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


def print_release_table(orders, sample_repo: SampleRepository) -> None:
    if not orders:
        print("출고 가능한 주문이 없습니다.")
        return
    headers = ["번호", "주문번호", "고객", "시료", "수량"]
    widths = [4, 14, 12, 20, 6]
    rows = []
    for i, o in enumerate(orders, start=1):
        try:
            sample_name = sample_repo.get(o.sample_id).name
        except KeyError:
            sample_name = "(삭제된 시료)"
        rows.append([i, o.order_id, o.customer_name, sample_name, o.quantity])
    print_table(headers, rows, widths)


def release_menu(sample_repo: SampleRepository, order_repo: OrderRepository, service: OrderService) -> None:
    page = 0
    while True:
        clear_screen()
        print("\n===== 출고 처리 =====")
        orders = order_repo.list_all("CONFIRMED")
        page_items, page, total_pages = paginate(orders, page)
        print_release_table(page_items, sample_repo)
        print(f"(페이지 {page + 1}/{total_pages})")
        choice = input("[N] 다음  [B] 이전  번호 입력(출고)  [0] 뒤로 > ").strip().upper()
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
            order = page_items[index - 1]
            service.ship(order.order_id)
            print(f"주문 {order.order_id} 출고 처리되었습니다.")
        except (ValueError, KeyError) as exc:
            print(f"[오류] {exc}")
        pause()


ORDER_VOLUME_STATUSES = ["RECEIVED", "CONFIRMED", "PRODUCTION", "RELEASE"]

STOCK_FULL_CAPACITY = 1000
STOCK_ABUNDANT_THRESHOLD = 60
STOCK_LOW_THRESHOLD = 20


def check_order_volume(order_repo: OrderRepository) -> None:
    orders = [o for o in order_repo.list_all() if o.status != "REJECTED"]
    print("상태별 주문 현황")
    counts = {status: 0 for status in ORDER_VOLUME_STATUSES}
    for o in orders:
        if o.status in counts:
            counts[o.status] += 1
    for status in ORDER_VOLUME_STATUSES:
        print(f"{status}: {counts[status]}건")
    print()
    if not orders:
        print("조회된 주문이 없습니다.")
        return
    headers = ["ID", "시료ID", "고객", "수량", "상태"]
    widths = [14, 8, 12, 6, 12]
    rows = [[o.order_id, o.sample_id, o.customer_name, o.quantity, o.status] for o in orders]
    print_table(headers, rows, widths)


def _stock_ratio_status(stock: int):
    ratio = stock / STOCK_FULL_CAPACITY * 100
    if ratio >= STOCK_ABUNDANT_THRESHOLD:
        return ratio, "여유", GREEN
    if ratio >= STOCK_LOW_THRESHOLD:
        return ratio, "부족", ORANGE
    return ratio, "고갈", RED


def check_stock_level(sample_repo: SampleRepository) -> None:
    samples = sample_repo.list_all()
    if not samples:
        print("등록된 시료가 없습니다.")
        return
    headers = ["시료명", "재고", "상태", "잔여율"]
    widths = [20, 8, 10, 8]
    rows = []
    for s in samples:
        ratio, label, color = _stock_ratio_status(s.stock)
        colored_label = f"{color}{label}{RESET}"
        rows.append([s.name, s.stock, colored_label, f"{ratio:.0f}%"])
    print_table(headers, rows, widths)


def monitoring_menu(sample_repo: SampleRepository, order_repo: OrderRepository) -> None:
    while True:
        clear_screen()
        print("\n===== 모니터링 =====")
        choice = input("[1] 주문량 확인  [2] 재고량 확인  [0] 뒤로 > ").strip()
        if choice == "0":
            return
        action = {
            "1": lambda: check_order_volume(order_repo),
            "2": lambda: check_stock_level(sample_repo),
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


def _format_local(iso_str: str) -> str:
    return datetime.fromisoformat(iso_str).astimezone().strftime("%Y-%m-%d %H:%M")


def _gauge(progress_pct: float, width: int = 20) -> str:
    filled = int(round(width * min(100, max(0, progress_pct)) / 100))
    return "[" + "#" * filled + "-" * (width - filled) + "]"


PRODUCTION_LINE_REFRESH_SECONDS = 0.3


def _render_production_line(sample_repo: SampleRepository, order_repo: OrderRepository, service: OrderService) -> None:
    clear_screen()
    service.advance_production_line()
    orders = order_repo.list_all("PRODUCTION")
    current = next((o for o in orders if o.production_started_at), None)
    waiting = sorted(
        (o for o in orders if not o.production_started_at),
        key=lambda o: (o.production_queue_seq is None, o.production_queue_seq or 0, o.created_at),
    )

    print("\n===== 생산 라인 조회 =====")
    print(f"생산라인 1 | 현재 상태: {'RUN' if current else 'STOP'}\n")

    print("현재 처리 중")
    expected_completion = None
    if current is None:
        print("  현재 처리 중인 주문이 없습니다.")
    else:
        try:
            sample = sample_repo.get(current.sample_id)
        except KeyError:
            sample = None
        sample_name = sample.name if sample else "(삭제된 시료)"
        production_quantity = current.production_quantity or 0
        shortage = round(production_quantity * sample.yield_rate) if sample else production_quantity
        total_minutes = production_quantity * sample.avg_production_time if sample else 0
        started = datetime.fromisoformat(current.production_started_at)
        elapsed_minutes = (datetime.now(timezone.utc) - started).total_seconds() / 60
        progress = min(100, elapsed_minutes / total_minutes * 100) if total_minutes > 0 else 100
        expected_completion = started + timedelta(minutes=total_minutes)
        avg_time_display = f"{sample.avg_production_time:.2f} min/ea" if sample else "-"
        print(f"  주문번호: {current.order_id}")
        print(f"  시료: {sample_name} (평균 생산시간 {avg_time_display})")
        print(f"  주문량: {current.quantity}   재고: {sample.stock if sample else '-'}   부족: {shortage}   실 생산량: {production_quantity}")
        print(f"  진행: {_gauge(progress)} {progress:.0f}%   완료 예정: {_format_local(expected_completion.isoformat())}")

    print("\n대기 중인 주문")
    if not waiting:
        print("  대기 중인 주문이 없습니다.")
    else:
        headers = ["순서", "주문번호", "시료", "주문량", "부족분", "실생산량", "예상 완료"]
        widths = [4, 14, 20, 6, 6, 8, 16]
        rows = []
        cumulative_start = expected_completion or datetime.now(timezone.utc)
        for i, o in enumerate(waiting, start=1):
            try:
                sample = sample_repo.get(o.sample_id)
                sample_name = sample.name
                avg_time = sample.avg_production_time
                yield_rate = sample.yield_rate
            except KeyError:
                sample_name = "(삭제된 시료)"
                avg_time = 0
                yield_rate = 1
            production_quantity = o.production_quantity or 0
            shortage = round(production_quantity * yield_rate)
            total_minutes = production_quantity * avg_time
            expected = cumulative_start + timedelta(minutes=total_minutes)
            rows.append([i, o.order_id, sample_name, o.quantity, shortage, production_quantity, _format_local(expected.isoformat())])
            cumulative_start = expected
        print_table(headers, rows, widths)

    print("\n[0] 뒤로  (실시간 자동 갱신 중...)")


def production_line_menu(sample_repo: SampleRepository, order_repo: OrderRepository, service: OrderService) -> None:
    while True:
        _render_production_line(sample_repo, order_repo, service)
        tick_start = time.monotonic()
        while time.monotonic() - tick_start < PRODUCTION_LINE_REFRESH_SECONDS:
            if msvcrt.kbhit() and msvcrt.getch() == b"0":
                return
            time.sleep(0.05)


def run(sample_repo: SampleRepository, order_repo: OrderRepository, service: OrderService) -> None:
    actions = {
        "1": lambda: sample_management_menu(sample_repo),
        "2": lambda: order_reception_menu(service),
        "3": lambda: order_approval_menu(sample_repo, order_repo, service),
        "4": lambda: monitoring_menu(sample_repo, order_repo),
        "5": lambda: production_line_menu(sample_repo, order_repo, service),
        "6": lambda: release_menu(sample_repo, order_repo, service),
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
        if choice not in ("1", "2", "3", "4", "5", "6"):
            pause()
