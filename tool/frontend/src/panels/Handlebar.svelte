<script>
  import { bike, updateSection } from '../lib/store.js'
  $: hb = $bike?.handlebar ?? {}
  const upd = patch => updateSection('handlebar', patch)

  const styles = [
    { value: 'flat_mtn',     label: 'Plat VTT' },
    { value: 'BMX',          label: 'BMX' },
    { value: 'drop_anatomic',label: 'Route anatomique' },
    { value: 'drop_compact', label: 'Route compact' },
    { value: 'drop_ergo',    label: 'Route ergo' },
    { value: 'bullhorn',     label: 'Bullhorn' },
    { value: 'track',        label: 'Piste' },
  ]
  $: isFlat = ['flat_mtn','BMX'].includes(hb.style ?? 'flat_mtn')
</script>

<section class="panel">
  <h3>Cintre</h3>

  <fieldset>
    <legend>Type</legend>
    <label>Style
      <select value={hb.style ?? 'flat_mtn'}
        on:change={e => upd({ style: e.target.value })}>
        {#each styles as s}
          <option value={s.value}>{s.label}</option>
        {/each}
      </select>
    </label>
    <label>Ø centre (mm)
      <input type="number" step="0.1" value={hb.diameter ?? 31.8}
        on:change={e => upd({ diameter: +e.target.value })} />
    </label>
  </fieldset>

  <fieldset>
    <legend>Dimensions</legend>
    <label>Largeur hors-tout (mm)
      <input type="number" step="5" value={hb.width ?? 760}
        on:change={e => upd({ width: +e.target.value })} />
    </label>
    <label>Relevé / rise (mm)
      <input type="number" step="1" value={hb.rise ?? 20}
        on:change={e => upd({ rise: +e.target.value })} />
    </label>
    {#if isFlat}
      <label>Sweep arrière (°)
        <input type="number" step="1" value={hb.sweep ?? 9}
          on:change={e => upd({ sweep: +e.target.value })} />
      </label>
      <label>Ø poignée (mm)
        <input type="number" step="0.5" value={hb.grip_dia ?? 22}
          on:change={e => upd({ grip_dia: +e.target.value })} />
      </label>
    {:else}
      <label>Reach cintre (mm)
        <input type="number" step="1" value={hb.reach ?? 80}
          on:change={e => upd({ reach: +e.target.value })} />
      </label>
      <label>Drop (mm)
        <input type="number" step="1" value={hb.drop ?? 125}
          on:change={e => upd({ drop: +e.target.value })} />
      </label>
    {/if}
  </fieldset>

  <fieldset>
    <legend>Orientation</legend>
    <label>Alpha (°)
      <input type="number" step="1" value={hb.alpha ?? 0}
        on:change={e => upd({ alpha: +e.target.value })} />
    </label>
    <label>Theta (°)
      <input type="number" step="1" value={hb.theta ?? 0}
        on:change={e => upd({ theta: +e.target.value })} />
    </label>
    <label>Extension (mm)
      <input type="number" step="5" value={hb.extend ?? 0}
        on:change={e => upd({ extend: +e.target.value })} />
    </label>
    <label class="check">
      <input type="checkbox" checked={hb.include_brakes ?? true}
        on:change={e => upd({ include_brakes: e.target.checked })} />
      Inclure leviers de frein
    </label>
  </fieldset>
</section>
