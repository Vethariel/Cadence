import { useEffect } from 'react'
import { useCadenceStore } from '../store'

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

export default function Productions({ onSelect }) {
  const {
    productions,
    productionsLoading,
    productionsError,
    currentProductionId,
    loadProductions,
    selectProduction,
    setView,
  } = useCadenceStore()

  useEffect(() => {
    loadProductions()
  }, [loadProductions])

  async function handleSelect(filename) {
    const ok = await selectProduction(filename)
    if (ok) onSelect?.()
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
            fontFamily: 'Syne, sans-serif',
            fontSize: '22px', fontWeight: 800,
            background: 'linear-gradient(135deg, #06d6a0, #7c3aed)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}>
            mis producciones
          </div>
          <div style={{
            fontFamily: 'Space Mono, monospace',
            fontSize: '11px', color: 'var(--muted)', marginTop: '4px',
          }}>
            outputs en /output — comparar .rsong vs .mid
          </div>
        </div>
        <button
          onClick={() => setView('chat')}
          style={{
            background: 'var(--surface2)',
            border: '1px solid var(--border)',
            borderRadius: '4px',
            padding: '6px 12px',
            color: 'var(--muted)',
            fontFamily: 'Space Mono, monospace',
            fontSize: '11px',
            cursor: 'pointer',
          }}
        >
          ← chat
        </button>
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

      <div style={{
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
              style={{
                textAlign: 'left',
                background: active ? 'rgba(124,58,237,0.12)' : 'var(--surface2)',
                border: `1px solid ${active ? 'rgba(124,58,237,0.5)' : 'var(--border)'}`,
                borderRadius: '6px',
                padding: '14px 16px',
                cursor: 'pointer',
                transition: 'border-color 0.2s, background 0.2s',
              }}
            >
              <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
                marginBottom: '6px',
              }}>
                <span style={{
                  fontFamily: 'Syne, sans-serif',
                  fontSize: '14px', fontWeight: 700,
                  color: active ? 'var(--accent2)' : 'var(--text)',
                }}>
                  {p.title || p.filename}
                </span>
                <span style={{
                  fontFamily: 'Space Mono, monospace',
                  fontSize: '10px', color: 'var(--muted)',
                }}>
                  {formatDate(p.created_at)}
                </span>
              </div>
              <div style={{
                fontFamily: 'Space Mono, monospace',
                fontSize: '11px', color: 'var(--muted)',
                display: 'flex', flexWrap: 'wrap', gap: '12px',
              }}>
                <span>{p.bpm} BPM</span>
                <span>{p.key}</span>
                <span>{formatDuration(p.duration_ms)}</span>
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
