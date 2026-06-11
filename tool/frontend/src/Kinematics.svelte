<script>
  import { kinematics } from './lib/store.js'

  $: k = $kinematics
  $: samples = k?.samples ?? []

  // Construit un path SVG pour une série (x = wheel_travel, y = valeur)
  function buildPath(key, w, h, pad, yMin, yMax) {
    if (!samples.length) return ''
    const xs = samples.map(s => s.wheel_travel)
    const xMin = Math.min(...xs), xMax = Math.max(...xs)
    const sx = v => pad + (v - xMin) / (xMax - xMin || 1) * (w - 2 * pad)
    const sy = v => h - pad - (v - yMin) / (yMax - yMin || 1) * (h - 2 * pad)
    return samples.map((s, i) =>
      `${i === 0 ? 'M' : 'L'}${sx(s.wheel_travel).toFixed(1)},${sy(s[key]).toFixed(1)}`
    ).join(' ')
  }

  // Bande cible (rectangle) entre lo et hi
  function bandY(lo, hi, h, pad, yMin, yMax) {
    const sy = v => h - pad - (v - yMin) / (yMax - yMin || 1) * (h - 2 * pad)
    return { y: sy(hi), height: Math.abs(sy(lo) - sy(hi)) }
  }

  const W = 440, H = 200, PAD = 34

  // Plage anti-squat adaptée aux données (peut largement dépasser 200% sur une
  // géométrie mal placée — on évite de couper la courbe).
  $: asMax = samples.length ? Math.max(...samples.map(s => s.anti_squat)) : 200
  $: asMin = samples.length ? Math.min(...samples.map(s => s.anti_squat)) : -50
  $: arMax = samples.length ? Math.max(...samples.map(s => s.anti_rise ?? 0)) : 150
  $: arMin = samples.length ? Math.min(...samples.map(s => s.anti_rise ?? 0)) : 0

  // Définition des graphes
  $: charts = [
    {
      title: 'Ratio de levier', key: 'leverage', color: '#e8851a',
      yMin: 2.0, yMax: 3.6, band: [2.8, 3.2], unit: '',
    },
    {
      title: 'Anti-squat (%)', key: 'anti_squat', color: '#4caf50',
      yMin: Math.min(-50, Math.floor((asMin) / 50) * 50),
      yMax: Math.max(200, Math.ceil((asMax) / 50) * 50),
      band: [100, 115], unit: '%',
    },
    {
      title: 'Anti-rise (%) — freinage', key: 'anti_rise', color: '#16a085',
      yMin: Math.min(0, Math.floor(arMin / 50) * 50),
      yMax: Math.max(130, Math.ceil(arMax / 50) * 50),
      band: [50, 130], unit: '%',
    },
    {
      title: 'Belt growth (mm)', key: 'belt_growth', color: '#5b9bd5',
      yMin: 0, yMax: Math.max(4, Math.ceil((k?.belt_growth_max ?? 2))), band: [0, 2], unit: 'mm',
    },
    {
      title: 'Pedal kickback (°)', key: 'pedal_kickback', color: '#b07bd5',
      yMin: 0, yMax: Math.max(8, Math.ceil((k?.pedal_kickback_max ?? 4))), band: [0, 8], unit: '°',
    },
  ]

  function ticks(yMin, yMax, n = 4) {
    const out = []
    for (let i = 0; i <= n; i++) out.push(yMin + (yMax - yMin) * i / n)
    return out
  }

  // Synthèse + verdicts vs cibles linkage_DOM_eMTB.txt
  $: verdicts = k?.ok ? [
    { label: 'Course roue AR', val: `${k.total_travel} mm`,
      ok: Math.abs(k.total_travel - 160) <= 10, target: '≈ 160 mm' },
    { label: 'Course amorto requise', val: `${k.shock_stroke_used} mm`,
      ok: k.shock_stroke_used <= k.shock_stroke_spec + 1, target: `≤ ${k.shock_stroke_spec} mm` },
    { label: 'Levier (sag)', val: k.leverage_sag,
      ok: k.leverage_sag >= 2.8 && k.leverage_sag <= 3.2, target: '2.8 – 3.2' },
    { label: 'Progressivité', val: `${k.progressivity} %`,
      ok: k.progressivity >= 20 && k.progressivity <= 30, target: '20 – 30 %' },
    { label: 'Anti-squat (sag)', val: `${k.anti_squat_sag} %`,
      ok: k.anti_squat_sag >= 100 && k.anti_squat_sag <= 115, target: '100 – 115 %' },
    { label: 'Anti-rise (sag)', val: `${k.anti_rise_sag} %`,
      ok: k.anti_rise_sag >= 50 && k.anti_rise_sag <= 130, target: '50 – 130 % (freinage)' },
    { label: 'Belt growth max', val: `${k.belt_growth_max} mm`,
      ok: k.belt_growth_max < 2, target: '< 2 mm' },
    { label: 'Pedal kickback max', val: `${k.pedal_kickback_max}°`,
      ok: k.pedal_kickback_max < 8, target: '< 8° (manivelle)' },
    { label: 'Recul axe (max)', val: `${k.axle_path_rearward} mm`,
      ok: k.axle_path_rearward > 0, target: '> 0 (rearward)' },
    { label: 'Dégagement moteur', ok: k.motor_clearance_ok,
      val: k.motor_clearance_ok ? 'OK' : (k.motor_collisions ?? []).join(', '),
      target: 'hors carter' },
  ] : []
</script>

<div class="kin-wrap">
  {#if !k}
    <div class="placeholder">Calcul cinématique…</div>
  {:else if !k.ok}
    <div class="error-banner">Cinématique non résolue : {k.message}</div>
  {:else}
    {#if k.message}
      <div class="warn-banner">⚠ {k.message}</div>
    {/if}

    <div class="kin-content">
      <!-- Tableau de synthèse -->
      <div class="summary">
        <h4>Synthèse vs cibles (linkage DOM eMTB)</h4>
        <table>
          {#each verdicts as v}
            <tr>
              <td class="vl">{v.label}</td>
              <td class="vv">{v.val}</td>
              <td class="vt">{v.target}</td>
              <td class="vb"><span class="badge {v.ok ? 'ok' : 'no'}">{v.ok ? '✓' : '✗'}</span></td>
            </tr>
          {/each}
        </table>
        <p class="note">
          Méthode anti-squat indicative (IC + ligne de courroie) — à valider dans
          Linkage avant fabrication. Pic au topout = position de conception proche
          du point mort du four-bar.
        </p>
      </div>

      <!-- Graphes -->
      <div class="charts">
        {#each charts as c}
          {@const band = bandY(c.band[0], c.band[1], H, PAD, c.yMin, c.yMax)}
          <div class="chart">
            <div class="chart-title">{c.title}</div>
            <svg viewBox="0 0 {W} {H}" class="chart-svg">
              <!-- bande cible -->
              <rect x={PAD} y={band.y} width={W - 2 * PAD} height={band.height}
                fill="rgba(76,175,80,.12)" />
              <!-- axes -->
              <line x1={PAD} y1={PAD} x2={PAD} y2={H - PAD} stroke="var(--border-strong)" />
              <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} stroke="var(--border-strong)" />
              <!-- graduations Y -->
              {#each ticks(c.yMin, c.yMax) as t}
                {@const yy = H - PAD - (t - c.yMin) / (c.yMax - c.yMin) * (H - 2 * PAD)}
                <line x1={PAD - 3} y1={yy} x2={W - PAD} y2={yy} stroke="var(--border)" stroke-width="0.5" />
                <text x={PAD - 6} y={yy + 3} text-anchor="end" class="tick">{t.toFixed(c.key === 'leverage' ? 1 : 0)}</text>
              {/each}
              <!-- courbe -->
              <path d={buildPath(c.key, W, H, PAD, c.yMin, c.yMax)}
                fill="none" stroke={c.color} stroke-width="2" />
              <!-- label X -->
              <text x={W / 2} y={H - 6} text-anchor="middle" class="axlabel">course roue (mm)</text>
            </svg>
          </div>
        {/each}
      </div>
    </div>
  {/if}
</div>

<style>
  .kin-wrap {
    height: 100%;
    overflow-y: auto;
    background: var(--bg);
    border-radius: var(--radius);
    padding: 10px;
  }
  .placeholder { display: flex; align-items: center; justify-content: center; height: 100%; color: var(--text-muted); }
  .error-banner { background: var(--no); color: #fff; padding: 8px 12px; border-radius: var(--radius); }
  .warn-banner { background: var(--accent-soft); color: var(--warn); border: 1px solid var(--border); padding: 6px 12px; border-radius: var(--radius); font-size: .8rem; margin-bottom: 10px; }
  .kin-content { display: flex; flex-direction: column; gap: 14px; }

  .summary h4 { font-size: .85rem; color: var(--brand); margin-bottom: 8px; text-transform: uppercase; letter-spacing: .04em; }
  .summary table { width: 100%; border-collapse: collapse; }
  .summary td { padding: 4px 8px; border-bottom: 1px solid var(--border); font-size: .8rem; }
  .vl { color: var(--text-muted); }
  .vv { color: var(--text); font-weight: 600; font-variant-numeric: tabular-nums; }
  .vt { color: var(--text-muted); font-size: .72rem; }
  .vb { text-align: right; }
  .badge { display: inline-block; width: 18px; height: 18px; line-height: 18px; text-align: center; border-radius: 50%; font-size: .72rem; font-weight: 700; }
  .badge.ok { background: var(--ok); color: #fff; }
  .badge.no { background: var(--no); color: #fff; }
  .note { font-size: .68rem; color: var(--text-muted); margin-top: 8px; font-style: italic; }

  .charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 12px; }
  .chart { background: var(--panel); border: 1px solid var(--border); border-radius: var(--radius); padding: 8px; }
  .chart-title { font-size: .78rem; color: var(--accent); margin-bottom: 4px; text-align: center; }
  .chart-svg { width: 100%; height: auto; }
  .tick { fill: var(--text-muted); font-size: 9px; }
  .axlabel { fill: var(--text-muted); font-size: 9px; }
</style>
