import { create } from 'zustand'
import { fetchProductions, fetchProduction } from './api'
import { uid } from './uid'

function buildTrackMutes(rsong) {
  const trackMutes = {}
  for (const t of rsong?.tracks || []) {
    const id = t.instrument_id || t.id
    trackMutes[id] = false
  }
  return trackMutes
}

export const useCadenceStore = create((set, get) => ({
  // App shell
  appScreen: 'landing', // 'landing' | 'studio'
  leftPaneView: 'chat', // 'chat' | 'productions'

  // Chat
  messages: [],
  isGenerating: false,

  // Resultado activo
  rsong: null,
  meta: null,
  currentProductionId: null,

  // Mis producciones
  productions: [],
  productionsLoading: false,
  productionsError: null,

  // Reproductor
  isPlaying: false,
  isPaused: false,
  isAudioLoading: false,
  currentTimeMs: 0,
  activeSection: null,
  /** instrument_id → true si la pista está silenciada */
  trackMutes: {},

  enterStudio: () => set({ appScreen: 'studio' }),
  showLanding: () => set({ appScreen: 'landing' }),
  setLeftPaneView: (leftPaneView) => set({ leftPaneView }),

  addMessage: (role, content) =>
    set((s) => ({
      messages: [...s.messages, { role, content, id: uid() }],
    })),

  addMessageWithMeta: (role, content, extra = {}) =>
    set((s) => ({
      messages: [...s.messages, { role, content, id: uid(), ...extra }],
    })),

  setGenerating: (v) => set({ isGenerating: v }),

  setResult: (rsong, meta, productionId = null) => {
    const trackMutes = buildTrackMutes(rsong)
    return set({
      rsong,
      meta,
      currentProductionId: productionId,
      trackMutes,
      currentTimeMs: 0,
      activeSection: null,
      isPaused: false,
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
      const trackMutes = buildTrackMutes(rsong)
      set({
        rsong,
        meta: {
          title: header.title,
          bpm: header.bpm,
          key: header.key,
          mode: header.mode,
          meter: header.meter,
          archetype: rsong.game_meta?.policy?.archetype,
          pattern_id: rsong.game_meta?.policy?.pattern_id,
          active_instruments: rsong.game_meta?.arrangement?.active_instruments || [],
          sections: rsong.game_meta?.sections || [],
          duration_ms: header.duration_ms,
          validation_score: rsong.validation?.score,
          knowledge_level: rsong.game_meta?.knowledge_level,
        },
        currentProductionId: filename,
        trackMutes,
        productionsLoading: false,
        currentTimeMs: 0,
        activeSection: null,
        isPaused: false,
      })
      return true
    } catch (e) {
      set({ productionsError: e.message, productionsLoading: false })
      return false
    }
  },

  setPlaying: (v) => set({ isPlaying: v }),
  setPaused: (v) => set({ isPaused: v }),

  setAudioLoading: (v) => set({ isAudioLoading: v }),

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
    isPaused: false,
    isAudioLoading: false,
    currentTimeMs: 0,
    activeSection: null,
  }),
}))
