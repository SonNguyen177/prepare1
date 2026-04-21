from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, UTC
import uuid


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"


class OrderStatus(str, Enum):
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"


@dataclass
class Order:
    symbol: str
    side: OrderSide
    order_type: OrderType
    qty: int
    price: float | None  # None for market orders

    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    cl_ord_id: str = ""          # Client-supplied ID (from FIX or REST)
    filled_qty: int = 0
    status: OrderStatus = OrderStatus.NEW
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    source: str = "REST"         # "REST" | "FIX"

    @property
    def remaining_qty(self) -> int:
        return self.qty - self.filled_qty

    def fill(self, qty: int) -> None:
        self.filled_qty += qty
        if self.filled_qty >= self.qty:
            self.status = OrderStatus.FILLED
        else:
            self.status = OrderStatus.PARTIALLY_FILLED

    def cancel(self) -> None:
        self.status = OrderStatus.CANCELLED

    def to_dict(self) -> dict:
        return {
            "order_id": self.order_id,
            "cl_ord_id": self.cl_ord_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "price": self.price,
            "qty": self.qty,
            "filled_qty": self.filled_qty,
            "remaining_qty": self.remaining_qty,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
        }
