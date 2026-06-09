<script>
  import { bike, fit, showRider, scheduleRefresh } from '../lib/store.js'

  $: rd = $bike?.rider ?? null
  $: f = $fit

  const DEFAULT_RIDER = {
    inseam: 810, lower_leg: 380, upper_leg: 430, torso_length: 580,
    upper_arm: 300, lower_arm: 260, shoulder_width: 410, shoe_length: 270,
    pelvis_thickness: 200, knee_thickness: 90, ankle_thickness: 65,
    elbow_thickness: 70, arm_thickness: 80, forehead_to_back: 200,
    shoulder_to_jaw: 220, hip_angle: 0, knee_angle: 0, torso_angle: 0,
    shoulder_angle: 0, elbow_angle: 0, shoulder_roll: 0,
  }

  function activate() {
    const b = { ...$bike, rider: { ...DEFAULT_RIDER } }
    showRider.set(true)
    scheduleRefresh(b)
  }
  function deactivate() {
    const b = { ...$bike, rider: null }
    showRider.set(false)
    scheduleRefresh(b)
  }
  function upd(patch) {
    const b = { ...$bike, rider: { ...$bike.rider, ...patch } }
    scheduleRefresh(b)
  }

  const fields = [
    ['inseam', 'Entrejambe'], ['upper_leg', 'Cuisse (fémur)'],
    ['lower_leg', 'Tibia'], ['torso_length', 'Torse'],
    ['upper_arm', 'Bras'], ['lower_arm', 'Avant-bras'],
    ['shoulder_width', 'Largeur épaules'], ['shoe_length', 'Pointure (mm)'],
    ['shoulder_to_jaw', 'Épaule → tête'],
  ]

  // Verdicts fit
  function band(v, lo, hi) { return v != null && v >= lo && v <= hi }
  $: verdicts = f?.ok ? [
    { l: 'Hauteur de selle', v: `${f.saddle_height} mm`, ok: true, t: 'BB → selle' },
    { l: 'Extension jambe', v: `${f.leg_extension_pct} %`, ok: band(f.leg_extension_pct, 88, 96), t: '88 – 96 %' },
    { l: 'Angle genou (bas)', v: f.knee_angle_bdc != null ? `${f.knee_angle_bdc}°` : '—', ok: band(f.knee_angle_bdc, 137, 150), t: '137 – 150°' },
    { l: 'KOPS', v: f.kops_offset != null ? `${f.kops_offset} mm` : '—', ok: band(f.kops_offset, -25, 25), t: '−25 à +25 mm' },
    { l: 'Reach selle→cintre', v: `${f.saddle_to_bar_reach} mm`, ok: true, t: 'cockpit' },
    { l: 'Drop selle→cintre', v: `${f.saddle_to_bar_drop} mm`, ok: true, t: '− = cintre haut' },
    { l: 'Angle de dos', v: f.back_angle != null ? `${f.back_angle}°` : '—', ok: band(f.back_angle, 40, 60), t: '40 – 60° (enduro)' },
    { l: 'Angle de coude', v: f.elbow_angle != null ? `${f.elbow_angle}°` : '—', ok: band(f.elbow_angle, 150, 170), t: '150 – 170°' },
    { l: 'Hanche (haut)', v: f.hip_angle_tdc != null ? `${f.hip_angle_tdc}°` : '—', ok: band(f.hip_angle_tdc, 40, 95), t: '> 40° ouvert' },
  ] : []
</script>

<section class="panel">
  <h3>Pilote — fit</h3>

  {#if !rd}
    <p class="hint">Aucun pilote défini.</p>
    <button class="big" on:click={activate}>Activer le pilote (réf. 1.80 m)</button>
  {:else}
    <fieldset>
      <legend>Affichage</legend>
      <label class="check">
        <input type="checkbox" checked={$showRider}
          on:change={e => { showRider.set(e.target.checked); scheduleRefresh($bike); }} />
        Afficher le pilote sur la vue 2D
      </label>
      <button class="small" on:click={deactivate}>Retirer le pilote</button>
    </fieldset>

    <fieldset>
      <legend>Anthropométrie (mm)</legend>
      <div class="grid-2">
        {#each fields as [key, label]}
          <label>{label}
            <input type="number" step="5" value={rd[key] ?? 0}
              on:change={e => upd({ [key]: +e.target.value })} />
          </label>
        {/each}
      </div>
    </fieldset>

    {#if f?.ok}
      <fieldset>
        <legend>Résultats fit</legend>
        <table class="fit">
          {#each verdicts as v}
            <tr>
              <td class="fl">{v.l}</td>
              <td class="fv">{v.v}</td>
              <td class="ft">{v.t}</td>
              <td class="fb"><span class="badge {v.ok ? 'ok' : 'no'}">{v.ok ? '✓' : '!'}</span></td>
            </tr>
          {/each}
        </table>
        {#if f.notes?.length}
          {#each f.notes as n}<p class="warn">⚠ {n}</p>{/each}
        {/if}
        <p class="note">Aide à la mise en position (plan sagittal) — bras fléchi modélisé à 0.92. Pas un protocole de fitting clinique.</p>
      </fieldset>
    {/if}
  {/if}
</section>

<style>
  .hint { color: #99a; font-size: .8rem; margin-bottom: 10px; }
  button.big { width: 100%; padding: 8px; background: #1e3a5f; color: #8ecae6; border: 1px solid #3a5a8f; border-radius: 4px; cursor: pointer; }
  button.small { margin-top: 6px; padding: 3px 10px; background: #3a2020; color: #e8a; border: 1px solid #5a3030; border-radius: 3px; cursor: pointer; font-size: .75rem; }
  table.fit { width: 100%; border-collapse: collapse; }
  table.fit td { padding: 3px 6px; border-bottom: 1px solid #2a2a4a; font-size: .74rem; }
  .fl { color: #aab; }
  .fv { color: #fff; font-weight: 600; font-variant-numeric: tabular-nums; }
  .ft { color: #778; font-size: .68rem; }
  .fb { text-align: right; }
  .badge { display: inline-block; width: 16px; height: 16px; line-height: 16px; text-align: center; border-radius: 50%; font-size: .68rem; font-weight: 700; }
  .badge.ok { background: #2e7d32; color: #fff; }
  .badge.no { background: #c89020; color: #1a1a2e; }
  .warn { color: #e8a; font-size: .72rem; margin-top: 6px; }
  .note { color: #667; font-size: .66rem; font-style: italic; margin-top: 8px; }
</style>
