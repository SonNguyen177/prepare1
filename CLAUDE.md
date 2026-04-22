# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A simplified stock exchange system with a matching engine, FIX 4.4 protocol support, and web-based trading UI. Simulates Vietnamese stock market trading for three symbols: ACB, FPT, VCK.

## Architecture

**Three-service architecture** launched via `run.sh` (macOS-specific, uses `osascript`):

1. **Exchange Engine** (`exchange/engine/`) — Python/FastAPI backend on port 8000
   - Matching engine with price-time priority (best price first, FIFO within a level)
   - REST API (`/api/*`) for order submission, market control, stock config, trade history
   - WebSocket endpoints: `/ws/market-data` (client feeds), `/ws/admin` (admin dashboard)
   - FIX 4.4 TCP server on port 9876 for institutional order entry
   - All mutable state lives in a singleton `AppState` in `src/state.py` (in-memory, no persistence)

2. **Client UI** (`client/`) — React + Vite on port 3000
   - Trading terminal with order book visualization, order entry, trade feed
   - Connects via WebSocket to `/ws/market-data` for real-time updates

3. **Admin UI** (`exchange/admin/`) — referenced in `run.sh` but not present in repo yet, port 3001

### Engine internals

- `OrderBook` uses `SortedDict` (sorted containers): bids stored with negated price keys (highest-first), asks with positive keys (lowest-first). Each price level is a `deque` of Orders.
- `match_order()` fills against the resting book, then either adds remainder as resting limit order or cancels unmatched market orders.
- Stock configs enforce floor/ceiling prices and price/qty step validation.
- FIX layer uses `simplefix` library; `FIXSession` tracks sequence numbers per connection.

## Commands

### Engine (from `exchange/engine/`)
```bash
# Run engine
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# Run all tests
uv run pytest

# Run a single test file
uv run pytest tests/test_matching.py

# Run a specific test
uv run pytest tests/test_matching.py::test_name -v

# Install dependencies
uv sync --extra dev
```

### Client UI (from `client/`)
```bash
npm run dev -- --port 3000
npm run build
```

### All services
```bash
./run.sh   # Start all services (opens Terminal windows on macOS)
./stop.sh  # Kill all services by port
```

## Key API Endpoints

- `POST /api/market/start` / `POST /api/market/stop` — market must be OPEN to accept orders
- `POST /api/orders` — submit order (requires symbol, side, order_type, qty; price for LIMIT)
- `PUT /api/orders/{order_id}` — amend resting order (price/qty)
- `POST /api/orders/cancel-all` — cancel all resting orders across all symbols
- `GET /api/trades` / `GET /api/trades/{symbol}` — trade history

## Testing

Tests use `pytest-asyncio` with `asyncio_mode = "auto"`. Test files cover: order book operations, matching logic, REST API (via `httpx` TestClient), FIX message building/parsing, cancel-all, and order amendments.

## Other rules
- Đọc file `/_bmad-output/project-context.md` cẩn thận để nắm bắt rõ ràng về hệ thống

## MCP Servers

### Playwright (browser testing)

Configured in `.mcp.json`. Uses `@playwright/mcp` to automate browser interactions for testing the Admin (:3001) and Client (:3000) UIs.