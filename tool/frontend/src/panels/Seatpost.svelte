<script>
  import { bike, updateSection } from '../lib/store.js'
  $: sp = $bike?.seatpost ?? {}
  const upd = patch => updateSection('seatpost', patch)

  const styles = [
    { value: 'standard', label: 'Standard' },
    { value: 'dropper',  label: 'Dropper' },
    { value: 'aero',     label: 'Aéro' },
  ]
  $: isDropper = (sp.style ?? 'dropper') === 'dropper'
</script>

<section class="panel">
  <h3>Tige de selle</h3>

  <fieldset>
    <legend>Type</legend>
    <label>Style
      <select value={sp.style ?? 'dropper'}
        on:change={e => upd({ style: e.target.value })}>
        {#each styles as s}
          <option value={s.value}>{s.label}</option>
        {/each}
      </select>
    </label>
    <label>Ø tige (mm)
      <input type="number" step="0.1" value={sp.diameter ?? 30.9}
        on:change={e => upd({ diameter: +e.target.value })} />
    </label>
  </fieldset>

  <fieldset>
    <legend>Dimensions</legend>
    <label>Longueur totale (mm)
      <input type="number" step="5" value={sp.length ?? 440}
        on:change={e => upd({ length: +e.target.value })} />
    </label>
    <label>Longueur exposée (mm)
      <input type="number" step="5" value={sp.exposed ?? 150}
        on:change={e => upd({ exposed: +e.target.value })} />
    </label>
    <label>Recul (mm)
      <input type="number" step="1" value={sp.setback ?? 0}
        on:change={e => upd({ setback: +e.target.value })} />
    </label>
    <label>Longueur de corde (mm)
      <input type="number" step="1" value={sp.chord_length ?? 0}
        on:change={e => upd({ chord_length: +e.target.value })} />
    </label>
    {#if isDropper}
      <label>Course dropper (mm)
        <input type="number" step="5" value={sp.travel ?? 150}
          on:change={e => upd({ travel: +e.target.value })} />
      </label>
    {/if}
  </fieldset>
</section>
