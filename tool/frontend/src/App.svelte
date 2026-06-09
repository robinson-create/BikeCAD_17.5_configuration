<script>
  import { onMount } from 'svelte'
  import { activeTab, TABS, bike, scheduleRefresh, viewMode, showDims } from './lib/store.js'
  import { fetchDefault, loadBcad, exportBcad, exportDxf, listBikes } from './lib/api.js'
  import BikeRenderer from './BikeRenderer.svelte'
  import Kinematics from './Kinematics.svelte'
  import Compare from './Compare.svelte'

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
    rider:      Rider,
  }

  let bikes = []
  let bcadPath = ''
  let status = ''

  onMount(async () => {
    const defaultBike = await fetchDefault()
    if (defaultBike) scheduleRefresh(defaultBike)
    bikes = await listBikes()
  })

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
    const defaultOut = 'BIKE/eMTB_DOM_Engineering.bcad'
    try {
      await exportBcad($bike, defaultOut)
      status = 'Exporté ✓'
    } catch {
      status = 'Erreur export'
    }
    setTimeout(() => status = '', 2000)
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
      {#if bikes.length > 0}
        <select on:change={handleBikeSelect}>
          <option value="">-- Ouvrir un vélo --</option>
          {#each bikes as b}
            <option value={b.path}>{b.name}</option>
          {/each}
        </select>
      {/if}
      <input class="path-input" type="text" placeholder="chemin/vers/fichier.bcad"
        bind:value={bcadPath} on:keydown={e => e.key === 'Enter' && handleLoadBcad()} />
      <button on:click={handleLoadBcad}>Charger</button>
      <button on:click={handleExportBcad}>Exporter .bcad</button>
      <button on:click={handleExportDxf}>Export DXF</button>
      <label class="check-label">
        <input type="checkbox" bind:checked={$showDims}
          on:change={() => $bike && scheduleRefresh($bike)} />
        Cotes
      </label>
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
      </div>
      <div class="view-body">
        {#if $viewMode === 'bike'}
          <BikeRenderer />
        {:else if $viewMode === 'kinematics'}
          <Kinematics />
        {:else}
          <Compare />
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
    padding: 8px 16px;
    background: #16213e;
    border-bottom: 1px solid #2a2a4a;
    flex-shrink: 0;
  }
  .brand {
    font-weight: 700;
    font-size: .9rem;
    color: #e8851a;
    letter-spacing: .02em;
  }
  .toolbar {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .toolbar button {
    padding: 4px 10px;
    border-radius: 3px;
    border: 1px solid #444;
    background: #1e3a5f;
    color: #cce;
    cursor: pointer;
    font-size: .8rem;
  }
  .toolbar button:hover { background: #2a4a7f; }
  .path-input {
    width: 240px;
    padding: 4px 8px;
    border-radius: 3px;
    border: 1px solid #444;
    background: #111;
    color: #ddf;
    font-size: .8rem;
  }
  .check-label { display: flex; align-items: center; gap: 4px; font-size: .8rem; }
  .status { font-size: .8rem; color: #4caf50; }

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
