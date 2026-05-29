import { useState } from 'react'
import { useCadenceStore } from './store'
import Chat from './components/Chat'
import './index.css'

export default function App() {
  const rsong = useCadenceStore(s => s.rsong)
  const [showVisualizer, setShowVisualizer] = useState(false)

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: rsong && showVisualizer ? '380px 1fr' : '480px',
      justifyContent: 'center',
      height: '100vh',
      background: 'var(--bg)',
      transition: 'grid-template-columns 0.4s ease',
    }}>

      {/* Panel izquierdo: chat */}
      <div style={{
        borderRight: rsong && showVisualizer
          ? '1px solid var(--border)' : 'none',
        height: '100vh',
        overflow: 'hidden',
      }}>
        <Chat onResult={() => setShowVisualizer(true)} />
      </div>

      {/* Panel derecho: visualizador (placeholder hasta paso 14) */}
      {rsong && showVisualizer && (
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexDirection: 'column', gap: '12px',
        }}>
          <p style={{
            color: 'var(--accent3)',
            fontFamily: 'Space Mono, monospace',
            fontSize: '13px',
          }}>
            visualizador — paso 14
          </p>
          <button
            onClick={() => setShowVisualizer(false)}
            style={{
              background: 'transparent',
              border: '1px solid var(--border)',
              borderRadius: '4px',
              padding: '6px 14px',
              color: 'var(--muted)',
              fontFamily: 'Space Mono, monospace',
              fontSize: '11px',
              cursor: 'pointer',
            }}>
            ← volver al chat
          </button>
        </div>
      )}
    </div>
  )
}
