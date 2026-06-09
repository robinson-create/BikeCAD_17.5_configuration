const BASE = '/api'

export async function fetchDefault() {
  const r = await fetch(`${BASE}/default`)
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function calcAndRender(bike, width = 1400, height = 750, showDims = true, showRider = false) {
  const r = await fetch(`${BASE}/render/svg`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ bike, width, height, show_dims: showDims, show_rider: showRider }),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()  // { svg: string, calc: CalcResult }
}

export async function fetchFit(bike) {
  const r = await fetch(`${BASE}/fit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(bike),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()  // FitResult
}

export async function loadBcad(path) {
  const r = await fetch(`${BASE}/load/bcad`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path }),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function exportBcad(bike, path, sourcePath = null) {
  const r = await fetch(`${BASE}/export/bcad`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ bike, path, source_path: sourcePath, backup: true }),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function fetchKinematics(bike) {
  const r = await fetch(`${BASE}/kinematics`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(bike),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()  // KinematicsResult
}

export async function exportDxf(bike, opts = {}) {
  // Sans path : récupère le contenu DXF et déclenche un téléchargement client.
  const r = await fetch(`${BASE}/export/dxf`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ bike, ...opts }),
  })
  if (!r.ok) throw new Error(await r.text())
  if (opts.path) return r.json()
  const text = await r.text()
  const blob = new Blob([text], { type: 'application/dxf' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${(bike?.name ?? 'bike').replace(/\s+/g, '_')}.dxf`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
  return { ok: true }
}

export async function listBikes() {
  const r = await fetch(`${BASE}/bikes`)
  if (!r.ok) return []
  return r.json()
}

export async function listMotors() {
  const r = await fetch(`${BASE}/motors`)
  if (!r.ok) return []
  return r.json()
}
