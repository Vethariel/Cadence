import { Midi } from '@tonejs/midi'
import { resolveGmProgram } from './gm-programs'

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export function filterRsongByMutes(rsong, trackMutes = {}) {
  if (!rsong) return null
  const filteredTracks = (rsong.tracks || []).filter((track) => {
    const id = track.instrument_id || track.id
    return !trackMutes[id]
  })

  return {
    ...rsong,
    tracks: filteredTracks,
    game_meta: {
      ...(rsong.game_meta || {}),
      arrangement: {
        ...(rsong.game_meta?.arrangement || {}),
        active_instruments: filteredTracks.map((t) => t.instrument_id || t.id),
      },
    },
  }
}

export function downloadRsong(rsong, trackMutes, filename = 'cadence.rsong.json') {
  const filtered = filterRsongByMutes(rsong, trackMutes)
  const payload = JSON.stringify(filtered, null, 2)
  downloadBlob(new Blob([payload], { type: 'application/json' }), filename)
}

export function downloadMidiFromRsong(rsong, trackMutes, filename = 'cadence.mid') {
  const filtered = filterRsongByMutes(rsong, trackMutes)
  if (!filtered) return

  const midi = new Midi()
  const bpm = filtered.header?.bpm || 120
  midi.header.setTempo(bpm, 0)

  for (const srcTrack of filtered.tracks || []) {
    const track = midi.addTrack()
    const id = srcTrack.instrument_id || srcTrack.id || 'track'
    const isDrum = srcTrack.role === 'rhythm' || id === 'drums' || id === 'perc_aux'
    const channel = isDrum ? 9 : Math.max(0, Math.min(15, srcTrack.midi_channel ?? 0))

    track.channel = channel
    track.name = id
    track.instrument.number = isDrum
      ? 0
      : (srcTrack.gm_program ?? resolveGmProgram(id, srcTrack.role))

    for (const event of srcTrack.events || []) {
      if (event.type === 'rest') continue
      track.addNote({
        midi: event.pitch,
        time: event.t / 1000,
        duration: Math.max(0.04, (event.duration_ms || 120) / 1000),
        velocity: Math.max(0.05, Math.min(1, (event.velocity || 90) / 127)),
      })
    }
  }

  downloadBlob(new Blob([midi.toArray()], { type: 'audio/midi' }), filename)
}
