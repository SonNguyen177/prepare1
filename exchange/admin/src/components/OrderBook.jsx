import React, { useState, useEffect } from 'react'

export default function OrderBook({ symbol, book }) {
  const bids = book?.bids || []
  const asks = book?.asks || []
  const maxRows = 8
  const [expanded, setExpanded] = useState(false)
  const [orders, setOrders] = useState([])
  const [amendingId, setAmendingId] = useState(null)
  const [amendPrice, setAmendPrice] = useState('')
  const [amendQty, setAmendQty] = useState('')
  const [amendError, setAmendError] = useState(null)

  useEffect(() => {
    if (!expanded) return
    const timer = setTimeout(() => {
      fetch(`/api/orders/${symbol}`)
        .then(r => r.json())
        .then(setOrders)
        .catch(() => setOrders([]))
    }, 300)
    return () => clearTimeout(timer)
  }, [expanded, symbol, book])

  const startAmend = (order) => {
    setAmendingId(order.order_id)
    setAmendPrice(String(order.price))
    setAmendQty(String(order.qty))
    setAmendError(null)
  }

  const submitAmend = async (orderId) => {
    setAmendError(null)
    const original = orders.find(o => o.order_id === orderId)
    const body = {}
    const newPrice = parseFloat(amendPrice)
    const newQty = parseInt(amendQty)
    if (newPrice !== original.price) body.price = newPrice
    if (newQty !== original.qty) body.qty = newQty

    if (Object.keys(body).length === 0) {
      setAmendError('Không có thay đổi')
      return
    }

    try {
      const r = await fetch(`/api/orders/${orderId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await r.json()
      if (!r.ok) {
        setAmendError(data.detail || 'Amend failed')
      } else {
        setAmendingId(null)
      }
    } catch (err) {
      setAmendError(err.message)
    }
  }

  return (
    <div style={styles.card}>
      <h3 style={styles.heading}>{symbol}</h3>
      <div style={styles.bookContainer}>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={{ ...styles.th, textAlign: 'right' }}>Bid Qty</th>
              <th style={{ ...styles.th, textAlign: 'right' }}>Bid Price</th>
              <th style={{ ...styles.th, textAlign: 'left' }}>Ask Price</th>
              <th style={{ ...styles.th, textAlign: 'left' }}>Ask Qty</th>
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: maxRows }).map((_, i) => {
              const bid = bids[i]
              const ask = asks[i]
              return (
                <tr key={i}>
                  <td style={{ ...styles.td, textAlign: 'right', color: '#3fb950' }}>
                    {bid ? bid.qty.toLocaleString() : ''}
                  </td>
                  <td style={{ ...styles.td, textAlign: 'right', color: '#3fb950', fontWeight: 600 }}>
                    {bid ? bid.price.toLocaleString() : ''}
                  </td>
                  <td style={{ ...styles.td, textAlign: 'left', color: '#f85149', fontWeight: 600 }}>
                    {ask ? ask.price.toLocaleString() : ''}
                  </td>
                  <td style={{ ...styles.td, textAlign: 'left', color: '#f85149' }}>
                    {ask ? ask.qty.toLocaleString() : ''}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <div style={styles.spread}>
        Spread: {bids[0] && asks[0]
          ? (asks[0].price - bids[0].price).toLocaleString()
          : '—'}
      </div>

      <button style={styles.expandBtn} onClick={() => setExpanded(!expanded)}>
        {expanded ? '▲ Ẩn lệnh' : '▼ Xem lệnh'}
      </button>

      {expanded && orders.length > 0 && (
        <div style={styles.ordersSection}>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Side</th>
                <th style={styles.th}>Price</th>
                <th style={styles.th}>Qty</th>
                <th style={styles.th}>Filled</th>
                <th style={styles.th}>Status</th>
                <th style={styles.th}></th>
              </tr>
            </thead>
            <tbody>
              {orders.map(o => (
                <React.Fragment key={o.order_id}>
                  <tr>
                    <td style={{ ...styles.td, color: o.side === 'BUY' ? '#3fb950' : '#f85149' }}>{o.side}</td>
                    <td style={styles.td}>{o.price?.toLocaleString()}</td>
                    <td style={styles.td}>{o.qty}</td>
                    <td style={styles.td}>{o.filled_qty}</td>
                    <td style={styles.td}>{o.status}</td>
                    <td style={styles.td}>
                      {amendingId === o.order_id ? (
                        <button style={styles.cancelBtn} onClick={() => setAmendingId(null)}>✕</button>
                      ) : (
                        <button style={styles.amendBtn} onClick={() => startAmend(o)}>Sửa</button>
                      )}
                    </td>
                  </tr>
                  {amendingId === o.order_id && (
                    <tr>
                      <td colSpan={6} style={styles.amendRow}>
                        <div style={styles.amendForm}>
                          <label style={styles.amendLabel}>Giá:</label>
                          <input style={styles.amendInput} type="number" value={amendPrice} onChange={e => setAmendPrice(e.target.value)} />
                          <label style={styles.amendLabel}>SL:</label>
                          <input style={styles.amendInput} type="number" value={amendQty} onChange={e => setAmendQty(e.target.value)} />
                          <button style={styles.amendSubmitBtn} onClick={() => submitAmend(o.order_id)}>Xác nhận</button>
                        </div>
                        {amendError && <div style={styles.amendError}>{amendError}</div>}
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {expanded && orders.length === 0 && (
        <div style={styles.noOrders}>Không có lệnh</div>
      )}
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
  heading: { margin: '0 0 10px', color: '#58a6ff', fontSize: 16, textAlign: 'center' },
  bookContainer: { overflow: 'auto' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 13 },
  th: { padding: '4px 6px', borderBottom: '1px solid #30363d', color: '#8b949e', fontWeight: 500, fontSize: 12 },
  td: { padding: '3px 6px', borderBottom: '1px solid #21262d', fontFamily: 'monospace', fontSize: 13, color: '#c9d1d9' },
  spread: { marginTop: 8, fontSize: 12, color: '#8b949e', textAlign: 'center' },
  expandBtn: {
    marginTop: 8,
    width: '100%',
    padding: '4px 0',
    background: '#21262d',
    border: '1px solid #30363d',
    borderRadius: 4,
    color: '#8b949e',
    fontSize: 12,
    cursor: 'pointer',
  },
  ordersSection: { marginTop: 8, borderTop: '1px solid #30363d', paddingTop: 8 },
  noOrders: { marginTop: 8, fontSize: 12, color: '#484f58', textAlign: 'center' },
  amendBtn: {
    padding: '2px 8px',
    background: '#1f6feb',
    border: 'none',
    borderRadius: 4,
    color: '#fff',
    fontSize: 11,
    cursor: 'pointer',
    fontWeight: 600,
  },
  cancelBtn: {
    padding: '2px 6px',
    background: 'none',
    border: '1px solid #da3633',
    borderRadius: 4,
    color: '#f85149',
    fontSize: 11,
    cursor: 'pointer',
  },
  amendRow: { padding: 8, background: '#0d1117' },
  amendForm: { display: 'flex', alignItems: 'center', gap: 6 },
  amendLabel: { color: '#8b949e', fontSize: 12 },
  amendInput: {
    width: 90,
    padding: '3px 6px',
    background: '#161b22',
    border: '1px solid #30363d',
    borderRadius: 4,
    color: '#c9d1d9',
    fontSize: 12,
  },
  amendSubmitBtn: {
    padding: '3px 10px',
    background: '#238636',
    border: 'none',
    borderRadius: 4,
    color: '#fff',
    fontSize: 11,
    fontWeight: 600,
    cursor: 'pointer',
  },
  amendError: {
    marginTop: 4,
    fontSize: 11,
    color: '#f85149',
  },
}
