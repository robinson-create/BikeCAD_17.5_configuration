<script>
  import { bike, updateSection } from '../lib/store.js'
  $: f = $bike?.frame ?? {}
  const upd = patch => updateSection('frame', patch)
</script>

<section class="panel">
  <h3>Géométrie cadre</h3>

  <fieldset>
    <legend>Angles</legend>
    <label><span class="dimkey">HA</span>Angle de direction (°)
      <input type="number" step="0.1" value={f.head_angle ?? 64}
        on:change={e => upd({ head_angle: +e.target.value })} />
    </label>
    <label><span class="dimkey">STA</span>Angle tube de selle (°)
      <input type="number" step="0.1" value={f.seat_angle ?? 78}
        on:change={e => upd({ seat_angle: +e.target.value })} />
    </label>
  </fieldset>

  <fieldset>
    <legend>Longueurs (mm)</legend>
    <label><span class="dimkey">CS</span>Bases
      <input type="number" step="1" value={f.cs ?? 435}
        on:change={e => upd({ cs: +e.target.value })} />
    </label>
    <label><span class="dimkey">BB</span>Chute BB
      <input type="number" step="1" value={f.bb_drop ?? 30}
        on:change={e => upd({ bb_drop: +e.target.value })} />
    </label>
    <label><span class="dimkey">FCD</span>Front center
      <input type="number" step="1" value={f.fcd ?? 820}
        on:change={e => upd({ fcd: +e.target.value })} />
    </label>
    <label><span class="dimkey">ST</span>Tube de selle c-c
      <input type="number" step="1" value={f.seat_tube ?? 423}
        on:change={e => upd({ seat_tube: +e.target.value })} />
    </label>
    <label><span class="dimkey">HT</span>Tube de direction
      <input type="number" step="1" value={f.head_tube ?? 125}
        on:change={e => upd({ head_tube: +e.target.value })} />
    </label>
    <label>Extension HT haut
      <input type="number" step="1" value={f.head_tube_upper_ext ?? 0}
        on:change={e => upd({ head_tube_upper_ext: +e.target.value })} />
    </label>
    <label>Extension HT bas
      <input type="number" step="1" value={f.head_tube_lower_ext ?? 0}
        on:change={e => upd({ head_tube_lower_ext: +e.target.value })} />
    </label>
  </fieldset>

  <fieldset>
    <legend>Diamètres tubes (mm)</legend>
    <label>Tube horizontal Ø
      <input type="number" step="0.5" value={f.top_tube_d ?? 38}
        on:change={e => upd({ top_tube_d: +e.target.value })} />
    </label>
    <label>Tube diagonal Ø
      <input type="number" step="0.5" value={f.down_tube_d ?? 44}
        on:change={e => upd({ down_tube_d: +e.target.value })} />
    </label>
    <label>Tube de selle Ø avant
      <input type="number" step="0.5" value={f.seat_tube_fd ?? 35}
        on:change={e => upd({ seat_tube_fd: +e.target.value })} />
    </label>
    <label>Tube de direction Ø
      <input type="number" step="0.5" value={f.head_tube_d ?? 44}
        on:change={e => upd({ head_tube_d: +e.target.value })} />
    </label>
    <label>Bases Ø
      <input type="number" step="0.5" value={f.chainstay_d ?? 32}
        on:change={e => upd({ chainstay_d: +e.target.value })} />
    </label>
    <label>Haubans Ø
      <input type="number" step="0.5" value={f.seatstay_d ?? 20}
        on:change={e => upd({ seatstay_d: +e.target.value })} />
    </label>
  </fieldset>

  <fieldset>
    <legend>Boîtier de pédalier</legend>
    <label>Largeur BB (mm)
      <input type="number" step="1" value={f.bb_width ?? 68}
        on:change={e => upd({ bb_width: +e.target.value })} />
    </label>
    <label>Ø extérieur BB (mm)
      <input type="number" step="0.1" value={f.bb_shell_d ?? 34.8}
        on:change={e => upd({ bb_shell_d: +e.target.value })} />
    </label>
  </fieldset>

  <fieldset>
    <legend>Roues</legend>
    <label>Ø roue avant (mm)
      <input type="number" step="1" value={f.wheel_f ?? 736}
        on:change={e => upd({ wheel_f: +e.target.value })} />
    </label>
    <label>Ø roue arrière (mm)
      <input type="number" step="1" value={f.wheel_r ?? 736}
        on:change={e => upd({ wheel_r: +e.target.value })} />
    </label>
  </fieldset>
</section>
