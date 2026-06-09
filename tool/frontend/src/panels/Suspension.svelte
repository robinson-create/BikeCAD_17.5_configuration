<script>
  import { bike, updateSection } from '../lib/store.js'
  $: su = $bike?.suspension ?? {}
  const upd = patch => updateSection('suspension', patch)

  // Édition d'un pivot {x,y}
  function updPivot(key, axis, val) {
    const cur = su[key] ?? { x: 0, y: 0 }
    upd({ [key]: { ...cur, [axis]: +val } })
  }

  const pivots = [
    { key: 'main_pivot',        label: 'Pivot principal' },
    { key: 'horst_pivot',       label: 'Pivot Horst (bases)' },
    { key: 'upper_frame_pivot', label: 'Rocker / cadre' },
    { key: 'upper_ss_pivot',    label: 'Rocker / hauban' },
    { key: 'shock_lower',       label: 'Amorto bas' },
    { key: 'shock_upper',       label: 'Amorto haut' },
    { key: 'idler',             label: 'Galet courroie' },
  ]
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
    <label>Course roue AR cible (mm)
      <input type="number" step="5" value={su.rear_travel ?? 160}
        on:change={e => upd({ rear_travel: +e.target.value })} />
    </label>
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
    <label class="check">
      <input type="checkbox" checked={su.shock_on_chainstay ?? true}
        on:change={e => upd({ shock_on_chainstay: e.target.checked })} />
      Montage bas sur les bases (sinon rocker)
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
  .pivot-head span { font-size: .68rem; color: #8ecae6; text-align: center; }
  .pivot-head span:first-child { text-align: left; }
  .pivot-label { font-size: .72rem; color: #9999bb; }
  .pivot-row input { padding: 2px 4px; }
</style>
