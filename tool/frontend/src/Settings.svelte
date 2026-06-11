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
  .set-wrap { height: 100%; display: flex; flex-direction: column; background: var(--panel); border: 1px solid var(--border); border-radius: var(--radius); padding: 10px; }
  .head { flex-shrink: 0; }
  h4 { font-size: .85rem; color: var(--brand); margin-bottom: 6px; text-transform: uppercase; letter-spacing: .04em; }
  .srcs { font-size: .68rem; color: var(--text-muted); margin-bottom: 8px; }
  .tag { background: var(--accent-soft); color: var(--accent); padding: 1px 6px; border-radius: 3px; margin-right: 4px; }
  .cat { color: var(--text-muted); margin-right: 8px; }
  .search { width: 100%; padding: 6px 10px; background: var(--surface); border: 1px solid var(--border-strong); border-radius: 4px; color: var(--text); font-size: .85rem; }
  .count { font-size: .7rem; color: var(--text-muted); margin: 4px 0; }
  .rows { flex: 1; overflow-y: auto; }
  table { width: 100%; border-collapse: collapse; }
  th { position: sticky; top: 0; background: var(--surface); text-align: left; padding: 5px 8px; font-size: .7rem; color: var(--accent); }
  td { padding: 3px 8px; border-bottom: 1px solid var(--border); font-size: .74rem; }
  td.k { color: var(--text); font-family: monospace; }
  td.v { color: var(--text); font-variant-numeric: tabular-nums; }
  .more { color: var(--text-muted); font-size: .72rem; font-style: italic; padding: 8px; }
</style>
