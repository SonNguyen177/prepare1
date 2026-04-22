---
title: 'Trade History Chart'
type: 'feature'
created: '2026-04-21'
status: 'done'
baseline_commit: '030cc98'
context: ['_bmad-output/project-context.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Client UI hiện chỉ hiển thị trade feed dạng bảng text. Không có cách nào để trader nhìn trực quan xu hướng giá, khối lượng theo thời gian — thiếu công cụ phân tích cơ bản nhất của một trading terminal.

**Approach:** Thêm component chart sử dụng TradingView Lightweight Charts library. Hỗ trợ 2 dạng hiển thị (candlestick và line), trục thời gian 8h–15h, trục khối lượng và giá. Cho phép xem 1 mã hoặc overlay nhiều mã trên cùng chart.

## Boundaries & Constraints

**Always:**
- Dùng inline styles theo dark theme hiện tại (`#0d1117`, `#161b22`, `#30363d`)
- Nhận `trades` data qua props từ App.jsx, không fetch riêng
- Chart tự cập nhật real-time khi có trade mới qua WebSocket
- Aggregate trades thành candlestick theo interval 1 phút
- Giữ functional component + hooks pattern

**Ask First:**
- Thay đổi layout chính của App.jsx (vị trí đặt chart)

**Never:**
- Không thêm CSS files hay CSS-in-JS library
- Không dùng TypeScript
- Không thêm state management library
- Không modify backend API

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Chart load với trades có sẵn | trades array không rỗng | Chart render candlestick/line với data | N/A |
| Không có trades | trades = [] | Chart hiển thị empty state với trục thời gian 8h-15h | Hiển thị text "Chưa có giao dịch" |
| Trade mới qua WebSocket | trade message arrive | Chart update real-time, thêm point/update candle cuối | N/A |
| Chuyển đổi nến ↔ line | Click toggle button | Chart re-render đúng dạng, giữ data và zoom | N/A |
| Multi-symbol mode | Chọn nhiều mã | Overlay line charts cho các mã, mỗi mã 1 màu riêng | N/A |
| Single symbol mode | Chọn 1 mã | Chart hiển thị đầy đủ candlestick + volume | N/A |

</frozen-after-approval>

## Code Map

- `client/src/App.jsx` -- Root component, quản lý trades state, nơi mount TradeChart
- `client/src/components/TradeFeed.jsx` -- Component hiện tại hiển thị trades, reference cho data flow
- `client/src/components/TradeChart.jsx` -- **MỚI** — Component chart chính
- `client/package.json` -- Thêm dependency lightweight-charts

## Tasks & Acceptance

**Execution:**
- [x] `client/package.json` -- Thêm `lightweight-charts` dependency -- Library charting nhẹ, style TradingView
- [x] `client/src/components/TradeChart.jsx` -- Tạo component chart mới -- Bao gồm: candlestick series, line series, volume histogram, chart type toggle, symbol selector (single/multi), aggregate trades thành OHLCV candles 1 phút, time scale 8h-15h
- [x] `client/src/App.jsx` -- Mount TradeChart vào layout, truyền trades + configs props -- Đặt chart bên dưới main row hoặc thay thế khu vực phù hợp

**Acceptance Criteria:**
- Given market đang mở và có trades, when mở client UI, then chart hiển thị candlestick với volume bars
- Given chart đang hiển thị, when click toggle Line, then chart chuyển sang dạng line giữ nguyên data
- Given chart đang hiển thị ACB, when chọn thêm FPT, then chart overlay 2 line series với màu khác nhau
- Given chart đang hiển thị, when trade mới arrive qua WebSocket, then chart cập nhật real-time

## Design Notes

**Lightweight Charts integration:**
- `lightweight-charts` là library chính thức của TradingView, nhẹ (~40KB gzip), zero dependencies
- Candlestick mode: 1 CandlestickSeries + 1 HistogramSeries (volume)
- Line mode: LineSeries cho mỗi symbol
- Multi-symbol: chỉ hỗ trợ Line mode (candlestick không hợp lý khi overlay nhiều mã giá khác nhau)

**Trade aggregation thành OHLCV:**
```js
// Group trades theo phút, tính open/high/low/close/volume
// time = floor(timestamp / 60) * 60
// Candle cuối cùng update liên tục khi có trade mới
```

**Color scheme cho multi-symbol:**
- ACB: `#3fb950` (green)
- FPT: `#58a6ff` (blue)  
- VCK: `#e3b341` (yellow)

## Verification

**Commands:**
- `cd client && npm install` -- expected: lightweight-charts installed thành công
- `cd client && npm run build` -- expected: build thành công, không lỗi

**Manual checks:**
- Mở browser localhost:3000, start market, đặt vài lệnh khớp → chart hiển thị candlestick + volume
- Toggle sang Line → chart chuyển dạng line
- Chọn multi-symbol → overlay nhiều mã với màu riêng biệt
- Trade mới → chart update real-time

## Suggested Review Order

- Entry point: Chart component — data flow, state, và chart lifecycle
  [`TradeChart.jsx:54`](../client/src/components/TradeChart.jsx#L54)

- Trade aggregation logic: OHLCV candle builder theo interval 1 phút
  [`TradeChart.jsx:12`](../client/src/components/TradeChart.jsx#L12)

- Chart creation effect: lightweight-charts instance + resize handler
  [`TradeChart.jsx:76`](../client/src/components/TradeChart.jsx#L76)

- Series rebuild effect: candlestick/line/volume rendering + time scale 8h-15h
  [`TradeChart.jsx:121`](../client/src/components/TradeChart.jsx#L121)

- Mount point: TradeChart integration vào App layout
  [`App.jsx:116`](../client/src/App.jsx#L116)

- Dependency: lightweight-charts package addition
  [`package.json:12`](../client/package.json#L12)
