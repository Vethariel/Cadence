import * as Tone from 'tone'
import { useCadenceStore } from '../store'

// ── Síntesis por rol de track ─────────────────────────────────

function makeSynth(role) {
  switch (role) {
    case 'lead':
      return new Tone.Synth({
        oscillator: { type: 'sawtooth' },
        envelope: { attack: 0.01, decay: 0.1, sustain: 0.6, release: 0.3 },
      }).toDestination()

    case 'bass':
      return new Tone.Synth({
        oscillator: { type: 'square' },
        envelope: { attack: 0.01, decay: 0.2, sustain: 0.8, release: 0.1 },
      }).toDestination()

    case 'pad':
      return new Tone.PolySynth(Tone.Synth, {
        oscillator: { type: 'sine' },
        envelope: { attack: 0.8, decay: 0.3, sustain: 0.7, release: 1.2 },
      }).toDestination()

    case 'fx':
      return new Tone.Synth({
        oscillator: { type: 'sine' },
        envelope: { attack: 0.05, decay: 0.2, sustain: 0.3, release: 0.4 },
      }).toDestination()

    case 'rhythm':
      return new Tone.MembraneSynth({
        pitchDecay: 0.05,
        octaves: 4,
        envelope: { attack: 0.001, decay: 0.2, sustain: 0, release: 0.1 },
      }).toDestination()

    default:
      return new Tone.Synth().toDestination()
  }
}

function midiToFreq(midi) {
  return 440 * Math.pow(2, (midi - 69) / 12)
}

function midiToDrumNote(pitch) {
  // Mapeo básico GM → nota perceptible
  if (pitch === 36) return 'C1'  // kick
  if (pitch === 38) return 'G1'  // snare
  if (pitch === 42) return 'C3'  // hihat
  return 'C2'
}


// ── Estado interno del player ─────────────────────────────────

let parts  = []
let timerId = null
let analyser = null

export function getAnalyser() {
  return analyser
}


// ── API pública ───────────────────────────────────────────────

export async function startPlayback(rsong) {
  await stopPlayback()
  await Tone.start()

  Tone.getTransport().bpm.value = rsong.header.bpm
  Tone.getTransport().cancel()

  // Analyser para FFT
  analyser = new Tone.Analyser('fft', 256)
  const masterGain = new Tone.Gain(0.7).connect(analyser).toDestination()

  for (const track of rsong.tracks) {
    const synth = makeSynth(track.role === 'fx' ? 'fx' : track.role)
    synth.disconnect()
    synth.connect(masterGain)

    // Volumen por rol
    const vol = { lead: -8, bass: -6, rhythm: -10, pad: -14, fx: -12 }
    synth.volume.value = vol[track.role] ?? -8

    const events = track.events.map(e => {
      const timeSeconds = e.t / 1000
      return [timeSeconds, e]
    })

    const part = new Tone.Part((time, event) => {
      const durationSec = Math.max(0.05, event.duration_ms / 1000)

      if (track.role === 'rhythm' || (track.instrument_id === 'perc_aux')) {
        synth.triggerAttackRelease(
          midiToDrumNote(event.pitch),
          durationSec,
          time,
          event.velocity / 127,
        )
      } else if (track.role === 'pad' && event.type === 'chord') {
        synth.triggerAttackRelease(
          midiToFreq(event.pitch),
          durationSec,
          time,
          event.velocity / 127,
        )
      } else {
        synth.triggerAttackRelease(
          midiToFreq(event.pitch),
          durationSec,
          time,
          event.velocity / 127,
        )
      }
    }, events)

    part.start(0)
    parts.push({ part, synth })
  }

  // Ticker para actualizar el store cada 50ms
  timerId = setInterval(() => {
    const ms = Tone.getTransport().seconds * 1000
    useCadenceStore.getState().setCurrentTime(ms)

    // Detener al llegar al final
    if (ms >= rsong.header.duration_ms) {
      stopPlayback()
      useCadenceStore.getState().setPlaying(false)
    }
  }, 50)

  Tone.getTransport().start()
  useCadenceStore.getState().setPlaying(true)
}

export async function stopPlayback() {
  if (timerId) {
    clearInterval(timerId)
    timerId = null
  }

  Tone.getTransport().stop()
  Tone.getTransport().cancel()

  for (const { part, synth } of parts) {
    part.stop()
    part.dispose()
    synth.dispose()
  }
  parts = []

  if (analyser) {
    analyser.dispose()
    analyser = null
  }

  useCadenceStore.getState().reset()
}
