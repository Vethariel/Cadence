import { useCadenceStore } from '../store'
import { startPlayback, startMidiPlayback, stopPlayback } from '../audio/player'
import { productionMidiUrl } from '../api'
import { trackKey, trackShortLabel } from '../audio/track-labels'

export default function Player() {
  const {
    rsong, isPlaying, isAudioLoading, currentTimeMs, activeSection, meta,
    playbackSource, setPlaybackSource, currentProductionId,
    trackMutes, toggleTrackMute, setAllTrackMutes,
  } = useCadenceStore()

  if (!rsong) return null

  const duration = rsong.header.duration_ms
  const progress = Math.min(1, currentTimeMs / duration)

  function formatTime(ms) {
    const s = Math.floor(ms / 1000)
    const m = Math.floor(s / 60)
    return `${m}:${String(s % 60).padStart(2, '0')}`
  }

  async function handleToggle() {
    if (isPlaying || isAudioLoading) {
      await stopPlayback()
      return
    }
    if (playbackSource === 'midi' && currentProductionId) {
      await startMidiPlayback(productionMidiUrl(currentProductionId), {
        durationMs: duration,
        rsong,
      })
    } else {
      await startPlayback(rsong)
    }
  }

  async function restartIfPlaying() {
    const playing = useCadenceStore.getState().isPlaying
    if (!playing || !rsong) return
    await stopPlayback()
    if (playbackSource === 'midi' && currentProductionId) {
      await startMidiPlayback(productionMidiUrl(currentProductionId), {
        durationMs: duration,
        rsong,
      })
    } else {
      await startPlayback(rsong)
    }
  }

  async function handleTrackToggle(trackId) {
    toggleTrackMute(trackId)
    await restartIfPlaying()
  }

  async function handleMuteAll(muted) {
    setAllTrackMutes(muted)
    await restartIfPlaying()
  }

  async function handleSourceChange(source) {
    if (source === playbackSource) return
    const wasPlaying = isPlaying
    if (wasPlaying) await stopPlayback()
    setPlaybackSource(source)
    if (wasPlaying) {
      if (source === 'midi' && currentProductionId) {
        await startMidiPlayback(productionMidiUrl(currentProductionId), {
          durationMs: duration,
          bpm: rsong.header.bpm,
        })
      } else {
        await startPlayback(rsong)
      }
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

      {/* Mixer — silenciar pistas */}
      <div style={{ marginBottom: '12px' }}>
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          marginBottom: '8px',
        }}>
          <span style={{
            fontFamily: 'Space Mono, monospace',
            fontSize: '10px', color: 'var(--muted)', letterSpacing: '0.08em',
          }}>
            PISTAS
          </span>
          <div style={{ display: 'flex', gap: '6px' }}>
            <button
              type="button"
              onClick={() => handleMuteAll(false)}
              disabled={isAudioLoading}
              style={mixerActionStyle()}
            >
              todas
            </button>
            <button
              type="button"
              onClick={() => handleMuteAll(true)}
              disabled={isAudioLoading}
              style={mixerActionStyle()}
            >
              ninguna
            </button>
          </div>
        </div>
        <div style={{
          display: 'flex', flexWrap: 'wrap', gap: '6px',
          maxHeight: '120px', overflowY: 'auto',
        }}>
          {[...(rsong.tracks || [])]
            .sort((a, b) => (b.event_count ?? b.events?.length ?? 0)
              - (a.event_count ?? a.events?.length ?? 0))
            .map((track) => {
              const id = trackKey(track)
              const muted = !!trackMutes[id]
              const count = track.event_count ?? track.events?.length ?? 0
              return (
                <button
                  key={id}
                  type="button"
                  title={muted ? 'Silenciada — clic para activar' : 'Activa — clic para silenciar'}
                  onClick={() => handleTrackToggle(id)}
                  disabled={isAudioLoading}
                  style={trackToggleStyle(muted)}
                >
                  <span style={{
                    display: 'inline-block', width: '6px', height: '6px',
                    borderRadius: '50%', marginRight: '6px',
                    background: muted ? 'var(--muted)' : 'var(--accent3)',
                    opacity: muted ? 0.4 : 1,
                  }} />
                  {trackShortLabel(track)}
                  <span style={{ opacity: 0.55, marginLeft: '5px' }}>{count}</span>
                </button>
              )
            })}
        </div>
        <p style={{
          margin: '8px 0 0', fontSize: '9px', color: 'var(--muted)',
          fontFamily: 'Space Mono, monospace',
        }}>
          Si está sonando, al cambiar una pista se reinicia la reproducción con la nueva mezcla.
        </p>
      </div>

      {/* Comparativa A/B */}
      {currentProductionId && (
        <div style={{
          display: 'flex', gap: '6px', marginBottom: '10px',
        }}>
          {[
            { id: 'rsong', label: 'Cadence (.rsong)' },
            { id: 'midi', label: 'MIDI export' },
          ].map(({ id, label }) => (
            <button
              key={id}
              onClick={() => handleSourceChange(id)}
              disabled={isAudioLoading}
              style={{
                fontFamily: 'Space Mono, monospace',
                fontSize: '10px',
                padding: '4px 10px',
                borderRadius: '3px',
                cursor: isAudioLoading ? 'wait' : 'pointer',
                background: playbackSource === id
                  ? (id === 'rsong' ? 'rgba(124,58,237,0.25)' : 'rgba(6,214,160,0.2)')
                  : 'var(--surface2)',
                border: `1px solid ${
                  playbackSource === id
                    ? (id === 'rsong' ? 'rgba(124,58,237,0.6)' : 'rgba(6,214,160,0.5)')
                    : 'var(--border)'
                }`,
                color: playbackSource === id
                  ? (id === 'rsong' ? 'var(--accent2)' : 'var(--accent3)')
                  : 'var(--muted)',
              }}
            >
              {label}
            </button>
          ))}
        </div>
      )}

      <div style={{
        height: '3px', background: 'var(--surface2)',
        borderRadius: '2px', marginBottom: '12px',
        overflow: 'hidden',
      }}>
        <div style={{
          height: '100%', borderRadius: '2px',
          width: `${progress * 100}%`,
          background: playbackSource === 'midi'
            ? 'linear-gradient(90deg, var(--accent3), #06d6a0)'
            : 'linear-gradient(90deg, var(--accent2), var(--accent1))',
          transition: 'width 0.05s linear',
        }} />
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <button onClick={handleToggle} disabled={isAudioLoading} style={{
          background: isPlaying
            ? 'rgba(255,77,109,0.15)'
            : isAudioLoading
              ? 'var(--surface2)'
              : 'linear-gradient(135deg, var(--accent2), var(--accent1))',
          border: isPlaying ? '1px solid rgba(255,77,109,0.4)' : 'none',
          borderRadius: '4px',
          width: '40px', height: '40px',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          cursor: isAudioLoading ? 'wait' : 'pointer', fontSize: '16px',
          opacity: isAudioLoading ? 0.6 : 1,
        }}>
          {isAudioLoading ? '…' : isPlaying ? '⏹' : '▶'}
        </button>

        <div style={{ flex: 1, display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
          {(rsong.game_meta?.cue_points || []).map(cue => {
            const isActive = activeSection === cue.label
            return (
              <div key={`${cue.label}-${cue.t}`} style={{
                fontFamily: 'Space Mono, monospace',
                fontSize: '9px',
                padding: '2px 6px',
                borderRadius: '2px',
                background: isActive ? 'rgba(124,58,237,0.25)' : 'var(--surface2)',
                border: `1px solid ${isActive ? 'rgba(124,58,237,0.5)' : 'var(--border)'}`,
                color: isActive ? 'var(--accent2)' : 'var(--muted)',
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

function mixerActionStyle() {
  return {
    fontFamily: 'Space Mono, monospace',
    fontSize: '9px',
    padding: '3px 8px',
    borderRadius: '3px',
    cursor: 'pointer',
    background: 'var(--surface2)',
    border: '1px solid var(--border)',
    color: 'var(--muted)',
  }
}

function trackToggleStyle(muted) {
  return {
    fontFamily: 'Space Mono, monospace',
    fontSize: '10px',
    padding: '5px 10px',
    borderRadius: '4px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    background: muted ? 'rgba(255,255,255,0.04)' : 'rgba(6,214,160,0.12)',
    border: `1px solid ${muted ? 'var(--border)' : 'rgba(6,214,160,0.45)'}`,
    color: muted ? 'var(--muted)' : 'var(--text)',
    textDecoration: muted ? 'line-through' : 'none',
    opacity: muted ? 0.55 : 1,
  }
}
