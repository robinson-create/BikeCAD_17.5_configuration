<script>
  import { bike, updateSection } from '../lib/store.js'
  import CatalogSelect from '../lib/CatalogSelect.svelte'
  $: cr = $bike?.cranks ?? {}
  const upd = patch => updateSection('cranks', patch)
</script>

<section class="panel">
  <h3>Pédalier</h3>
  <CatalogSelect category="cranks" />

  <fieldset>
    <legend>Manivelles</legend>
    <label>Référence
      <input type="text" value={cr.standard ?? ''}
        on:change={e => upd({ standard: e.target.value })} />
    </label>
    <label>Longueur manivelle (mm)
      <input type="number" step="2.5" value={cr.crank_length ?? 165}
        on:change={e => upd({ crank_length: +e.target.value })} />
    </label>
    <label>Q-factor (mm)
      <input type="number" step="1" value={cr.q_factor ?? 168}
        on:change={e => upd({ q_factor: +e.target.value })} />
    </label>
    <label>Épaisseur bras (mm)
      <input type="number" step="0.5" value={cr.arm_thickness ?? 12}
        on:change={e => upd({ arm_thickness: +e.target.value })} />
    </label>
  </fieldset>

  <fieldset>
    <legend>Plateaux</legend>
    <label>Nombre de plateaux
      <input type="number" step="1" min="1" max="3" value={cr.chainrings ?? 1}
        on:change={e => upd({ chainrings: +e.target.value })} />
    </label>
    <div class="grid-2">
      <label>Dents plateau 1
        <input type="number" step="1" value={cr.teeth_0 ?? 36}
          on:change={e => upd({ teeth_0: +e.target.value })} />
      </label>
      <label>Dents plateau 2
        <input type="number" step="1" value={cr.teeth_1 ?? 0}
          on:change={e => upd({ teeth_1: +e.target.value })} />
      </label>
    </div>
    <label>Ø araignée (mm)
      <input type="number" step="1" value={cr.spider_dia ?? 64}
        on:change={e => upd({ spider_dia: +e.target.value })} />
    </label>
    <label>Largeur bras araignée (mm)
      <input type="number" step="0.5" value={cr.spider_arm_width ?? 12}
        on:change={e => upd({ spider_arm_width: +e.target.value })} />
    </label>
  </fieldset>

  <fieldset>
    <legend>Largeurs (BB / pédale)</legend>
    <label>Largeur au boîtier (mm)
      <input type="number" step="1" value={cr.width_at_bb ?? 68}
        on:change={e => upd({ width_at_bb: +e.target.value })} />
    </label>
    <label>Largeur à la pédale (mm)
      <input type="number" step="1" value={cr.width_at_pedal ?? 168}
        on:change={e => upd({ width_at_pedal: +e.target.value })} />
    </label>
    <label>Jeu manivelle/base (mm)
      <input type="number" step="0.5" value={cr.crank_clearance ?? 0}
        on:change={e => upd({ crank_clearance: +e.target.value })} />
    </label>
  </fieldset>
</section>
