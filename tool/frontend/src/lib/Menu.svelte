<script>
  // Menu déroulant générique (style barre de menus logiciel).
  // Usage : <Menu label="Fichier"> <button class="mi" on:click=…>…</button> </Menu>
  export let label = ''
  export let icon = ''
  let open = false
  let root

  function toggle() { open = !open }
  function close() { open = false }
  function onWindowClick(e) { if (open && root && !root.contains(e.target)) close() }
  function onKey(e) { if (e.key === 'Escape') close() }
</script>

<svelte:window on:click={onWindowClick} on:keydown={onKey} />

<div class="menu" bind:this={root}>
  <button class="menu-trigger" class:open on:click|stopPropagation={toggle}>
    {#if icon}<span class="mic">{icon}</span>{/if}{label}<span class="caret">▾</span>
  </button>
  {#if open}
    <div class="menu-pop" role="menu" tabindex="-1" on:click={close} on:keydown={onKey}>
      <slot />
    </div>
  {/if}
</div>

<style>
  .menu { position: relative; display: inline-block; }
  .menu-trigger {
    display: inline-flex; align-items: center; gap: 5px;
    padding: 5px 11px; border-radius: var(--radius);
    border: 1px solid var(--border-strong); background: #fff; color: var(--text);
    cursor: pointer; font-size: .78rem; white-space: nowrap;
  }
  .menu-trigger:hover, .menu-trigger.open {
    background: var(--accent-soft); border-color: var(--accent); color: var(--accent);
  }
  .mic { font-size: .95rem; }
  .caret { font-size: .62rem; opacity: .7; }
  .menu-pop {
    position: absolute; top: calc(100% + 4px); right: 0; z-index: 50;
    min-width: 220px; padding: 5px; background: #fff;
    border: 1px solid var(--border-strong); border-radius: var(--radius);
    box-shadow: 0 8px 28px rgba(16,24,40,.16); display: flex; flex-direction: column; gap: 1px;
  }
  /* éléments de menu (slottés) */
  .menu-pop :global(.mi) {
    display: flex; align-items: center; gap: 8px; width: 100%; text-align: left;
    padding: 7px 10px; border: none; background: none; color: var(--text);
    cursor: pointer; font-size: .8rem; border-radius: 5px;
  }
  .menu-pop :global(.mi:hover) { background: var(--accent-soft); color: var(--accent); }
  .menu-pop :global(.mi:disabled) { opacity: .4; cursor: not-allowed; }
  .menu-pop :global(.mi:disabled:hover) { background: none; color: var(--text); }
  .menu-pop :global(.mi .k) { margin-left: auto; font-size: .68rem; color: var(--text-muted); }
  .menu-pop :global(.mi.danger:hover) { background: #fdecea; color: #c0392b; }
  .menu-pop :global(.msep) { height: 1px; background: var(--border); margin: 4px 2px; }
  .menu-pop :global(.mh) {
    font-size: .62rem; text-transform: uppercase; letter-spacing: .07em;
    color: var(--text-muted); padding: 6px 10px 2px;
  }
</style>
