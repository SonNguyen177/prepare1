"""REST API routes for market control, stock config, and order submission."""

from __future__ import annotations

from datetime import datetime, UTC

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..state import app_state, MarketStatus
from ..engine.order import Order, OrderSide, OrderType, OrderStatus
from ..engine.matching import match_order
from ..stocks.config import SUPPORTED_SYMBOLS

router = APIRouter(prefix="/api")


# ------------------------------------------------------------------
# Request / Response schemas
# ------------------------------------------------------------------

class OrderRequest(BaseModel):
    symbol: str
    side: str        # "BUY" | "SELL"
    order_type: str  # "LIMIT" | "MARKET"
    price: float | None = None
    qty: int
    cl_ord_id: str = ""


class AmendRequest(BaseModel):
    price: float | None = None
    qty: int | None = None


class StockConfigUpdate(BaseModel):
    floor: float | None = None
    ceiling: float | None = None
    price_step: float | None = None
    qty_step: int | None = None


# ------------------------------------------------------------------
# Market control
# ------------------------------------------------------------------

@router.post("/market/start")
async def start_market():
    app_state.market_status = MarketStatus.OPEN
    log = app_state.add_log("OUT", "REST", "Market OPENED")
    await app_state.broadcast_admin({"type": "market_status", "status": "OPEN"})
    await app_state.broadcast_admin({"type": "log", "entry": log.to_dict()})
    return {"status": "OPEN"}


@router.post("/market/stop")
async def stop_market():
    app_state.market_status = MarketStatus.CLOSED
    log = app_state.add_log("OUT", "REST", "Market CLOSED")
    await app_state.broadcast_admin({"type": "market_status", "status": "CLOSED"})
    await app_state.broadcast_admin({"type": "log", "entry": log.to_dict()})
    return {"status": "CLOSED"}


@router.get("/market/status")
async def market_status():
    return {"status": app_state.market_status.value}


# ------------------------------------------------------------------
# Stock config
# ------------------------------------------------------------------

@router.get("/stocks")
async def list_stocks():
    return {sym: cfg.to_dict() for sym, cfg in app_state.stock_configs.items()}


@router.get("/stocks/{symbol}")
async def get_stock(symbol: str):
    symbol = symbol.upper()
    cfg = app_state.stock_configs.get(symbol)
    if cfg is None:
        raise HTTPException(404, f"Unknown symbol: {symbol}")
    return cfg.to_dict()


@router.put("/stocks/{symbol}")
async def update_stock(symbol: str, body: StockConfigUpdate):
    symbol = symbol.upper()
    cfg = app_state.stock_configs.get(symbol)
    if cfg is None:
        raise HTTPException(404, f"Unknown symbol: {symbol}")

    if body.floor is not None:
        cfg.floor = body.floor
    if body.ceiling is not None:
        cfg.ceiling = body.ceiling
    if body.price_step is not None:
        cfg.price_step = body.price_step
    if body.qty_step is not None:
        cfg.qty_step = body.qty_step

    if cfg.floor >= cfg.ceiling:
        raise HTTPException(400, "Floor must be less than ceiling")

    log = app_state.add_log("IN", "REST", f"Updated config for {symbol}")
    await app_state.broadcast_admin({"type": "stock_config", "config": cfg.to_dict()})
    await app_state.broadcast_admin({"type": "log", "entry": log.to_dict()})
    return cfg.to_dict()


# ------------------------------------------------------------------
# Orders
# ------------------------------------------------------------------

@router.post("/orders")
async def submit_order(req: OrderRequest):
    # Validate market is open
    if app_state.market_status != MarketStatus.OPEN:
        raise HTTPException(400, "Market is closed")

    symbol = req.symbol.upper()
    if symbol not in SUPPORTED_SYMBOLS:
        raise HTTPException(400, f"Unsupported symbol: {symbol}")

    try:
        side = OrderSide(req.side.upper())
    except ValueError:
        raise HTTPException(400, f"Invalid side: {req.side}")

    try:
        order_type = OrderType(req.order_type.upper())
    except ValueError:
        raise HTTPException(400, f"Invalid order_type: {req.order_type}")

    # Validate price for limit orders
    cfg = app_state.stock_configs[symbol]
    if order_type == OrderType.LIMIT:
        if req.price is None:
            raise HTTPException(400, "Price required for limit orders")
        if not cfg.validate_price(req.price):
            raise HTTPException(
                400,
                f"Price {req.price} invalid: must be between {cfg.floor}-{cfg.ceiling}, step {cfg.price_step}",
            )
    if not cfg.validate_qty(req.qty):
        raise HTTPException(
            400,
            f"Qty {req.qty} invalid: must be positive multiple of {cfg.qty_step}",
        )

    order = Order(
        symbol=symbol,
        side=side,
        order_type=order_type,
        price=req.price,
        qty=req.qty,
        cl_ord_id=req.cl_ord_id,
        source="REST",
    )

    book = app_state.order_books[symbol]
    trades = match_order(order, book)
    app_state.all_orders.append(order)
    app_state.trades.extend(trades)

    # Log
    log = app_state.add_log(
        "IN", "REST",
        f"Order {order.order_id[:8]} {side.value} {order_type.value} {symbol} "
        f"qty={req.qty} price={req.price} → {order.status.value}",
    )

    # Broadcast updates
    snapshot = book.get_snapshot()
    await app_state.broadcast_market_data({
        "type": "book_update",
        "book": snapshot,
    })
    for t in trades:
        await app_state.broadcast_market_data({
            "type": "trade",
            "trade": t.to_dict(),
        })
    await app_state.broadcast_admin({"type": "log", "entry": log.to_dict()})

    return {
        "order": order.to_dict(),
        "trades": [t.to_dict() for t in trades],
    }


@router.post("/orders/cancel-all")
async def cancel_all_orders():
    """Cancel all resting orders across all symbols (admin action)."""
    # Phase 1: Cancel all orders synchronously (no awaits — atomic)
    total_cancelled = 0
    affected_symbols: list[str] = []
    for sym, book in app_state.order_books.items():
        cancelled = book.cancel_all_orders()
        if cancelled:
            total_cancelled += len(cancelled)
            affected_symbols.append(sym)

    # Phase 2: Broadcast updates (only for affected symbols)
    for sym in affected_symbols:
        snapshot = app_state.order_books[sym].get_snapshot()
        await app_state.broadcast_market_data({
            "type": "book_update",
            "book": snapshot,
        })
        await app_state.broadcast_admin({
            "type": "book_update",
            "book": snapshot,
        })

    log = app_state.add_log("OUT", "REST", f"Cancel all orders: {total_cancelled} cancelled")
    await app_state.broadcast_admin({"type": "log", "entry": log.to_dict()})

    return {"cancelled_count": total_cancelled}


@router.put("/orders/{order_id}")
async def amend_order(order_id: str, req: AmendRequest):
    """Amend price and/or quantity of a resting order."""
    if app_state.market_status != MarketStatus.OPEN:
        raise HTTPException(400, "Market is closed")

    if req.price is None and req.qty is None:
        raise HTTPException(400, "Must provide price and/or qty to amend")

    # Find the order across all books
    order = None
    book = None
    for sym, b in app_state.order_books.items():
        order = b.get_order(order_id)
        if order is not None:
            book = b
            break

    if order is None:
        raise HTTPException(404, "Order not found")

    if order.status not in (OrderStatus.NEW, OrderStatus.PARTIALLY_FILLED):
        raise HTTPException(400, f"Cannot amend order with status {order.status.value}")

    # Validate new values
    cfg = app_state.stock_configs[order.symbol]

    new_price = req.price if req.price is not None else order.price
    new_qty = req.qty if req.qty is not None else order.qty

    if not cfg.validate_price(new_price):
        raise HTTPException(
            400,
            f"Price {new_price} invalid: must be between {cfg.floor}-{cfg.ceiling}, step {cfg.price_step}",
        )
    if not cfg.validate_qty(new_qty):
        raise HTTPException(
            400,
            f"Qty {new_qty} invalid: must be positive multiple of {cfg.qty_step}",
        )
    if new_qty <= order.filled_qty:
        raise HTTPException(
            400,
            f"New qty {new_qty} must be greater than filled qty {order.filled_qty}",
        )

    # No-op check
    if new_price == order.price and new_qty == order.qty:
        return {"order": order.to_dict(), "trades": []}

    # Remove from book
    price_changed = new_price != order.price
    book.remove_order(order_id)

    # Update order fields
    order.price = new_price
    order.qty = new_qty
    if price_changed:
        order.timestamp = datetime.now(UTC)

    # Re-match
    trades = match_order(order, book)
    app_state.trades.extend(trades)

    # Log
    log = app_state.add_log(
        "IN", "REST",
        f"Amend {order_id[:8]} {order.side.value} {order.symbol} "
        f"price={new_price} qty={new_qty} → {order.status.value}",
    )

    # Broadcast updates
    snapshot = book.get_snapshot()
    await app_state.broadcast_market_data({
        "type": "book_update",
        "book": snapshot,
    })
    for t in trades:
        await app_state.broadcast_market_data({
            "type": "trade",
            "trade": t.to_dict(),
        })
    await app_state.broadcast_admin({"type": "book_update", "book": snapshot})
    await app_state.broadcast_admin({"type": "log", "entry": log.to_dict()})

    return {
        "order": order.to_dict(),
        "trades": [t.to_dict() for t in trades],
    }


@router.get("/orders/{symbol}")
async def get_orders(symbol: str):
    symbol = symbol.upper()
    if symbol not in SUPPORTED_SYMBOLS:
        raise HTTPException(400, f"Unsupported symbol: {symbol}")
    book = app_state.order_books[symbol]
    return [o.to_dict() for o in book.all_orders()]


@router.get("/trades")
async def get_all_trades():
    return [t.to_dict() for t in app_state.trades]


@router.get("/trades/{symbol}")
async def get_trades(symbol: str):
    symbol = symbol.upper()
    if symbol not in SUPPORTED_SYMBOLS:
        raise HTTPException(400, f"Unsupported symbol: {symbol}")
    return [t.to_dict() for t in app_state.trades if t.symbol == symbol]


# ------------------------------------------------------------------
# Clients
# ------------------------------------------------------------------

@router.get("/clients/count")
async def client_count():
    return {
        "ws_clients": len(app_state.market_data_clients),
        "fix_clients": app_state.fix_client_count,
        "total": app_state.total_clients(),
    }


# ------------------------------------------------------------------
# Comm logs
# ------------------------------------------------------------------

@router.get("/logs")
async def get_logs():
    return [l.to_dict() for l in app_state.comm_logs]
