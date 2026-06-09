import { writable, derived, get } from 'svelte/store'
import { calcAndRender, fetchKinematics, fetchFit, fetchSuspensionPreset } from './api.js'

// ── Design courant ─────────────────────────────────────────────────────────
export const bike = writable(null)      // BikeDesign (null = pas encore chargé)
export const calc = writable(null)      // CalcResult
export const svg  = writable('')        // SVG string
export const kinematics = writable(null) // KinematicsResult
export const fit  = writable(null)       // FitResult
export const loading = writable(false)
export const error   = writable('')
export const activeTab = writable('frame')  // onglet actif
export const viewMode  = writable('bike')   // 'bike' | 'kinematics'
export const showRider = writable(false)    // afficher le pilote sur la vue 2D
export const showDims  = writable(true)     // afficher les cotes
export const baseline  = writable(null)     // snapshot de référence pour comparaison

// Fige le design courant comme référence de comparaison
export function snapshotBaseline() {
  const b = get(bike)
  const c = get(calc)
  if (!b || !c) return
  baseline.set({
    name: b.name,
    frame: JSON.parse(JSON.stringify(b.frame)),
    calc: JSON.parse(JSON.stringify(c)),
  })
}

// ── Debounce refresh ────────────────────────────────────────────────────────
let refreshTimer = null

export function scheduleRefresh(bikeData) {
  bike.set(bikeData)
  clearTimeout(refreshTimer)
  refreshTimer = setTimeout(() => doRefresh(bikeData), 180)
}

async function doRefresh(bikeData) {
  loading.set(true)
  error.set('')
  try {
    const [result, kin, fitRes] = await Promise.all([
      calcAndRender(bikeData, 1400, 750, get(showDims), get(showRider)),
      fetchKinematics(bikeData).catch(() => null),
      bikeData.rider ? fetchFit(bikeData).catch(() => null) : Promise.resolve(null),
    ])
    svg.set(result.svg)
    calc.set(result.calc)
    if (kin) kinematics.set(kin)
    fit.set(fitRes)
  } catch (e) {
    error.set(e.message ?? 'Erreur de calcul')
  } finally {
    loading.set(false)
  }
}

// ── Mise à jour d'une section du design ─────────────────────────────────────
export function updateSection(section, patch) {
  bike.update(b => {
    if (!b) return b
    const updated = { ...b, [section]: { ...b[section], ...patch } }
    scheduleRefresh(updated)
    return updated
  })
}

// ── Application d'un preset suspension ──────────────────────────────────────
// Charge un preset (ex. high_pivot_m620) et l'applique au design courant ;
// pour le preset M620 on bascule aussi le moteur sur le M620 (enveloppe carter).
export async function applySuspensionPreset(name) {
  const preset = await fetchSuspensionPreset(name)
  bike.update(b => {
    if (!b) return b
    const drivetrain = name === 'high_pivot_m620'
      ? { ...b.drivetrain, motor_key: 'bafang_m620', use_motor: true }
      : b.drivetrain
    const updated = { ...b, suspension: preset, drivetrain }
    scheduleRefresh(updated)
    return updated
  })
}

// ── Tabs disponibles ─────────────────────────────────────────────────────────
export const TABS = [
  { id: 'frame',     label: 'Cadre',      icon: '⬡' },
  { id: 'fork',      label: 'Fourche',    icon: '⑂' },
  { id: 'stem',      label: 'Potence',    icon: '⌒' },
  { id: 'handlebar', label: 'Cintre',     icon: '⌀' },
  { id: 'saddle',    label: 'Selle',      icon: '◜' },
  { id: 'seatpost',  label: 'Tige selle', icon: '↑' },
  { id: 'cranks',    label: 'Manivelles', icon: '⟳' },
  { id: 'drivetrain',label: 'Transmission','icon': '⚙' },
  { id: 'wheels',    label: 'Roues',      icon: '◯' },
  { id: 'brakes',    label: 'Freins',     icon: '⊠' },
  { id: 'suspension',label: 'Suspension', icon: '◇' },
  { id: 'rider',     label: 'Pilote',     icon: '☻' },
]
