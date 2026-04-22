import React, { useState, useEffect, useRef } from 'react'
import OrderEntry from './components/OrderEntry.jsx'
import OrderBook from './components/OrderBook.jsx'
import TradeFeed from './components/TradeFeed.jsx'
import TradeChart from './components/TradeChart.jsx'

const API = ''

export default function App() {
  const [marketStatus, setMarketStatus] = useState('CLOSED')
  const [books, setBooks] = useState({})
  const [trades, setTrades] = useState([])
  const [selectedSymbol, setSelectedSymbol] = useState('ACB')
  const [configs, setConfigs] = useState({})
  const [myOrders, setMyOrders] = useState([])
  const [amendOrder, setAmendOrder] = useState(null)
  const wsRef = useRef(null)

  useEffect(() => {
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${window.location.host}/ws/market-data`)

    ws.onopen = () => console.log('Market data WS connected')
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data)
      switch (msg.type) {
        case 'snapshot':
          setMarketStatus(msg.market_status)
          setBooks(msg.books)
          // Extract configs from snapshot
          const cfgs = {}
          for (const [sym, data] of Object.entries(msg.books)) {
            if (data.config) cfgs[sym] = data.config
          }
          setConfigs(cfgs)
          break
        case 'book_update':
          setBooks(prev => ({ ...prev, [msg.book.symbol]: msg.book }))
          break
        case 'trade':
          setTrades(prev => [...prev, msg.trade])
          break
      }
    }
    ws.onclose = () => console.log('Market data WS disconnected')
    wsRef.current = ws
    return () => ws.close()
  }, [])

  const onOrderPlaced = (order) => {
    if (order.status === 'NEW' || order.status === 'PARTIALLY_FILLED') {
      setMyOrders(prev => [...prev, order])
    }
  }

  const onOrderAmended = (updatedOrder) => {
    setAmendOrder(null)
    if (updatedOrder.status === 'FILLED' || updatedOrder.status === 'CANCELLED') {
      setMyOrders(prev => prev.filter(o => o.order_id !== updatedOrder.order_id))
    } else {
      setMyOrders(prev => prev.map(o => o.order_id === updatedOrder.order_id ? updatedOrder : o))
    }
  }

  const symbols = ['ACB', 'FPT', 'VCK']

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <h1 style={styles.title}>Trading Terminal</h1>
        <div style={styles.statusRow}>
          <span style={{
            ...styles.badge,
            background: marketStatus === 'OPEN' ? '#238636' : '#da3633',
          }}>
            Market: {marketStatus}
          </span>
        </div>
      </header>

      <div style={styles.symbolTabs}>
        {symbols.map(sym => (
          <button
            key={sym}
            style={{
              ...styles.tab,
              ...(selectedSymbol === sym ? styles.activeTab : {}),
            }}
            onClick={() => setSelectedSymbol(sym)}
          >
            {sym}
          </button>
        ))}
      </div>

      <div style={styles.mainRow}>
        <OrderBook
          symbol={selectedSymbol}
          book={books[selectedSymbol]}
        />
        <OrderEntry
          symbol={selectedSymbol}
          config={configs[selectedSymbol]}
          api={API}
          amendOrder={amendOrder}
          onOrderPlaced={onOrderPlaced}
          onOrderAmended={onOrderAmended}
          onCancelAmend={() => setAmendOrder(null)}
        />
        <TradeFeed
          trades={trades.filter(t => t.symbol === selectedSymbol)}
          symbol={selectedSymbol}
        />
      </div>

      <TradeChart
        trades={trades}
        selectedSymbol={selectedSymbol}
        configs={configs}
      />

      {myOrders.filter(o => o.status === 'NEW' || o.status === 'PARTIALLY_FILLED').length > 0 && (
        <div style={styles.myOrders}>
          <h3 style={styles.sectionTitle}>Lệnh của tôi</h3>
          <table style={styles.orderTable}>
            <thead>
              <tr>
                <th style={styles.orderTh}>Symbol</th>
                <th style={styles.orderTh}>Side</th>
                <th style={styles.orderTh}>Price</th>
                <th style={styles.orderTh}>Qty</th>
                <th style={styles.orderTh}>Filled</th>
                <th style={styles.orderTh}>Status</th>
                <th style={styles.orderTh}></th>
              </tr>
            </thead>
            <tbody>
              {myOrders
                .filter(o => o.status === 'NEW' || o.status === 'PARTIALLY_FILLED')
                .map(o => (
                  <tr key={o.order_id}>
                    <td style={styles.orderTd}>{o.symbol}</td>
                    <td style={{ ...styles.orderTd, color: o.side === 'BUY' ? '#3fb950' : '#f85149' }}>{o.side}</td>
                    <td style={styles.orderTd}>{o.price?.toLocaleString()}</td>
                    <td style={styles.orderTd}>{o.qty}</td>
                    <td style={styles.orderTd}>{o.filled_qty}</td>
                    <td style={styles.orderTd}>{o.status}</td>
                    <td style={styles.orderTd}>
                      <button
                        style={styles.amendBtn}
                        onClick={() => setAmendOrder(o)}
                      >Sửa</button>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}

      <div style={styles.allBooks}>
        <h3 style={styles.sectionTitle}>All Markets</h3>
        <div style={styles.booksRow}>
          {symbols.filter(s => s !== selectedSymbol).map(sym => (
            <MiniBook key={sym} symbol={sym} book={books[sym]} onSelect={() => setSelectedSymbol(sym)} />
          ))}
        </div>
      </div>
    </div>
  )
}

function MiniBook({ symbol, book, onSelect }) {
  const bids = book?.bids || []
  const asks = book?.asks || []
  return (
    <div style={miniStyles.card} onClick={onSelect}>
      <h4 style={miniStyles.heading}>{symbol}</h4>
      <div style={miniStyles.row}>
        <span style={{ color: '#3fb950' }}>
          {bids[0] ? `${bids[0].price.toLocaleString()} (${bids[0].qty})` : '—'}
        </span>
        <span style={{ color: '#8b949e' }}> / </span>
        <span style={{ color: '#f85149' }}>
          {asks[0] ? `${asks[0].price.toLocaleString()} (${asks[0].qty})` : '—'}
        </span>
      </div>
    </div>
  )
}

const styles = {
  container: {
    fontFamily: "'Segoe UI', system-ui, -apple-system, sans-serif",
    maxWidth: 1200,
    margin: '0 auto',
    padding: 20,
    background: '#0d1117',
    minHeight: '100vh',
    color: '#c9d1d9',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
    borderBottom: '1px solid #30363d',
    paddingBottom: 12,
  },
  title: { margin: 0, fontSize: 22, color: '#58a6ff' },
  statusRow: { display: 'flex', alignItems: 'center', gap: 10 },
  badge: {
    padding: '4px 12px',
    borderRadius: 12,
    fontSize: 13,
    fontWeight: 600,
    color: '#fff',
  },
  symbolTabs: {
    display: 'flex',
    gap: 4,
    marginBottom: 16,
  },
  tab: {
    padding: '8px 24px',
    background: '#21262d',
    border: '1px solid #30363d',
    borderRadius: '6px 6px 0 0',
    color: '#8b949e',
    cursor: 'pointer',
    fontSize: 14,
    fontWeight: 600,
  },
  activeTab: {
    background: '#161b22',
    color: '#58a6ff',
    borderBottom: '2px solid #58a6ff',
  },
  mainRow: {
    display: 'flex',
    gap: 16,
    marginBottom: 20,
  },
  myOrders: {
    background: '#161b22',
    border: '1px solid #30363d',
    borderRadius: 8,
    padding: 16,
    marginBottom: 16,
  },
  orderTable: { width: '100%', borderCollapse: 'collapse', fontSize: 13 },
  orderTh: { padding: '4px 8px', borderBottom: '1px solid #30363d', color: '#8b949e', fontWeight: 500, fontSize: 12, textAlign: 'left' },
  orderTd: { padding: '4px 8px', borderBottom: '1px solid #21262d', fontFamily: 'monospace', fontSize: 13, color: '#c9d1d9' },
  amendBtn: {
    padding: '3px 10px',
    background: '#1f6feb',
    border: 'none',
    borderRadius: 4,
    color: '#fff',
    fontSize: 12,
    cursor: 'pointer',
    fontWeight: 600,
  },
  allBooks: { marginTop: 8 },
  sectionTitle: { color: '#8b949e', fontSize: 14, marginBottom: 10 },
  booksRow: { display: 'flex', gap: 12 },
}

const miniStyles = {
  card: {
    background: '#161b22',
    border: '1px solid #30363d',
    borderRadius: 8,
    padding: 12,
    cursor: 'pointer',
    minWidth: 200,
  },
  heading: { margin: '0 0 6px', color: '#58a6ff', fontSize: 14 },
  row: { fontSize: 13, fontFamily: 'monospace' },
}
