const BASE = '/api'

// ── Helpers de téléchargement / aperçu ──────────────────────────────────────
export function downloadText(filename, text, mime = 'text/plain') {
  const blob = new Blob([text], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename
  document.body.appendChild(a); a.click(); a.remove()
  URL.revokeObjectURL(url)
}

export function slug(bike) {
  return (bike?.name ?? 'bike').replace(/\s+/g, '_')
}

export async function fetchDefault() {
  const r = await fetch(`${BASE}/default`)
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function calcAndRender(bike, width = 1400, height = 750, showDims = true,
                                    showRider = false, showSuspension = false,
                                    animateSuspension = false, showLugs = false,
                                    showPivots = false, showFasteners = false) {
  const r = await fetch(`${BASE}/render/svg`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      bike, width, height,
      show_dims: showDims, show_rider: showRider,
      show_suspension: showSuspension, animate_suspension: animateSuspension,
      show_lugs: showLugs, show_pivots: showPivots, show_fasteners: showFasteners,
    }),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()  // { svg: string, calc: CalcResult }
}

export async function fetchFasteners(bike) {
  const r = await fetch(`${BASE}/fasteners`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(bike),
  })
  if (!r.ok) return null
  return r.json()  // FastenerResult
}

export async function exportFasteners(bike, fmt = 'csv') {
  const r = await fetch(`${BASE}/export/fasteners`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ bike, fmt }),
  })
  if (!r.ok) throw new Error(await r.text())
  const text = await r.text()
  const blob = new Blob([text], { type: fmt === 'json' ? 'application/json' : 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = `visserie.${fmt === 'summary' ? 'txt' : fmt}`; a.click()
  URL.revokeObjectURL(url)
}

export async function fetchMaterials() {
  const r = await fetch(`${BASE}/materials`)
  if (!r.ok) return { materials: [], adhesives: [] }
  return r.json()  // { materials:[{key,label,re,rm,E,rho}], adhesives:[{key,label,tau_test,tau_adm}] }
}

export async function fetchTubes(bike, testMomentNm = 0, testTube = 'down_tube', adhesive = 'dp460') {
  const r = await fetch(`${BASE}/tubes`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ bike, test_moment_nm: testMomentNm, test_tube: testTube, adhesive }),
  })
  if (!r.ok) return null
  return r.json()  // TubeResult
}

// Récupère le contenu texte d'un export tubes (pour aperçu live dans la fenêtre).
// fmt : csv | json | summary | fab_csv | fab_summary
export async function fetchTubeExport(bike, fmt = 'csv', testMomentNm = 0, testTube = 'down_tube', adhesive = 'dp460') {
  const r = await fetch(`${BASE}/export/tubes`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ bike, fmt, test_moment_nm: testMomentNm, test_tube: testTube, adhesive }),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.text()
}

const TUBE_EXT = { csv: 'csv', json: 'json', summary: 'txt', fab_csv: 'csv', fab_summary: 'txt' }

export async function exportTubes(bike, fmt = 'csv', testMomentNm = 0, testTube = 'down_tube', adhesive = 'dp460') {
  const text = await fetchTubeExport(bike, fmt, testMomentNm, testTube, adhesive)
  const base = fmt.startsWith('fab') ? `${slug(bike)}_fabrication_tubes` : `${slug(bike)}_tubes_lugs`
  downloadText(`${base}.${TUBE_EXT[fmt] ?? 'txt'}`, text,
               fmt === 'json' ? 'application/json' : 'text/plain')
}

export async function fetchPivots(bike) {
  const r = await fetch(`${BASE}/pivots`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(bike),
  })
  if (!r.ok) return null
  return r.json()  // PivotResult
}

export async function listBearings() {
  const r = await fetch(`${BASE}/bearings`)
  if (!r.ok) return []
  return r.json()  // [{ref,bore,od,width,type}]
}

export async function exportPivots(bike, fmt = 'csv') {
  const r = await fetch(`${BASE}/export/pivots`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ bike, fmt }),
  })
  if (!r.ok) throw new Error(await r.text())
  const text = await r.text()
  const blob = new Blob([text], { type: fmt === 'json' ? 'application/json' : 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = `pivots.${fmt === 'summary' ? 'txt' : fmt}`; a.click()
  URL.revokeObjectURL(url)
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

export async function fetchTransmission(bike) {
  const r = await fetch(`${BASE}/transmission`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(bike),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()  // TransmissionResult
}

export async function listIgh() {
  const r = await fetch(`${BASE}/igh`)
  if (!r.ok) return []
  return r.json()  // [{key,label,gears,range_pct,max_torque_nm,...}]
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

export async function deleteLibrary(name) {
  const r = await fetch(`${BASE}/library/delete`, {
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

// ── Dossier de conception (rapport HTML agrégé) ─────────────────────────────
export async function fetchReportHtml(bike, opts = {}) {
  const r = await fetch(`${BASE}/export/report`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ bike, ...opts }),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.text()  // HTML auto-suffisant
}

// Ouvre le dossier dans un nouvel onglet (l'utilisateur fait Imprimer → PDF).
export async function openReport(bike, opts = {}) {
  const htmlText = await fetchReportHtml(bike, opts)
  const blob = new Blob([htmlText], { type: 'text/html' })
  const url = URL.createObjectURL(blob)
  window.open(url, '_blank')
  setTimeout(() => URL.revokeObjectURL(url), 60000)
  return { ok: true }
}

export async function downloadReport(bike, opts = {}) {
  const htmlText = await fetchReportHtml(bike, opts)
  downloadText(`${slug(bike)}_dossier_conception.html`, htmlText, 'text/html')
  return { ok: true }
}
