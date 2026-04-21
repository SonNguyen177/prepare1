import React, { useRef, useEffect } from 'react'

export default function TradeFeed({ trades, symbol }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [trades.length])

  const recent = trades.slice(-50).reverse()

  return (
    <div style={styles.card}>
      <h3 style={styles.heading}>Trades — {symbol}</h3>
      <div style={styles.scroll}>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>Time</th>
              <th style={styles.th}>Price</th>
              <th style={styles.th}>Qty</th>
            </tr>
          </thead>
          <tbody>
            {recent.map((t, i) => (
              <tr key={t.trade_id || i}>
                <td style={styles.td}>
                  {new Date(t.timestamp).toLocaleTimeString()}
                </td>
                <td style={{ ...styles.td, color: '#e3b341', fontWeight: 600 }}>
                  {t.price?.toLocaleString()}
                </td>
                <td style={styles.td}>
                  {t.qty?.toLocaleString()}
                </td>
              </tr>
            ))}
            {recent.length === 0 && (
              <tr>
                <td style={{ ...styles.td, color: '#484f58' }} colSpan={3}>
                  No trades yet
                </td>
              </tr>
            )}
          </tbody>
        </table>
        <div ref={bottomRef} />
      </div>
    </div>
  )
}

const styles = {
  card: {
    background: '#161b22',
    border: '1px solid #30363d',
    borderRadius: 8,
    padding: 16,
    flex: '0 0 250px',
  },
  heading: { margin: '0 0 10px', color: '#58a6ff', fontSize: 16 },
  scroll: { maxHeight: 400, overflow: 'auto' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 13 },
  th: {
    textAlign: 'left',
    padding: '4px 6px',
    borderBottom: '1px solid #30363d',
    color: '#8b949e',
    fontWeight: 500,
    fontSize: 12,
    position: 'sticky',
    top: 0,
    background: '#161b22',
  },
  td: {
    padding: '3px 6px',
    borderBottom: '1px solid #21262d',
    fontFamily: 'monospace',
  },
}
