import math
from datetime import datetime, timezone

from app.models import CONFIRMED, PRODUCTION, REJECTED, RECEIVED, RELEASE, Order
from app.repository import OrderRepository, SampleRepository

ALLOWED_TRANSITIONS = {
    RECEIVED: {CONFIRMED, PRODUCTION, REJECTED},
    PRODUCTION: {CONFIRMED},
    CONFIRMED: {RELEASE},
}


class OrderService:
    def __init__(self, order_repo: OrderRepository, sample_repo: SampleRepository):
        self.order_repo = order_repo
        self.sample_repo = sample_repo

    def _transition(self, order_id: str, new_status: str) -> None:
        order = self.order_repo.get(order_id)
        allowed = ALLOWED_TRANSITIONS.get(order.status, set())
        if new_status not in allowed:
            raise ValueError(f"Cannot move order {order_id} from {order.status} to {new_status}")
        self.order_repo.update_status(order_id, new_status)

    def receive_order(self, sample_id: str, customer_name: str, quantity: int) -> str:
        self.sample_repo.get(sample_id)
        order_id = self.order_repo.next_order_id(datetime.now().strftime("%Y%m%d"))
        order = Order(order_id, sample_id, customer_name, quantity, RECEIVED, datetime.now(timezone.utc).isoformat())
        self.order_repo.create(order)
        return order_id

    def decide(self, order_id: str, approve: bool) -> str:
        order = self.order_repo.get(order_id)
        if order.status != RECEIVED:
            raise ValueError(f"Cannot decide order {order_id} from status {order.status}")
        if not approve:
            self._transition(order_id, REJECTED)
            return REJECTED
        sample = self.sample_repo.get(order.sample_id)
        if sample.stock >= order.quantity:
            self._transition(order_id, CONFIRMED)
            self.sample_repo.update_stock(sample.sample_id, sample.stock - order.quantity)
            return CONFIRMED
        shortage = order.quantity - sample.stock
        production_quantity = math.ceil(shortage / sample.yield_rate)
        self.order_repo.set_production_quantity(order_id, production_quantity)
        self.order_repo.set_production_queue_seq(order_id, self.order_repo.next_production_queue_seq())
        self._transition(order_id, PRODUCTION)
        self.advance_production_line()
        return PRODUCTION

    def complete_production(self, order_id: str) -> None:
        order = self.order_repo.get(order_id)
        if order.status != PRODUCTION:
            raise ValueError(f"Cannot complete production for order {order_id} from status {order.status}")
        sample = self.sample_repo.get(order.sample_id)
        self._transition(order_id, CONFIRMED)
        self.sample_repo.update_stock(sample.sample_id, sample.stock + order.production_quantity - order.quantity)

    def advance_production_line(self) -> None:
        orders = self.order_repo.list_all(PRODUCTION)
        current = next((o for o in orders if o.production_started_at), None)
        if current is not None:
            sample = self.sample_repo.get(current.sample_id)
            total_minutes = current.production_quantity * sample.avg_production_time
            started = datetime.fromisoformat(current.production_started_at)
            elapsed_minutes = (datetime.now(timezone.utc) - started).total_seconds() / 60
            if elapsed_minutes >= total_minutes:
                self.complete_production(current.order_id)
                orders = self.order_repo.list_all(PRODUCTION)
                current = None
        if current is None:
            waiting = sorted(orders, key=lambda o: (o.production_queue_seq is None, o.production_queue_seq or 0, o.created_at))
            if waiting:
                next_order = waiting[0]
                if next_order.production_quantity is None:
                    sample = self.sample_repo.get(next_order.sample_id)
                    shortage = max(0, next_order.quantity - sample.stock)
                    fallback_quantity = math.ceil(shortage / sample.yield_rate) if shortage > 0 else next_order.quantity
                    self.order_repo.set_production_quantity(next_order.order_id, fallback_quantity)
                self.order_repo.set_production_started_at(next_order.order_id, datetime.now(timezone.utc).isoformat())

    def ship(self, order_id: str) -> None:
        self._transition(order_id, RELEASE)
