<script>
  // Sélecteur de composant catalogue (bibliothèques BikeCAD Pro).
  // Applique le patch {section: {...}} renvoyé par l'API au design courant.
  import { onMount } from 'svelte'
  import { updateSection, scheduleRefresh, bike } from './store.js'
  import { fetchCatalog, loadCatalogPart } from './api.js'

  export let category          // 'fork' | 'saddle' | 'wheel' | 'bike' | ...
  export let label = '📚 Catalogue'
  let parts = []
  let busy = false

  onMount(async () => { parts = await fetchCatalog(category) })

  async function pick(e) {
    const file = e.target.value
    if (!file) return
    busy = true
    try {
      const patch = await loadCatalogPart(category, file)
      if (patch.__full__) {
        // preset de vélo complet → on conserve le nom courant
        scheduleRefresh({ ...patch.__full__, name: patch.__full__.name })
      } else {
        for (const [section, vals] of Object.entries(patch)) updateSection(section, vals)
      }
    } finally {
      busy = false
      e.target.selectedIndex = 0
    }
  }
</script>

{#if parts.length}
  <label class="catalog">{label} ({parts.length})
    <select on:change={pick} disabled={busy}>
      <option value="">— choisir —</option>
      {#each parts as p}
        <option value={p.file}>{p.name}{p.sources ? `  [${p.sources.join('/')}]` : ''}</option>
      {/each}
    </select>
  </label>
{/if}

<style>
  .catalog { display: flex; flex-direction: column; gap: 2px; font-size: .72rem;
             color: #8ecae6; margin-bottom: 8px; }
</style>
