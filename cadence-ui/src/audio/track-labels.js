/** Etiquetas legibles para pistas del .rsong (mixer UI). */

const LABELS = {
  drums: 'Batería',
  bass: 'Bajo',
  melody: 'Melodía',
  pad: 'Pad',
  countermelody: 'Contramelodía',
  echo_synth: 'Eco',
  arp_synth: 'Arpeggio',
  chord_stab: 'Stabs',
  synth_pluck: 'Pluck',
  perc_aux: 'Perc extra',
  fx_riser: 'FX riser',
  woodwind_a: 'Madera A',
  woodwind_b: 'Madera B',
  keys_piano: 'Piano',
  keys_organ: 'Órgano',
  strings_ensemble: 'Cuerdas',
  guitar_acoustic: 'Guitarra acústica',
  guitar_electric: 'Guitarra eléctrica',
  brass_a: 'Metal',
}

export function trackKey(track) {
  return track.instrument_id || track.id
}

export function trackLabel(track) {
  const id = trackKey(track)
  const name = track.instrument || LABELS[id] || id
  const gm = track.gm_program != null ? ` · GM ${track.gm_program}` : ''
  return `${name}${gm}`
}

export function trackShortLabel(track) {
  const id = trackKey(track)
  return LABELS[id] || track.instrument || id
}
