import { useCadenceStore } from '../store'
import { startPlayback, stopPlayback } from '../audio/player'

export default function Player() {
  const { rsong, isPlaying, currentTimeMs, activeSection, meta } =
    useCadenceStore()

  if (!rsong) return null

  const duration = rsong.header.duration_ms
  const progress = Math.min(1, currentTimeMs / duration)

  function formatTime(ms) {
    const s = Math.floor(ms / 1000)
    const m = Math.floor(s / 60)
    return `${m}:${String(s % 60).padStart(2, '0')}`
  }

  async function handleToggle() {
    if (isPlaying) {
      await stopPlayback()
    } else {
      await startPlayback(rsong)
    }
  }

  return (
    <div style={{
      position: 'absolute', bottom: 0, left: 0, right: 0,
      background: 'rgba(10,10,15,0.92)',
      backdropFilter: 'blur(12px)',
      borderTop: '1px solid var(--border)',
      padding: '16px 24px',
      zIndex: 10,
    }}>

      {/* Info */}
      <div style={{
        display: 'flex', justifyContent: 'space-between',
        alignItems: 'baseline', marginBottom: '10px',
      }}>
        <div style={{
          fontFamily: 'Syne, sans-serif',
          fontSize: '13px', fontWeight: 700,
          color: 'var(--text)',
          letterSpacing: '0.05em',
        }}>
          {rsong.header.title}
          <span style={{
            marginLeft: '10px', fontSize: '11px',
            color: 'var(--muted)', fontFamily: 'Space Mono',
          }}>
            {meta?.bpm} BPM · {meta?.key}
          </span>
        </div>
        <div style={{
          fontFamily: 'Space Mono, monospace',
          fontSize: '11px', color: 'var(--muted)',
        }}>
          {activeSection && (
            <span style={{
              marginRight: '12px',
              color: 'var(--accent2)',
              border: '1px solid rgba(124,58,237,0.4)',
              padding: '2px 8px', borderRadius: '2px',
            }}>
              {activeSection}
            </span>
          )}
          {formatTime(currentTimeMs)} / {formatTime(duration)}
        </div>
      </div>

      {/* Progress bar */}
      <div style={{
        height: '3px', background: 'var(--surface2)',
        borderRadius: '2px', marginBottom: '12px',
        overflow: 'hidden',
      }}>
        <div style={{
          height: '100%', borderRadius: '2px',
          width: `${progress * 100}%`,
          background: 'linear-gradient(90deg, var(--accent2), var(--accent1))',
          transition: 'width 0.05s linear',
        }} />
      </div>

      {/* Controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <button onClick={handleToggle} style={{
          background: isPlaying
            ? 'rgba(255,77,109,0.15)'
            : 'linear-gradient(135deg, var(--accent2), var(--accent1))',
          border: isPlaying
            ? '1px solid rgba(255,77,109,0.4)' : 'none',
          borderRadius: '4px',
          width: '40px', height: '40px',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          cursor: 'pointer', fontSize: '16px',
          transition: 'all 0.2s',
        }}>
          {isPlaying ? '⏹' : '▶'}
        </button>

        {/* Sección markers */}
        <div style={{
          flex: 1, display: 'flex', gap: '4px', flexWrap: 'wrap',
        }}>
          {rsong.game_meta.cue_points.map(cue => {
            const pos = cue.t / duration
            const isActive = activeSection === cue.label
            return (
              <div key={cue.label} style={{
                fontFamily: 'Space Mono, monospace',
                fontSize: '9px',
                padding: '2px 6px',
                borderRadius: '2px',
                background: isActive
                  ? 'rgba(124,58,237,0.25)' : 'var(--surface2)',
                border: `1px solid ${isActive
                  ? 'rgba(124,58,237,0.5)' : 'var(--border)'}`,
                color: isActive ? 'var(--accent2)' : 'var(--muted)',
                transition: 'all 0.15s',
                letterSpacing: '0.08em',
              }}>
                {cue.label}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
