<script>
  import { bike, updateSection } from '../lib/store.js'
  $: wf = $bike?.wheel_f ?? {}
  $: wr = $bike?.wheel_r ?? {}

  const bsdOptions = [
    { value: 559, label: '559 — 26"' },
    { value: 584, label: '584 — 27.5"' },
    { value: 622, label: '622 — 29" / 700c' },
  ]

  // Le calcul géométrique lit le Ø roue dans frame.wheel_f/wheel_r :
  // on synchronise le Ø pneu de la roue avec le cadre.
  function setTireDia(sec, val) {
    updateSection(sec, { tire_diameter: +val })
    updateSection('frame', sec === 'wheel_f' ? { wheel_f: +val } : { wheel_r: +val })
  }
</script>

<section class="panel">
  <h3>Roues</h3>

  {#each [['wheel_f', wf, 'Roue avant'], ['wheel_r', wr, 'Roue arrière']] as [sec, w, title]}
    <fieldset>
      <legend>{title}</legend>
      <label>Ø extérieur pneu (mm)
        <input type="number" step="1" value={w.tire_diameter ?? 736}
          on:change={e => setTireDia(sec, e.target.value)} />
      </label>
      <label>Largeur pneu (mm)
        <input type="number" step="1" value={w.tire_width ?? 61}
          on:change={e => updateSection(sec, { tire_width: +e.target.value })} />
      </label>
      <label>BSD / ETRTO (mm)
        <select value={w.bead_seat_dia ?? 622}
          on:change={e => updateSection(sec, { bead_seat_dia: +e.target.value })}>
          {#each bsdOptions as o}
            <option value={o.value}>{o.label}</option>
          {/each}
        </select>
      </label>
      <label>Profil de jante (mm)
        <input type="number" step="1" value={w.rim_depth ?? 25}
          on:change={e => updateSection(sec, { rim_depth: +e.target.value })} />
      </label>
      <div class="grid-2">
        <label>Nb rayons
          <input type="number" step="1" value={w.spokes ?? 32}
            on:change={e => updateSection(sec, { spokes: +e.target.value })} />
        </label>
        <label>Croisement
          <input type="number" step="1" value={w.cross_pattern ?? 3}
            on:change={e => updateSection(sec, { cross_pattern: +e.target.value })} />
        </label>
      </div>
      <div class="grid-2">
        <label>Ø flasque DS (mm)
          <input type="number" step="1" value={w.hub_flange_dia_ds ?? 58}
            on:change={e => updateSection(sec, { hub_flange_dia_ds: +e.target.value })} />
        </label>
        <label>Ø flasque NDS (mm)
          <input type="number" step="1" value={w.hub_flange_dia_nd ?? 58}
            on:change={e => updateSection(sec, { hub_flange_dia_nd: +e.target.value })} />
        </label>
      </div>
      <div class="grid-2">
        <label>Dist. flasque DS (mm)
          <input type="number" step="0.5" value={w.flange_dist_ds ?? 17}
            on:change={e => updateSection(sec, { flange_dist_ds: +e.target.value })} />
        </label>
        <label>Dist. flasque NDS (mm)
          <input type="number" step="0.5" value={w.flange_dist_nd ?? 34}
            on:change={e => updateSection(sec, { flange_dist_nd: +e.target.value })} />
        </label>
      </div>
    </fieldset>
  {/each}
</section>
