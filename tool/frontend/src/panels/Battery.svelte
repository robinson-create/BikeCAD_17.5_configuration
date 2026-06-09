<script>
  import { bike, battery, updateSection } from '../lib/store.js'
  $: bt = $bike?.battery ?? {}
  $: res = $battery
  const upd = patch => updateSection('battery', patch)
</script>

<section class="panel">
  <h3>Batterie</h3>

  <fieldset>
    <legend>Type</legend>
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
      <input type="number" step="5" value={bt.mount_offset ?? 60}
        on:change={e => upd({ mount_offset: +e.target.value })} />
    </label>
    <label>Jeu tube ↔ pack (mm)
      <input type="number" step="1" value={bt.standoff ?? 8}
        on:change={e => upd({ standoff: +e.target.value })} />
    </label>
  </fieldset>

  {#if res?.enabled}
    <fieldset>
      <legend>Intégration</legend>
      <table class="bat">
        <tr><td>Tient dans le triangle avant</td>
          <td><span class="badge {res.fits_triangle ? 'ok' : 'no'}">{res.fits_triangle ? '✓' : '✗'}</span></td></tr>
        <tr><td>Dégage le carter moteur</td>
          <td><span class="badge {res.clears_motor ? 'ok' : 'no'}">{res.clears_motor ? '✓' : '✗'}</span></td></tr>
        <tr><td>Ne croise aucun tube</td>
          <td><span class="badge {res.clears_tubes ? 'ok' : 'no'}">{res.clears_tubes ? '✓' : '✗'}</span></td></tr>
        <tr><td>Volume du pack</td><td class="v">{res.volume_l} L</td></tr>
        <tr><td>Capacité estimée (volume)</td><td class="v">≈ {res.est_capacity_wh} Wh</td></tr>
      </table>
      {#each res.notes as n}<p class="warn">⚠ {n}</p>{/each}
      <p class="note">Vérification 2D (vue de côté) — aide au pré-dimensionnement, pas un packaging 3D complet.</p>
    </fieldset>
  {/if}
</section>

<style>
  table.bat { width: 100%; border-collapse: collapse; }
  table.bat td { padding: 4px 6px; border-bottom: 1px solid #2a2a4a; font-size: .76rem; color: #aab; }
  table.bat td.v { color: #fff; font-weight: 600; text-align: right; font-variant-numeric: tabular-nums; }
  table.bat td:last-child { text-align: right; }
  .badge { display: inline-block; width: 16px; height: 16px; line-height: 16px; text-align: center; border-radius: 50%; font-size: .68rem; font-weight: 700; }
  .badge.ok { background: #2e7d32; color: #fff; }
  .badge.no { background: #c0392b; color: #fff; }
  .warn { color: #e8a; font-size: .72rem; margin-top: 6px; }
  .note { color: #667; font-size: .66rem; font-style: italic; margin-top: 8px; }
</style>
