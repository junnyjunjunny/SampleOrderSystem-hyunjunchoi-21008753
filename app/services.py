from datetime import datetime, timezone

from app.models import CONFIRMED, PRODUCTION, REJECTED, RECEIVED, SHIPPED, Order
from app.repository import OrderRepository, SampleRepository

ALLOWED_TRANSITIONS = {
    RECEIVED: {CONFIRMED, PRODUCTION, REJECTED},
    PRODUCTION: {CONFIRMED},
    CONFIRMED: {SHIPPED},
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
        new_status = CONFIRMED if sample.stock >= order.quantity else PRODUCTION
        self._transition(order_id, new_status)
        return new_status

    def complete_production(self, order_id: str) -> None:
        order = self.order_repo.get(order_id)
        if order.status != PRODUCTION:
            raise ValueError(f"Cannot complete production for order {order_id} from status {order.status}")
        sample = self.sample_repo.get(order.sample_id)
        self._transition(order_id, CONFIRMED)
        self.sample_repo.update_stock(sample.sample_id, sample.stock + order.quantity)

    def ship(self, order_id: str) -> None:
        order = self.order_repo.get(order_id)
        sample = self.sample_repo.get(order.sample_id)
        self._transition(order_id, SHIPPED)
        self.sample_repo.update_stock(sample.sample_id, sample.stock - order.quantity)
