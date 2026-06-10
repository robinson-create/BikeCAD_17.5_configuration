<script>
  // Référence exhaustive des réglages BikeCAD (union Pro 16.0 + Free 17.5).
  import { onMount } from 'svelte'
  import { searchSettings, catalogOverview } from './lib/api.js'

  let q = ''
  let res = { total: 0, matched: 0, rows: [] }
  let ov = null
  let timer

  async function run() {
    res = await searchSettings(q, 400)
  }
  function onInput() {
    clearTimeout(timer)
    timer = setTimeout(run, 200)
  }
  onMount(async () => { ov = await catalogOverview(); run() })
</script>

<div class="set-wrap">
  <div class="head">
    <h4>Réglages BikeCAD — référence exhaustive</h4>
    {#if ov}
      <div class="srcs">
        Sources : {#each ov.roots as r}<span class="tag">{r.version}</span>{/each}
        · {ov.total_settings} réglages · pièces :
        {#each Object.entries(ov.categories) as [c, n]}<span class="cat">{c}&nbsp;{n}</span>{/each}
      </div>
    {/if}
    <input class="search" type="text" placeholder="Filtrer une clé (ex. belt, fork, head angle, gearbox…)"
      bind:value={q} on:input={onInput} />
    <div class="count">{res.matched} / {res.total} clés</div>
  </div>

  <div class="rows">
    <table>
      <thead><tr><th>Clé BikeCAD</th><th>Valeur (réf.)</th></tr></thead>
      <tbody>
        {#each res.rows as row}
          <tr><td class="k">{row.key}</td><td class="v">{row.value}</td></tr>
        {/each}
      </tbody>
    </table>
    {#if res.matched > res.rows.length}
      <p class="more">… {res.matched - res.rows.length} autres — affine la recherche.</p>
    {/if}
  </div>
</div>

<style>
  .set-wrap { height: 100%; display: flex; flex-direction: column; background: #1a1a2e; border-radius: 4px; padding: 10px; }
  .head { flex-shrink: 0; }
  h4 { font-size: .85rem; color: #e8851a; margin-bottom: 6px; text-transform: uppercase; letter-spacing: .04em; }
  .srcs { font-size: .68rem; color: #778; margin-bottom: 8px; }
  .tag { background: #1e3a5f; color: #8ecae6; padding: 1px 6px; border-radius: 3px; margin-right: 4px; }
  .cat { color: #99a; margin-right: 8px; }
  .search { width: 100%; padding: 6px 10px; background: #0f0f20; border: 1px solid #333; border-radius: 4px; color: #dde; font-size: .85rem; }
  .count { font-size: .7rem; color: #667; margin: 4px 0; }
  .rows { flex: 1; overflow-y: auto; }
  table { width: 100%; border-collapse: collapse; }
  th { position: sticky; top: 0; background: #16213e; text-align: left; padding: 5px 8px; font-size: .7rem; color: #8ecae6; }
  td { padding: 3px 8px; border-bottom: 1px solid #23233a; font-size: .74rem; }
  td.k { color: #cce; font-family: monospace; }
  td.v { color: #fff; font-variant-numeric: tabular-nums; }
  .more { color: #667; font-size: .72rem; font-style: italic; padding: 8px; }
</style>
