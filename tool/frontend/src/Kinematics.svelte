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

  // Définition des 3 graphes
  $: charts = [
    {
      title: 'Ratio de levier', key: 'leverage', color: '#e8851a',
      yMin: 2.0, yMax: 3.6, band: [2.8, 3.2], unit: '',
    },
    {
      title: 'Anti-squat (%)', key: 'anti_squat', color: '#4caf50',
      yMin: -50, yMax: 200, band: [100, 115], unit: '%',
    },
    {
      title: 'Belt growth (mm)', key: 'belt_growth', color: '#5b9bd5',
      yMin: 0, yMax: Math.max(4, Math.ceil((k?.belt_growth_max ?? 2))), band: [0, 2], unit: 'mm',
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
    { label: 'Belt growth max', val: `${k.belt_growth_max} mm`,
      ok: k.belt_growth_max < 2, target: '< 2 mm' },
    { label: 'Recul axe (max)', val: `${k.axle_path_rearward} mm`,
      ok: k.axle_path_rearward > 0, target: '> 0 (rearward)' },
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
              <line x1={PAD} y1={PAD} x2={PAD} y2={H - PAD} stroke="#444" />
              <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} stroke="#444" />
              <!-- graduations Y -->
              {#each ticks(c.yMin, c.yMax) as t}
                {@const yy = H - PAD - (t - c.yMin) / (c.yMax - c.yMin) * (H - 2 * PAD)}
                <line x1={PAD - 3} y1={yy} x2={W - PAD} y2={yy} stroke="#2a2a4a" stroke-width="0.5" />
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
    background: #1a1a2e;
    border-radius: 4px;
    padding: 10px;
  }
  .placeholder { display: flex; align-items: center; justify-content: center; height: 100%; color: #555; }
  .error-banner { background: #c0392b; color: #fff; padding: 8px 12px; border-radius: 4px; }
  .warn-banner { background: #6b5320; color: #ffd; padding: 6px 12px; border-radius: 4px; font-size: .8rem; margin-bottom: 10px; }
  .kin-content { display: flex; flex-direction: column; gap: 14px; }

  .summary h4 { font-size: .85rem; color: #e8851a; margin-bottom: 8px; text-transform: uppercase; letter-spacing: .04em; }
  .summary table { width: 100%; border-collapse: collapse; }
  .summary td { padding: 4px 8px; border-bottom: 1px solid #2a2a4a; font-size: .8rem; }
  .vl { color: #aab; }
  .vv { color: #fff; font-weight: 600; font-variant-numeric: tabular-nums; }
  .vt { color: #778; font-size: .72rem; }
  .vb { text-align: right; }
  .badge { display: inline-block; width: 18px; height: 18px; line-height: 18px; text-align: center; border-radius: 50%; font-size: .72rem; font-weight: 700; }
  .badge.ok { background: #2e7d32; color: #fff; }
  .badge.no { background: #c0392b; color: #fff; }
  .note { font-size: .68rem; color: #667; margin-top: 8px; font-style: italic; }

  .charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 12px; }
  .chart { background: #16213e; border: 1px solid #2a2a4a; border-radius: 4px; padding: 8px; }
  .chart-title { font-size: .78rem; color: #8ecae6; margin-bottom: 4px; text-align: center; }
  .chart-svg { width: 100%; height: auto; }
  .tick { fill: #667; font-size: 9px; }
  .axlabel { fill: #778; font-size: 9px; }
</style>
