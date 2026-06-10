<script>
  import { bike, updateSection } from '../lib/store.js'
  import Diagram from '../lib/Diagram.svelte'
  import CatalogSelect from '../lib/CatalogSelect.svelte'
  $: st = $bike?.stem ?? {}
  const upd = patch => updateSection('stem', patch)
</script>

<section class="panel">
  <h3>Potence</h3>
  <Diagram src="stemconst.png" caption="Géométrie potence" />
  <CatalogSelect category="stem" />
  <CatalogSelect category="headset" label="📚 Jeu de direction" />

  <fieldset>
    <legend>Dimensions (mm / °)</legend>
    <label>Longueur (mm)
      <input type="number" step="1" value={st.length ?? 50}
        on:change={e => upd({ length: +e.target.value })} />
    </label>
    <label>Angle (°, + = relevé)
      <input type="number" step="0.5" value={st.angle ?? 6}
        on:change={e => upd({ angle: +e.target.value })} />
    </label>
    <label>Offset X (mm)
      <input type="number" step="1" value={st.x ?? 0}
        on:change={e => upd({ x: +e.target.value })} />
    </label>
    <label>Offset Y (mm)
      <input type="number" step="1" value={st.y ?? 0}
        on:change={e => upd({ y: +e.target.value })} />
    </label>
  </fieldset>

  <fieldset>
    <legend>Collier</legend>
    <label>Hauteur collier (mm)
      <input type="number" step="1" value={st.collar_height ?? 25}
        on:change={e => upd({ collar_height: +e.target.value })} />
    </label>
    <label>Ø collier cintre (mm)
      <input type="number" step="0.1" value={st.collar_diameter ?? 31.8}
        on:change={e => upd({ collar_diameter: +e.target.value })} />
    </label>
  </fieldset>

  <fieldset>
    <legend>Jeu de direction / entretoises</legend>
    <label>Stack haut JDD (mm)
      <input type="number" step="0.5" value={$bike?.headset?.upper_stack ?? 8.5}
        on:change={e => updateSection('headset', { upper_stack: +e.target.value })} />
    </label>
    <label>Stack bas JDD (mm)
      <input type="number" step="0.5" value={$bike?.headset?.lower_stack ?? 6.5}
        on:change={e => updateSection('headset', { lower_stack: +e.target.value })} />
    </label>
    <label>Entretoises (mm)
      <input type="number" step="5" value={$bike?.headset?.spacers ?? 20}
        on:change={e => updateSection('headset', { spacers: +e.target.value })} />
    </label>
  </fieldset>
</section>
