<script>
  // Schéma de cotes (extrait de BikeCAD) affiché en tête de panneau pour
  // expliquer visuellement chaque paramètre.
  export let src                 // nom de fichier dans /public/diagrams/
  export let caption = ""
  let open = true
</script>

<div class="diagram">
  <button class="dg-head" on:click={() => (open = !open)} type="button">
    <span class="chev">{open ? '▾' : '▸'}</span> Schéma{caption ? ' — ' + caption : ''}
  </button>
  {#if open}
    <div class="dg-img"><img src={`/diagrams/${src}`} alt={caption || src} loading="lazy" /></div>
  {/if}
</div>

<style>
  .diagram { margin: 4px 0 12px; border: 1px solid #2a2a4a; border-radius: 6px; overflow: hidden; }
  .dg-head {
    width: 100%; text-align: left; padding: 5px 9px; cursor: pointer;
    background: #16213e; color: #8ecae6; border: none; font-size: .72rem;
    text-transform: uppercase; letter-spacing: .04em;
  }
  .dg-head:hover { background: #1c2a4a; }
  .chev { color: #e8851a; }
  .dg-img { background: #fff; padding: 6px; display: flex; justify-content: center; }
  .dg-img img { max-width: 100%; height: auto; display: block; }
</style>
