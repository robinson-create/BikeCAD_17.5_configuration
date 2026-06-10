<script>
  import { onMount } from 'svelte'
  import { activeTab, TABS, bike, scheduleRefresh, viewMode, showDims,
           showSuspension, animateSuspension } from './lib/store.js'
  import { fetchDefault, loadBcad, exportBcad, exportDxf, exportLugs, listBikes,
           saveBikeLibrary, listLibrary, loadLibrary } from './lib/api.js'
  import BikeRenderer from './BikeRenderer.svelte'
  import CatalogSelect from './lib/CatalogSelect.svelte'
  import Kinematics from './Kinematics.svelte'
  import Compare from './Compare.svelte'
  import Settings from './Settings.svelte'
  import Assistant from './Assistant.svelte'

  import Frame      from './panels/Frame.svelte'
  import Fork       from './panels/Fork.svelte'
  import Stem       from './panels/Stem.svelte'
  import Handlebar  from './panels/Handlebar.svelte'
  import Saddle     from './panels/Saddle.svelte'
  import Seatpost   from './panels/Seatpost.svelte'
  import Cranks     from './panels/Cranks.svelte'
  import Drivetrain from './panels/Drivetrain.svelte'
  import Wheels     from './panels/Wheels.svelte'
  import Brakes     from './panels/Brakes.svelte'
  import Suspension from './panels/Suspension.svelte'
  import Battery    from './panels/Battery.svelte'
  import Rider      from './panels/Rider.svelte'

  const PANELS = {
    frame:      Frame,
    fork:       Fork,
    stem:       Stem,
    handlebar:  Handlebar,
    saddle:     Saddle,
    seatpost:   Seatpost,
    cranks:     Cranks,
    drivetrain: Drivetrain,
    wheels:     Wheels,
    brakes:     Brakes,
    suspension: Suspension,
    battery:    Battery,
    rider:      Rider,
  }

  let bikes = []
  let library = []
  let bcadPath = ''
  let status = ''

  onMount(async () => {
    const defaultBike = await fetchDefault()
    if (defaultBike) scheduleRefresh(defaultBike)
    bikes = await listBikes()
    library = await listLibrary()
  })

  async function handleSaveLibrary() {
    if (!$bike) return
    const name = prompt('Nom du vélo à sauvegarder :', $bike.name || 'Mon vélo')
    if (!name) return
    try {
      await saveBikeLibrary({ ...$bike, name }, name)
      library = await listLibrary()
      status = 'Vélo sauvegardé ✓'
    } catch {
      status = 'Erreur sauvegarde'
    }
    setTimeout(() => status = '', 2000)
  }

  async function handleLibrarySelect(e) {
    const file = e.target.value
    if (!file) return
    try {
      const result = await loadLibrary(file)
      if (result) { scheduleRefresh(result); status = 'Vélo chargé ✓' }
    } catch {
      status = 'Erreur chargement'
    }
    setTimeout(() => status = '', 2000)
  }

  async function handleLoadBcad() {
    if (!bcadPath.trim()) return
    const result = await loadBcad(bcadPath.trim())
    if (result) {
      scheduleRefresh(result)
      status = 'Fichier chargé'
      setTimeout(() => status = '', 2000)
    }
  }

  async function handleExportBcad() {
    // Export d'interop BikeCAD Free : fichier SÉPARÉ (le fichier principal garde
    // la courroie). free_safe rétrograde en chaîne pour ne pas crasher Free.
    const slug = ($bike?.name ?? 'bike').replace(/\s+/g, '_')
    const out = `BIKE/${slug}_bikecad_free.bcad`
    const source = 'BIKE/eMTB_DOM_Engineering.bcad'
    try {
      await exportBcad($bike, out, source, true)
      status = `Exporté → ${slug}_bikecad_free.bcad (chaîne, BikeCAD Free)`
    } catch {
      status = 'Erreur export'
    }
    setTimeout(() => status = '', 3500)
  }

  async function handleExportDxf() {
    try {
      await exportDxf($bike)
      status = 'DXF téléchargé ✓'
    } catch {
      status = 'Erreur DXF'
    }
    setTimeout(() => status = '', 2000)
  }

  async function handleExportLugs() {
    try {
      await exportLugs($bike, 'csv')
      status = 'Lugs CSV téléchargé ✓'
    } catch {
      status = 'Erreur lugs'
    }
    setTimeout(() => status = '', 2000)
  }

  async function handleBikeSelect(e) {
    const path = e.target.value
    if (!path) return
    const result = await loadBcad(path)
    if (result) scheduleRefresh(result)
  }
</script>

<div class="app">
  <!-- Top bar -->
  <header class="topbar">
    <div class="brand">DOM Engineering · BikeCAD Tool</div>
    <div class="toolbar">
      <!-- Groupe : design / fichiers -->
      <div class="tgroup">
        <div class="model-select"><CatalogSelect category="bike" label="🚲 Modèle" /></div>
        <select class="tb-select" on:change={handleLibrarySelect} title="Bibliothèque (vélos complets)">
          <option value="">📁 Bibliothèque…</option>
          {#each library as b}<option value={b.file}>{b.name}</option>{/each}
        </select>
        <button class="btn" on:click={handleSaveLibrary} title="Sauvegarde complète JSON (tous composants)">💾 Sauver</button>
        {#if bikes.length > 0}
          <select class="tb-select" on:change={handleBikeSelect} title="Importer un .bcad BikeCAD">
            <option value="">📥 Importer .bcad…</option>
            {#each bikes as b}<option value={b.path}>{b.name}</option>{/each}
          </select>
        {/if}
      </div>

      <!-- Groupe : exports -->
      <div class="tgroup">
        <span class="tlabel">Export</span>
        <button class="btn" on:click={handleExportBcad} title="Fichier .bcad (Free-safe par défaut)">.bcad</button>
        <button class="btn" on:click={handleExportDxf} title="DXF 2D pour SolidWorks">DXF</button>
        <button class="btn" on:click={handleExportLugs} title="Table de conception des lugs">Lugs</button>
      </div>

      <!-- Groupe : affichage (toggles segmentés) -->
      <div class="tgroup">
        <span class="tlabel">Affichage</span>
        <div class="toggles">
          <button class="tg" class:on={$showDims}
            on:click={() => { $showDims = !$showDims; $bike && scheduleRefresh($bike) }}>Cotes</button>
          <button class="tg" class:on={$showSuspension}
            on:click={() => { $showSuspension = !$showSuspension; $bike && scheduleRefresh($bike) }}>Suspension</button>
          <button class="tg" class:on={$animateSuspension} disabled={!$showSuspension}
            on:click={() => { $animateSuspension = !$animateSuspension; $bike && scheduleRefresh($bike) }}>▶ Animer</button>
        </div>
      </div>

      {#if status}<span class="status">{status}</span>{/if}
    </div>
  </header>

  <!-- Main layout -->
  <div class="main">
    <!-- Left: tabs + panel -->
    <aside class="sidebar">
      <nav class="tabs">
        {#each TABS as tab}
          <button
            class="tab-btn"
            class:active={$activeTab === tab.id}
            on:click={() => activeTab.set(tab.id)}>
            {tab.label}
          </button>
        {/each}
      </nav>
      <div class="panel-area">
        {#if PANELS[$activeTab]}
          <svelte:component this={PANELS[$activeTab]} />
        {/if}
      </div>
    </aside>

    <!-- Right: SVG canvas / kinematics -->
    <main class="canvas-area">
      <div class="view-switch">
        <button class:active={$viewMode === 'bike'} on:click={() => viewMode.set('bike')}>Vélo 2D</button>
        <button class:active={$viewMode === 'kinematics'} on:click={() => viewMode.set('kinematics')}>Cinématique</button>
        <button class:active={$viewMode === 'compare'} on:click={() => viewMode.set('compare')}>Comparaison</button>
        <button class:active={$viewMode === 'settings'} on:click={() => viewMode.set('settings')}>Réglages (réf.)</button>
        <button class:active={$viewMode === 'assistant'} on:click={() => viewMode.set('assistant')}>🤖 Assistant</button>
      </div>
      <div class="view-body">
        {#if $viewMode === 'bike'}
          <BikeRenderer />
        {:else if $viewMode === 'kinematics'}
          <Kinematics />
        {:else if $viewMode === 'compare'}
          <Compare />
        {:else if $viewMode === 'settings'}
          <Settings />
        {:else}
          <Assistant />
        {/if}
      </div>
    </main>
  </div>
</div>

<style>
  :global(*) { box-sizing: border-box; margin: 0; padding: 0; }
  :global(body) {
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 13px;
    background: #0f0f1a;
    color: #e2e2f0;
    height: 100vh;
    overflow: hidden;
  }

  .app {
    display: flex;
    flex-direction: column;
    height: 100vh;
  }

  /* Top bar */
  .topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 8px 16px;
    background: linear-gradient(180deg, #1b2740, #15203a);
    border-bottom: 1px solid #2a3654;
    flex-shrink: 0;
  }
  .brand {
    font-weight: 700;
    font-size: .9rem;
    color: #e8851a;
    letter-spacing: .02em;
    white-space: nowrap;
  }
  .toolbar {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
    justify-content: flex-end;
    flex: 1;
  }
  /* groupes logiques séparés par un filet */
  .tgroup {
    display: flex;
    align-items: center;
    gap: 6px;
    padding-right: 10px;
    border-right: 1px solid #2a3654;
  }
  .tgroup:last-of-type { border-right: none; padding-right: 0; }
  .tlabel {
    font-size: .62rem; text-transform: uppercase; letter-spacing: .08em;
    color: #6b7a9a; margin-right: 2px;
  }
  /* boutons d'action */
  .btn {
    padding: 5px 11px;
    border-radius: 6px;
    border: 1px solid #34406a;
    background: #22304f;
    color: #dce6f7;
    cursor: pointer;
    font-size: .78rem;
    transition: background .12s, border-color .12s;
  }
  .btn:hover { background: #2d4170; border-color: #4358a0; }
  .tb-select {
    padding: 5px 8px; border-radius: 6px; border: 1px solid #34406a;
    background: #1a2440; color: #cdd8ee; font-size: .78rem; cursor: pointer;
    max-width: 170px;
  }
  /* toggles segmentés */
  .toggles { display: inline-flex; border: 1px solid #34406a; border-radius: 6px; overflow: hidden; }
  .tg {
    padding: 5px 10px; border: none; border-right: 1px solid #34406a;
    background: #1a2440; color: #93a3c4; cursor: pointer; font-size: .76rem;
  }
  .tg:last-child { border-right: none; }
  .tg:hover:not(:disabled) { background: #243358; color: #cdd8ee; }
  .tg.on { background: #e8851a; color: #1a1a2e; font-weight: 600; }
  .tg:disabled { opacity: .4; cursor: not-allowed; }
  .status { font-size: .76rem; color: #4caf50; white-space: nowrap; }

  /* Main layout */
  .main {
    display: flex;
    flex: 1;
    overflow: hidden;
  }

  /* Sidebar */
  .sidebar {
    display: flex;
    flex-direction: column;
    width: 280px;
    flex-shrink: 0;
    border-right: 1px solid #2a2a4a;
    background: #131324;
    overflow: hidden;
  }
  .tabs {
    display: flex;
    flex-wrap: wrap;
    gap: 2px;
    padding: 6px;
    border-bottom: 1px solid #2a2a4a;
    background: #0f0f1e;
  }
  .tab-btn {
    padding: 3px 8px;
    border: 1px solid transparent;
    border-radius: 3px;
    background: transparent;
    color: #9999bb;
    cursor: pointer;
    font-size: .72rem;
    transition: all .15s;
  }
  .tab-btn:hover { color: #ccc; background: #1a1a3a; }
  .tab-btn.active {
    background: #1e3a5f;
    border-color: #3a5a8f;
    color: #8ecae6;
    font-weight: 600;
  }
  .panel-area {
    flex: 1;
    overflow-y: auto;
    padding: 0;
  }

  /* Panel styles (global) */
  :global(.panel) {
    padding: 12px;
  }
  :global(.panel h3) {
    font-size: .85rem;
    color: #e8851a;
    margin-bottom: 10px;
    padding-bottom: 4px;
    border-bottom: 1px solid #2a2a4a;
    letter-spacing: .04em;
    text-transform: uppercase;
  }
  :global(fieldset) {
    border: 1px solid #2a2a4a;
    border-radius: 4px;
    padding: 8px 10px;
    margin-bottom: 8px;
  }
  :global(legend) {
    font-size: .72rem;
    color: #8ecae6;
    padding: 0 4px;
    text-transform: uppercase;
    letter-spacing: .05em;
  }
  :global(label) {
    display: flex;
    flex-direction: column;
    gap: 2px;
    font-size: .75rem;
    color: #9999bb;
    margin-bottom: 6px;
  }
  :global(label.check) {
    flex-direction: row;
    align-items: center;
    gap: 6px;
  }
  :global(input[type="number"]),
  :global(input[type="text"]),
  :global(select) {
    background: #0f0f20;
    border: 1px solid #333;
    border-radius: 3px;
    color: #dde;
    padding: 3px 6px;
    font-size: .8rem;
    width: 100%;
  }
  :global(input[type="number"]:focus),
  :global(input[type="text"]:focus),
  :global(select:focus) {
    outline: none;
    border-color: #3a5a8f;
  }
  :global(.grid-2) {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 4px;
  }

  /* Canvas */
  .canvas-area {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    padding: 8px;
  }
  .view-switch {
    display: flex;
    gap: 4px;
    margin-bottom: 6px;
    flex-shrink: 0;
  }
  .view-switch button {
    padding: 4px 14px;
    border: 1px solid #2a2a4a;
    border-radius: 3px;
    background: #131324;
    color: #99a;
    cursor: pointer;
    font-size: .78rem;
  }
  .view-switch button.active {
    background: #1e3a5f;
    border-color: #3a5a8f;
    color: #8ecae6;
    font-weight: 600;
  }
  .view-body {
    flex: 1;
    overflow: hidden;
    min-height: 0;
  }
</style>
