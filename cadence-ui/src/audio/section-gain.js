const FALLBACK_DENSITY = {
  intro: 0.4,
  'build-up': 0.7,
  drop: 1.0,
  breakdown: 0.3,
  outro: 0.2,
}

function narrativeSections(rsong) {
  return rsong?.game_meta?.narrative?.sections ?? rsong?.narrative?.sections ?? []
}

export function findSectionDensity(sectionId, rsong) {
  const matches = narrativeSections(rsong).filter(s => s.id === sectionId)
  if (matches.length) {
    return Math.max(...matches.map(s => s.density ?? 0.5))
  }
  return FALLBACK_DENSITY[sectionId] ?? 0.7
}

/** Extra dB for sparse sections; drop (density ~1) stays at 0. */
export function sectionVolumeBoost(sectionId, rsong) {
  const density = findSectionDensity(sectionId, rsong)
  if (density >= 0.95) return 0
  return Math.min(10, (1 - density) * 12)
}

export function sectionAtTimeMs(ms, rsong) {
  const cues = rsong?.game_meta?.cue_points ?? []
  if (!cues.length) return 'drop'
  let section = cues[0].label
  for (const cue of cues) {
    if (ms >= cue.t) section = cue.label
  }
  return section
}

export function effectiveTrackVolumeDb(track, rsong, sectionId, baseDb) {
  return baseDb + sectionVolumeBoost(sectionId, rsong)
}

export function effectiveVelocity(velocity, sectionId, rsong) {
  const boost = sectionVolumeBoost(sectionId, rsong)
  if (boost <= 0) return Math.max(1, Math.min(127, Math.round(velocity)))
  const scale = 10 ** ((boost * 0.35) / 20)
  return Math.max(1, Math.min(127, Math.round(velocity * scale)))
}
