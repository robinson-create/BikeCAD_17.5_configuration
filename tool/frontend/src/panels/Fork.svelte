<script>
  import { bike, updateSection } from '../lib/store.js'
  import CatalogSelect from '../lib/CatalogSelect.svelte'
  $: fk = $bike?.fork ?? {}
  const upd = patch => updateSection('fork', patch)
</script>

<section class="panel">
  <h3>Fourche</h3>
  <CatalogSelect category="fork" />

  <fieldset>
    <legend>Suspension</legend>
    <label>Débattement (mm)
      <input type="number" step="1" value={fk.travel ?? 160}
        on:change={e => upd({ travel: +e.target.value })} />
    </label>
    <label>Sag statique (mm)
      <input type="number" step="1" value={fk.sag ?? 40}
        on:change={e => upd({ sag: +e.target.value })} />
    </label>
  </fieldset>

  <fieldset>
    <legend>Géométrie fourche</legend>
    <label>A2C — Axe à couronne (mm)
      <input type="number" step="0.1" value={fk.a2c ?? 570.8}
        on:change={e => upd({ a2c: +e.target.value })} />
    </label>
    <label>Déport / rake (mm)
      <input type="number" step="0.5" value={fk.offset ?? 44}
        on:change={e => upd({ offset: +e.target.value })} />
    </label>
    <label>Tube plongeur haut (mm)
      <input type="number" step="1" value={fk.upper_stanchion ?? 425}
        on:change={e => upd({ upper_stanchion: +e.target.value })} />
    </label>
    <label>Largeur lame (mm)
      <input type="number" step="1" value={fk.blade_width ?? 32}
        on:change={e => upd({ blade_width: +e.target.value })} />
    </label>
  </fieldset>

  <fieldset>
    <legend>Type</legend>
    <label class="check">
      <input type="checkbox" checked={fk.dual_crown ?? true}
        on:change={e => upd({ dual_crown: e.target.checked })} />
      Double couronne
    </label>
    <label>Style BikeCAD
      <select value={fk.fork_style ?? 1}
        on:change={e => upd({ fork_style: +e.target.value })}>
        <option value={0}>Rigide</option>
        <option value={1}>Suspendu</option>
        <option value={2}>Carbon straight</option>
      </select>
    </label>
  </fieldset>

  <fieldset>
    <legend>Frein (trou de fixation)</legend>
    <label>Trou frein → couronne (mm)
      <input type="number" step="1" value={fk.brake_hole_to_crown ?? 490}
        on:change={e => upd({ brake_hole_to_crown: +e.target.value })} />
    </label>
    <label>Trou frein → axe (mm)
      <input type="number" step="1" value={fk.brake_hole_to_axle ?? 0}
        on:change={e => upd({ brake_hole_to_axle: +e.target.value })} />
    </label>
  </fieldset>
</section>
