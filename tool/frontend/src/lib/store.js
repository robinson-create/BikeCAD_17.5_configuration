import { writable, derived, get } from 'svelte/store'
import { calcAndRender, fetchKinematics, fetchFit, fetchSuspensionPreset, fetchBattery, fetchTransmission, fetchPivots } from './api.js'

// ── Design courant ─────────────────────────────────────────────────────────
export const bike = writable(null)      // BikeDesign (null = pas encore chargé)
export const calc = writable(null)      // CalcResult
export const svg  = writable('')        // SVG string
export const kinematics = writable(null) // KinematicsResult
export const fit  = writable(null)       // FitResult
export const battery = writable(null)    // BatteryResult
export const transmission = writable(null) // TransmissionResult
export const loading = writable(false)
export const error   = writable('')
export const activeTab = writable('frame')  // onglet actif
export const viewMode  = writable('bike')   // 'bike' | 'kinematics'
export const showRider = writable(false)    // afficher le pilote sur la vue 2D
export const showDims  = writable(true)     // afficher les cotes
export const showSuspension    = writable(false)  // overlay biellette sur la vue 2D
export const animateSuspension = writable(false)  // animation de la course
export const showLugs          = writable(false)  // lugs CNC aux jonctions
export const showPivots        = writable(false)  // roulements/axes aux pivots
export const pivots            = writable(null)    // PivotResult
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
    const [result, kin, fitRes, batRes, txRes, pivRes] = await Promise.all([
      calcAndRender(bikeData, 1400, 750, get(showDims), get(showRider),
                    get(showSuspension), get(animateSuspension), get(showLugs), get(showPivots)),
      fetchKinematics(bikeData).catch(() => null),
      bikeData.rider ? fetchFit(bikeData).catch(() => null) : Promise.resolve(null),
      bikeData.battery?.enabled ? fetchBattery(bikeData).catch(() => null) : Promise.resolve(null),
      fetchTransmission(bikeData).catch(() => null),
      bikeData.suspension?.enabled ? fetchPivots(bikeData).catch(() => null) : Promise.resolve(null),
    ])
    svg.set(result.svg)
    calc.set(result.calc)
    if (kin) kinematics.set(kin)
    fit.set(fitRes)
    battery.set(batRes)
    transmission.set(txRes)
    pivots.set(pivRes)
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
// Onglets regroupés (UX) : 6 groupes au lieu de 13 onglets, AUCUN champ perdu —
// chaque groupe empile ses panneaux (chacun garde son titre/section).
export const GROUPS = [
  { id: 'frame',      label: 'Cadre',          icon: '⬡', panels: ['frame'] },
  { id: 'suspension', label: 'Suspension',     icon: '◇', panels: ['suspension'] },
  { id: 'drive',      label: 'Motorisation',   icon: '⚙', panels: ['drivetrain', 'cranks', 'battery'] },
  { id: 'wheels',     label: 'Roues & freins', icon: '◯', panels: ['wheels', 'brakes'] },
  { id: 'cockpit',    label: 'Pilotage',       icon: '⌒', panels: ['fork', 'stem', 'handlebar', 'saddle', 'seatpost'] },
  { id: 'rider',      label: 'Pilote',         icon: '☻', panels: ['rider'] },
]
// Compat : ancien `TABS` (certains imports) = liste à plat des panneaux.
export const TABS = GROUPS
