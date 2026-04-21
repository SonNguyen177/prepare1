import React from 'react'

export default function MarketControl({ status, api }) {
  const start = () => fetch(`${api}/api/market/start`, { method: 'POST' })
  const stop = () => fetch(`${api}/api/market/stop`, { method: 'POST' })
  const cancelAll = () => {
    if (window.confirm('Cancel ALL resting orders across all symbols?')) {
      fetch(`${api}/api/orders/cancel-all`, { method: 'POST' })
        .then(r => r.json())
        .then(data => console.log(`Cancelled ${data.cancelled_count} orders`))
        .catch(err => alert('Failed to cancel orders: ' + err.message))
    }
  }

  const isOpen = status === 'OPEN'

  return (
    <div style={styles.card}>
      <h3 style={styles.heading}>Market Control</h3>
      <div style={styles.statusRow}>
        <span style={styles.label}>Status:</span>
        <span style={{
          ...styles.badge,
          background: isOpen ? '#238636' : '#da3633',
        }}>
          {status}
        </span>
      </div>
      <div style={styles.buttons}>
        <button style={{ ...styles.btn, ...styles.startBtn }} onClick={start} disabled={isOpen}>
          Start Market
        </button>
        <button style={{ ...styles.btn, ...styles.stopBtn }} onClick={stop} disabled={!isOpen}>
          Stop Market
        </button>
        <button style={{ ...styles.btn, ...styles.cancelAllBtn }} onClick={cancelAll}>
          Cancel All Orders
        </button>
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
    flex: '0 0 280px',
  },
  heading: { margin: '0 0 12px', color: '#58a6ff', fontSize: 16 },
  statusRow: { display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 },
  label: { color: '#8b949e', fontSize: 14 },
  badge: {
    padding: '4px 12px',
    borderRadius: 12,
    fontSize: 13,
    fontWeight: 600,
    color: '#fff',
  },
  buttons: { display: 'flex', gap: 8 },
  btn: {
    padding: '8px 16px',
    border: 'none',
    borderRadius: 6,
    cursor: 'pointer',
    fontWeight: 600,
    fontSize: 13,
    color: '#fff',
  },
  startBtn: { background: '#238636' },
  stopBtn: { background: '#da3633' },
  cancelAllBtn: { background: '#b87a1a' },
}
