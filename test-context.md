Bạn là senior engineer audit hệ thống giao dịch chứng khoán.
Stack: Python asyncio (FastAPI + FIX 4.4), React frontend.
Mục tiêu: tìm TỐI ĐA bug thực sự, zero false positive.

═══════════════════════════════════════════
BƯỚC 0 — XÁC ĐỊNH CONCURRENCY MODEL ĐANG DÙNG
═══════════════════════════════════════════
Xác định concurrency model đang dùng (asyncio / threading / 
multiprocessing / không có). Output 1 dòng rồi tiếp tục đọc codebase.

═══════════════════════════════════════════
BƯỚC 1 — ĐỌC TOÀN BỘ CODEBASE (KHÔNG FIX GÌ)
═══════════════════════════════════════════
Đọc theo thứ tự này. Ghi chú nội bộ, không output:

1. pyproject.toml / package.json — biết dependencies
2. src/state.py, src/engine/ — core data model
3. src/api/rest.py, src/api/ws.py — HTTP + WS layer
4. src/fix/server.py, src/fix/messages.py, src/fix/session.py — FIX layer
5. src/stocks/config.py, src/main.py
6. Toàn bộ React components (client/ và exchange/admin/)

═══════════════════════════════════════════
BƯỚC 2 — SCAN THEO 11 DANH MỤC SAU
═══════════════════════════════════════════
Với mỗi finding: ghi file + dòng | điều kiện reproduce | hậu quả

── DANH MỤC 1: LOGIC KHỚP LỆNH ─────────────
□ Price priority: bids dùng key âm (cao → thấp)? Asks dùng key dương (thấp → cao)?
□ Market order khi book rỗng → cancelled, không khớp giá 0
□ Trade price = resting order's price (maker), không phải taker
□ filled_qty + remaining_qty == original_qty sau mỗi partial fill
□ Order state machine: fill() và cancel() có guard terminal state không?
  FILLED → không được fill/cancel thêm
  CANCELLED → không được fill/cancel thêm

── DANH MỤC 2: LOGIC ĐẶT LỆNH ─────────────
□ Đã chặn đặt lệnh khi không trong phiên OPEN?
□ Trường Khối lượng chỉ cho nhập số nguyên dương, là bội của bước khối lượng đã cài đặt trên Admin?
□ Trường Giá đặt cần là số >= giá sàn và <= giá trần?
□ Trường Giá đặt cần chia được hết cho bước giá đã cài đặt trên Admin?
□ Mã cổ phiếu đặt lệnh phải nằm trong danh sách mã cổ phiếu đã khai báo trên Admin? 
□ Mã cổ phiếu, Giá đặt, Khối lượng không được để trống, nhập là khoảng trắng?

── DANH MỤC 3: LOGIC SỬA LỆNH ─────────────
 Project có endpoint sửa lệnh không? Nếu không, bỏ qua.

□ Đã chặn sửa lệnh khi không trong phiên OPEN?
□ Chỉ cho sửa Giá đặt và Khối lượng?
□ Các lệnh có trạng thái Đã khớp, Đã huỷ, Khớp 1 phần đã huỷ phần còn lại đã chặn sửa lệnh?
□ Các lệnh có trạng thái Đã khớp, Đã huỷ, Khớp 1 phần đã huỷ phần còn lại đã chặn sửa lệnh?
□ Trường Khối lượng chỉ cho nhập số nguyên dương, là bội của bước khối lượng đã cài đặt trên Admin?
□ Trường Giá đặt đã validate: chỉ cho nhập số, >= giá sàn và <= giá trần?
□ Trường Giá đặt đã validate cần chia được hết cho bước giá đã cài đặt trên Admin?
□ Giá đặt, Khối lượng đã validate không được để trống, nhập là khoảng trắng?
□ Đã chặn sửa Giá và Khối lượng cùng lúc?
□ Lệnh Limit đã chặn sửa sang lệnh Martket?
□ Lệnh Martket đã chặn không cho sửa?

── DANH MỤC 4: LOGIC HUỶ LỆNH ─────────────
Project có endpoint huỷ lệnh không? Nếu không, bỏ qua.

□ Đã chặn huỷ lệnh khi không trong phiên OPEN?
□ Các lệnh có trạng thái Đã khớp, Đã huỷ, Khớp 1 phần đã huỷ phần còn lại đã chặn huỷ lệnh?
□ Hệ thống đã chặn sửa và huỷ 1 lệnh cùng lúc?

── DANH MỤC 5: ASYNCIO RACE CONDITIONS ─────
□ Tìm MỌI vòng lặp có dạng: for x in <set/dict>: ... await ...
  → set/dict thay đổi khi await yield → RuntimeError
□ Tìm asyncio.create_task() không lưu reference → silently dropped
□ Tìm pattern: check state → await → act on state (TOCTOU)
□ Tìm global/shared mutable state được modify trong async context
  mà không có lock

── DANH MỤC 6: SECURITY — BACKEND ──────────
□ Với MỖI endpoint: liệt kê authentication requirement của nó
□ Với MỖI endpoint có auth: xác nhận dependency được khai báo đúng
□ Tìm endpoint được thêm auth SAU NÀY mà quên endpoint khác cùng nhóm
□ Input validation: price ≤ 0, qty ≤ 0, negative values lọt qua không?
□ FIX session: mọi tag numeric được parse bằng int()/float() có
  try/except ValueError không?
□ CORS: allow_origins=["*"] + allow_credentials=True là cấu hình
  nguy hiểm (phản chiếu Origin header cho credentialed requests)

── DANH MỤC 7: SECURITY — FRONTEND/BACKEND CONTRACT ──
⚠️ QUAN TRỌNG NHẤT — hay bị bỏ sót nhất:
□ Với MỖI endpoint có authentication/authorization trên backend:
  → Liệt kê MỌI component React gọi endpoint đó (grep fetch URL)
  → Kiểm tra component đó có gửi đúng header không (X-Admin-Key, Bearer, etc.)
  → "Half-fix" pattern: backend được thêm auth nhưng frontend chưa update  
□ Khi backend thêm auth cho endpoint X, frontend phải được update
  cùng lúc. Tìm các "half-fix" này.
□ Kiểm tra fetch() calls trong React: có Content-Type header không?
  Có auth header không (nếu endpoint yêu cầu)?

── DANH MỤC 8: UNHANDLED CRASH — PYTHON ────
□ int(x), float(x) từ external input (FIX tag, HTTP param) không có
  try/except ValueError → crash connection
□ dict["key"] trên FIX message không có .get() hoặc KeyError handler
□ Bare except: pass hoặc except Exception: pass (nuốt lỗi im lặng)
□ asyncio Task exception never retrieved:
  asyncio.create_task(coro()) không có .add_done_callback hoặc await

── DANH MỤC 9: SYMMETRY ANALYSIS ──────────
⚠️ QUAN TRỌNG — kiểm tra tính đối xứng:
□ WebSocket connect → broadcast notify? Disconnect → cũng broadcast?
  So sánh từng WS endpoint (market_data_ws vs admin_ws):
  - connect: add to clients set, gửi init, broadcast client_count?
  - disconnect: discard from set, broadcast client_count?
□ Market start → broadcast? Market stop → cũng broadcast?
□ FIX connect → fix_client_count++, broadcast. Disconnect → --,
  broadcast. Cả 2 chiều?
□ Mọi resource add() phải có discard()/remove() tương ứng

── DANH MỤC 10: REACT CRASH & MEMORY LEAKS ─
□ JSON.parse(e.data) trong WebSocket onmessage không có try/catch
  → uncaught exception khi server gửi invalid JSON
□ Array.map() trên data từ API: có guard null/undefined không?
□ useEffect có cleanup return để đóng WS và clearTimeout không?
□ setState sau component unmount (memory leak + warning):
  async fetch → component unmount → setState → warning
□ trades/logs state grow unbounded không có cap

── DANH MỤC 11: VALIDATION CONSISTENCY ──────
□ REST và FIX interface của cùng 1 operation có validate như nhau không?
  Ví dụ: REST reject market order với price → FIX cũng phải reject
□ update_stock: floor, ceiling, price_step, qty_step đều cần > 0 check
□ StockConfig.validate_price(): nếu floor hoặc ceiling bị set âm,
  validate_price có hoạt động đúng không?

═══════════════════════════════════════════
BƯỚC 3 — LIỆT KÊ, HỎI TRƯỚC KHI FIX
═══════════════════════════════════════════
Output format:
[P0-LOGIC]   file:dòng  — mô tả ngắn
[P0-RACE]    file:dòng  — mô tả ngắn
[P0-SEC]     file:dòng  — mô tả ngắn
[P1-CRASH]   file:dòng  — mô tả ngắn
[P1-LOGIC]   file:dòng  — mô tả ngắn

Tổng kết: "Tìm được X bug. Xác nhận fix không?"
DỪNG — đợi xác nhận.

═══════════════════════════════════════════
BƯỚC 4 — FIX P0 → P1, MỖI BUG 1 COMMIT
═══════════════════════════════════════════
1. Fix code — minimal change
2. Test: logic → boundary assert; race → asyncio.gather; 
   security → assert 401/403; crash → malformed input không raise
3. Run pytest → confirm pass
#4. git commit -m "fix(scope): mô tả [P0-LOGIC|P0-RACE|...]"

═══════════════════════════════════════════
BƯỚC 5 — XUẤT report-bug.md
═══════════════════════════════════════════
Mỗi bug: ID | Priority | Hệ thống | Mô tả | Step test manual

RÀNG BUỘC: Không thay đổi API interface, FIX format. 
Không refactor ngoài phạm vi bug. Mỗi fix phải có test.

report-e2e.md
 - ID testcase dạng [E2E-1, E2E-2, E2E-3...]
 - [ ] Fixed
 - Severity: P0/P1/P2/P3
 - Mô tả lỗi
 - Step test để tái hiện khi test manual
 - Suggested fix (1-2 dòng)
 