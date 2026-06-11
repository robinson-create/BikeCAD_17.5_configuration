<script>
  import { bike, transmission, updateSection } from '../lib/store.js'
  import Diagram from '../lib/Diagram.svelte'
  import { listMotors, listIgh } from '../lib/api.js'
  import { onMount } from 'svelte'

  $: dt = $bike?.drivetrain ?? {}
  $: tx = $transmission
  const upd = patch => updateSection('drivetrain', patch)

  let motors = []
  let ighList = []
  onMount(async () => {
    motors = await listMotors()
    ighList = await listIgh()
  })

  $: isBelt = (dt.drive_type ?? 'belt') === 'belt'
  $: isIgh = (dt.transmission ?? 'derailleur') === 'igh'
</script>

<section class="panel">
  <h3>Transmission</h3>
  <Diagram src="BELT_WIDTH.png" caption="Courroie / chaîne"
    legend={[{k:'W', v:'Largeur courroie'}, {k:'P', v:'Pas (pitch)'}]} />

  <fieldset>
    <legend>Système</legend>
    <label>Type de transmission
      <select value={dt.transmission ?? 'derailleur'}
        on:change={e => upd({ transmission: e.target.value })}>
        <option value="derailleur">Dérailleur + cassette</option>
        <option value="igh">Moyeu à vitesses (IGH)</option>
      </select>
    </label>
    {#if isIgh}
      <label>Moyeu IGH
        <select value={dt.igh_model ?? 'rohloff_14'}
          on:change={e => upd({ igh_model: e.target.value })}>
          {#each ighList as h}
            <option value={h.key}>{h.label} — {h.gears}v · {h.range_pct}%</option>
          {/each}
          <option value="custom">Personnalisé</option>
        </select>
      </label>
      <label>Couple moteur au pédalier (Nm)
        <input type="number" step="5" value={dt.motor_torque_nm ?? 150}
          on:change={e => upd({ motor_torque_nm: +e.target.value })} />
      </label>
    {/if}

    {#if tx}
      <table class="tx">
        {#if tx.kind === 'igh'}
          <tr><td>Moyeu</td><td class="v">{tx.label}</td></tr>
          <tr><td>Vitesses · étendue</td><td class="v">{tx.gears}v · {tx.range_pct}%{tx.weight_g ? ` · ${tx.weight_g} g` : ''}</td></tr>
          <tr><td>Rapport primaire (plateau/pignon)</td>
            <td class="v"><span class="badge {tx.ratio_ok ? 'ok' : 'no'}">{tx.primary_ratio}</span> (≥ {tx.min_ratio})</td></tr>
          <tr><td>Couple entrée moyeu</td>
            <td class="v"><span class="badge {tx.torque_ok ? 'ok' : 'no'}">{tx.hub_input_nm} Nm</span> / {tx.max_torque_nm} Nm</td></tr>
        {:else}
          <tr><td>Type</td><td class="v">{tx.label}</td></tr>
          <tr><td>Étendue cassette</td><td class="v">{tx.range_pct}%</td></tr>
          <tr><td>Rapport plateau/pignon</td><td class="v">{tx.primary_ratio}</td></tr>
        {/if}
      </table>
      {#each tx.notes as n}<p class="warn">⚠ {n}</p>{/each}
    {/if}
  </fieldset>

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
        <label><span class="dimkey">P</span>Pas courroie (mm)
          <input type="number" step="0.5" value={dt.belt_pitch ?? 11}
            on:change={e => upd({ belt_pitch: +e.target.value })} />
        </label>
        <label><span class="dimkey">W</span>Largeur courroie (mm)
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

  {#if !isIgh}
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
  {/if}
</section>

<style>
  table.tx { width: 100%; border-collapse: collapse; margin-top: 8px; }
  table.tx td { padding: 4px 6px; border-bottom: 1px solid var(--border); font-size: .74rem; color: var(--text-muted); }
  table.tx td.v { color: var(--text); font-weight: 600; text-align: right; }
  table.tx tr:last-child td { border-bottom: none; }
  .badge { display: inline-block; padding: 0 5px; border-radius: 4px; font-weight: 700; font-size: .72rem; color: #fff; }
  .badge.ok { background: var(--ok); }
  .badge.no { background: var(--no); }
  .warn { color: var(--warn); font-size: .72rem; margin-top: 6px; }
</style>
