---
project_name: 'matching-engine'
user_name: 'NaPo'
date: '2026-04-21'
sections_completed: ['technology_stack', 'language_rules', 'framework_rules', 'testing_rules', 'code_quality', 'workflow_rules', 'critical_rules']
status: 'complete'
rule_count: 42
optimized_for_llm: true
---

# Project Context cho AI Agents

_File này chứa các quy tắc và patterns quan trọng mà AI agents phải tuân theo khi triển khai code trong dự án này. Tập trung vào các chi tiết không hiển nhiên mà agents có thể bỏ sót._

---

## Technology Stack & Versions

### Backend (exchange/engine/)
- Python >=3.11
- FastAPI >=0.115.0
- Uvicorn[standard] >=0.30.0
- simplefix >=1.0.11 (FIX 4.4 protocol)
- sortedcontainers >=2.4.0 (SortedDict cho order book)
- websockets >=12.0
- Build system: hatchling + uv

### Dev/Test
- pytest >=8.0.0
- pytest-asyncio >=0.23.0 (asyncio_mode = "auto")
- httpx >=0.27.0 (TestClient)

### Client UI (client/)
- React ^18.3.1 / React DOM ^18.3.1
- Vite ^6.0.0 / @vitejs/plugin-react ^4.3.4
- Proxy: `/api` → localhost:8000, `/ws` → ws://localhost:8000

### Admin UI (exchange/admin/)
- React ^18.3.1 / Vite ^6.0.0
- Port 3001, cùng proxy config hướng đến engine port 8000

## Critical Implementation Rules

### Language-Specific Rules

**Python (Backend):**
- Dùng `dataclass` cho domain models (Order, Trade, StockConfig, LogEntry) — Pydantic `BaseModel` chỉ cho REST request/response schemas
- Tất cả models tự viết `to_dict()` thay vì dùng `dataclasses.asdict()`
- Union types dùng cú pháp 3.10+: `float | None`, `Order | None` — không dùng `Optional[]`
- Enum kế thừa cả `str` và `Enum` (`class OrderSide(str, Enum)`) để serialize trực tiếp
- `from __future__ import annotations` trong các module có type hints phức tạp
- Datetime: luôn `datetime.now(UTC)` — không bao giờ `utcnow()` (deprecated)
- ID generation: `str(uuid.uuid4())` cho tất cả IDs

**JavaScript (Frontend):**
- JSX thuần, không TypeScript
- Inline styles object — không CSS files, không CSS-in-JS library
- Functional components + hooks only (useState, useEffect, useRef)
- Không state management library — chỉ React built-in hooks

### Framework-Specific Rules

**FastAPI (Backend):**
- REST routes gom trong `APIRouter(prefix="/api")` — tất cả endpoints `/api/*`
- WebSocket endpoints ở root level: `/ws/market-data`, `/ws/admin`
- CORS `allow_origins=["*"]` trong development
- Lifespan context manager khởi động FIX TCP server cùng FastAPI app
- Singleton `app_state` (module-level `AppState()` trong `state.py`) chia sẻ giữa REST, WS, và FIX layers
- Broadcast pattern: `broadcast_market_data()` / `broadcast_admin()` tự loại bỏ dead WebSocket connections
- Symbol luôn gọi `.upper()` trước khi xử lý

**React (Frontend):**
- WebSocket kết nối qua Vite proxy — URL dùng `window.location.host`, không hardcode port
- `useRef` giữ WebSocket connection instance
- Server message types: `snapshot`, `book_update`, `trade`
- App.jsx là single source of truth — components nhận data qua props, không fetch riêng
- UI text có tiếng Việt ("Lệnh của tôi", "Sửa")

### Testing Rules

- `asyncio_mode = "auto"` — không cần `@pytest.mark.asyncio` trên từng test
- Tất cả test files trong `exchange/engine/tests/`, naming: `test_*.py`
- API tests dùng `httpx.AsyncClient` với `ASGITransport(app=app)` — không dùng FastAPI TestClient trực tiếp
- Unit tests matching engine: tạo `OrderBook` + `Order` trực tiếp, gọi `match_order()`
- FIX tests: dùng `simplefix` build/parse messages, kiểm tra byte output
- `app_state` là singleton — tests cần quản lý state riêng hoặc tạo OrderBook mới để tránh interference giữa các tests
- Chạy tests: `cd exchange/engine && uv run pytest`

### Code Quality & Style Rules

**Naming:**
- Python: snake_case functions/variables, PascalCase classes/Enums
- Files: snake_case (order_book.py, fix_messages.py)
- Test files: `test_` prefix match module name (test_order_book.py ↔ order_book.py)
- React: PascalCase components (OrderBook.jsx), camelCase variables

**Code organization:**
- Backend chia theo layer: `engine/` (domain), `api/` (REST + WS), `fix/` (FIX protocol), `stocks/` (config)
- Mỗi module có `__init__.py` — explicit package structure
- Frontend: `src/components/` chứa components, `src/App.jsx` là root

**Style:**
- Không có linter/formatter config (không ESLint, Prettier, Ruff, Black)
- Docstrings `"""..."""` cho module-level và class-level, không bắt buộc mọi function
- Private methods prefix `_` (`_match_buy`, `_heartbeat_loop`)
- Constants viết UPPER_CASE (TAG_MSG_TYPE, MSG_LOGON, ENGINE_COMP_ID)

### Development Workflow Rules

**Services & Ports:**
- Engine: 8000, Admin UI: 3001, Client UI: 3000, FIX TCP: 9876
- `./run.sh` khởi động 3 services bằng `osascript` (macOS only)
- `./stop.sh` kill processes theo port bằng `lsof`
- Engine: `uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload`

**Package management:**
- Python: `uv` (uv sync, uv run) — không pip
- Node.js: `npm` — không yarn/pnpm

**Không có:** CI/CD, Docker, .env files, database — toàn bộ state in-memory

### Critical Don't-Miss Rules

**Order Book — negated price keys (DỄ SAI):**
- Bids lưu key `-price` (âm) trong SortedDict → index 0 = giá cao nhất
- Asks lưu key `+price` → index 0 = giá thấp nhất
- Đọc best bid: `return -self._bids.peekitem(0)[0]` — PHẢI negate lại
- Thêm bid: `key = -order.price` — PHẢI nhớ negate

**Market gate:**
- Cả REST và FIX kiểm tra `app_state.market_status == MarketStatus.OPEN` trước khi nhận order
- Market CLOSED → HTTP 400 hoặc FIX ExecutionReport reject

**Matching logic — price-time priority:**
- Trade price = resting order's price (KHÔNG phải incoming order's price)
- Market orders không match → bị cancel (không thêm vào book)
- Limit orders không match → thêm vào book làm resting order
- Filled orders xóa khỏi deque VÀ `_orders` dict

**Validation:**
- Price: `[floor, ceiling]` VÀ align `price_step` (float tolerance 1e-9)
- Qty: > 0 VÀ bội số `qty_step`
- Chỉ 3 symbols: ACB, FPT, VCK (`SUPPORTED_SYMBOLS`)

**FIX protocol mapping:**
- Side: `"1"` = BUY, `"2"` = SELL
- OrdType: `"1"` = MARKET, `"2"` = LIMIT
- ExecType: `"0"` = NEW, `"1"` = PARTIAL_FILL, `"2"` = FILL, `"4"` = CANCELLED, `"8"` = REJECTED
- FIX messages là bytes — `get_field()` decode bytes → str

**State singleton:**
- `app_state` global singleton — mọi thay đổi ảnh hưởng tất cả connections
- Không có locking — single asyncio event loop, không thread-safe
- `comm_logs` giới hạn 500 entries, tự cắt cũ

---

## Hướng dẫn sử dụng

**Cho AI Agents:**
- Đọc file này trước khi triển khai bất kỳ code nào
- Tuân theo TẤT CẢ quy tắc như đã ghi
- Khi không chắc chắn, chọn phương án chặt chẽ hơn
- Cập nhật file này nếu phát hiện patterns mới

**Cho con người:**
- Giữ file lean, tập trung vào nhu cầu agent
- Cập nhật khi technology stack thay đổi
- Review định kỳ để loại bỏ rules lỗi thời

Cập nhật lần cuối: 2026-04-21
