"""WebSocket endpoints for market data and admin feeds."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..state import app_state

router = APIRouter()


@router.websocket("/ws/market-data")
async def market_data_ws(ws: WebSocket):
    await ws.accept()
    app_state.market_data_clients.add(ws)

    # Send initial snapshot of all books + stock configs
    snapshots = {}
    for sym, book in app_state.order_books.items():
        snapshots[sym] = book.get_snapshot()
        snapshots[sym]["config"] = app_state.stock_configs[sym].to_dict()

    await ws.send_json({
        "type": "snapshot",
        "market_status": app_state.market_status.value,
        "books": snapshots,
    })

    # Notify admin of new client
    await app_state.broadcast_admin({
        "type": "client_count",
        "count": app_state.total_clients(),
    })

    try:
        # Keep connection open; client may send pings or subscription filters
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        app_state.market_data_clients.discard(ws)
        await app_state.broadcast_admin({
            "type": "client_count",
            "count": app_state.total_clients(),
        })


@router.websocket("/ws/admin")
async def admin_ws(ws: WebSocket):
    await ws.accept()
    app_state.admin_clients.add(ws)

    # Send initial state
    await ws.send_json({
        "type": "init",
        "market_status": app_state.market_status.value,
        "stocks": {sym: cfg.to_dict() for sym, cfg in app_state.stock_configs.items()},
        "books": {sym: book.get_snapshot() for sym, book in app_state.order_books.items()},
        "trades": [t.to_dict() for t in app_state.trades],
        "logs": [l.to_dict() for l in app_state.comm_logs[-100:]],
        "client_count": app_state.total_clients(),
    })

    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        app_state.admin_clients.discard(ws)
