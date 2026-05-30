import { create } from 'zustand'
import { fetchProductions, fetchProduction } from './api'
import { uid } from './uid'

export const useCadenceStore = create((set, get) => ({
  // Chat
  messages: [],
  isGenerating: false,

  // Resultado activo
  rsong: null,
  meta: null,
  currentProductionId: null,

  // Mis producciones
  view: 'chat', // 'chat' | 'productions'
  productions: [],
  productionsLoading: false,
  productionsError: null,

  // Reproductor
  isPlaying: false,
  isAudioLoading: false,
  playbackSource: 'rsong', // 'rsong' | 'midi'
  currentTimeMs: 0,
  activeSection: null,
  /** instrument_id → true si la pista está silenciada */
  trackMutes: {},

  addMessage: (role, content) =>
    set((s) => ({
      messages: [...s.messages, { role, content, id: uid() }],
    })),

  setGenerating: (v) => set({ isGenerating: v }),

  setView: (view) => set({ view }),

  setResult: (rsong, meta, productionId = null) => {
    const trackMutes = {}
    for (const t of rsong?.tracks || []) {
      const id = t.instrument_id || t.id
      trackMutes[id] = false
    }
    return set({
      rsong,
      meta,
      currentProductionId: productionId,
      playbackSource: 'rsong',
      trackMutes,
    })
  },

  loadProductions: async () => {
    set({ productionsLoading: true, productionsError: null })
    try {
      const productions = await fetchProductions()
      set({ productions, productionsLoading: false })
    } catch (e) {
      set({ productionsError: e.message, productionsLoading: false })
    }
  },

  selectProduction: async (filename) => {
    set({ productionsLoading: true, productionsError: null })
    try {
      const rsong = await fetchProduction(filename)
      const header = rsong.header || {}
      const trackMutes = {}
      for (const t of rsong?.tracks || []) {
        const id = t.instrument_id || t.id
        trackMutes[id] = false
      }
      set({
        rsong,
        meta: {
          bpm: header.bpm,
          key: header.key,
          sections: rsong.game_meta?.sections || [],
          duration_ms: header.duration_ms,
          validation_score: rsong.validation?.score,
        },
        currentProductionId: filename,
        playbackSource: 'rsong',
        trackMutes,
        productionsLoading: false,
        view: 'chat',
      })
      return true
    } catch (e) {
      set({ productionsError: e.message, productionsLoading: false })
      return false
    }
  },

  setPlaying: (v) => set({ isPlaying: v }),

  setAudioLoading: (v) => set({ isAudioLoading: v }),

  setPlaybackSource: (playbackSource) => set({ playbackSource }),

  toggleTrackMute: (trackId) => set((s) => ({
    trackMutes: {
      ...s.trackMutes,
      [trackId]: !s.trackMutes[trackId],
    },
  })),

  setAllTrackMutes: (muted) => set((s) => {
    const next = { ...s.trackMutes }
    for (const id of Object.keys(next)) {
      next[id] = muted
    }
    return { trackMutes: next }
  }),

  isTrackMuted: (trackId) => !!get().trackMutes[trackId],

  setCurrentTime: (ms) => {
    set((s) => {
      if (!s.rsong) return {}
      const cues = s.rsong.game_meta?.cue_points || []
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
    isAudioLoading: false,
    currentTimeMs: 0,
    activeSection: null,
  }),
}))
