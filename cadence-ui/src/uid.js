let _seq = 0

export function uid() {
  _seq += 1
  return `${Date.now()}-${_seq}`
}
