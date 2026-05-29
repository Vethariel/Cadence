// GM program numbers — aligned with cadence/analysis/rsong_to_midi.py + FluidR3 naming
export const GM_PROGRAM = {
  melody: 80,        // Lead 1 (square)
  countermelody: 53, // Voice Oohs
  echo_synth: 88,    // Pad 1 (new age)
  arp_synth: 12,     // Marimba
  bass: 38,          // Synth Bass 1
  pad: 89,           // Pad 2 (warm)
  fx_riser: 119,     // Reverse Cymbal
}

export const ROLE_PROGRAM = {
  lead: 80,
  bass: 38,
  pad: 89,
  fx: 80,
}

export function resolveGmProgram(instrumentId, role) {
  return GM_PROGRAM[instrumentId] ?? ROLE_PROGRAM[role] ?? 0
}

export const TRACK_NAME_TO_INSTRUMENT = {
  'Lead Melody': 'melody',
  'Counter Melody': 'countermelody',
  'Echo Synth': 'echo_synth',
  'Arp Synth': 'arp_synth',
  'Drums': 'drums',
  'Bass': 'bass',
  'Pad': 'pad',
  'Perc Aux': 'perc_aux',
  'FX Riser': 'fx_riser',
}

export function resolveInstrumentId(trackOrName) {
  if (typeof trackOrName === 'object' && trackOrName) {
    const id = trackOrName.instrument_id || trackOrName.id
    if (id) return id
    trackOrName = trackOrName.name || ''
  }
  const name = String(trackOrName || '')
  if (TRACK_NAME_TO_INSTRUMENT[name]) return TRACK_NAME_TO_INSTRUMENT[name]
  return resolveMidiVoiceId(name)
}
export function resolveMidiVoiceId(trackName) {
  const n = (trackName || '').toLowerCase()
  if (n.includes('counter')) return 'countermelody'
  if (n.includes('echo')) return 'echo_synth'
  if (n.includes('arp')) return 'arp_synth'
  if (n.includes('bass')) return 'bass'
  if (n.includes('pad')) return 'pad'
  if (n.includes('fx') || n.includes('riser')) return 'fx_riser'
  return 'melody'
}
