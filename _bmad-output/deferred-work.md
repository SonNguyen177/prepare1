# Deferred Work

## From: spec-trade-history-chart (2026-04-22)

- **Unbounded trades array growth** — App.jsx `setTrades(prev => [...prev, msg.trade])` grows indefinitely. In long sessions (hours), this degrades TradeChart performance since `aggregateToCandles` sorts the full array on every render. Consider capping or windowing trades.
- **NaN timestamp validation** — If backend sends invalid/missing timestamp in trade messages, `new Date(undefined).getTime()` produces `NaN` which propagates into chart data and corrupts lightweight-charts. Add validation at the WebSocket message handler level.
