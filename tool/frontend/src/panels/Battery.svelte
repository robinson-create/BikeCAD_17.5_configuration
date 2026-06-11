<script>
  import { bike, battery, updateSection } from '../lib/store.js'
  $: bt = $bike?.battery ?? {}
  $: res = $battery
  const upd = patch => updateSection('battery', patch)
</script>

<section class="panel">
  <h3>Batterie &amp; alimentation</h3>

  <fieldset>
    <legend>Énergie</legend>
    <label class="check">
      <input type="checkbox" checked={bt.enabled ?? true}
        on:change={e => upd({ enabled: e.target.checked })} />
      Batterie présente
    </label>
    <div class="grid-2">
      <label>Tension (V)
        <input type="number" step="1" value={bt.voltage ?? 52}
          on:change={e => upd({ voltage: +e.target.value })} />
      </label>
      <label>Capacité (Wh)
        <input type="number" step="20" value={bt.capacity_wh ?? 960}
          on:change={e => upd({ capacity_wh: +e.target.value })} />
      </label>
    </div>
    <label class="check">
      <input type="checkbox" checked={bt.in_downtube ?? false}
        on:change={e => upd({ in_downtube: e.target.checked })} />
      Intégrée dans le tube diagonal
    </label>
  </fieldset>

  <fieldset>
    <legend>Puissance moteur</legend>
    <div class="grid-2">
      <label>Nominale (W)
        <input type="number" step="50" value={bt.nominal_power_w ?? 500}
          on:change={e => upd({ nominal_power_w: +e.target.value })} />
      </label>
      <label>Crête (W)
        <input type="number" step="50" value={bt.peak_power_w ?? 1000}
          on:change={e => upd({ peak_power_w: +e.target.value })} />
      </label>
    </div>
    <label>Conso de référence (Wh/km)
      <input type="number" step="1" value={bt.consumption_whkm ?? 14}
        on:change={e => upd({ consumption_whkm: +e.target.value })} />
    </label>
  </fieldset>

  <fieldset>
    <legend>Encombrement du pack (mm)</legend>
    <div class="grid-2">
      <label>Longueur
        <input type="number" step="5" value={bt.length ?? 380}
          on:change={e => upd({ length: +e.target.value })} />
      </label>
      <label>Hauteur
        <input type="number" step="5" value={bt.height ?? 90}
          on:change={e => upd({ height: +e.target.value })} />
      </label>
    </div>
    <label>Largeur transversale
      <input type="number" step="5" value={bt.width ?? 90}
        on:change={e => upd({ width: +e.target.value })} />
    </label>
  </fieldset>

  <fieldset>
    <legend>Placement (le long du tube diagonal)</legend>
    <label>Décalage depuis le BB (mm)
      <input type="number" step="5" value={bt.mount_offset ?? 120}
        on:change={e => upd({ mount_offset: +e.target.value })} />
    </label>
    <label>Jeu surface tube ↔ pack (mm)
      <input type="number" step="1" value={bt.standoff ?? 8}
        on:change={e => upd({ standoff: +e.target.value })} />
    </label>
  </fieldset>

  {#if res?.enabled}
    <fieldset>
      <legend>Autonomie estimée</legend>
      <div class="auto">
        {#each (res.autonomy ?? []) as a}
          <div class="acard {a.mode === 'Boost' ? 'hot' : a.mode === 'Éco' ? 'cool' : ''}">
            <div class="amode">{a.mode}</div>
            <div class="akm">{a.km}<span>km</span></div>
            <div class="awh">{a.whkm} Wh/km</div>
          </div>
        {/each}
      </div>
    </fieldset>

    <fieldset>
      <legend>Alimentation</legend>
      <table class="bat">
        <tr><td>Capacité</td><td class="v">{res.capacity_ah} Ah · {bt.capacity_wh} Wh</td></tr>
        <tr><td>Courant nominal</td><td class="v">{res.nominal_current_a} A</td></tr>
        <tr><td>Courant crête</td><td class="v">{res.peak_current_a} A ({res.c_rate_peak}C)</td></tr>
        <tr><td>Tenue à puissance crête</td><td class="v">{res.runtime_peak_min} min</td></tr>
        <tr><td>Autonomie à P nominale</td><td class="v">{res.runtime_nominal_h} h</td></tr>
      </table>
    </fieldset>

    <fieldset>
      <legend>Intégration (vue 2D)</legend>
      <table class="bat">
        <tr><td>Tient dans le triangle avant</td>
          <td><span class="badge {res.fits_triangle ? 'ok' : 'no'}">{res.fits_triangle ? '✓' : '✗'}</span></td></tr>
        <tr><td>Dégage le carter moteur</td>
          <td><span class="badge {res.clears_motor ? 'ok' : 'no'}">{res.clears_motor ? '✓' : '✗'}</span></td></tr>
        <tr><td>Ne croise aucun tube</td>
          <td><span class="badge {res.clears_tubes ? 'ok' : 'no'}">{res.clears_tubes ? '✓' : '✗'}</span></td></tr>
        <tr><td>Volume du pack</td><td class="v">{res.volume_l} L</td></tr>
        <tr><td>Capacité tenable (volume)</td><td class="v">≈ {res.est_capacity_wh} Wh</td></tr>
      </table>
      {#each res.notes as n}<p class="warn">⚠ {n}</p>{/each}
      <p class="note">Estimations 2D / pré-dimensionnement — pas un packaging 3D ni une validation BMS.</p>
    </fieldset>
  {/if}
</section>

<style>
  .auto { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; }
  .acard {
    border: 1px solid var(--border); border-radius: 6px; padding: 7px 4px;
    text-align: center; background: var(--surface);
  }
  .acard.cool { border-color: #9ec5fe; background: #eef5ff; }
  .acard.hot  { border-color: #f3b9b0; background: #fdeeec; }
  .amode { font-size: .62rem; text-transform: uppercase; letter-spacing: .04em; color: var(--text-muted); }
  .akm { font-size: 1.05rem; font-weight: 700; color: var(--text); font-variant-numeric: tabular-nums; }
  .akm span { font-size: .6rem; font-weight: 500; color: var(--text-muted); margin-left: 2px; }
  .awh { font-size: .6rem; color: var(--text-muted); }

  table.bat { width: 100%; border-collapse: collapse; }
  table.bat td { padding: 4px 6px; border-bottom: 1px solid var(--border); font-size: .76rem; color: var(--text-muted); }
  table.bat td.v { color: var(--text); font-weight: 600; text-align: right; font-variant-numeric: tabular-nums; }
  table.bat tr:last-child td { border-bottom: none; }
  .badge { display: inline-block; width: 16px; height: 16px; line-height: 16px; text-align: center; border-radius: 50%; font-size: .68rem; font-weight: 700; }
  .badge.ok { background: var(--ok); color: #fff; }
  .badge.no { background: var(--no); color: #fff; }
  .warn { color: var(--warn); font-size: .72rem; margin-top: 6px; }
  .note { color: var(--text-muted); font-size: .66rem; font-style: italic; margin-top: 8px; }
</style>
