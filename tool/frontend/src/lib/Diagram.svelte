<script>
  // Schéma de cotes (extrait de BikeCAD) affiché en tête de panneau pour
  // expliquer visuellement chaque paramètre. `legend` = [{k,v}] relie chaque
  // lettre du schéma au champ correspondant de l'outil.
  export let src                 // nom de fichier dans /public/diagrams/
  export let caption = ""
  export let legend = []         // [{k:'AC', v:'Axe → couronne'}, ...]
  let open = true
</script>

<div class="diagram">
  <button class="dg-head" on:click={() => (open = !open)} type="button">
    <span class="chev">{open ? '▾' : '▸'}</span> Schéma{caption ? ' — ' + caption : ''}
  </button>
  {#if open}
    <div class="dg-img"><img src={`/diagrams/${src}`} alt={caption || src} loading="lazy" /></div>
    {#if legend.length}
      <ul class="dg-legend">
        {#each legend as l}
          <li><span class="dimkey">{l.k}</span> {l.v}</li>
        {/each}
      </ul>
    {/if}
  {/if}
</div>

<style>
  .diagram { margin: 4px 0 12px; border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; background: var(--panel); }
  .dg-head {
    width: 100%; text-align: left; padding: 6px 9px; cursor: pointer;
    background: var(--surface); color: var(--accent); border: none; font-size: .72rem;
    text-transform: uppercase; letter-spacing: .04em; font-weight: 600;
  }
  .dg-head:hover { background: var(--accent-soft); }
  .chev { color: var(--brand); }
  .dg-img { background: #fff; padding: 10px; display: flex; justify-content: center; }
  .dg-img img {
    width: 100%; max-width: 280px; height: auto; display: block;
    image-rendering: -webkit-optimize-contrast;
  }
  .dg-legend {
    list-style: none; margin: 0; padding: 8px 10px; border-top: 1px solid var(--border);
    display: grid; grid-template-columns: 1fr 1fr; gap: 3px 10px;
  }
  .dg-legend li { font-size: .68rem; color: var(--text-muted); display: flex; align-items: center; }
</style>
