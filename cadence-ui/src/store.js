import { create } from 'zustand'

export const useCadenceStore = create((set) => ({
  // Estado del chat
  messages: [],
  isGenerating: false,

  // Resultado del agente
  rsong: null,
  meta: null,

  // Estado del reproductor
  isPlaying: false,
  currentTimeMs: 0,
  activeSection: null,

  // Acciones
  addMessage: (role, content) =>
    set((s) => ({
      messages: [...s.messages, { role, content, id: Date.now() }],
    })),

  setGenerating: (v) => set({ isGenerating: v }),

  setResult: (rsong, meta) => set({ rsong, meta }),

  setPlaying: (v) => set({ isPlaying: v }),

  setCurrentTime: (ms) => {
    set((s) => {
      if (!s.rsong) return {}
      const cues = s.rsong.game_meta.cue_points
      const active = [...cues]
        .reverse()
        .find((c) => ms >= c.t)
      return {
        currentTimeMs: ms,
        activeSection: active ? active.label : null,
      }
    })
  },

  reset: () => set({
    isPlaying: false,
    currentTimeMs: 0,
    activeSection: null,
  }),
}))
