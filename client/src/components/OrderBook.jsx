import React from 'react'

export default function OrderBook({ symbol, book }) {
  const bids = book?.bids || []
  const asks = (book?.asks || []).slice().reverse()  // Show highest ask at top
  const maxRows = 10

  const bestBid = bids[0]?.price
  const bestAsk = (book?.asks || [])[0]?.price
  const spread = bestBid && bestAsk ? bestAsk - bestBid : null

  // Find max qty for bar width scaling
  const allQtys = [...bids, ...(book?.asks || [])].map(l => l.qty)
  const maxQty = Math.max(...allQtys, 1)

  return (
    <div style={styles.card}>
      <h3 style={styles.heading}>{symbol} Order Book</h3>

      <div style={styles.bookContainer}>
        {/* Asks (reversed so highest at top) */}
        <div style={styles.section}>
          {asks.slice(-maxRows).map((level, i) => (
            <div key={`a-${i}`} style={styles.row}>
              <div style={{
                ...styles.bar,
                ...styles.askBar,
                width: `${(level.qty / maxQty) * 100}%`,
              }} />
              <span style={styles.askPrice}>{level.price.toLocaleString()}</span>
              <span style={styles.qty}>{level.qty.toLocaleString()}</span>
            </div>
          ))}
        </div>

        {/* Spread indicator */}
        <div style={styles.spreadRow}>
          <span style={styles.spreadLabel}>
            Spread: {spread != null ? spread.toLocaleString() : '—'}
          </span>
        </div>

        {/* Bids */}
        <div style={styles.section}>
          {bids.slice(0, maxRows).map((level, i) => (
            <div key={`b-${i}`} style={styles.row}>
              <div style={{
                ...styles.bar,
                ...styles.bidBar,
                width: `${(level.qty / maxQty) * 100}%`,
              }} />
              <span style={styles.bidPrice}>{level.price.toLocaleString()}</span>
              <span style={styles.qty}>{level.qty.toLocaleString()}</span>
            </div>
          ))}
        </div>
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
    flex: 1,
    minWidth: 0,
  },
  heading: { margin: '0 0 10px', color: '#58a6ff', fontSize: 16 },
  bookContainer: { fontFamily: 'monospace', fontSize: 13 },
  section: {},
  row: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '2px 4px',
    position: 'relative',
  },
  bar: {
    position: 'absolute',
    top: 0,
    right: 0,
    bottom: 0,
    opacity: 0.15,
    borderRadius: 2,
  },
  askBar: { background: '#f85149' },
  bidBar: { background: '#3fb950' },
  askPrice: { color: '#f85149', fontWeight: 600, zIndex: 1 },
  bidPrice: { color: '#3fb950', fontWeight: 600, zIndex: 1 },
  qty: { color: '#8b949e', zIndex: 1 },
  spreadRow: {
    padding: '6px 4px',
    borderTop: '1px solid #30363d',
    borderBottom: '1px solid #30363d',
    margin: '4px 0',
    textAlign: 'center',
  },
  spreadLabel: { color: '#8b949e', fontSize: 12 },
}
