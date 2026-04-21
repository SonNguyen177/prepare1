import React, { useState, useEffect, useRef, useCallback } from 'react'
import MarketControl from './components/MarketControl.jsx'
import StockConfig from './components/StockConfig.jsx'
import OrderBook from './components/OrderBook.jsx'
import TradeHistory from './components/TradeHistory.jsx'
import CommLogs from './components/CommLogs.jsx'
import ClientCount from './components/ClientCount.jsx'

const API = ''  // proxied via vite

export default function App() {
  const [marketStatus, setMarketStatus] = useState('CLOSED')
  const [stocks, setStocks] = useState({})
  const [books, setBooks] = useState({})
  const [trades, setTrades] = useState([])
  const [logs, setLogs] = useState([])
  const [clientCount, setClientCount] = useState(0)
  const wsRef = useRef(null)
  const adminWsRef = useRef(null)

  // Connect to admin WebSocket
  useEffect(() => {
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${window.location.host}/ws/admin`)

    ws.onopen = () => console.log('Admin WS connected')
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data)
      switch (msg.type) {
        case 'init':
          setMarketStatus(msg.market_status)
          setStocks(msg.stocks)
          setBooks(msg.books)
          setTrades(msg.trades || [])
          setLogs(msg.logs || [])
          setClientCount(msg.client_count || 0)
          break
        case 'market_status':
          setMarketStatus(msg.status)
          break
        case 'stock_config':
          setStocks(prev => ({ ...prev, [msg.config.symbol]: msg.config }))
          break
        case 'log':
          setLogs(prev => [...prev.slice(-499), msg.entry])
          break
        case 'client_count':
          setClientCount(msg.count)
          break
      }
    }
    ws.onclose = () => console.log('Admin WS disconnected')
    adminWsRef.current = ws
    return () => ws.close()
  }, [])

  // Connect to market data WebSocket for live book updates
  useEffect(() => {
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${window.location.host}/ws/market-data`)

    ws.onopen = () => console.log('Market data WS connected')
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data)
      switch (msg.type) {
        case 'snapshot':
          setBooks(msg.books)
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

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <h1 style={styles.title}>Exchange Admin Panel</h1>
        <ClientCount count={clientCount} />
      </header>

      <div style={styles.topRow}>
        <MarketControl status={marketStatus} api={API} />
        <StockConfig stocks={stocks} api={API} />
      </div>

      <div style={styles.booksRow}>
        {['ACB', 'FPT', 'VCK'].map(sym => (
          <OrderBook key={sym} symbol={sym} book={books[sym]} />
        ))}
      </div>

      <div style={styles.bottomRow}>
        <TradeHistory trades={trades} />
        <CommLogs logs={logs} />
      </div>
    </div>
  )
}

const styles = {
  container: {
    fontFamily: "'Segoe UI', system-ui, -apple-system, sans-serif",
    maxWidth: 1400,
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
    marginBottom: 20,
    borderBottom: '1px solid #30363d',
    paddingBottom: 15,
  },
  title: {
    margin: 0,
    fontSize: 24,
    color: '#58a6ff',
  },
  topRow: {
    display: 'flex',
    gap: 20,
    marginBottom: 20,
  },
  booksRow: {
    display: 'flex',
    gap: 20,
    marginBottom: 20,
  },
  bottomRow: {
    display: 'flex',
    gap: 20,
  },
}
