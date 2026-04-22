import React, { useState, useEffect, useRef } from 'react'
import { createChart, ColorType, CrosshairMode } from 'lightweight-charts'

const SYMBOL_COLORS = {
  ACB: '#3fb950',
  FPT: '#58a6ff',
  VCK: '#e3b341',
}

const ALL_SYMBOLS = ['ACB', 'FPT', 'VCK']

function aggregateToCandles(trades, intervalSec = 60) {
  if (!trades.length) return []
  const sorted = [...trades].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
  const candles = []
  let current = null

  for (const t of sorted) {
    const ts = Math.floor(new Date(t.timestamp).getTime() / 1000)
    const bucket = Math.floor(ts / intervalSec) * intervalSec
    if (!current || current.time !== bucket) {
      if (current) candles.push(current)
      current = {
        time: bucket,
        open: t.price,
        high: t.price,
        low: t.price,
        close: t.price,
        volume: t.qty,
      }
    } else {
      current.high = Math.max(current.high, t.price)
      current.low = Math.min(current.low, t.price)
      current.close = t.price
      current.volume += t.qty
    }
  }
  if (current) candles.push(current)
  return candles
}

function candlesToLine(candles) {
  return candles.map(c => ({ time: c.time, value: c.close }))
}

function candlesToVolume(candles) {
  return candles.map(c => ({
    time: c.time,
    value: c.volume,
    color: c.close >= c.open ? 'rgba(63,185,80,0.4)' : 'rgba(248,81,73,0.4)',
  }))
}

export default function TradeChart({ trades, selectedSymbol, configs }) {
  const chartContainerRef = useRef(null)
  const chartRef = useRef(null)
  const seriesRef = useRef({})
  const [chartType, setChartType] = useState('candlestick')
  const [multiMode, setMultiMode] = useState(false)
  const [selectedSymbols, setSelectedSymbols] = useState([])

  // Determine which symbols to show
  const activeSymbols = multiMode ? (selectedSymbols.length > 0 ? [...selectedSymbols].sort() : ALL_SYMBOLS) : [selectedSymbol]

  // When switching to single mode, reset multi selection
  useEffect(() => {
    if (!multiMode) {
      setSelectedSymbols([])
    }
  }, [multiMode])

  // Force line mode in multi-symbol
  const effectiveChartType = multiMode ? 'line' : chartType

  // Create chart instance
  useEffect(() => {
    if (!chartContainerRef.current) return

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#161b22' },
        textColor: '#8b949e',
        fontSize: 12,
      },
      grid: {
        vertLines: { color: '#21262d' },
        horzLines: { color: '#21262d' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
      },
      rightPriceScale: {
        borderColor: '#30363d',
      },
      timeScale: {
        borderColor: '#30363d',
        timeVisible: true,
        secondsVisible: false,
      },
      width: chartContainerRef.current.clientWidth,
      height: 360,
    })

    chartRef.current = chart

    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({ width: chartContainerRef.current.clientWidth })
      }
    }
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
      chartRef.current = null
      seriesRef.current = {}
    }
  }, [])

  // Update series data when trades, chart type, or symbols change
  useEffect(() => {
    const chart = chartRef.current
    if (!chart) return

    // Remove all existing series
    for (const key of Object.keys(seriesRef.current)) {
      try {
        chart.removeSeries(seriesRef.current[key])
      } catch (e) { /* series already removed */ }
    }
    seriesRef.current = {}

    if (effectiveChartType === 'candlestick' && !multiMode) {
      // Single symbol candlestick + volume
      const sym = activeSymbols[0]
      const symTrades = trades.filter(t => t.symbol === sym)
      const candles = aggregateToCandles(symTrades)

      const candleSeries = chart.addCandlestickSeries({
        upColor: '#3fb950',
        downColor: '#f85149',
        borderUpColor: '#3fb950',
        borderDownColor: '#f85149',
        wickUpColor: '#3fb950',
        wickDownColor: '#f85149',
      })
      candleSeries.setData(candles)
      seriesRef.current['candle'] = candleSeries

      const volumeSeries = chart.addHistogramSeries({
        priceFormat: { type: 'volume' },
        priceScaleId: 'volume',
      })
      chart.priceScale('volume').applyOptions({
        scaleMargins: { top: 0.8, bottom: 0 },
      })
      volumeSeries.setData(candlesToVolume(candles))
      seriesRef.current['volume'] = volumeSeries
    } else {
      // Line mode (single or multi)
      for (const sym of activeSymbols) {
        const symTrades = trades.filter(t => t.symbol === sym)
        const candles = aggregateToCandles(symTrades)
        const lineData = candlesToLine(candles)

        const lineSeries = chart.addLineSeries({
          color: SYMBOL_COLORS[sym] || '#c9d1d9',
          lineWidth: 2,
          title: sym,
        })
        lineSeries.setData(lineData)
        seriesRef.current[`line-${sym}`] = lineSeries
      }

      // Volume for single symbol (reuse last candles from loop above)
      if (activeSymbols.length === 1) {
        const symTrades = trades.filter(t => t.symbol === activeSymbols[0])
        const volCandles = aggregateToCandles(symTrades)
        const volumeSeries = chart.addHistogramSeries({
          priceFormat: { type: 'volume' },
          priceScaleId: 'volume',
        })
        chart.priceScale('volume').applyOptions({
          scaleMargins: { top: 0.8, bottom: 0 },
        })
        volumeSeries.setData(candlesToVolume(volCandles))
        seriesRef.current['volume'] = volumeSeries
      }
    }

    // Pin visible range to trading session 8h-15h (Vietnam time UTC+7)
    const now = new Date()
    const todayBase = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    const from = Math.floor(todayBase.getTime() / 1000) + (8 * 3600) - (7 * 3600)
    const to = Math.floor(todayBase.getTime() / 1000) + (15 * 3600) - (7 * 3600)
    chart.timeScale().setVisibleRange({ from, to })
  }, [trades, effectiveChartType, multiMode, activeSymbols.join(',')])

  const toggleSymbol = (sym) => {
    setSelectedSymbols(prev => {
      if (prev.includes(sym)) {
        return prev.filter(s => s !== sym)
      }
      return [...prev, sym]
    })
  }

  const noTrades = activeSymbols.every(sym => trades.filter(t => t.symbol === sym).length === 0)

  return (
    <div style={styles.wrapper}>
      <div style={styles.toolbar}>
        <span style={styles.toolbarTitle}>Chart</span>

        <div style={styles.toggleGroup}>
          <button
            style={{
              ...styles.toggleBtn,
              ...(effectiveChartType === 'candlestick' && !multiMode ? styles.toggleBtnActive : {}),
              ...(multiMode ? styles.toggleBtnDisabled : {}),
            }}
            onClick={() => !multiMode && setChartType('candlestick')}
            disabled={multiMode}
          >
            Nến
          </button>
          <button
            style={{
              ...styles.toggleBtn,
              ...(effectiveChartType === 'line' ? styles.toggleBtnActive : {}),
            }}
            onClick={() => setChartType('line')}
          >
            Line
          </button>
        </div>

        <div style={styles.separator} />

        <div style={styles.toggleGroup}>
          <button
            style={{
              ...styles.toggleBtn,
              ...(!multiMode ? styles.toggleBtnActive : {}),
            }}
            onClick={() => setMultiMode(false)}
          >
            1 mã
          </button>
          <button
            style={{
              ...styles.toggleBtn,
              ...(multiMode ? styles.toggleBtnActive : {}),
            }}
            onClick={() => setMultiMode(true)}
          >
            Nhiều mã
          </button>
        </div>

        {multiMode && (
          <div style={styles.symbolPicker}>
            {ALL_SYMBOLS.map(sym => (
              <button
                key={sym}
                style={{
                  ...styles.symbolBtn,
                  borderColor: SYMBOL_COLORS[sym],
                  ...(selectedSymbols.length === 0 || selectedSymbols.includes(sym)
                    ? { background: SYMBOL_COLORS[sym] + '33', color: SYMBOL_COLORS[sym] }
                    : {}),
                }}
                onClick={() => toggleSymbol(sym)}
              >
                {sym}
              </button>
            ))}
          </div>
        )}
      </div>

      <div ref={chartContainerRef} style={styles.chartContainer}>
        {noTrades && (
          <div style={styles.emptyOverlay}>
            Chưa có giao dịch
          </div>
        )}
      </div>
    </div>
  )
}

const styles = {
  wrapper: {
    background: '#161b22',
    border: '1px solid #30363d',
    borderRadius: 8,
    padding: 0,
    marginBottom: 16,
    overflow: 'hidden',
  },
  toolbar: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '8px 12px',
    borderBottom: '1px solid #30363d',
    flexWrap: 'wrap',
  },
  toolbarTitle: {
    color: '#8b949e',
    fontSize: 13,
    fontWeight: 600,
    marginRight: 8,
  },
  toggleGroup: {
    display: 'flex',
    gap: 0,
  },
  toggleBtn: {
    padding: '4px 12px',
    background: '#21262d',
    border: '1px solid #30363d',
    color: '#8b949e',
    fontSize: 12,
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.15s',
  },
  toggleBtnActive: {
    background: '#1f6feb',
    color: '#fff',
    borderColor: '#1f6feb',
  },
  toggleBtnDisabled: {
    opacity: 0.4,
    cursor: 'not-allowed',
  },
  separator: {
    width: 1,
    height: 20,
    background: '#30363d',
    margin: '0 4px',
  },
  symbolPicker: {
    display: 'flex',
    gap: 4,
    marginLeft: 4,
  },
  symbolBtn: {
    padding: '3px 10px',
    background: 'transparent',
    border: '1px solid #30363d',
    borderRadius: 4,
    color: '#8b949e',
    fontSize: 11,
    fontWeight: 600,
    cursor: 'pointer',
  },
  chartContainer: {
    position: 'relative',
    width: '100%',
    minHeight: 360,
  },
  emptyOverlay: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    color: '#484f58',
    fontSize: 14,
    fontWeight: 500,
    zIndex: 10,
    pointerEvents: 'none',
  },
}
