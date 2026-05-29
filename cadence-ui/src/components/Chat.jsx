import { useState, useRef, useEffect } from 'react'
import { useCadenceStore } from '../store'

const SUGGESTIONS = [
  'canción agresiva para un boss fight techno dubstep',
  'loop ambiental para un mapa de exploración espacial',
  'tema energético para pantalla de victoria arcade',
  'melodía oscura para cinemática de villano',
]

function Message({ msg }) {
  const isUser = msg.role === 'user'
  const isSystem = msg.role === 'system'

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

export default function Chat({ onResult }) {
  const [input, setInput] = useState('')
  const { messages, isGenerating, addMessage, setGenerating, setResult } =
    useCadenceStore()
  const bottomRef = useRef(null)
  const inputRef  = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isGenerating])

  useEffect(() => {
    if (messages.length === 0) {
      addMessage('system',
        'bienvenido a cadence.\ndescribe la canción que necesitas\n' +
        'o usa uno de los ejemplos de abajo.'
      )
    }
  }, [])

  async function handleSubmit(prompt) {
    const text = (prompt || input).trim()
    if (!text || isGenerating) return

    setInput('')
    addMessage('user', text)
    setGenerating(true)
    addMessage('agent', 'analizando tu solicitud...')

    try {
      const res = await fetch('/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: text }),
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'error desconocido')
      }

      const data = await res.json()

      // Reemplazar el mensaje "analizando..." con el resultado
      useCadenceStore.setState(s => ({
        messages: s.messages.slice(0, -1).concat({
          role: 'agent',
          content:
            `✓ canción generada\n` +
            `  bpm        : ${data.bpm}\n` +
            `  tonalidad  : ${data.key}\n` +
            `  secciones  : ${data.sections.join(' → ')}\n` +
            `  duración   : ${(data.duration_ms / 1000).toFixed(1)}s\n` +
            `  score      : ${data.validation_score}`,
          id: Date.now(),
        })
      }))

      setResult(data.rsong, {
        bpm: data.bpm,
        key: data.key,
        sections: data.sections,
        duration_ms: data.duration_ms,
        knowledge_level: data.knowledge_level,
        validation_score: data.validation_score,
      })

      onResult?.()

    } catch (err) {
      useCadenceStore.setState(s => ({
        messages: s.messages.slice(0, -1).concat({
          role: 'system',
          content: `✗ error: ${err.message}`,
          id: Date.now(),
        })
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
      height: '100%', padding: '24px',
    }}>

      {/* Header */}
      <div style={{
        fontFamily: 'Syne, sans-serif',
        fontSize: '22px', fontWeight: 800,
        letterSpacing: '-0.02em',
        marginBottom: '20px',
        background: 'linear-gradient(135deg, #ff4d6d, #7c3aed)',
        WebkitBackgroundClip: 'text',
        WebkitTextFillColor: 'transparent',
      }}>
        cadence
      </div>

      {/* Messages */}
      <div style={{
        flex: 1, overflowY: 'auto',
        paddingRight: '4px',
        scrollbarWidth: 'thin',
        scrollbarColor: 'var(--border) transparent',
      }}>
        {messages.map(msg => <Message key={msg.id} msg={msg} />)}
        {isGenerating && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* Suggestions */}
      {messages.length <= 2 && !isGenerating && (
        <div style={{
          display: 'flex', flexWrap: 'wrap', gap: '6px',
          marginBottom: '12px',
        }}>
          {SUGGESTIONS.map(s => (
            <button key={s} onClick={() => handleSubmit(s)} style={{
              background: 'var(--surface2)',
              border: '1px solid var(--border)',
              borderRadius: '2px',
              padding: '5px 10px',
              fontSize: '11px',
              fontFamily: 'Space Mono, monospace',
              color: 'var(--muted)',
              cursor: 'pointer',
              transition: 'border-color 0.2s, color 0.2s',
            }}
            onMouseEnter={e => {
              e.target.style.borderColor = 'var(--accent2)'
              e.target.style.color = 'var(--text)'
            }}
            onMouseLeave={e => {
              e.target.style.borderColor = 'var(--border)'
              e.target.style.color = 'var(--muted)'
            }}>
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
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
          onFocus={e => e.target.style.borderColor = 'var(--accent2)'}
          onBlur={e  => e.target.style.borderColor = 'var(--border)'}
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
