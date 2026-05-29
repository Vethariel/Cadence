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

// ── Componente ────────────────────────────────────────────────

export default function FrequencyAnalyzer() {
  const canvasRef  = useRef(null)
  const frameRef   = useRef(null)
  const { isPlaying, rsong, currentTimeMs } = useCadenceStore()

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')

    // Colores CSS vars resueltos
    const accent1  = '#ff4d6d'
    const accent2  = '#7c3aed'
    const accent3  = '#06d6a0'
    const accent4  = '#ffd166'
    const muted    = '#6b6b8a'
    const surface  = 'rgba(17,17,26,0.85)'
    const border   = '#2a2a3f'

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
      ctx.fillStyle = muted
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
        ctx.globalAlpha = 0.3
        ctx.lineWidth = 1.5
        for (let x = 0; x <= plotW; x++) {
          const y = plotBottom - 4 -
            Math.abs(Math.sin(x * 0.06 + t * 1.5)) * 8
          x === 0 ? ctx.moveTo(plotLeft + x, y) : ctx.lineTo(plotLeft + x, y)
        }
        ctx.stroke()
        ctx.globalAlpha = 1

        // Texto idle
        ctx.fillStyle = muted
        ctx.font = '10px Space Mono'
        ctx.textAlign = 'center'
        ctx.fillText('sin señal de audio', W / 2, plotBottom - plotH / 2)
        ctx.textAlign = 'left'

        drawIntensityCurve(ctx, W, H, plotBottom, plotLeft, plotRight,
                           muted, accent4, border)
        return
      }

      // ── FFT data ────────────────────────────────────────────
      const rawData = analyser.getValue()
      // Usar solo la primera mitad (frecuencias positivas)
      const fftBins = Math.floor(rawData.length / 2)
      const data    = Array.from(rawData).slice(0, fftBins)

      // ── Gradiente de relleno ────────────────────────────────
      const grad = ctx.createLinearGradient(0, plotTop, 0, plotBottom)
      grad.addColorStop(0,   'rgba(255,77,109,0.6)')
      grad.addColorStop(0.4, 'rgba(124,58,237,0.4)')
      grad.addColorStop(1,   'rgba(124,58,237,0.05)')

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
      freqMarkers.forEach(freq => {
        const binIdx = Math.round((freq / sampleRate) * fftBins * 2)
        const t      = Math.pow(binIdx / (fftBins - 1), 1 / 1.8)
        if (t < 0 || t > 1) return
        const x = plotLeft + t * plotW
        ctx.fillStyle = muted
        ctx.font      = '8px Space Mono'
        ctx.textAlign = 'center'
        ctx.fillText(freq >= 1000 ? `${freq/1000}k` : `${freq}`, x, plotBottom + 10)
        ctx.textAlign = 'left'
        ctx.beginPath()
        ctx.moveTo(x, plotBottom)
        ctx.lineTo(x, plotBottom + 4)
        ctx.strokeStyle = border
        ctx.lineWidth   = 1
        ctx.stroke()
      })

      drawIntensityCurve(ctx, W, H, plotBottom, plotLeft, plotRight,
                         muted, accent4, border)
    }

    function drawIntensityCurve(
      ctx, W, H, plotBottom, plotLeft, plotRight,
      muted, accent4, border
    ) {
      const { rsong, currentTimeMs } = useCadenceStore.getState()
      if (!rsong) return

      const curve    = rsong.game_meta.intensity_curve
      const sections = rsong.game_meta.sections
      const duration = rsong.header.duration_ms
      const barTop   = H - 38
      const barH     = 14
      const barW     = plotRight - plotLeft

      // Fondo de la barra
      ctx.fillStyle = 'rgba(42,42,63,0.4)'
      roundRect(ctx, plotLeft, barTop, barW, barH, 3)
      ctx.fill()

      // Segmentos por sección
      const cues = rsong.game_meta.cue_points
      cues.forEach((cue, i) => {
        const nextT   = cues[i + 1] ? cues[i + 1].t : duration
        const x0      = plotLeft + (cue.t / duration) * barW
        const x1      = plotLeft + (nextT / duration) * barW
        const intensity = curve[i] ?? 0.5
        const alpha   = 0.3 + intensity * 0.5

        ctx.fillStyle = `rgba(124,58,237,${alpha})`
        ctx.fillRect(x0, barTop, x1 - x0 - 1, barH)

        // Label de sección
        if (x1 - x0 > 24) {
          ctx.fillStyle = `rgba(232,232,240,${0.4 + intensity * 0.4})`
          ctx.font      = '7px Space Mono'
          ctx.textAlign = 'center'
          ctx.fillText(
            cue.label.substring(0, 6),
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
      ctx.fillText('INTENSITY', plotLeft + 2, barTop - 4)
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
        pointerEvents: 'none',
      }}
    />
  )
}
