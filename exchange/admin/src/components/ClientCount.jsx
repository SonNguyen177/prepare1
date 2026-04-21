import React from 'react'

export default function ClientCount({ count }) {
  return (
    <div style={styles.container}>
      <span style={styles.label}>Connected Clients</span>
      <span style={styles.badge}>{count}</span>
    </div>
  )
}

const styles = {
  container: { display: 'flex', alignItems: 'center', gap: 8 },
  label: { color: '#8b949e', fontSize: 14 },
  badge: {
    background: '#238636',
    color: '#fff',
    padding: '4px 12px',
    borderRadius: 12,
    fontSize: 14,
    fontWeight: 700,
    minWidth: 24,
    textAlign: 'center',
  },
}
