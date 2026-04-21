import React, { useRef, useEffect } from 'react'

export default function CommLogs({ logs }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs.length])

  const recent = logs.slice(-200)

  return (
    <div style={styles.card}>
      <h3 style={styles.heading}>Communication Logs ({logs.length})</h3>
      <div style={styles.scroll}>
        {recent.map((entry, i) => (
          <div key={i} style={styles.line}>
            <span style={styles.time}>
              {new Date(entry.timestamp).toLocaleTimeString()}
            </span>
            <span style={{
              ...styles.dir,
              color: entry.direction === 'IN' ? '#3fb950' : '#f0883e',
            }}>
              {entry.direction === 'IN' ? '\u2192' : '\u2190'}
            </span>
            <span style={styles.source}>[{entry.source}]</span>
            <span style={styles.summary}>{entry.summary}</span>
          </div>
        ))}
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
    flex: 1,
  },
  heading: { margin: '0 0 10px', color: '#58a6ff', fontSize: 16 },
  scroll: { maxHeight: 300, overflow: 'auto', fontFamily: 'monospace', fontSize: 12 },
  line: { padding: '2px 0', display: 'flex', gap: 8, lineHeight: 1.6 },
  time: { color: '#8b949e', flexShrink: 0 },
  dir: { flexShrink: 0, fontWeight: 700 },
  source: { color: '#58a6ff', flexShrink: 0 },
  summary: { color: '#c9d1d9', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
}
