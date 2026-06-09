<script>
  import { bike, updateSection } from '../lib/store.js'
  $: sd = $bike?.saddle ?? {}
  const upd = patch => updateSection('saddle', patch)

  // Dimensions BikeCAD A→N
  const dims = ['a','b','c','d','e','f','g','h','i','j','k','l','m','n']
</script>

<section class="panel">
  <h3>Selle</h3>

  <fieldset>
    <legend>Référence</legend>
    <label>Standard
      <input type="text" value={sd.standard ?? ''}
        on:change={e => upd({ standard: e.target.value })} />
    </label>
    <label>Longueur (mm)
      <input type="number" step="1" value={sd.length ?? 270}
        on:change={e => upd({ length: +e.target.value })} />
    </label>
    <label>Épaisseur (mm)
      <input type="number" step="1" value={sd.thickness ?? 35}
        on:change={e => upd({ thickness: +e.target.value })} />
    </label>
  </fieldset>

  <fieldset>
    <legend>Position</legend>
    <label>Angle selle (°)
      <input type="number" step="0.5" value={sd.angle ?? 0}
        on:change={e => upd({ angle: +e.target.value })} />
    </label>
    <label>Recul setback (mm)
      <input type="number" step="1" value={sd.setback ?? 0}
        on:change={e => upd({ setback: +e.target.value })} />
    </label>
    <label>Référence X (mm)
      <input type="number" step="1" value={sd.ref_point_x ?? 0}
        on:change={e => upd({ ref_point_x: +e.target.value })} />
    </label>
    <label>Référence Y (mm)
      <input type="number" step="1" value={sd.ref_point_y ?? 0}
        on:change={e => upd({ ref_point_y: +e.target.value })} />
    </label>
  </fieldset>

  <fieldset>
    <legend>Dimensions BikeCAD (A→N)</legend>
    <div class="grid-2">
      {#each dims as d}
        <label>{d.toUpperCase()}
          <input type="number" step="0.1" value={sd[d] ?? 0}
            on:change={e => upd({ [d]: +e.target.value })} />
        </label>
      {/each}
    </div>
  </fieldset>
</section>
