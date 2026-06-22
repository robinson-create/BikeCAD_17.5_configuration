<script>
  // Fenêtre d'export des TUBES — « savoir exactement ce qu'il faut ».
  // Nomenclature d'achat (barres à commander) + aperçu live de l'export choisi
  // (fiche de fabrication / nomenclature), avec téléchargement.
  import { onMount } from 'svelte'
  import { bike } from './store.js'
  import Modal from './Modal.svelte'
  import { fetchTubes, fetchMaterials, fetchTubeExport, exportTubes, downloadText, slug } from './api.js'

  let res = null
  let materials = []
  let adhesives = []
  let adhesive = 'dp460'
  let fmt = 'fab_summary'
  let preview = ''
  let loading = false

  const FORMATS = [
    { key: 'fab_summary', label: 'Fiche de fabrication (texte)' },
    { key: 'fab_csv',     label: 'Fiche de fabrication (CSV)' },
    { key: 'summary',     label: 'Nomenclature tubes (texte)' },
    { key: 'csv',         label: 'Nomenclature tubes (CSV)' },
    { key: 'json',        label: 'Données complètes (JSON)' },
  ]

  onMount(async () => {
    const m = await fetchMaterials()
    materials = m.materials ?? []
    adhesives = m.adhesives ?? []
  })

  async function refresh(b, fmt_, adh) {
    if (!b) return
    loading = true
    try {
      res = await fetchTubes(b, 0, 'down_tube', adh)
      preview = await fetchTubeExport(b, fmt_, 0, 'down_tube', adh)
    } catch (e) { preview = 'Erreur : ' + (e.message ?? e) }
    loading = false
  }
  $: refresh($bike, fmt, adhesive)

  const matLabel = k => (materials.find(m => m.key === k)?.label) ?? k

  function copy() { navigator.clipboard?.writeText(preview) }
  function download() {
    const ext = (fmt === 'csv' || fmt === 'fab_csv') ? 'csv' : (fmt === 'json' ? 'json' : 'txt')
    const base = fmt.startsWith('fab') ? `${slug($bike)}_fabrication_tubes` : `${slug($bike)}_tubes_lugs`
    downloadText(`${base}.${ext}`, preview, fmt === 'json' ? 'application/json' : 'text/plain')
  }
</script>

<Modal title="Export des tubes — fabrication & achat" icon="▭" wide on:close>
  <div class="bar">
    <label class="il">Adhésif (collage lug)
      <select bind:value={adhesive}>
        {#each adhesives as a}<option value={a.key}>{a.label} (τ_adm {a.tau_adm} MPa)</option>{/each}
      </select>
    </label>
    <label class="il">Format d'export
      <select bind:value={fmt}>
        {#each FORMATS as f}<option value={f.key}>{f.label}</option>{/each}
      </select>
    </label>
  </div>

  {#if res}
    <h4>Nomenclature d'achat — ce qu'il faut commander</h4>
    <table class="grid">
      <thead><tr><th>Spec à commander</th><th>Membres</th><th>Nb</th>
        <th>Long. totale</th><th>Barre conseillée</th><th>Masse</th></tr></thead>
      <tbody>
        {#each (res.bom ?? []) as b}
          <tr>
            <td class="l"><strong>{b.stock_label}</strong></td>
            <td class="l sm">{b.members.join(', ')}</td>
            <td>{b.count}</td>
            <td>{b.total_length_mm} mm</td>
            <td><strong>{b.stock_length_mm} mm</strong></td>
            <td>{Math.round(b.total_mass_g)} g</td>
          </tr>
        {/each}
      </tbody>
    </table>
    <p class="tot">Masse tubes (cadre nu) ≈ <strong>{res.total_mass_g} g</strong> ·
      tubes {matLabel(res.frame_material)} · lugs {res.lug_material_props?.label ?? res.lug_material}.
      Barre conseillée = longueur totale +12 % de chute (coupe/onglet), arrondie aux 50 mm.</p>
  {/if}

  <h4>Aperçu de l'export {loading ? '…' : ''}</h4>
  <pre class="prev">{preview}</pre>

  <svelte:fragment slot="footer">
    <span class="note">Fiche de fabrication = tubes ↔ jonctions de lugs (emmanchements, alésages, angles).</span>
    <button class="btn ghost" on:click={copy}>Copier</button>
    <button class="btn primary" on:click={download}>⬇ Télécharger</button>
  </svelte:fragment>
</Modal>

<style>
  .bar { display: flex; gap: 14px; flex-wrap: wrap; margin-bottom: 12px; }
  .il { display: flex; flex-direction: column; gap: 3px; font-size: .74rem; color: var(--text-muted); min-width: 240px; }
  h4 { font-size: .82rem; color: var(--accent); margin: 14px 0 6px; }
  table.grid { width: 100%; border-collapse: collapse; font-size: .78rem; }
  table.grid th { background: #f3f5f9; color: var(--text-muted); border: 1px solid var(--border); padding: 5px 7px; text-align: right; }
  table.grid td { border: 1px solid var(--border); padding: 4px 7px; text-align: right; }
  table.grid td.l, table.grid th:first-child { text-align: left; }
  td.sm { font-size: .72rem; color: var(--text-muted); }
  .tot { font-size: .76rem; color: var(--text-muted); margin: 8px 0 0; line-height: 1.45; }
  .prev {
    background: #0f1722; color: #d7e0ea; border-radius: 7px; padding: 12px;
    font-family: 'SF Mono', ui-monospace, monospace; font-size: 11px; line-height: 1.5;
    max-height: 320px; overflow: auto; white-space: pre; margin: 0;
  }
  .note { font-size: .72rem; color: var(--text-muted); margin-right: auto; }
  .btn { padding: 6px 13px; border-radius: var(--radius); border: 1px solid var(--border-strong);
         background: #fff; color: var(--text); cursor: pointer; font-size: .8rem; }
  .btn.ghost:hover { background: var(--accent-soft); border-color: var(--accent); color: var(--accent); }
  .btn.primary { background: var(--accent); border-color: var(--accent); color: #fff; font-weight: 600; }
  .btn.primary:hover { filter: brightness(1.06); }
</style>
