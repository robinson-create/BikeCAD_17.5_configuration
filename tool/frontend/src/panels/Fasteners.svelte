<script>
  import { bike, fasteners, showFasteners, scheduleRefresh } from '../lib/store.js'
  import { exportFasteners } from '../lib/api.js'

  // Couleurs alignées sur _FAST_CAT_COL (svg_export.py)
  const CAT_COL = {
    'Cockpit': '#2980b9', 'Tige de selle': '#8e44ad', 'Freins': '#c0392b',
    'Roues': '#16a085', 'Transmission': '#d35400', 'Moteur': '#2c3e50',
    'Suspension': '#e67e22', 'Divers': '#7f8c8d',
  }

  $: res = $fasteners
  // Regroupe les items par catégorie en préservant l'ordre d'apparition
  $: groups = (() => {
    const g = []
    for (const it of (res?.items ?? [])) {
      let grp = g.find(x => x.cat === it.category)
      if (!grp) { grp = { cat: it.category, items: [] }; g.push(grp) }
      grp.items.push(it)
    }
    return g
  })()
  $: total = (res?.items ?? []).reduce((s, it) => s + it.qty, 0)

  function toggle() {
    $showFasteners = !$showFasteners
    if ($bike) scheduleRefresh($bike)
  }
</script>

<section class="panel">
  <h3>Visserie</h3>
  <p class="hint">
    Chaque point de vis/boulon du vélo + le type choisi (taille, empreinte, couple
    de référence). Couples = specs constructeur — prioriser toujours la valeur
    <strong>gravée sur la pièce</strong>. Dimensionnement fatigue ⇒ bureau d'études.
  </p>

  <div class="row">
    <button class="tg" class:on={$showFasteners} on:click={toggle}>
      {$showFasteners ? '◉' : '○'} Afficher sur la vue 2D
    </button>
    {#if res}<span class="count">{res.items.length} jonctions · {total} vis</span>{/if}
  </div>

  {#if res}
    <div class="exp">
      <span>Export :</span>
      <button on:click={() => exportFasteners($bike, 'csv')}>CSV</button>
      <button on:click={() => exportFasteners($bike, 'json')}>JSON</button>
      <button on:click={() => exportFasteners($bike, 'summary')}>Résumé</button>
    </div>

    {#each groups as grp}
      <fieldset>
        <legend>
          <span class="dot" style="background:{CAT_COL[grp.cat] ?? '#7f8c8d'}"></span>
          {grp.cat}
        </legend>
        <table>
          <thead>
            <tr><th>Jonction</th><th>Taille</th><th>Empreinte</th><th>Qté</th><th>Nm</th></tr>
          </thead>
          <tbody>
            {#each grp.items as it}
              <tr title={it.note}>
                <td>{it.name}</td>
                <td class="mono">{it.size}</td>
                <td>{it.drive}</td>
                <td class="num">×{it.qty}</td>
                <td class="num">{it.torque_nm}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </fieldset>
    {/each}

    <fieldset>
      <legend>Nomenclature</legend>
      <table>
        <tbody>
          {#each res.bom as b}
            <tr><td class="mono">{b.size}</td><td>{b.drive}</td><td class="num">×{b.qty}</td></tr>
          {/each}
        </tbody>
      </table>
    </fieldset>

    {#each (res.notes ?? []) as n}
      <p class="note">• {n}</p>
    {/each}
  {:else}
    <p class="hint">Chargement…</p>
  {/if}
</section>

<style>
  .hint { font-size: 12px; color: #667; line-height: 1.45; margin: 4px 0 10px; }
  .row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
  .count { font-size: 12px; color: #556; }
  .tg { padding: 5px 10px; border: 1px solid #c5ccd6; border-radius: 6px; background: #fff;
        cursor: pointer; font-size: 12px; }
  .tg.on { background: #2980b9; color: #fff; border-color: #2980b9; }
  .exp { display: flex; align-items: center; gap: 6px; font-size: 12px; margin-bottom: 10px; }
  .exp button { padding: 3px 8px; border: 1px solid #c5ccd6; border-radius: 5px;
                background: #f6f8fa; cursor: pointer; }
  .dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%;
         border: 1px solid #0d0f12; margin-right: 5px; vertical-align: middle; }
  table { width: 100%; border-collapse: collapse; font-size: 11.5px; }
  th { text-align: left; color: #889; font-weight: 600; border-bottom: 1px solid #e2e6ec; padding: 2px 4px; }
  td { padding: 3px 4px; border-bottom: 1px solid #eef1f5; vertical-align: top; }
  td.num, .num { text-align: right; white-space: nowrap; }
  .mono { font-family: ui-monospace, monospace; }
  .note { font-size: 11px; color: #778; line-height: 1.4; margin: 6px 0 0; }
</style>
