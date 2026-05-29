import { useCadenceStore } from '../store'
import { resolveGmProgram, resolveInstrumentId } from './gm-programs'
import {
  effectiveTrackVolumeDb,
  effectiveVelocity,
  sectionAtTimeMs,
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

function findRsongTrack(rsong, instrumentId) {
  return rsong?.tracks?.find(t => (t.instrument_id || t.id) === instrumentId)
}

function scheduleRsongTrack(synthInstance, track, rsong, startTime) {
  const channel = resolveChannel(track)
  const instrumentId = track.instrument_id || track.id
  let lastSection = null

  for (const event of track.events) {
    if (event.type === 'rest') continue

    const section = event.section || 'drop'
    const t = startTime + event.t / 1000

    if (section !== lastSection) {
      setupChannel(synthInstance, channel, {
        program: isDrumTrack(track) ? null : resolveGmProgram(instrumentId, track.role),
        isDrum: isDrumTrack(track),
        volumeDb: effectiveTrackVolumeDb(
          track, rsong, section, trackVolumeDb(track, rsong),
        ),
        pan: trackPan(track),
        time: t,
      })
      lastSection = section
    }

    const dur = Math.max(0.04, event.duration_ms / 1000)
    const vel = effectiveVelocity(event.velocity, section, rsong)
    scheduleNote(synthInstance, channel, event.pitch, vel, t, dur)
  }
}

function scheduleMidiTrack(synthInstance, track, rsong, startTime) {
  if (!track.notes.length) return

  const instrumentId = resolveInstrumentId(track.name)
  const isDrum = track.channel === 9
    || instrumentId === 'drums'
    || instrumentId === 'perc_aux'
    || (track.name || '').toLowerCase().includes('drum')
    || (track.name || '').toLowerCase().includes('perc')

  const channel = isDrum ? 9 : (track.channel ?? 0)
  const rsongTrack = findRsongTrack(rsong, instrumentId)
  const role = rsongTrack?.role ?? (isDrum ? 'rhythm' : 'lead')
  const baseDb = rsongTrack
    ? trackVolumeDb(rsongTrack, rsong)
    : (isDrum ? DEFAULT_VOL.rhythm : DEFAULT_VOL.lead)

  let lastSection = null

  for (const note of track.notes) {
    const section = sectionAtTimeMs(note.time * 1000, rsong)
    const t = startTime + note.time

    if (section !== lastSection) {
      setupChannel(synthInstance, channel, {
        program: isDrum ? null : resolveGmProgram(instrumentId, role),
        isDrum,
        volumeDb: effectiveTrackVolumeDb(
          rsongTrack ?? { role, instrument_id: instrumentId },
          rsong,
          section,
          baseDb,
        ),
        pan: trackPan({ instrument_id: instrumentId }),
        time: t,
      })
      lastSection = section
    }

    scheduleNote(
      synthInstance,
      channel,
      note.midi,
      effectiveVelocity(Math.round(note.velocity * 127), section, rsong),
      t,
      Math.max(0.04, note.duration),
    )
  }
}

export function getAnalyser() {
  return masterBus ?? null
}

export async function startPlayback(rsong) {
  if (loadingPromise) return loadingPromise
  loadingPromise = _startRsong(rsong)
  try {
    await loadingPromise
  } finally {
    loadingPromise = null
  }
}

export async function startMidiPlayback(midiUrl, { durationMs, rsong }) {
  if (loadingPromise) return loadingPromise
  loadingPromise = _startMidi(midiUrl, { durationMs, rsong })
  try {
    await loadingPromise
  } finally {
    loadingPromise = null
  }
}

function _beginTransport(durationMs) {
  const ctx = getAudioContext()
  timerId = setInterval(() => {
    const ms = Math.max(0, (ctx.currentTime - playbackStartTime) * 1000)
    useCadenceStore.getState().setCurrentTime(ms)
    if (ms >= durationMs) {
      stopPlayback()
      useCadenceStore.getState().setPlaying(false)
    }
  }, 50)
  useCadenceStore.getState().setPlaying(true)
}

async function _startSession({ durationMs, schedule }) {
  await stopPlayback()
  useCadenceStore.getState().setAudioLoading(true)
  try {
    const ctx = getAudioContext()
    if (ctx.state !== 'running') await ctx.resume()

    masterBus = buildMasterBus(ctx)
    synth = await createSpessaSynth(masterBus.comp)

    playbackStartTime = ctx.currentTime + PLAYBACK_LOOKAHEAD
    schedule(synth, playbackStartTime)
    _beginTransport(durationMs)
  } finally {
    useCadenceStore.getState().setAudioLoading(false)
  }
}

async function _startMidi(midiUrl, { durationMs, rsong }) {
  const { Midi } = await import('@tonejs/midi')
  const res = await fetch(midiUrl)
  const midi = new Midi(await res.arrayBuffer())

  await _startSession({
    durationMs,
    schedule: (synthInstance, startTime) => {
      for (const track of midi.tracks) {
        scheduleMidiTrack(synthInstance, track, rsong, startTime)
      }
    },
  })
}

async function _startRsong(rsong) {
  const sorted = [...rsong.tracks].sort((a, b) => {
    const ord = { rhythm: 0, bass: 1, pad: 2, lead: 3, fx: 4 }
    return (ord[a.role] ?? 2) - (ord[b.role] ?? 2)
  })

  await _startSession({
    durationMs: rsong.header.duration_ms,
    schedule: (synthInstance, startTime) => {
      for (const track of sorted) {
        scheduleRsongTrack(synthInstance, track, rsong, startTime)
      }
    },
  })
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

  useCadenceStore.getState().reset()
}
