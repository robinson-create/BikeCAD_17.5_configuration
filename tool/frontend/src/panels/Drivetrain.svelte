<script>
  import { bike, updateSection } from '../lib/store.js'
  import { listMotors } from '../lib/api.js'
  import { onMount } from 'svelte'

  $: dt = $bike?.drivetrain ?? {}
  const upd = patch => updateSection('drivetrain', patch)

  let motors = []
  onMount(async () => { motors = await listMotors() })  // [{key,label}]

  $: isBelt = (dt.drive_type ?? 'belt') === 'belt'
</script>

<section class="panel">
  <h3>Transmission</h3>

  <fieldset>
    <legend>Moteur</legend>
    <label class="check">
      <input type="checkbox" checked={dt.use_motor ?? true}
        on:change={e => upd({ use_motor: e.target.checked })} />
      Vélo à assistance (moteur)
    </label>
    {#if dt.use_motor ?? true}
      <label>Type moteur
        <select value={dt.motor_key ?? 'bafang_mm520'}
          on:change={e => upd({ motor_key: e.target.value })}>
          {#each motors as m}
            <option value={m.key}>{m.key}</option>
          {/each}
        </select>
      </label>
      <label>Angle moteur (°)
        <input type="number" step="1" value={dt.motor_angle ?? 0}
          on:change={e => upd({ motor_angle: +e.target.value })} />
      </label>
      <div class="grid-2">
        <label>Offset X (mm)
          <input type="number" step="1" value={dt.motor_x ?? 0}
            on:change={e => upd({ motor_x: +e.target.value })} />
        </label>
        <label>Offset Y (mm)
          <input type="number" step="1" value={dt.motor_y ?? 0}
            on:change={e => upd({ motor_y: +e.target.value })} />
        </label>
      </div>
    {/if}
  </fieldset>

  <fieldset>
    <legend>Chaîne / courroie</legend>
    <label>Type transmission
      <select value={dt.drive_type ?? 'belt'}
        on:change={e => upd({ drive_type: e.target.value })}>
        <option value="belt">Courroie</option>
        <option value="chain">Chaîne</option>
      </select>
    </label>
    {#if isBelt}
      <div class="grid-2">
        <label>Pas courroie (mm)
          <input type="number" step="0.5" value={dt.belt_pitch ?? 11}
            on:change={e => upd({ belt_pitch: +e.target.value })} />
        </label>
        <label>Largeur courroie (mm)
          <input type="number" step="0.5" value={dt.belt_width ?? 11}
            on:change={e => upd({ belt_width: +e.target.value })} />
        </label>
      </div>
      <label>Position galet X (mm)
        <input type="number" step="1" value={dt.idler_x ?? 283}
          on:change={e => upd({ idler_x: +e.target.value })} />
      </label>
    {/if}
  </fieldset>

  <fieldset>
    <legend>Cassette / pignons</legend>
    <label>Référence cassette
      <input type="text" value={dt.sprockets ?? '12-speed+10-50'}
        on:change={e => upd({ sprockets: e.target.value })} />
    </label>
    <div class="grid-2">
      <label>Pignon min (dents)
        <input type="number" step="1" value={dt.rear_cog_min ?? 10}
          on:change={e => upd({ rear_cog_min: +e.target.value })} />
      </label>
      <label>Pignon max (dents)
        <input type="number" step="1" value={dt.rear_cog_max ?? 50}
          on:change={e => upd({ rear_cog_max: +e.target.value })} />
      </label>
    </div>
  </fieldset>
</section>
