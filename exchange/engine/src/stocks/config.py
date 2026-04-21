from dataclasses import dataclass


@dataclass
class StockConfig:
    symbol: str
    floor: float
    ceiling: float
    price_step: float
    qty_step: int

    def validate_price(self, price: float) -> bool:
        """Check price is within floor/ceiling and aligns to price_step."""
        if price < self.floor or price > self.ceiling:
            return False
        # Check alignment to step (allow small float tolerance)
        remainder = round((price - self.floor) % self.price_step, 6)
        return remainder == 0.0 or abs(remainder - self.price_step) < 1e-9

    def validate_qty(self, qty: int) -> bool:
        """Check quantity is a positive multiple of qty_step."""
        return qty > 0 and qty % self.qty_step == 0

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "floor": self.floor,
            "ceiling": self.ceiling,
            "price_step": self.price_step,
            "qty_step": self.qty_step,
        }


# Default stock configurations
DEFAULT_STOCKS: dict[str, StockConfig] = {
    "ACB": StockConfig(
        symbol="ACB",
        floor=20000,
        ceiling=30000,
        price_step=100,
        qty_step=100,
    ),
    "FPT": StockConfig(
        symbol="FPT",
        floor=50000,
        ceiling=75000,
        price_step=100,
        qty_step=100,
    ),
    "VCK": StockConfig(
        symbol="VCK",
        floor=10000,
        ceiling=15000,
        price_step=100,
        qty_step=100,
    ),
}

SUPPORTED_SYMBOLS = set(DEFAULT_STOCKS.keys())
