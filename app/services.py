from datetime import datetime, timezone

from app.models import APPROVED, IN_PRODUCTION, REJECTED, RECEIVED, SHIPPED, Order
from app.repository import OrderRepository, SampleRepository

ALLOWED_TRANSITIONS = {
    RECEIVED: {APPROVED, REJECTED},
    APPROVED: {IN_PRODUCTION},
    IN_PRODUCTION: {SHIPPED},
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

    def approve(self, order_id: str) -> None:
        order = self.order_repo.get(order_id)
        sample = self.sample_repo.get(order.sample_id)
        if sample.stock < order.quantity:
            raise ValueError(f"Insufficient stock for sample {sample.sample_id}: have {sample.stock}, need {order.quantity}")
        self._transition(order_id, APPROVED)

    def reject(self, order_id: str) -> None:
        self._transition(order_id, REJECTED)

    def start_production(self, order_id: str) -> None:
        self._transition(order_id, IN_PRODUCTION)

    def ship(self, order_id: str) -> None:
        order = self.order_repo.get(order_id)
        sample = self.sample_repo.get(order.sample_id)
        self._transition(order_id, SHIPPED)
        self.sample_repo.update_stock(sample.sample_id, sample.stock - order.quantity)
