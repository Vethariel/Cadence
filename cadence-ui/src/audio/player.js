import { useCadenceStore } from '../store'
import { resolveGmProgram } from './gm-programs'
import {
  effectiveTrackVolumeDb,
  effectiveVelocity,
} from './section-gain'
import {
  buildMasterBus,
  createSpessaSynth,
  destroySpessaSynth,
  getAudioContext,
  scheduleNote,
  setupChannel,
} from './spessa-engine'

const DEFAULT_VOL = { lead: -4, bass: -2, rhythm: -6, pad: -10, fx: -8 }
const PLAYBACK_LOOKAHEAD = 0.08

const PAN = {
  melody: 0,
  countermelody: 0.35,
  echo_synth: -0.3,
  arp_synth: 0.45,
  bass: -0.05,
  pad: 0,
  drums: 0,
  perc_aux: 0.25,
  fx_riser: 0,
  chord_stab: 0.15,
}

let timerId = null
let masterBus = null
let synth = null
let playbackStartTime = 0
let loadingPromise = null
let activeRsong = null

function trackVolumeDb(track, rsong) {
  const layers = rsong?.game_meta?.arrangement?.layers
  const layer = layers?.find(l => l.instrument_id === (track.instrument_id || track.id))
  return layer?.mix_level ?? DEFAULT_VOL[track.role] ?? -8
}

function trackPan(track) {
  return PAN[track.instrument_id || track.id] ?? 0
}

function isDrumTrack(track) {
  return track.role === 'rhythm'
    || track.instrument_id === 'drums'
    || track.instrument_id === 'perc_aux'
}

function resolveChannel(track) {
  if (isDrumTrack(track)) return 9
  const ch = track.midi_channel ?? 0
  return Math.min(15, Math.max(0, ch))
}

function isTrackMutedById(instrumentId) {
  return !!useCadenceStore.getState().trackMutes[instrumentId]
}

function shouldScheduleTrack(track) {
  const id = track.instrument_id || track.id
  return !isTrackMutedById(id)
}

function scheduleRsongTrack(synthInstance, track, rsong, startTime, startAtMs = 0) {
  const channel = resolveChannel(track)
  const instrumentId = track.instrument_id || track.id
  let lastSection = null

  for (const event of track.events) {
    if (event.type === 'rest') continue
    const eventStartMs = event.t
    const eventEndMs = event.t + event.duration_ms
    if (eventEndMs <= startAtMs) continue

    const section = event.section || 'drop'
    const normalizedStartMs = Math.max(startAtMs, eventStartMs) - startAtMs
    const trimMs = Math.max(0, startAtMs - eventStartMs)
    const t = startTime + normalizedStartMs / 1000

    if (section !== lastSection) {
      setupChannel(synthInstance, channel, {
        program: isDrumTrack(track) ? null : (track.gm_program ?? resolveGmProgram(instrumentId, track.role)),
        isDrum: isDrumTrack(track),
        volumeDb: effectiveTrackVolumeDb(
          track, rsong, section, trackVolumeDb(track, rsong),
        ),
        pan: trackPan(track),
        time: t,
      })
      lastSection = section
    }

    const dur = Math.max(0.04, (event.duration_ms - trimMs) / 1000)
    const vel = effectiveVelocity(event.velocity, section, rsong)
    scheduleNote(synthInstance, channel, event.pitch, vel, t, dur)
  }
}

export function getAnalyser() {
  return masterBus ?? null
}

export async function startPlayback(rsong, { startAtMs = 0 } = {}) {
  if (loadingPromise) return loadingPromise
  loadingPromise = _startRsong(rsong, startAtMs)
  try {
    await loadingPromise
  } finally {
    loadingPromise = null
  }
}

function _beginTransport(durationMs, startAtMs) {
  const ctx = getAudioContext()
  timerId = setInterval(() => {
    const ms = Math.max(0, startAtMs + (ctx.currentTime - playbackStartTime) * 1000)
    useCadenceStore.getState().setCurrentTime(ms)
    if (ms >= durationMs) {
      stopPlayback()
      useCadenceStore.getState().setPlaying(false)
    }
  }, 50)
  useCadenceStore.getState().setPlaying(true)
  useCadenceStore.getState().setPaused(false)
}

async function _startSession({ durationMs, schedule, startAtMs = 0 }) {
  await stopPlayback()
  useCadenceStore.getState().setAudioLoading(true)
  try {
    const ctx = getAudioContext()
    if (ctx.state !== 'running') await ctx.resume()

    masterBus = buildMasterBus(ctx)
    synth = await createSpessaSynth(masterBus.comp)

    playbackStartTime = ctx.currentTime + PLAYBACK_LOOKAHEAD
    schedule(synth, playbackStartTime)
    _beginTransport(durationMs, startAtMs)
  } finally {
    useCadenceStore.getState().setAudioLoading(false)
  }
}

async function _startRsong(rsong, startAtMs = 0) {
  activeRsong = rsong
  const sorted = [...rsong.tracks]
    .filter(shouldScheduleTrack)
    .sort((a, b) => {
      const ord = { rhythm: 0, bass: 1, pad: 2, lead: 3, fx: 4 }
      return (ord[a.role] ?? 2) - (ord[b.role] ?? 2)
    })

  await _startSession({
    durationMs: rsong.header.duration_ms,
    startAtMs,
    schedule: (synthInstance, startTime) => {
      for (const track of sorted) {
        scheduleRsongTrack(synthInstance, track, rsong, startTime, startAtMs)
      }
    },
  })
}

export async function pausePlayback() {
  if (!useCadenceStore.getState().isPlaying) return
  if (timerId) {
    clearInterval(timerId)
    timerId = null
  }
  const ctx = getAudioContext()
  const current = useCadenceStore.getState().currentTimeMs
  useCadenceStore.getState().setCurrentTime(current)
  await ctx.suspend()
  useCadenceStore.getState().setPlaying(false)
  useCadenceStore.getState().setPaused(true)
}

export async function resumePlayback() {
  if (!useCadenceStore.getState().isPaused) return
  const ctx = getAudioContext()
  await ctx.resume()
  const currentOffset = Math.max(0, useCadenceStore.getState().currentTimeMs)
  playbackStartTime = ctx.currentTime
  _beginTransport(activeRsong?.header?.duration_ms || Infinity, currentOffset)
}

export async function seekTo(ms) {
  const state = useCadenceStore.getState()
  const rsong = state.rsong || activeRsong
  if (!rsong) return
  const duration = rsong.header?.duration_ms || 0
  const next = Math.max(0, Math.min(ms, duration))
  state.setCurrentTime(next)
  if (state.isPlaying || state.isPaused) {
    await startPlayback(rsong, { startAtMs: next })
  }
}

export async function stopPlayback() {
  if (timerId) {
    clearInterval(timerId)
    timerId = null
  }

  destroySpessaSynth(synth)
  synth = null
  playbackStartTime = 0

  if (masterBus) {
    try {
      masterBus.comp.disconnect()
      masterBus.gain.disconnect()
      masterBus.analyser.disconnect()
    } catch { /* noop */ }
    masterBus = null
  }
  activeRsong = null

  useCadenceStore.getState().reset()
}
