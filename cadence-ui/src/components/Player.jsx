import { useState } from 'react'
import { useCadenceStore } from '../store'
import {
  pausePlayback,
  resumePlayback,
  seekTo,
  startPlayback,
  stopPlayback,
} from '../audio/player'
import { downloadMidiFromRsong, downloadRsong } from '../audio/export'
import { trackKey, trackShortLabel } from '../audio/track-labels'

function formatTime(ms) {
  const s = Math.floor(ms / 1000)
  const m = Math.floor(s / 60)
  return `${m}:${String(s % 60).padStart(2, '0')}`
}

function deriveModeFromKey(key) {
  if (!key || typeof key !== 'string') return null
  const lower = key.toLowerCase()
  if (lower.includes('minor') || lower.includes(' min')) return 'minor'
  if (lower.includes('major') || lower.includes(' maj')) return 'major'
  return null
}

function formatMeter(sig) {
  if (Array.isArray(sig) && sig.length >= 2) {
    return `${sig[0]}/${sig[1]}`
  }
  if (typeof sig === 'string' && sig.trim()) return sig
  return null
}

function buildPatternSummary(rsong) {
  const audit = rsong?.game_meta?.pattern_selection_audit
  if (audit?.rhythm_combo) return audit.rhythm_combo
  const fields = audit?.fields
  if (Array.isArray(fields) && fields.length) {
    return fields
      .slice(0, 4)
      .map((f) => `${f.field}:${f.chosen || '—'}`)
      .join(' · ')
  }
  const layers = rsong?.game_meta?.arrangement?.layers
  if (Array.isArray(layers) && layers.length) {
    return layers
      .slice(0, 4)
      .map((l) => l.pattern_strategy)
      .filter(Boolean)
      .join(' · ') || null
  }
  return null
}

function formatJsonLeaf(value) {
  if (typeof value === 'string') return `"${value}"`
  if (value === null) return 'null'
  return String(value)
}

function JsonTreeNode({ nodeKey, value, depth = 0, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  const isObject = value && typeof value === 'object'
  const indent = Math.min(depth * 12, 132)

  if (!isObject) {
    return (
      <div className="json-leaf-row" style={{ paddingLeft: `${indent}px` }}>
        <span className="json-key">{nodeKey}:</span>
        <span className="json-leaf-value">{formatJsonLeaf(value)}</span>
      </div>
    )
  }

  const entries = Array.isArray(value)
    ? value.map((item, idx) => [`[${idx}]`, item])
    : Object.entries(value)
  const shape = Array.isArray(value) ? `[${entries.length}]` : `{${entries.length}}`

  return (
    <div className="json-node">
      <button
        type="button"
        className="json-toggle-row"
        style={{ paddingLeft: `${indent}px` }}
        onClick={() => setOpen((prev) => !prev)}
      >
        <span className="json-caret">{open ? '▾' : '▸'}</span>
        <span className="json-key">{nodeKey}</span>
        <span className="json-shape">{shape}</span>
      </button>
      {open && (
        <div className="json-children">
          {entries.map(([childKey, childValue]) => (
            <JsonTreeNode
              key={`${nodeKey}.${childKey}`}
              nodeKey={childKey}
              value={childValue}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default function Player() {
  const [showDetails, setShowDetails] = useState(false)
  const [showRsongTree, setShowRsongTree] = useState(false)
  const {
    rsong,
    isPlaying,
    isPaused,
    isAudioLoading,
    currentTimeMs,
    activeSection,
    meta,
    currentProductionId,
    trackMutes,
    toggleTrackMute,
    setAllTrackMutes,
  } = useCadenceStore()

  if (!rsong) return null

  const duration = rsong.header.duration_ms
  const progress = Math.min(1, currentTimeMs / duration)
  const filenameBase = (currentProductionId || rsong.header?.title || 'cadence')
    .replace(/\.rsong$/i, '')
  const detailKey = meta?.key || rsong.header?.key || rsong.game_meta?.harmony?.key
  const detailMode = (
    meta?.mode ||
    rsong.header?.mode ||
    rsong.game_meta?.harmony?.mode ||
    deriveModeFromKey(detailKey)
  )
  const detailMeter = (
    meta?.meter ||
    rsong.header?.meter ||
    formatMeter(rsong.header?.time_signature)
  )
  const detailArchetype = (
    meta?.archetype ||
    rsong.game_meta?.composition_archetype ||
    rsong.game_meta?.voice_register?.composition_archetype ||
    rsong.game_meta?.pattern_intent?.composition_archetype
  )
  const detailPattern = (
    meta?.pattern_id ||
    buildPatternSummary(rsong)
  )
  const detailValidation = (
    meta?.validation_score ??
    rsong.validation?.score
  )
  const detailKnowledge = (
    meta?.knowledge_level ||
    rsong.game_meta?.knowledge_level ||
    rsong.game_meta?.style_profile?.reasoning ||
    rsong.game_meta?.voice_register?.melody_texture
  )
  const detailSections = (
    meta?.sections ||
    rsong.game_meta?.sections ||
    (rsong.game_meta?.cue_points || [])
      .filter((c) => c.kind === 'section')
      .map((c) => c.label)
  )
  const detailActiveInstruments = (
    meta?.active_instruments?.length
      ? meta.active_instruments
      : rsong.game_meta?.arrangement?.active_instruments?.length
        ? rsong.game_meta.arrangement.active_instruments
        : rsong.game_meta?.arrangement?.required_layers?.length
          ? rsong.game_meta.arrangement.required_layers
          : (rsong.tracks || []).map((t) => t.instrument_id || t.id)
  )

  async function handlePlayPause() {
    if (isAudioLoading) return
    if (isPlaying) {
      await pausePlayback()
      return
    }
    if (isPaused) {
      await resumePlayback()
      return
    }
    await startPlayback(rsong, { startAtMs: 0 })
  }

  async function restartIfActive() {
    const state = useCadenceStore.getState()
    if (!state.isPlaying && !state.isPaused) return
    await startPlayback(state.rsong, { startAtMs: state.currentTimeMs })
    if (state.isPaused) {
      await pausePlayback()
    }
  }

  async function handleTrackToggle(trackId) {
    toggleTrackMute(trackId)
    await restartIfActive()
  }

  async function handleMuteAll(muted) {
    setAllTrackMutes(muted)
    await restartIfActive()
  }

  function handleSeek(event) {
    const value = Number(event.target.value)
    seekTo(value)
  }

  return (
    <div className="player-overlay">
      <div className="player-header">
        <div className="player-title">
          {rsong.header.title}
          <span className="player-subtitle">
            {meta?.bpm || rsong.header?.bpm} BPM · {meta?.key || rsong.header?.key}
          </span>
        </div>
        <div className="player-time">
          {activeSection && <span className="active-section-chip">{activeSection}</span>}
          {formatTime(currentTimeMs)} / {formatTime(duration)}
        </div>
      </div>

      <div className="player-controls-row">
        <button onClick={handlePlayPause} disabled={isAudioLoading} className="primary-player-btn">
          {isAudioLoading ? '…' : isPlaying ? '⏸ Pause' : isPaused ? '▶ Resume' : '▶ Play'}
        </button>
        <button onClick={() => stopPlayback()} disabled={isAudioLoading} className="secondary-player-btn">
          ⏹ Stop
        </button>
        <button
          onClick={() => downloadRsong(rsong, trackMutes, `${filenameBase}.rsong.json`)}
          className="secondary-player-btn"
        >
          Descargar RSong
        </button>
        <button
          onClick={() => downloadMidiFromRsong(rsong, trackMutes, `${filenameBase}.mid`)}
          className="secondary-player-btn"
        >
          Descargar MIDI
        </button>
        <button
          onClick={() => setShowDetails(true)}
          className="secondary-player-btn"
        >
          Ver detalles
        </button>
        <button
          onClick={() => {
            setShowDetails(false)
            setShowRsongTree(true)
          }}
          className="secondary-player-btn"
        >
          Ver rsong
        </button>
      </div>

      <div className="seek-wrap">
        <input
          type="range"
          min={0}
          max={duration}
          value={Math.min(currentTimeMs, duration)}
          onChange={handleSeek}
          className="seek-slider"
        />
        <div className="seek-progress" style={{ width: `${progress * 100}%` }} />
      </div>

      <section className="player-panel">
        <div className="tracks-header">
          <div className="panel-label">Tracks (session mutes)</div>
          <div className="track-actions">
            <button type="button" onClick={() => handleMuteAll(false)} className="tiny-btn">todas</button>
            <button type="button" onClick={() => handleMuteAll(true)} className="tiny-btn">ninguna</button>
          </div>
        </div>
        <div className="track-grid">
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
                  onClick={() => handleTrackToggle(id)}
                  disabled={isAudioLoading}
                  className={`track-chip ${muted ? 'muted' : ''}`}
                >
                  {trackShortLabel(track)} <span>{count}</span>
                </button>
              )
            })}
        </div>
      </section>

      {showDetails && (
        <div className="details-modal-backdrop" onClick={() => setShowDetails(false)}>
          <div className="details-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="details-modal-header">
              <h3>Detalles técnicos</h3>
              <button type="button" className="tiny-btn" onClick={() => setShowDetails(false)}>
                cerrar
              </button>
            </div>
            <div className="meta-grid">
              <div><strong>Tempo:</strong> {meta?.bpm || rsong.header?.bpm} BPM</div>
              <div><strong>Tonalidad:</strong> {detailKey || '—'}</div>
              <div><strong>Modo:</strong> {detailMode || '—'}</div>
              <div><strong>Compás:</strong> {detailMeter || '—'}</div>
              <div><strong>Arquetipo:</strong> {detailArchetype || '—'}</div>
              <div><strong>Patrón:</strong> {detailPattern || '—'}</div>
              <div><strong>Duración:</strong> {formatTime(meta?.duration_ms || duration)}</div>
              <div><strong>Validación:</strong> {detailValidation ?? '—'}</div>
              <div><strong>Conocimiento:</strong> {detailKnowledge || '—'}</div>
              <div><strong>Secciones:</strong> {(detailSections || []).join(' · ') || '—'}</div>
              <div><strong>Puntos de entrada:</strong> {(rsong.game_meta?.cue_points || []).length}</div>
              <div><strong>Instrumentos activos:</strong> {(detailActiveInstruments || []).join(', ') || '—'}</div>
            </div>
          </div>
        </div>
      )}

      {showRsongTree && (
        <div className="details-modal-backdrop rsong-modal-backdrop" onClick={() => setShowRsongTree(false)}>
          <div className="details-modal-card rsong-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="details-modal-header">
              <h3>RSong (árbol JSON)</h3>
              <button type="button" className="tiny-btn" onClick={() => setShowRsongTree(false)}>
                cerrar
              </button>
            </div>
            <div className="rsong-modal-body">
              <div className="json-tree cadence-scrollbar">
                <JsonTreeNode nodeKey="rsong" value={rsong} defaultOpen />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
