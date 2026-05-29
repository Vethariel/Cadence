const API = ''

export async function fetchProductions() {
  const res = await fetch(`${API}/productions`)
  if (!res.ok) throw new Error('No se pudieron cargar las producciones')
  const data = await res.json()
  return data.productions
}

export async function fetchProduction(filename) {
  const res = await fetch(`${API}/productions/${encodeURIComponent(filename)}`)
  if (!res.ok) throw new Error('Producción no encontrada')
  return res.json()
}

export function productionMidiUrl(filename) {
  return `${API}/productions/${encodeURIComponent(filename)}/midi`
}

export async function generateSong(prompt) {
  const res = await fetch(`${API}/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Error al generar')
  }
  return res.json()
}
