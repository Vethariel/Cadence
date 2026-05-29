import { useState } from 'react'
import { useCadenceStore } from './store'
import Chat from './components/Chat'
import Player from './components/Player'
import Visualizer from './components/Visualizer'
import FrequencyAnalyzer from './components/FrequencyAnalyzer'
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

      <div style={{
        borderRight: rsong && showVisualizer
          ? '1px solid var(--border)' : 'none',
        height: '100vh', overflow: 'hidden',
      }}>
        <Chat onResult={() => setShowVisualizer(true)} />
      </div>

      {rsong && showVisualizer && (
        <div style={{
          position: 'relative',
          height: '100vh',
          overflow: 'hidden',
        }}>
          <Visualizer />

          {/* Analizador de frecuencias — esquina superior derecha */}
          <FrequencyAnalyzer />

          <button
            onClick={() => setShowVisualizer(false)}
            style={{
              position: 'absolute', top: '16px', left: '16px',
              zIndex: 20,
              background: 'rgba(10,10,15,0.7)',
              backdropFilter: 'blur(8px)',
              border: '1px solid var(--border)',
              borderRadius: '4px',
              padding: '6px 14px',
              color: 'var(--muted)',
              fontFamily: 'Space Mono, monospace',
              fontSize: '11px', cursor: 'pointer',
            }}>
            ← chat
          </button>

          <Player />
        </div>
      )}
    </div>
  )
}
