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
    const isFull = category === 'bike'
    try {
      const patch = await loadCatalogPart(category, file)
      if (patch.__full__) {
        // preset de vélo COMPLET → on charge tout (nom inclus → titre + specs + preview)
        scheduleRefresh({ ...patch.__full__ })
      } else {
        for (const [section, vals] of Object.entries(patch)) updateSection(section, vals)
      }
    } finally {
      busy = false
      // composant ponctuel → on ré-arme le sélecteur ; vélo complet → on GARDE
      // la sélection visible pour montrer le modèle chargé.
      if (!isFull) e.target.selectedIndex = 0
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
             color: var(--accent); margin-bottom: 8px; }
  .catalog select { background: var(--surface); color: var(--text);
             border: 1px solid var(--border); border-radius: var(--radius);
             padding: 4px 6px; font-size: .78rem; }
  .catalog select:disabled { color: var(--text-muted); }
</style>
