import { useState, useRef, useEffect } from 'react'
import { useCadenceStore } from '../store'
import { generateSong } from '../api'
import { uid } from '../uid'
import { startPlayback, stopPlayback } from '../audio/player'

const FALLBACK_SUGGESTIONS = [
  {
    id: 'sparse_loop',
    label: 'Loop ambiente',
    archetype: 'sparse_loop',
    prompt:
      'Loop de exploración overworld: ambiente calmado, pads y drones, melodía espaciada, poca percusión, música de fondo que se repite sin climax de combate.',
  },
  {
    id: 'moderate_cinematic',
    label: 'Cutscene moderada',
    archetype: 'moderate_cinematic',
    prompt:
      'Cutscene narrativa moderada: tensión contenida, melodía clara sin fraseo de batalla denso, armonía que acompaña el diálogo, pasillo o región misteriosa, sin edm ni victoria arcade.',
  },
  {
    id: 'dense_dance',
    label: 'Battle dance denso',
    archetype: 'dense_dance',
    prompt:
      'Combate arcade o victoria: melodía muy densa y rápida, muchas notas por compás, saltos amplios, energía alta estilo chiptune o eurobeat, sin techno ni dubstep ni orquesta épica.',
  },
  {
    id: 'energetic_game',
    label: 'Boss compacto',
    archetype: 'energetic_game',
    prompt:
      'Pelea de jefe en plataforma: orquestación compacta, pocos instrumentos a la vez, melodía urgente y directa, acción constante, sin chiptune ni eurobeat ni capas orquestales masivas.',
  },
  {
    id: 'boss_orchestral',
    label: 'Boss orquestal',
    archetype: 'boss_orchestral',
    prompt:
      'Boss fight orquestal épico: muchas capas simultáneas, registro amplio, tensión cinemática, melodía protagonista con densidad moderada, estilo confrontación final sin edm.',
  },
]

function Message({ msg, onPlay }) {
  const isUser = msg.role === 'user'
  const isSystem = msg.role === 'system'
  const canPlay = Boolean(msg.productionId) && !isUser && !isSystem

  return (
    <div style={{
      display: 'flex',
      justifyContent: isUser ? 'flex-end' : 'flex-start',
      marginBottom: '12px',
    }}>
      <div style={{
        maxWidth: '75%',
        padding: '10px 16px',
        borderRadius: '4px',
        background: isUser
          ? 'rgba(124,58,237,0.15)'
          : isSystem
            ? 'rgba(6,214,160,0.08)'
            : 'var(--surface2)',
        border: `1px solid ${
          isUser
            ? 'rgba(124,58,237,0.4)'
            : isSystem
              ? 'rgba(6,214,160,0.3)'
              : 'var(--border)'
        }`,
        fontFamily: 'Space Mono, monospace',
        fontSize: '13px',
        lineHeight: '1.7',
        color: isSystem ? 'var(--accent3)' : 'var(--text)',
        whiteSpace: 'pre-wrap',
      }}>
        {!isUser && (
          <span style={{
            fontSize: '10px',
            color: 'var(--muted)',
            display: 'block',
            marginBottom: '4px',
            letterSpacing: '0.15em',
            textTransform: 'uppercase',
          }}>
            {isSystem ? 'cadence' : 'agent'}
          </span>
        )}
        {msg.content}
        {canPlay && (
          <div style={{ marginTop: '10px' }}>
            <button
              type="button"
              onClick={() => onPlay(msg.productionId)}
              style={{
                background: 'rgba(124,58,237,0.2)',
                border: '1px solid rgba(124,58,237,0.5)',
                borderRadius: '4px',
                color: 'var(--accent4)',
                fontFamily: 'Space Mono, monospace',
                fontSize: '10px',
                cursor: 'pointer',
                padding: '4px 10px',
              }}
            >
              ▶ Play
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

function TypingIndicator() {
  return (
    <div style={{ display: 'flex', gap: '4px', padding: '10px 16px',
                  background: 'var(--surface2)', border: '1px solid var(--border)',
                  borderRadius: '4px', width: 'fit-content', marginBottom: '12px' }}>
      {[0, 1, 2].map(i => (
        <div key={i} style={{
          width: '6px', height: '6px', borderRadius: '50%',
          background: 'var(--accent2)',
          animation: `pulse 1.2s ease-in-out ${i * 0.2}s infinite`,
        }} />
      ))}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 0.3; transform: scale(0.8); }
          50%       { opacity: 1;   transform: scale(1.2); }
        }
      `}</style>
    </div>
  )
}

export default function Chat() {
  const [input, setInput] = useState('')
  const [suggestions, setSuggestions] = useState(FALLBACK_SUGGESTIONS)
  const {
    messages,
    isGenerating,
    addMessage,
    setGenerating,
    selectProduction,
    currentProductionId,
  } = useCadenceStore()
  const bottomRef = useRef(null)
  const inputRef = useRef(null)
  const welcomeInitializedRef = useRef(false)

  useEffect(() => {
    fetch('/benchmark-prompts')
      .then(r => (r.ok ? r.json() : null))
      .then(data => {
        if (data?.prompts?.length) {
          setSuggestions(data.prompts)
        }
      })
      .catch(() => {
        fetch('/benchmark_prompts.json')
          .then(r => (r.ok ? r.json() : null))
          .then(data => {
            if (data?.prompts?.length) setSuggestions(data.prompts)
          })
          .catch(() => {})
      })
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isGenerating])

  useEffect(() => {
    if (welcomeInitializedRef.current) return
    const hasWelcome = messages.some(
      (m) =>
        m.role === 'system' &&
        typeof m.content === 'string' &&
        m.content.includes('bienvenido a cadence.')
    )
    if (!hasWelcome) {
      addMessage(
        'system',
        'bienvenido a cadence.\ndescribe la canción que necesitas\n' +
          'o usa uno de los ejemplos de abajo.'
      )
    }
    welcomeInitializedRef.current = true
  }, [addMessage, messages])

  async function handlePlayFromHistory(productionId) {
    if (!productionId) return
    await stopPlayback()
    const state = useCadenceStore.getState()
    const needsLoad = state.currentProductionId !== productionId || !state.rsong
    if (needsLoad) {
      const ok = await selectProduction(productionId)
      if (!ok) return
    }
    const next = useCadenceStore.getState()
    if (next.rsong) {
      await startPlayback(next.rsong, { startAtMs: 0 })
    }
  }

  async function handleSubmit(prompt) {
    const text = (prompt || input).trim()
    if (!text || isGenerating) return

    setInput('')
    addMessage('user', text)
    setGenerating(true)
    addMessage('agent', 'analizando tu solicitud...')

    try {
      const data = await generateSong(text)
      const productionId = data.export_path?.split('/').pop() ?? currentProductionId
      const content =
        `✓ canción generada\n` +
        `  bpm        : ${data.bpm}\n` +
        `  tonalidad  : ${data.key}\n` +
        `  secciones  : ${data.sections.join(' → ')}\n` +
        `  duración   : ${(data.duration_ms / 1000).toFixed(1)}s\n` +
        `  score      : ${data.validation_score}`

      useCadenceStore.setState(s => ({
        messages: s.messages.slice(0, -1).concat({
          role: 'agent',
          content,
          productionId,
          id: uid(),
        }),
      }))

    } catch (err) {
      useCadenceStore.setState(s => ({
        messages: s.messages.slice(0, -1).concat({
          role: 'system',
          content: `✗ error: ${err.message}`,
          id: uid(),
        }),
      }))
    } finally {
      setGenerating(false)
      inputRef.current?.focus()
    }
  }

  function handleKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100%', padding: '18px',
    }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: '14px',
      }}>
        <div style={{
          fontFamily: 'var(--font-display)',
          fontSize: '22px', fontWeight: 800,
          letterSpacing: '0.04em',
          textTransform: 'uppercase',
          background: 'linear-gradient(135deg, var(--accent1), var(--accent2))',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
        }}>
          cadence
        </div>
        <div style={{
          fontFamily: 'Space Mono, monospace',
          fontSize: '10px',
          color: 'var(--muted)',
        }}>
          studio chat
        </div>
      </div>

      <div style={{
        flex: 1, overflowY: 'auto',
        paddingRight: '4px',
        scrollbarWidth: 'thin',
        scrollbarColor: 'var(--border) transparent',
      }}>
        {messages.map(msg => (
          <Message key={msg.id} msg={msg} onPlay={handlePlayFromHistory} />
        ))}
        {isGenerating && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {messages.length <= 2 && !isGenerating && (
        <div style={{
          display: 'flex', flexWrap: 'wrap', gap: '6px',
          marginBottom: '12px',
        }}>
          {suggestions.map(s => (
            <button
              key={s.id || s.prompt}
              title={s.prompt}
              onClick={() => handleSubmit(s.prompt)}
              style={{
                background: 'var(--surface2)',
                border: '1px solid var(--border)',
                borderRadius: '2px',
                padding: '5px 10px',
                fontSize: '11px',
                fontFamily: 'Space Mono, monospace',
                color: 'var(--muted)',
                cursor: 'pointer',
                transition: 'border-color 0.2s, color 0.2s',
                textAlign: 'left',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.borderColor = 'var(--accent2)'
                e.currentTarget.style.color = 'var(--text)'
              }}
              onMouseLeave={e => {
                e.currentTarget.style.borderColor = 'var(--border)'
                e.currentTarget.style.color = 'var(--muted)'
              }}
            >
              <span style={{ color: 'var(--accent3)', marginRight: '6px' }}>
                {s.archetype}
              </span>
              {s.label || s.id}
            </button>
          ))}
        </div>
      )}

      <div style={{
        display: 'flex', gap: '8px',
        borderTop: '1px solid var(--border)',
        paddingTop: '16px',
      }}>
        <textarea
          ref={inputRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKey}
          disabled={isGenerating}
          placeholder="describe tu canción..."
          rows={2}
          style={{
            flex: 1,
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: '4px',
            padding: '10px 14px',
            color: 'var(--text)',
            fontFamily: 'Space Mono, monospace',
            fontSize: '13px',
            resize: 'none',
            outline: 'none',
            transition: 'border-color 0.2s',
          }}
          onFocus={e => {
            e.target.style.borderColor = 'var(--accent2)'
          }}
          onBlur={e => {
            e.target.style.borderColor = 'var(--border)'
          }}
        />
        <button
          onClick={() => handleSubmit()}
          disabled={isGenerating || !input.trim()}
          style={{
            background: isGenerating
              ? 'var(--surface2)'
              : 'linear-gradient(135deg, var(--accent2), var(--accent1))',
            border: 'none',
            borderRadius: '4px',
            padding: '0 20px',
            color: 'var(--text)',
            fontFamily: 'Space Mono, monospace',
            fontSize: '12px',
            cursor: isGenerating ? 'not-allowed' : 'pointer',
            opacity: isGenerating || !input.trim() ? 0.5 : 1,
            transition: 'opacity 0.2s',
            letterSpacing: '0.05em',
          }}>
          {isGenerating ? '...' : 'gen →'}
        </button>
      </div>
    </div>
  )
}
