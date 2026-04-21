import React, { useState, useEffect } from 'react'

export default function OrderEntry({ symbol, config, api, amendOrder, onOrderPlaced, onOrderAmended, onCancelAmend }) {
  const [side, setSide] = useState('BUY')
  const [orderType, setOrderType] = useState('LIMIT')
  const [price, setPrice] = useState('')
  const [qty, setQty] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const isAmending = !!amendOrder

  // When amendOrder changes, pre-fill the form
  useEffect(() => {
    if (amendOrder) {
      setSide(amendOrder.side)
      setOrderType('LIMIT')
      setPrice(String(amendOrder.price))
      setQty(String(amendOrder.qty))
      setResult(null)
      setError(null)
    }
  }, [amendOrder])

  const submit = async (e) => {
    e.preventDefault()
    setError(null)
    setResult(null)

    if (isAmending) {
      // Amend existing order
      const body = {}
      const newPrice = parseFloat(price)
      const newQty = parseInt(qty)
      if (newPrice !== amendOrder.price) body.price = newPrice
      if (newQty !== amendOrder.qty) body.qty = newQty

      if (Object.keys(body).length === 0) {
        setError('Không có thay đổi')
        return
      }

      try {
        const r = await fetch(`${api}/api/orders/${amendOrder.order_id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
        const data = await r.json()
        if (!r.ok) {
          setError(data.detail || 'Amend rejected')
        } else {
          setResult(data)
          if (onOrderAmended) onOrderAmended(data.order)
          setPrice('')
          setQty('')
        }
      } catch (err) {
        setError(err.message)
      }
      return
    }

    // Place new order
    const body = {
      symbol,
      side,
      order_type: orderType,
      qty: parseInt(qty),
    }
    if (orderType === 'LIMIT') {
      body.price = parseFloat(price)
    }

    try {
      const r = await fetch(`${api}/api/orders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await r.json()
      if (!r.ok) {
        setError(data.detail || 'Order rejected')
      } else {
        setResult(data)
        if (onOrderPlaced) onOrderPlaced(data.order)
        setPrice('')
        setQty('')
      }
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div style={styles.card}>
      <h3 style={styles.heading}>
        {isAmending ? `Sửa lệnh — ${amendOrder.symbol}` : `Place Order — ${symbol}`}
      </h3>

      {isAmending && (
        <button type="button" style={styles.cancelAmendBtn} onClick={() => {
          if (onCancelAmend) onCancelAmend()
          setPrice('')
          setQty('')
          setError(null)
          setResult(null)
        }}>
          ✕ Hủy sửa
        </button>
      )}

      <form onSubmit={submit}>
        {!isAmending && (
          <>
            <div style={styles.row}>
              <label style={styles.label}>Side</label>
              <div style={styles.toggleGroup}>
                <button
                  type="button"
                  style={{ ...styles.toggle, ...(side === 'BUY' ? styles.buyActive : {}) }}
                  onClick={() => setSide('BUY')}
                >BUY</button>
                <button
                  type="button"
                  style={{ ...styles.toggle, ...(side === 'SELL' ? styles.sellActive : {}) }}
                  onClick={() => setSide('SELL')}
                >SELL</button>
              </div>
            </div>

            <div style={styles.row}>
              <label style={styles.label}>Type</label>
              <div style={styles.toggleGroup}>
                <button
                  type="button"
                  style={{ ...styles.toggle, ...(orderType === 'LIMIT' ? styles.typeActive : {}) }}
                  onClick={() => setOrderType('LIMIT')}
                >LIMIT</button>
                <button
                  type="button"
                  style={{ ...styles.toggle, ...(orderType === 'MARKET' ? styles.typeActive : {}) }}
                  onClick={() => setOrderType('MARKET')}
                >MARKET</button>
              </div>
            </div>
          </>
        )}

        {(isAmending || orderType === 'LIMIT') && (
          <div style={styles.row}>
            <label style={styles.label}>
              Price
              {config && <span style={styles.hint}> ({config.floor?.toLocaleString()} - {config.ceiling?.toLocaleString()}, step {config.price_step})</span>}
            </label>
            <input
              style={styles.input}
              type="number"
              value={price}
              onChange={e => setPrice(e.target.value)}
              step={config?.price_step || 100}
              min={config?.floor || 0}
              max={config?.ceiling || 100000}
              required
            />
          </div>
        )}

        <div style={styles.row}>
          <label style={styles.label}>
            Quantity
            {config && <span style={styles.hint}> (step {config.qty_step})</span>}
          </label>
          <input
            style={styles.input}
            type="number"
            value={qty}
            onChange={e => setQty(e.target.value)}
            step={config?.qty_step || 100}
            min={config?.qty_step || 100}
            required
          />
        </div>

        <button type="submit" style={{
          ...styles.submitBtn,
          background: isAmending ? '#1f6feb' : (side === 'BUY' ? '#238636' : '#da3633'),
        }}>
          {isAmending ? 'Sửa lệnh' : `${side} ${symbol}`}
        </button>
      </form>

      {error && <div style={styles.error}>{error}</div>}
      {result && (
        <div style={styles.success}>
          {result.order.status}
          {result.trades?.length > 0 && ` — ${result.trades.length} trade(s)`}
        </div>
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
    flex: '0 0 300px',
  },
  heading: { margin: '0 0 8px', color: '#58a6ff', fontSize: 16 },
  cancelAmendBtn: {
    background: 'none',
    border: '1px solid #da3633',
    borderRadius: 4,
    color: '#f85149',
    fontSize: 12,
    cursor: 'pointer',
    padding: '2px 8px',
    marginBottom: 10,
  },
  row: { marginBottom: 12 },
  label: { display: 'block', color: '#8b949e', fontSize: 13, marginBottom: 4 },
  hint: { fontSize: 11, color: '#484f58' },
  input: {
    width: '100%',
    padding: '8px 10px',
    background: '#0d1117',
    border: '1px solid #30363d',
    borderRadius: 6,
    color: '#c9d1d9',
    fontSize: 14,
    boxSizing: 'border-box',
  },
  toggleGroup: { display: 'flex', gap: 4 },
  toggle: {
    flex: 1,
    padding: '7px 0',
    background: '#21262d',
    border: '1px solid #30363d',
    borderRadius: 6,
    color: '#8b949e',
    cursor: 'pointer',
    fontSize: 13,
    fontWeight: 600,
  },
  buyActive: { background: '#238636', color: '#fff', borderColor: '#238636' },
  sellActive: { background: '#da3633', color: '#fff', borderColor: '#da3633' },
  typeActive: { background: '#1f6feb', color: '#fff', borderColor: '#1f6feb' },
  submitBtn: {
    width: '100%',
    padding: '10px 0',
    border: 'none',
    borderRadius: 6,
    color: '#fff',
    fontSize: 15,
    fontWeight: 700,
    cursor: 'pointer',
    marginTop: 4,
  },
  error: {
    marginTop: 10,
    padding: 8,
    background: '#3d1318',
    border: '1px solid #da3633',
    borderRadius: 6,
    color: '#f85149',
    fontSize: 13,
  },
  success: {
    marginTop: 10,
    padding: 8,
    background: '#0d2818',
    border: '1px solid #238636',
    borderRadius: 6,
    color: '#3fb950',
    fontSize: 13,
  },
}
