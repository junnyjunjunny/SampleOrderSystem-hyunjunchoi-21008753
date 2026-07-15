from app.cli import run
from app.db import get_connection
from app.repository import OrderRepository, SampleRepository
from app.services import OrderService


def main() -> None:
    conn = get_connection()
    sample_repo = SampleRepository(conn)
    order_repo = OrderRepository(conn)
    service = OrderService(order_repo, sample_repo)
    try:
        run(sample_repo, order_repo, service)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
