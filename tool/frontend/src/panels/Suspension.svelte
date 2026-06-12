<script>
  import { bike, updateSection, applySuspensionPreset, pivots as pivotsStore, showPivots, scheduleRefresh } from '../lib/store.js'
  import { listBearings, exportPivots } from '../lib/api.js'
  import { onMount } from 'svelte'
  $: su = $bike?.suspension ?? {}
  $: piv = $pivotsStore
  const upd = patch => updateSection('suspension', patch)

  let bearings = []
  onMount(async () => { bearings = await listBearings() })

  // Édition d'un pivot {x,y}
  function updPivot(key, axis, val) {
    const cur = su[key] ?? { x: 0, y: 0 }
    upd({ [key]: { ...cur, [axis]: +val } })
  }

  // Pivots utiles selon la topologie
  const FOUR_BAR = ['main_pivot', 'horst_pivot', 'upper_frame_pivot',
                    'upper_ss_pivot', 'shock_lower', 'shock_upper', 'idler']
  const HIGH_PIVOT = ['main_pivot', 'shock_lower', 'shock_upper', 'idler']
  const LABELS = {
    main_pivot:        'Pivot principal',
    horst_pivot:       'Pivot Horst (bases)',
    upper_frame_pivot: 'Rocker / cadre',
    upper_ss_pivot:    'Rocker / hauban',
    shock_lower:       'Amorto bas',
    shock_upper:       'Amorto haut',
    idler:             'Galet courroie',
  }
  $: keys = (su.linkage_type === 'high_pivot_idler' ? HIGH_PIVOT : FOUR_BAR)
  $: pivots = keys.map(key => ({ key, label: LABELS[key] }))
</script>

<section class="panel">
  <h3>Suspension — cinématique</h3>

  <fieldset>
    <legend>Type</legend>
    <label class="check">
      <input type="checkbox" checked={su.enabled ?? true}
        on:change={e => upd({ enabled: e.target.checked })} />
      Cadre tout-suspendu
    </label>
    <label>Topologie cinématique
      <select value={su.linkage_type ?? 'four_bar_horst'}
        on:change={e => upd({ linkage_type: e.target.value })}>
        <option value="four_bar_horst">Four-bar (Horst Link)</option>
        <option value="high_pivot_idler">High-pivot + galet (single-pivot)</option>
        <option value="four_bar_generic">Four-bar (solveur générique)</option>
      </select>
    </label>
    <label>Course roue AR cible (mm)
      <input type="number" step="5" value={su.rear_travel ?? 160}
        on:change={e => upd({ rear_travel: +e.target.value })} />
    </label>
    <button class="preset" on:click={() => applySuspensionPreset('high_pivot_m620')}>
      ⤓ Charger preset high-pivot M620
    </button>
    <button class="preset" on:click={() => applySuspensionPreset('high_pivot_emtb_tuned')}>
      ⤓ Charger preset eMTB ACCORDÉ (levier 3.3→2.7, AS 97%, kickback 3.8°)
    </button>
    <button class="preset" on:click={() => applySuspensionPreset('kavenz_vhp_style')}>
      ⤓ Charger preset façon KAVENZ VHP (kickback 1.7°, belt growth 1.9mm, levier 3.2→2.6)
    </button>
    <button class="preset" on:click={() => applySuspensionPreset('scott_ransom_style')}>
      ⤓ Charger preset façon SCOTT RANSOM (enduro 170mm, levier 2.8→2.6, AS 92%)
    </button>
  </fieldset>

  <fieldset>
    <legend>Pivots (coord. monde — BB origine, x avant +, mm)</legend>
    <div class="pivot-grid">
      <div class="pivot-head"><span></span><span>X</span><span>Y</span></div>
      {#each pivots as p}
        <div class="pivot-row">
          <span class="pivot-label">{p.label}</span>
          <input type="number" step="1" value={su[p.key]?.x ?? 0}
            on:change={e => updPivot(p.key, 'x', e.target.value)} />
          <input type="number" step="1" value={su[p.key]?.y ?? 0}
            on:change={e => updPivot(p.key, 'y', e.target.value)} />
        </div>
      {/each}
    </div>
  </fieldset>

  <fieldset>
    <legend>Amortisseur</legend>
    <label>Entraxe eye-to-eye (mm)
      <input type="number" step="5" value={su.shock_eye_to_eye ?? 205}
        on:change={e => upd({ shock_eye_to_eye: +e.target.value })} />
    </label>
    <label>Course (mm)
      <input type="number" step="2.5" value={su.shock_stroke ?? 60}
        on:change={e => upd({ shock_stroke: +e.target.value })} />
    </label>
    <label>Œillet bas monté sur
      <select value={su.shock_mount ?? 'auto'}
        on:change={e => upd({ shock_mount: e.target.value })}>
        <option value="rocker">Biellette / rocker (enduro moderne)</option>
        <option value="chainstay">Bras oscillant (base)</option>
        <option value="coupler">Hauban</option>
        <option value="auto">Auto (hérité)</option>
      </select>
    </label>
  </fieldset>

  <fieldset>
    <legend>Courroie / galet</legend>
    <label class="check">
      <input type="checkbox" checked={su.use_idler ?? true}
        on:change={e => upd({ use_idler: e.target.checked })} />
      Galet de renvoi actif
    </label>
    <label>Ø galet (mm)
      <input type="number" step="1" value={su.idler_dia ?? 32}
        on:change={e => upd({ idler_dia: +e.target.value })} />
    </label>
    <div class="grid-2">
      <label>Plateau (dents)
        <input type="number" step="1" value={su.chainring_teeth ?? 36}
          on:change={e => upd({ chainring_teeth: +e.target.value })} />
      </label>
      <label>Pignon AR (dents)
        <input type="number" step="1" value={su.cog_teeth ?? 24}
          on:change={e => upd({ cog_teeth: +e.target.value })} />
      </label>
    </div>
    <label>Pas courroie (mm)
      <input type="number" step="0.5" value={su.belt_pitch ?? 11}
        on:change={e => upd({ belt_pitch: +e.target.value })} />
    </label>
  </fieldset>

  <fieldset>
    <legend>Pivots — roulements &amp; axes</legend>
    <label class="check">
      <input type="checkbox" checked={$showPivots}
        on:change={e => { $showPivots = e.target.checked; $bike && scheduleRefresh($bike) }} />
      Afficher les roulements sur le vélo 2D
    </label>
    <label>Roulement pivot principal
      <select value={su.pivot_bearing_main ?? '7902-AC-MAX'}
        on:change={e => upd({ pivot_bearing_main: e.target.value })}>
        {#each bearings as b}<option value={b.ref}>{b.ref} — {b.bore}×{b.od}×{b.width}</option>{/each}
      </select>
    </label>
    <label>Roulement biellettes / Horst
      <select value={su.pivot_bearing_link ?? '6902-2RS'}
        on:change={e => upd({ pivot_bearing_link: e.target.value })}>
        {#each bearings as b}<option value={b.ref}>{b.ref} — {b.bore}×{b.od}×{b.width}</option>{/each}
      </select>
    </label>
    <div class="grid-2">
      <label>Roulement galet
        <select value={su.idler_bearing ?? '6900-2RS'}
          on:change={e => upd({ idler_bearing: e.target.value })}>
          {#each bearings as b}<option value={b.ref}>{b.ref}</option>{/each}
        </select>
      </label>
      <label>Couple axes (Nm)
        <input type="number" step="1" value={su.pivot_torque_nm ?? 12}
          on:change={e => upd({ pivot_torque_nm: +e.target.value })} />
      </label>
    </div>

    {#if piv?.ok && piv.pivots?.length}
      <table class="piv">
        <tr><th>Pivot</th><th>Roulement</th><th>Ø int×ext×l</th><th>Qté</th><th>Axe</th></tr>
        {#each piv.pivots as p}
          <tr>
            <td title={p.role}>{p.name.replace('_pivot','').replace('_',' ')}</td>
            <td>{p.bearing}</td>
            <td>{p.bore}×{p.od}×{p.width}</td>
            <td>{p.qty}</td>
            <td>Ø{p.axle_dia} {p.bolt}</td>
          </tr>
        {/each}
      </table>
      <div class="bom">
        <b>Nomenclature :</b>
        {#each piv.bom as b}<span class="chip">{b.qty}× {b.ref}</span>{/each}
      </div>
      <div class="exp">
        <button on:click={() => exportPivots($bike, 'csv')}>⤓ CSV (SolidWorks)</button>
        <button on:click={() => exportPivots($bike, 'summary')}>⤓ Résumé</button>
      </div>
      {#each piv.notes as n}<p class="pnote">• {n}</p>{/each}
    {/if}
  </fieldset>

  <fieldset>
    <legend>Anti-squat</legend>
    <label>Hauteur centre de gravité (mm)
      <input type="number" step="10" value={su.cog_height ?? 1100}
        on:change={e => upd({ cog_height: +e.target.value })} />
    </label>
    <label>Sag (% course)
      <input type="number" step="1" value={su.sag_percent ?? 30}
        on:change={e => upd({ sag_percent: +e.target.value })} />
    </label>
  </fieldset>
</section>

<style>
  .pivot-grid { display: flex; flex-direction: column; gap: 3px; }
  .pivot-head, .pivot-row {
    display: grid;
    grid-template-columns: 1.4fr 1fr 1fr;
    gap: 4px;
    align-items: center;
  }
  .pivot-head span { font-size: .68rem; color: var(--accent); text-align: center; }
  .pivot-head span:first-child { text-align: left; }
  .pivot-label { font-size: .72rem; color: var(--text-muted); }
  .pivot-row input { padding: 2px 4px; }
  .preset {
    margin-top: 8px; width: 100%; padding: 6px;
    background: var(--ok); color: #fff; border: none; border-radius: var(--radius);
    font-size: .76rem; cursor: pointer;
  }
  .preset:hover { filter: brightness(0.92); }
  table.piv { width: 100%; border-collapse: collapse; margin-top: 8px; }
  table.piv th { font-size: .62rem; color: var(--accent); text-align: left; padding: 2px 4px; border-bottom: 1px solid var(--border); }
  table.piv td { font-size: .68rem; color: var(--text); padding: 2px 4px; border-bottom: 1px solid var(--border); font-variant-numeric: tabular-nums; }
  .bom { margin-top: 6px; font-size: .7rem; color: var(--text-muted); display: flex; flex-wrap: wrap; gap: 4px; align-items: center; }
  .chip { background: var(--accent-soft); color: var(--accent); border-radius: 4px; padding: 1px 6px; font-weight: 600; }
  .exp { display: flex; gap: 6px; margin-top: 8px; }
  .exp button { flex: 1; padding: 5px; border: 1px solid var(--border-strong); background: #fff; color: var(--text); border-radius: var(--radius); font-size: .72rem; cursor: pointer; }
  .exp button:hover { background: var(--accent-soft); border-color: var(--accent); color: var(--accent); }
  .pnote { font-size: .64rem; color: var(--text-muted); margin-top: 5px; font-style: italic; }
</style>
