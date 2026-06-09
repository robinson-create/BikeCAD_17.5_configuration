<script>
  import { bike, updateSection } from '../lib/store.js'
  $: bk = $bike?.brakes ?? {}
  const upd = patch => updateSection('brakes', patch)

  const brakeStyles = [
    { value: 'disc_flat_mount',  label: 'Disque — Flat Mount' },
    { value: 'disc_post_mount',  label: 'Disque — Post Mount' },
    { value: 'disc_is',          label: 'Disque — IS Mount' },
    { value: 'v_brake',          label: 'Patins V-Brake' },
    { value: 'caliper',          label: 'Patins étrier' },
  ]
  $: isDisc = (bk.style ?? 'disc_flat_mount').startsWith('disc')
</script>

<section class="panel">
  <h3>Freins</h3>

  <fieldset>
    <legend>Type</legend>
    <label>Style
      <select value={bk.style ?? 'disc_flat_mount'}
        on:change={e => upd({ style: e.target.value })}>
        {#each brakeStyles as s}
          <option value={s.value}>{s.label}</option>
        {/each}
      </select>
    </label>
    {#if isDisc}
      <label>Type de fixation
        <select value={bk.mount_type ?? 'flat_mount'}
          on:change={e => upd({ mount_type: e.target.value })}>
          <option value="flat_mount">Flat Mount</option>
          <option value="post_mount">Post Mount</option>
          <option value="is_mount">IS Mount</option>
        </select>
      </label>
    {/if}
  </fieldset>

  {#if isDisc}
    <fieldset>
      <legend>Disques</legend>
      <label>Ø disque avant (mm)
        <input type="number" step="10" value={bk.rotor_front ?? 203}
          on:change={e => upd({ rotor_front: +e.target.value })} />
      </label>
      <label>Ø disque arrière (mm)
        <input type="number" step="10" value={bk.rotor_rear ?? 180}
          on:change={e => upd({ rotor_rear: +e.target.value })} />
      </label>
    </fieldset>
  {/if}
</section>
