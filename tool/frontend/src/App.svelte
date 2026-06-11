<script>
  import { onMount } from 'svelte'
  import { activeTab, GROUPS, bike, scheduleRefresh, viewMode, showDims,
           showSuspension, animateSuspension, showLugs, showPivots } from './lib/store.js'
  import { fetchDefault, loadBcad, exportBcad, exportDxf, exportLugs, exportDrawing, listBikes,
           saveBikeLibrary, listLibrary, loadLibrary } from './lib/api.js'
  import BikeRenderer from './BikeRenderer.svelte'
  import CatalogSelect from './lib/CatalogSelect.svelte'
  import Kinematics from './Kinematics.svelte'
  import Compare from './Compare.svelte'
  import Settings from './Settings.svelte'
  import Assistant from './Assistant.svelte'
  import BikeCADView from './BikeCADView.svelte'

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

  async function handleExportDrawing() {
    try {
      await exportDrawing($bike)
      status = 'Plan technique téléchargé ✓'
    } catch {
      status = 'Erreur plan'
    }
    setTimeout(() => status = '', 2500)
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
        <button class="btn" on:click={handleExportDrawing} title="Plan technique coté (axes, visserie, cartouche)">📐 Plan</button>
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
          <button class="tg" class:on={$showLugs}
            on:click={() => { $showLugs = !$showLugs; $bike && scheduleRefresh($bike) }}>Lugs</button>
          <button class="tg" class:on={$showPivots}
            on:click={() => { $showPivots = !$showPivots; $bike && scheduleRefresh($bike) }}>Pivots</button>
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
        {#each GROUPS as g}
          <button
            class="tab-btn"
            class:active={$activeTab === g.id}
            on:click={() => activeTab.set(g.id)}>
            <span class="tic">{g.icon}</span> {g.label}
          </button>
        {/each}
      </nav>
      <div class="panel-area">
        {#each (GROUPS.find(g => g.id === $activeTab)?.panels ?? []) as pid}
          {#if PANELS[pid]}
            <svelte:component this={PANELS[pid]} />
          {/if}
        {/each}
      </div>
    </aside>

    <!-- Right: SVG canvas / kinematics -->
    <main class="canvas-area">
      <div class="view-switch">
        <button class:active={$viewMode === 'bike'} on:click={() => viewMode.set('bike')}>Vélo 2D</button>
        <button class:active={$viewMode === 'kinematics'} on:click={() => viewMode.set('kinematics')}>Cinématique</button>
        <button class:active={$viewMode === 'compare'} on:click={() => viewMode.set('compare')}>Comparaison</button>
        <button class:active={$viewMode === 'bikecad'} on:click={() => viewMode.set('bikecad')}>🅑 Rendu BikeCAD</button>
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
        {:else if $viewMode === 'bikecad'}
          <BikeCADView />
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
  /* ── Thème CLAIR (variables globales) ─────────────────────────────────────
     Look « outil pro » : fond clair, cartes blanches, 1 accent bleu, texte
     ardoise. Les composants utilisent ces variables (var(--…)). */
  :global(:root) {
    --bg:           #eef0f3;   /* fond application */
    --panel:        #ffffff;   /* cartes / panneaux */
    --surface:      #f7f8fa;   /* surfaces secondaires (onglets) */
    --topbar:       #ffffff;
    --border:       #e3e6eb;
    --border-strong:#ccd2db;
    --text:         #1f2733;
    --text-muted:   #6b7480;
    --accent:       #2563eb;   /* interactif / actif */
    --accent-soft:  #eaf1fe;
    --accent-text:  #ffffff;
    --brand:        #e8851a;   /* orange DOM (titre + état marqué) */
    --ok:           #16a34a;
    --no:           #dc2626;
    --warn:         #b45309;
    --shadow:       0 1px 3px rgba(16,24,40,.08), 0 1px 2px rgba(16,24,40,.04);
    --radius:       7px;
  }
  :global(*) { box-sizing: border-box; margin: 0; padding: 0; }
  :global(body) {
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 13px;
    background: var(--bg);
    color: var(--text);
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
    padding: 9px 16px;
    background: var(--topbar);
    border-bottom: 1px solid var(--border);
    box-shadow: var(--shadow);
    flex-shrink: 0;
    z-index: 5;
  }
  .brand {
    font-weight: 700;
    font-size: .9rem;
    color: var(--brand);
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
    border-right: 1px solid var(--border);
  }
  .tgroup:last-of-type { border-right: none; padding-right: 0; }
  .tlabel {
    font-size: .62rem; text-transform: uppercase; letter-spacing: .08em;
    color: var(--text-muted); margin-right: 2px;
  }
  /* boutons d'action */
  .btn {
    padding: 5px 11px;
    border-radius: var(--radius);
    border: 1px solid var(--border-strong);
    background: #fff;
    color: var(--text);
    cursor: pointer;
    font-size: .78rem;
    transition: background .12s, border-color .12s, box-shadow .12s;
  }
  .btn:hover { background: var(--accent-soft); border-color: var(--accent); color: var(--accent); }
  .tb-select {
    padding: 5px 8px; border-radius: var(--radius); border: 1px solid var(--border-strong);
    background: #fff; color: var(--text); font-size: .78rem; cursor: pointer;
    max-width: 170px;
  }
  /* toggles segmentés */
  .toggles { display: inline-flex; border: 1px solid var(--border-strong); border-radius: var(--radius); overflow: hidden; }
  .tg {
    padding: 5px 10px; border: none; border-right: 1px solid var(--border);
    background: #fff; color: var(--text-muted); cursor: pointer; font-size: .76rem;
  }
  .tg:last-child { border-right: none; }
  .tg:hover:not(:disabled) { background: var(--surface); color: var(--text); }
  .tg.on { background: var(--brand); color: #fff; font-weight: 600; }
  .tg:disabled { opacity: .4; cursor: not-allowed; }
  .status { font-size: .76rem; color: var(--ok); white-space: nowrap; }

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
    width: 340px;
    flex-shrink: 0;
    border-right: 1px solid var(--border);
    background: var(--panel);
    overflow: hidden;
  }
  .tabs {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 5px;
    padding: 8px;
    border-bottom: 1px solid var(--border);
    background: var(--surface);
  }
  .tab-btn {
    display: flex; flex-direction: column; align-items: center; gap: 2px;
    padding: 8px 4px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: #fff;
    color: var(--text-muted);
    cursor: pointer;
    font-size: .72rem;
    transition: all .15s;
  }
  .tab-btn .tic { font-size: 1.05rem; line-height: 1; }
  .tab-btn:hover { color: var(--text); border-color: var(--border-strong); }
  .tab-btn.active {
    background: var(--accent-soft);
    border-color: var(--accent);
    color: var(--accent);
    font-weight: 600;
  }
  .panel-area {
    flex: 1;
    overflow-y: auto;
    padding: 0;
    background: var(--bg);
  }

  /* Panel styles (global) */
  :global(.panel) {
    padding: 12px;
  }
  :global(.panel h3) {
    font-size: .85rem;
    color: var(--brand);
    margin-bottom: 10px;
    padding-bottom: 4px;
    border-bottom: 1px solid var(--border);
    letter-spacing: .04em;
    text-transform: uppercase;
  }
  :global(fieldset) {
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 9px 11px;
    margin-bottom: 9px;
    background: var(--panel);
    box-shadow: var(--shadow);
  }
  :global(legend) {
    font-size: .72rem;
    color: var(--accent);
    padding: 0 5px;
    text-transform: uppercase;
    letter-spacing: .05em;
    font-weight: 600;
  }
  :global(label) {
    display: flex;
    flex-direction: column;
    gap: 3px;
    font-size: .75rem;
    color: var(--text-muted);
    margin-bottom: 7px;
  }
  :global(label.check) {
    flex-direction: row;
    align-items: center;
    gap: 6px;
  }
  /* pastille de cote (lettre A,B,C… liée au schéma) */
  :global(.dimkey) {
    display: inline-block; min-width: 15px; height: 15px; line-height: 15px;
    text-align: center; border-radius: 3px; background: var(--accent-soft);
    color: var(--accent); font-weight: 700; font-size: .64rem; margin-right: 5px;
    border: 1px solid var(--accent); padding: 0 2px;
  }
  :global(input[type="number"]),
  :global(input[type="text"]),
  :global(select) {
    background: #fff;
    border: 1px solid var(--border-strong);
    border-radius: 5px;
    color: var(--text);
    padding: 4px 7px;
    font-size: .8rem;
    width: 100%;
  }
  :global(input[type="number"]:focus),
  :global(input[type="text"]:focus),
  :global(select:focus) {
    outline: none;
    border-color: var(--accent);
    box-shadow: 0 0 0 2px var(--accent-soft);
  }
  :global(.grid-2) {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px;
  }

  /* Canvas */
  .canvas-area {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    padding: 8px;
    background: var(--bg);
  }
  .view-switch {
    display: flex;
    gap: 4px;
    margin-bottom: 6px;
    flex-shrink: 0;
  }
  .view-switch button {
    padding: 5px 14px;
    border: 1px solid var(--border-strong);
    border-radius: var(--radius);
    background: #fff;
    color: var(--text-muted);
    cursor: pointer;
    font-size: .78rem;
  }
  .view-switch button.active {
    background: var(--accent-soft);
    border-color: var(--accent);
    color: var(--accent);
    font-weight: 600;
  }
  .view-body {
    flex: 1;
    overflow: hidden;
    min-height: 0;
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: var(--radius);
  }
</style>
