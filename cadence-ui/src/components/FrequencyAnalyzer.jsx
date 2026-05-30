import { useRef, useEffect } from 'react'
import { useCadenceStore } from '../store'
import { getAnalyser } from '../audio/player'

// ── Helpers ───────────────────────────────────────────────────

function freqLabel(binIndex, fftSize, sampleRate = 44100) {
  const freq = (binIndex / fftSize) * sampleRate
  if (freq >= 1000) return `${(freq / 1000).toFixed(1)}k`
  return `${Math.round(freq)}Hz`
}

function findPeaks(data, count = 4, minDb = -50) {
  const peaks = []
  for (let i = 2; i < data.length - 2; i++) {
    if (
      data[i] > minDb &&
      data[i] > data[i - 1] &&
      data[i] > data[i - 2] &&
      data[i] > data[i + 1] &&
      data[i] > data[i + 2]
    ) {
      peaks.push({ index: i, db: data[i] })
    }
  }
  peaks.sort((a, b) => b.db - a.db)
  return peaks.slice(0, count)
}

function sectionWindows(rsong) {
  const cues = (rsong?.game_meta?.cue_points || [])
    .filter((c) => c.kind === 'section' && typeof c.t === 'number')
    .sort((a, b) => a.t - b.t)
  if (!cues.length) return []
  const duration = rsong?.header?.duration_ms || 0
  return cues.map((cue, idx) => {
    const end = cues[idx + 1]?.t ?? duration
    return {
      label: cue.label,
      start: cue.t,
      end,
      index: idx,
    }
  })
}

// ── Componente ────────────────────────────────────────────────

export default function FrequencyAnalyzer() {
  const canvasRef  = useRef(null)
  const frameRef   = useRef(null)
  const { isPlaying, rsong } = useCadenceStore()

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')

    // Colores CSS vars resueltos
    const accent1  = '#ff4fd8'
    const accent2  = '#6f7dff'
    const accent3  = '#00e5ff'
    const accent4  = '#ffe66d'
    const muted    = '#8fa3d1'
    const surface  = 'rgba(9,14,28,0.9)'
    const border   = '#2c3f70'
    const hoverState = { x: -1, y: -1, active: false }

    function onMouseMove(ev) {
      const rect = canvas.getBoundingClientRect()
      hoverState.x = ((ev.clientX - rect.left) / rect.width) * canvas.width
      hoverState.y = ((ev.clientY - rect.top) / rect.height) * canvas.height
      hoverState.active = true
    }

    function onMouseLeave() {
      hoverState.active = false
    }

    canvas.addEventListener('mousemove', onMouseMove)
    canvas.addEventListener('mouseleave', onMouseLeave)

    function draw() {
      frameRef.current = requestAnimationFrame(draw)

      const W = canvas.width
      const H = canvas.height
      ctx.clearRect(0, 0, W, H)

      const analyser = getAnalyser()

      // ── Fondo semitransparente ──────────────────────────────
      ctx.fillStyle = surface
      ctx.strokeStyle = border
      ctx.lineWidth = 1
      roundRect(ctx, 0, 0, W, H, 6)
      ctx.fill()
      ctx.stroke()

      // ── Título ──────────────────────────────────────────────
      ctx.fillStyle = accent3
      ctx.font = '9px Space Mono, monospace'
      ctx.letterSpacing = '0.1em'
      ctx.fillText('FREQ ANALYSIS', 12, 16)

      const plotTop    = 24
      const plotBottom = H - 52
      const plotLeft   = 10
      const plotRight  = W - 10
      const plotW      = plotRight - plotLeft
      const plotH      = plotBottom - plotTop

      if (!analyser || !isPlaying) {
        // Idle: línea plana animada
        const t = performance.now() / 1000
        ctx.beginPath()
        ctx.strokeStyle = accent2
        ctx.globalAlpha = 0.45
        ctx.lineWidth = 1.5
        for (let x = 0; x <= plotW; x++) {
          const y = plotBottom - 4 -
            Math.abs(Math.sin(x * 0.06 + t * 1.5)) * 8
          x === 0 ? ctx.moveTo(plotLeft + x, y) : ctx.lineTo(plotLeft + x, y)
        }
        ctx.stroke()
        ctx.globalAlpha = 1

        // Texto idle
        ctx.fillStyle = accent3
        ctx.font = '10px Space Mono'
        ctx.textAlign = 'center'
        ctx.fillText('sin señal de audio', W / 2, plotBottom - plotH / 2)
        ctx.textAlign = 'left'

        drawIntensityCurve(ctx, W, H, plotBottom, plotLeft, plotRight, muted, accent4)
        return
      }

      // ── FFT data ────────────────────────────────────────────
      const rawData = analyser.getValue()
      // Usar solo la primera mitad (frecuencias positivas)
      const fftBins = Math.floor(rawData.length / 2)
      const data    = Array.from(rawData).slice(0, fftBins)

      // ── Gradiente de relleno ────────────────────────────────
      const grad = ctx.createLinearGradient(0, plotTop, 0, plotBottom)
      grad.addColorStop(0,   'rgba(255,79,216,0.6)')
      grad.addColorStop(0.45, 'rgba(111,125,255,0.42)')
      grad.addColorStop(1,   'rgba(0,229,255,0.08)')

      // ── Curva FFT (escala logarítmica en X) ─────────────────
      ctx.beginPath()
      ctx.moveTo(plotLeft, plotBottom)

      for (let x = 0; x <= plotW; x++) {
        const t       = x / plotW
        // Log scale: las bajas frecuencias ocupan más espacio visual
        const binT    = Math.pow(t, 1.8)
        const binIdx  = Math.floor(binT * (fftBins - 1))
        const db      = Math.max(-80, data[binIdx] ?? -80)
        const norm    = (db + 80) / 80              // 0 (silencio) → 1 (pico)
        const y       = plotBottom - norm * plotH
        ctx.lineTo(plotLeft + x, y)
      }

      ctx.lineTo(plotRight, plotBottom)
      ctx.closePath()
      ctx.fillStyle = grad
      ctx.fill()

      // Línea superior de la curva
      ctx.beginPath()
      for (let x = 0; x <= plotW; x++) {
        const t      = x / plotW
        const binT   = Math.pow(t, 1.8)
        const binIdx = Math.floor(binT * (fftBins - 1))
        const db     = Math.max(-80, data[binIdx] ?? -80)
        const norm   = (db + 80) / 80
        const y      = plotBottom - norm * plotH
        x === 0 ? ctx.moveTo(plotLeft + x, y) : ctx.lineTo(plotLeft + x, y)
      }
      ctx.strokeStyle = accent1
      ctx.lineWidth   = 1.5
      ctx.stroke()

      // ── Ejes de referencia ──────────────────────────────────
      ctx.strokeStyle = border
      ctx.lineWidth   = 0.5
      ;[-20, -40, -60].forEach(db => {
        const norm = (db + 80) / 80
        const y    = plotBottom - norm * plotH
        ctx.beginPath()
        ctx.moveTo(plotLeft, y)
        ctx.lineTo(plotRight, y)
        ctx.stroke()
        ctx.fillStyle = muted
        ctx.font      = '8px Space Mono'
        ctx.fillText(`${db}dB`, plotLeft + 2, y - 2)
      })

      // ── Picos dominantes ────────────────────────────────────
      const peaks = findPeaks(data, 4, -45)
      peaks.forEach(({ index, db }) => {
        const t    = Math.pow(index / (fftBins - 1), 1 / 1.8)
        const x    = plotLeft + t * plotW
        const norm = (db + 80) / 80
        const y    = plotBottom - norm * plotH

        // Punto
        ctx.beginPath()
        ctx.arc(x, y, 3, 0, Math.PI * 2)
        ctx.fillStyle = accent3
        ctx.fill()

        // Línea vertical
        ctx.beginPath()
        ctx.moveTo(x, y + 4)
        ctx.lineTo(x, plotBottom)
        ctx.strokeStyle = 'rgba(6,214,160,0.2)'
        ctx.lineWidth   = 1
        ctx.stroke()

        // Etiqueta
        const label = freqLabel(index, fftBins * 2)
        ctx.fillStyle = accent3
        ctx.font      = '8px Space Mono'
        ctx.textAlign = 'center'
        const labelX  = Math.max(plotLeft + 16, Math.min(plotRight - 16, x))
        ctx.fillText(label, labelX, y - 7)
        ctx.textAlign = 'left'
      })

      // ── Etiquetas de eje X ──────────────────────────────────
      const freqMarkers = [100, 500, 1000, 4000, 10000]
      const sampleRate  = 44100
      const markerLabelRightLimit = plotRight - 12
      freqMarkers.forEach(freq => {
        const binIdx = Math.round((freq / sampleRate) * fftBins * 2)
        const t      = Math.pow(binIdx / (fftBins - 1), 1 / 1.8)
        if (t < 0 || t > 1) return
        const x = plotLeft + t * plotW
        if (x < plotLeft + 28) return
        ctx.fillStyle = muted
        ctx.font      = '8px Space Mono'
        ctx.textAlign = 'center'
        const labelX = Math.min(markerLabelRightLimit, x)
        ctx.fillText(freq >= 1000 ? `${freq/1000}k` : `${freq}`, labelX, plotBottom + 10)
        ctx.textAlign = 'left'
        ctx.beginPath()
        ctx.moveTo(x, plotBottom)
        ctx.lineTo(x, plotBottom + 4)
        ctx.strokeStyle = border
        ctx.lineWidth   = 1
        ctx.stroke()
      })

      drawIntensityCurve(ctx, W, H, plotBottom, plotLeft, plotRight, muted, accent4)
    }

    function drawIntensityCurve(
      ctx, W, H, plotBottom, plotLeft, plotRight,
      muted, accent4
    ) {
      const { rsong, currentTimeMs } = useCadenceStore.getState()
      if (!rsong) return

      const curve = rsong.game_meta.intensity_curve || []
      const duration = rsong.header.duration_ms
      const barTop   = plotBottom + 20
      const barH     = 14
      const barW     = plotRight - plotLeft
      const windows  = sectionWindows(rsong)
      const labelY = plotBottom + 17
      let hoveredSection = null

      // Fondo de la barra
      ctx.fillStyle = 'rgba(20,29,54,0.55)'
      roundRect(ctx, plotLeft, barTop, barW, barH, 3)
      ctx.fill()

      // Segmentos por sección
      windows.forEach((w, i) => {
        const x0      = plotLeft + (w.start / duration) * barW
        const x1      = plotLeft + (w.end / duration) * barW
        const intensity = curve[i] ?? 0.5
        const alpha   = 0.24 + intensity * 0.56

        ctx.fillStyle = `rgba(111,125,255,${alpha})`
        ctx.fillRect(x0, barTop, x1 - x0 - 1, barH)

        // Hover section name
        if (
          hoverState.active &&
          hoverState.y >= barTop - 2 &&
          hoverState.y <= barTop + barH + 2 &&
          hoverState.x >= x0 &&
          hoverState.x <= x1
        ) {
          hoveredSection = w.label
        }

        // Label de sección (solo inicial)
        if (x1 - x0 > 12) {
          ctx.fillStyle = `rgba(239,244,255,${0.45 + intensity * 0.45})`
          ctx.font      = '7px Space Mono'
          ctx.textAlign = 'center'
          ctx.fillText(
            (w.label || '?').charAt(0).toUpperCase(),
            x0 + (x1 - x0) / 2,
            barTop + barH - 3
          )
          ctx.textAlign = 'left'
        }
      })

      // Playhead
      const px = plotLeft + (currentTimeMs / duration) * barW
      ctx.fillStyle = accent4
      ctx.fillRect(px - 1, barTop - 2, 2, barH + 4)

      // Label
      ctx.fillStyle = muted
      ctx.font      = '8px Space Mono'
      ctx.fillText('INTENSITY', plotLeft + 34, labelY)

      // Tooltip sección completa
      if (hoveredSection) {
        const tip = hoveredSection.toUpperCase()
        ctx.font = '8px Space Mono'
        const tw = ctx.measureText(tip).width + 12
        const tx = Math.max(plotLeft, Math.min(plotRight - tw, hoverState.x - tw / 2))
        const ty = barTop - 14
        ctx.fillStyle = 'rgba(10,16,30,0.95)'
        roundRect(ctx, tx, ty, tw, 11, 3)
        ctx.fill()
        ctx.strokeStyle = 'rgba(0,229,255,0.55)'
        ctx.lineWidth = 1
        ctx.stroke()
        ctx.fillStyle = accent3
        ctx.fillText(tip, tx + 6, ty + 8)
      }
    }

    function roundRect(ctx, x, y, w, h, r) {
      ctx.beginPath()
      ctx.moveTo(x + r, y)
      ctx.lineTo(x + w - r, y)
      ctx.arcTo(x + w, y, x + w, y + r, r)
      ctx.lineTo(x + w, y + h - r)
      ctx.arcTo(x + w, y + h, x + w - r, y + h, r)
      ctx.lineTo(x + r, y + h)
      ctx.arcTo(x, y + h, x, y + h - r, r)
      ctx.lineTo(x, y + r)
      ctx.arcTo(x, y, x + r, y, r)
      ctx.closePath()
    }

    draw()

    return () => {
      if (frameRef.current) cancelAnimationFrame(frameRef.current)
      canvas.removeEventListener('mousemove', onMouseMove)
      canvas.removeEventListener('mouseleave', onMouseLeave)
    }
  }, [isPlaying, rsong])

  if (!rsong) return null

  return (
    <canvas
      ref={canvasRef}
      width={300}
      height={180}
      style={{
        position: 'absolute',
        top: '16px',
        right: '16px',
        zIndex: 20,
        borderRadius: '6px',
        pointerEvents: 'auto',
      }}
    />
  )
}
