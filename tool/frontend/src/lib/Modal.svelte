<script>
  // Fenêtre flottante (style « panneau d'outil » Adobe) : overlay + carte
  // centrée, en-tête avec titre + fermeture, corps défilant, pied optionnel.
  import { createEventDispatcher } from 'svelte'
  export let title = ''
  export let icon = ''
  export let wide = false
  const dispatch = createEventDispatcher()
  const close = () => dispatch('close')
  function onKey(e) { if (e.key === 'Escape') close() }
</script>

<svelte:window on:keydown={onKey} />

<div class="overlay" role="presentation" on:click|self={close}>
  <div class="win" class:wide role="dialog" aria-modal="true">
    <header class="win-head">
      <span class="win-title">{#if icon}<span class="wic">{icon}</span>{/if}{title}</span>
      <button class="win-x" on:click={close} title="Fermer (Échap)">✕</button>
    </header>
    <div class="win-body"><slot /></div>
    {#if $$slots.footer}<footer class="win-foot"><slot name="footer" /></footer>{/if}
  </div>
</div>

<style>
  .overlay {
    position: fixed; inset: 0; z-index: 200; background: rgba(16,24,40,.38);
    display: flex; align-items: center; justify-content: center; padding: 24px;
  }
  .win {
    display: flex; flex-direction: column; width: 640px; max-width: 96vw; max-height: 90vh;
    background: var(--panel); border: 1px solid var(--border-strong); border-radius: 10px;
    box-shadow: 0 24px 60px rgba(16,24,40,.32); overflow: hidden;
  }
  .win.wide { width: 1000px; }
  .win-head {
    display: flex; align-items: center; justify-content: space-between;
    padding: 11px 16px; border-bottom: 1px solid var(--border); background: var(--surface);
  }
  .win-title { font-weight: 700; font-size: .92rem; color: var(--text); display: flex; align-items: center; gap: 8px; }
  .wic { color: var(--brand); }
  .win-x {
    border: none; background: none; font-size: 1rem; color: var(--text-muted);
    cursor: pointer; padding: 2px 6px; border-radius: 5px;
  }
  .win-x:hover { background: var(--accent-soft); color: var(--accent); }
  .win-body { padding: 16px; overflow: auto; }
  .win-foot {
    padding: 11px 16px; border-top: 1px solid var(--border); background: var(--surface);
    display: flex; gap: 8px; justify-content: flex-end; align-items: center; flex-wrap: wrap;
  }
</style>
