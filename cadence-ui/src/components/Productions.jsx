import { useEffect } from 'react'
import { useCadenceStore } from '../store'
import { startPlayback, stopPlayback } from '../audio/player'

function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleString(undefined, {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
  })
}

function formatDuration(ms) {
  if (!ms) return '—'
  const s = Math.floor(ms / 1000)
  const m = Math.floor(s / 60)
  return `${m}:${String(s % 60).padStart(2, '0')}`
}

export default function Productions() {
  const {
    productions,
    productionsLoading,
    productionsError,
    currentProductionId,
    loadProductions,
    selectProduction,
  } = useCadenceStore()

  useEffect(() => {
    loadProductions()
  }, [loadProductions])

  async function handleSelect(filename) {
    await stopPlayback()
    const ok = await selectProduction(filename)
    if (!ok) return
    const { rsong } = useCadenceStore.getState()
    if (rsong) {
      await startPlayback(rsong, { startAtMs: 0 })
    }
  }

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100%', padding: '24px',
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: '20px',
      }}>
        <div>
          <div style={{
            fontFamily: 'var(--font-display)',
            fontSize: '22px', fontWeight: 800,
            letterSpacing: '0.04em',
            textTransform: 'uppercase',
            background: 'linear-gradient(135deg, var(--accent3), var(--accent2))',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}>
            mis producciones
          </div>
          <div style={{
            fontFamily: 'Space Mono, monospace',
            fontSize: '11px', color: 'var(--muted)', marginTop: '4px',
          }}>
            outputs en /output para reproducir y exportar
          </div>
        </div>
      </div>

      <button
        onClick={() => loadProductions()}
        disabled={productionsLoading}
        style={{
          alignSelf: 'flex-start',
          marginBottom: '16px',
          background: 'transparent',
          border: '1px solid var(--border)',
          borderRadius: '4px',
          padding: '5px 12px',
          color: 'var(--muted)',
          fontFamily: 'Space Mono, monospace',
          fontSize: '11px',
          cursor: productionsLoading ? 'wait' : 'pointer',
        }}
      >
        {productionsLoading ? 'cargando…' : '↻ actualizar'}
      </button>

      {productionsError && (
        <div style={{
          padding: '10px 14px', marginBottom: '12px',
          background: 'rgba(255,77,109,0.1)',
          border: '1px solid rgba(255,77,109,0.3)',
          borderRadius: '4px',
          fontFamily: 'Space Mono, monospace',
          fontSize: '12px', color: '#ff4d6d',
        }}>
          {productionsError}
        </div>
      )}

      <div className="cadence-scrollbar" style={{
        flex: 1, overflowY: 'auto',
        display: 'flex', flexDirection: 'column', gap: '8px',
      }}>
        {!productionsLoading && productions.length === 0 && (
          <div style={{
            fontFamily: 'Space Mono, monospace',
            fontSize: '12px', color: 'var(--muted)',
            padding: '24px 0', textAlign: 'center',
          }}>
            aún no hay producciones.
            <br />
            genera una canción desde el chat.
          </div>
        )}

        {productions.map((p) => {
          const active = p.id === currentProductionId
          return (
            <button
              key={p.id}
              onClick={() => handleSelect(p.id)}
              className={`production-card ${active ? 'active' : ''}`}
            >
              <div className="production-card-header">
                <span className="production-card-title">
                  {p.title || p.filename}
                </span>
                <span className="production-card-date">
                  {formatDate(p.created_at)}
                </span>
              </div>
              <div className="production-card-meta">
                <span>{p.bpm} BPM</span>
                <span>{p.key || '—'}</span>
                <span>{formatDuration(p.duration_ms)}</span>
              </div>
              <div className="production-card-meta production-card-meta-secondary">
                <span>{p.track_count} tracks</span>
                {p.validation_score != null && (
                  <span>score {p.validation_score.toFixed(2)}</span>
                )}
                <span style={{ color: p.has_midi ? 'var(--accent3)' : 'var(--muted)' }}>
                  {p.has_midi ? '✓ midi' : 'midi on play'}
                </span>
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
