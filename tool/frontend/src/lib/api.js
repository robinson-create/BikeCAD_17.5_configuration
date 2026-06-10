const BASE = '/api'

export async function fetchDefault() {
  const r = await fetch(`${BASE}/default`)
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function calcAndRender(bike, width = 1400, height = 750, showDims = true,
                                    showRider = false, showSuspension = false,
                                    animateSuspension = false, showLugs = false) {
  const r = await fetch(`${BASE}/render/svg`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      bike, width, height,
      show_dims: showDims, show_rider: showRider,
      show_suspension: showSuspension, animate_suspension: animateSuspension,
      show_lugs: showLugs,
    }),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()  // { svg: string, calc: CalcResult }
}

export async function fetchCatalog(category) {
  const r = await fetch(`${BASE}/catalog/${category}`)
  if (!r.ok) return []
  return r.json()  // [{name, file}]
}

export async function searchSettings(q = '', limit = 300) {
  const r = await fetch(`${BASE}/catalog/keys?q=${encodeURIComponent(q)}&limit=${limit}`)
  if (!r.ok) return { total: 0, matched: 0, rows: [] }
  return r.json()
}

export async function catalogOverview() {
  const r = await fetch(`${BASE}/catalog`)
  if (!r.ok) return null
  return r.json()
}

export async function loadCatalogPart(category, file) {
  const r = await fetch(`${BASE}/catalog/${category}/load`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file }),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()  // { section: patch, ... }
}

export async function fetchBattery(bike) {
  const r = await fetch(`${BASE}/battery`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(bike),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()  // BatteryResult
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

export async function exportBcad(bike, path, sourcePath = null, freeSafe = true) {
  const r = await fetch(`${BASE}/export/bcad`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ bike, path, source_path: sourcePath, backup: true, free_safe: freeSafe }),
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

export async function exportDrawing(bike) {
  // Plan technique SVG (cotation, axes, visserie, lugs, cartouche) → téléchargement.
  const r = await fetch(`${BASE}/export/drawing`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ bike }),
  })
  if (!r.ok) throw new Error(await r.text())
  const text = await r.text()
  const blob = new Blob([text], { type: 'image/svg+xml' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${(bike?.name ?? 'bike').replace(/\s+/g, '_')}_plan.svg`
  document.body.appendChild(a); a.click(); a.remove()
  URL.revokeObjectURL(url)
  return { ok: true }
}

export async function exportLugs(bike, fmt = 'csv') {
  // Récupère l'export lugs et déclenche un téléchargement client.
  const r = await fetch(`${BASE}/export/lugs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ bike, fmt }),
  })
  if (!r.ok) throw new Error(await r.text())
  const ext = fmt === 'json' ? 'json' : (fmt === 'csv' ? 'csv' : 'txt')
  const mime = fmt === 'json' ? 'application/json' : 'text/plain'
  const text = fmt === 'json' ? JSON.stringify(await r.json(), null, 2) : await r.text()
  const blob = new Blob([text], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${(bike?.name ?? 'bike').replace(/\s+/g, '_')}_lugs.${ext}`
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

// ── Bibliothèque native (JSON complet, lossless) ────────────────────────────
export async function saveBikeLibrary(bike, name = null) {
  const r = await fetch(`${BASE}/library/save`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ bike, name }),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function listLibrary() {
  const r = await fetch(`${BASE}/library`)
  if (!r.ok) return []
  return r.json()
}

export async function loadLibrary(name) {
  const r = await fetch(`${BASE}/library/load`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

// ── Assistant (Claude pilote l'outil) ───────────────────────────────────────
export async function assistantAvailable() {
  try {
    const r = await fetch(`${BASE}/assistant/available`)
    if (!r.ok) return false
    return (await r.json()).available === true
  } catch { return false }
}

export async function askAssistant(messages, bike) {
  const r = await fetch(`${BASE}/assistant`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages, bike }),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()  // { reply, bike, actions }
}

export async function listMotors() {
  const r = await fetch(`${BASE}/motors`)
  if (!r.ok) return []
  return r.json()
}

export async function fetchSuspensionPreset(name) {
  const r = await fetch(`${BASE}/suspension/preset/${name}`)
  if (!r.ok) throw new Error(await r.text())
  return r.json()  // SuspensionConfig
}
