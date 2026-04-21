import React, { useState } from 'react'

export default function StockConfig({ stocks, api }) {
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState({})

  const startEdit = (sym) => {
    setEditing(sym)
    setForm({ ...stocks[sym] })
  }

  const save = async () => {
    await fetch(`${api}/api/stocks/${editing}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    })
    setEditing(null)
  }

  return (
    <div style={styles.card}>
      <h3 style={styles.heading}>Stock Configuration</h3>
      <table style={styles.table}>
        <thead>
          <tr>
            <th style={styles.th}>Symbol</th>
            <th style={styles.th}>Floor</th>
            <th style={styles.th}>Ceiling</th>
            <th style={styles.th}>Price Step</th>
            <th style={styles.th}>Qty Step</th>
            <th style={styles.th}></th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(stocks).map(([sym, cfg]) => (
            <tr key={sym}>
              {editing === sym ? (
                <>
                  <td style={styles.td}>{sym}</td>
                  <td style={styles.td}>
                    <input style={styles.input} type="number" value={form.floor || ''} onChange={e => setForm({ ...form, floor: +e.target.value })} />
                  </td>
                  <td style={styles.td}>
                    <input style={styles.input} type="number" value={form.ceiling || ''} onChange={e => setForm({ ...form, ceiling: +e.target.value })} />
                  </td>
                  <td style={styles.td}>
                    <input style={styles.input} type="number" value={form.price_step || ''} onChange={e => setForm({ ...form, price_step: +e.target.value })} />
                  </td>
                  <td style={styles.td}>
                    <input style={styles.input} type="number" value={form.qty_step || ''} onChange={e => setForm({ ...form, qty_step: +e.target.value })} />
                  </td>
                  <td style={styles.td}>
                    <button style={styles.saveBtn} onClick={save}>Save</button>
                  </td>
                </>
              ) : (
                <>
                  <td style={{ ...styles.td, fontWeight: 600, color: '#58a6ff' }}>{sym}</td>
                  <td style={styles.td}>{cfg.floor?.toLocaleString()}</td>
                  <td style={styles.td}>{cfg.ceiling?.toLocaleString()}</td>
                  <td style={styles.td}>{cfg.price_step}</td>
                  <td style={styles.td}>{cfg.qty_step}</td>
                  <td style={styles.td}>
                    <button style={styles.editBtn} onClick={() => startEdit(sym)}>Edit</button>
                  </td>
                </>
              )}
            </tr>
          ))}
        </tbody>
      </table>
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
  },
  heading: { margin: '0 0 12px', color: '#58a6ff', fontSize: 16 },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 13 },
  th: { textAlign: 'left', padding: '6px 8px', borderBottom: '1px solid #30363d', color: '#8b949e', fontWeight: 500 },
  td: { padding: '6px 8px', borderBottom: '1px solid #21262d' },
  input: {
    width: 80,
    padding: '4px 6px',
    background: '#0d1117',
    border: '1px solid #30363d',
    borderRadius: 4,
    color: '#c9d1d9',
    fontSize: 13,
  },
  editBtn: {
    padding: '3px 10px',
    background: '#21262d',
    border: '1px solid #30363d',
    borderRadius: 4,
    color: '#c9d1d9',
    cursor: 'pointer',
    fontSize: 12,
  },
  saveBtn: {
    padding: '3px 10px',
    background: '#238636',
    border: 'none',
    borderRadius: 4,
    color: '#fff',
    cursor: 'pointer',
    fontSize: 12,
  },
}
