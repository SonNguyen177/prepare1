from dataclasses import dataclass, field
from datetime import datetime, UTC
import uuid


@dataclass
class Trade:
    symbol: str
    buy_order_id: str
    sell_order_id: str
    price: float
    qty: int

    trade_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        return {
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "buy_order_id": self.buy_order_id,
            "sell_order_id": self.sell_order_id,
            "price": self.price,
            "qty": self.qty,
            "timestamp": self.timestamp.isoformat(),
        }
