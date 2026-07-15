from dataclasses import dataclass

RECEIVED = "RECEIVED"
APPROVED = "APPROVED"
REJECTED = "REJECTED"
IN_PRODUCTION = "IN_PRODUCTION"
SHIPPED = "SHIPPED"


@dataclass
class Sample:
    sample_id: str
    name: str
    avg_production_time: float
    yield_rate: float
    stock: int = 0

    @classmethod
    def from_row(cls, row) -> "Sample":
        return cls(
            sample_id=row["sample_id"],
            name=row["name"],
            avg_production_time=row["avg_production_time"],
            yield_rate=row["yield_rate"],
            stock=row["stock"],
        )


@dataclass
class Order:
    order_id: str
    sample_id: str
    customer_name: str
    quantity: int
    status: str
    created_at: str

    @classmethod
    def from_row(cls, row) -> "Order":
        return cls(
            order_id=row["order_id"],
            sample_id=row["sample_id"],
            customer_name=row["customer_name"],
            quantity=row["quantity"],
            status=row["status"],
            created_at=row["created_at"],
        )
