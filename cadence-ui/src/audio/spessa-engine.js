import { WorkletSynthesizer } from 'spessasynth_lib'
import processorUrl from 'spessasynth_lib/dist/spessasynth_processor.min.js?url'

const SOUNDFONT_URL = '/soundfonts/A320U.sf2'
const SOUNDBANK_ID = 'main'

let audioCtx = null
let workletReady = null
let soundfontBytes = null
let activeSynth = null

export function getAudioContext() {
  if (!audioCtx) audioCtx = new AudioContext()
  return audioCtx
}

async function ensureWorkletModule(ctx) {
  if (!workletReady) {
    workletReady = ctx.audioWorklet.addModule(processorUrl)
  }
  await workletReady
}

async function loadSoundfontBuffer() {
  if (!soundfontBytes) {
    const res = await fetch(SOUNDFONT_URL)
    if (!res.ok) throw new Error(`SoundFont no encontrado: ${SOUNDFONT_URL} (${res.status})`)
    soundfontBytes = new Uint8Array(await res.arrayBuffer())
  }
  // addSoundBank transfiere el buffer al worklet — hay que entregar una copia cada vez.
  return new Uint8Array(soundfontBytes).buffer
}

export async function createSpessaSynth(destinationNode) {
  const ctx = getAudioContext()
  if (ctx.state !== 'running') await ctx.resume()

  await ensureWorkletModule(ctx)
  const sf2 = await loadSoundfontBuffer()

  const synth = new WorkletSynthesizer(ctx)
  await synth.soundBankManager.addSoundBank(sf2, SOUNDBANK_ID)
  await synth.isReady
  synth.connect(destinationNode)

  activeSynth = synth
  return synth
}

export function getActiveSynth() {
  return activeSynth
}

export function destroySpessaSynth(synth) {
  if (!synth) return
  try {
    synth.stopAll(true)
    synth.disconnect()
    synth.destroy()
  } catch { /* noop */ }
  if (activeSynth === synth) activeSynth = null
}

const PLAYBACK_TRIM_DB = 8

function dbToGain(db) {
  return 10 ** ((db ?? -10) / 20)
}

export function dbToMidiVolume(db) {
  const adjusted = (db ?? -10) + PLAYBACK_TRIM_DB
  return Math.max(0, Math.min(127, Math.round(dbToGain(adjusted) * 127)))
}

export function panToMidi(pan) {
  return Math.max(0, Math.min(127, Math.round((pan + 1) * 63.5)))
}

export function setupChannel(synth, channel, { program, isDrum, volumeDb, pan, time = 0 }) {
  const ch = channel % 16
  const opts = { time }
  if (isDrum) {
    synth.midiChannels[ch].setDrums(true)
  } else if (program != null) {
    synth.programChange(ch, program, opts)
  }
  synth.controllerChange(ch, 7, dbToMidiVolume(volumeDb), opts)
  synth.controllerChange(ch, 10, panToMidi(pan), opts)
}

export function scheduleNote(synth, channel, pitch, velocity, time, durationSec) {
  const ch = channel % 16
  const note = pitch % 128
  const vel = Math.max(1, Math.min(127, Math.round(velocity)))
  const dur = Math.max(0.04, durationSec)
  synth.noteOn(ch, note, vel, { time })
  synth.noteOff(ch, note, { time: time + dur })
}

export function buildMasterBus(ctx) {
  const comp = ctx.createDynamicsCompressor()
  comp.threshold.value = -14
  comp.ratio.value = 2.5
  comp.attack.value = 0.008
  comp.release.value = 0.18

  const gain = ctx.createGain()
  gain.gain.value = 1.35

  const analyser = ctx.createAnalyser()
  analyser.fftSize = 256

  comp.connect(gain)
  gain.connect(analyser)
  analyser.connect(ctx.destination)

  return {
    comp,
    gain,
    analyser,
    getValue() {
      const data = new Float32Array(analyser.frequencyBinCount)
      analyser.getFloatFrequencyData(data)
      return data
    },
  }
}
