<script>
  // Vue « Rendu BikeCAD » : affiche le rendu PIXEL-PERFECT de BikeCAD pour le
  // design courant. Flux : on génère un .bcad du design → l'utilisateur l'ouvre
  // dans BikeCAD Pro → Fichier → Exporter SVG → on charge ce SVG ici.
  import { bike } from './lib/store.js'
  import { exportBcad } from './lib/api.js'

  let bcadPath = ''
  let svgContent = ''
  let status = ''
  let busy = false
  let fileName = ''

  async function genBcad() {
    if (!$bike) return
    busy = true; status = 'Génération du .bcad…'
    try {
      const slug = ($bike.name ?? 'design').replace(/\s+/g, '_')
      const out = `BIKE/${slug}_render.bcad`
      // free_safe=false → garde la courroie/tout le design (fichier d'interop complet)
      const res = await exportBcad($bike, out, 'BIKE/eMTB_DOM_Engineering.bcad', false)
      bcadPath = res?.path || out
      status = '.bcad généré ✓'
    } catch (e) {
      status = 'Erreur génération : ' + (e.message || e)
    } finally { busy = false }
  }

  function onFile(e) {
    const f = e.target.files?.[0]
    if (!f) return
    fileName = f.name
    const r = new FileReader()
    r.onload = () => { svgContent = String(r.result); status = 'Rendu BikeCAD chargé ✓' }
    r.onerror = () => { status = 'Lecture du SVG impossible' }
    r.readAsText(f)
  }
</script>

<div class="bcadview">
  {#if !svgContent}
    <div class="guide">
      <h3>Rendu BikeCAD (fidèle)</h3>
      <p class="lead">Affiche le rendu <b>exact de BikeCAD</b> pour ton design courant — moteur,
        transmission, formes, tout est la sortie native de BikeCAD (zéro reconstruction).</p>

      <ol>
        <li>
          <b>Générer le .bcad du design courant</b>
          <button class="act" on:click={genBcad} disabled={busy || !$bike}>⤓ Générer .bcad</button>
          {#if bcadPath}<div class="path">→ <code>{bcadPath}</code></div>{/if}
        </li>
        <li><b>Ouvrir ce fichier dans BikeCAD Pro</b> (Fichier → Ouvrir), puis
          <b>Fichier → Exporter SVG</b>.</li>
        <li>
          <b>Charger le SVG exporté ici :</b>
          <input type="file" accept=".svg,image/svg+xml" on:change={onFile} />
        </li>
      </ol>

      <p class="tip">💡 Astuce : un export par lot existe aussi —
        <code>tool/scripts/bikecad_batch_export.sh</code> pilote BikeCAD pour exporter en SVG
        automatiquement (nécessite BikeCAD ouvert + autorisation Accessibilité du Terminal).</p>
      {#if status}<p class="status">{status}</p>{/if}
    </div>
  {:else}
    <div class="toolbar2">
      <span class="fname">🅑 {fileName || 'Rendu BikeCAD'}</span>
      <button class="act" on:click={() => { svgContent = ''; fileName = '' }}>↻ Charger un autre</button>
    </div>
    <div class="render">{@html svgContent}</div>
  {/if}
</div>

<style>
  .bcadview { height: 100%; overflow: auto; }
  .guide { max-width: 620px; margin: 24px auto; padding: 20px 24px;
           background: var(--panel); border: 1px solid var(--border);
           border-radius: var(--radius); box-shadow: var(--shadow); }
  .guide h3 { color: var(--brand); text-transform: uppercase; letter-spacing: .04em;
              font-size: .95rem; margin-bottom: 8px; }
  .lead { color: var(--text-muted); font-size: .82rem; margin-bottom: 16px; line-height: 1.4; }
  ol { margin: 0 0 14px 18px; display: flex; flex-direction: column; gap: 14px; }
  li { font-size: .82rem; color: var(--text); line-height: 1.5; }
  .act { display: inline-block; margin-left: 8px; padding: 5px 12px; border-radius: var(--radius);
         border: 1px solid var(--accent); background: var(--accent-soft); color: var(--accent);
         cursor: pointer; font-size: .78rem; font-weight: 600; }
  .act:hover:not(:disabled) { background: var(--accent); color: #fff; }
  .act:disabled { opacity: .5; cursor: not-allowed; }
  .path { margin-top: 6px; font-size: .74rem; color: var(--text-muted); }
  code { background: var(--surface); padding: 1px 5px; border-radius: 4px;
         font-size: .9em; color: var(--text); }
  input[type=file] { display: block; margin-top: 6px; font-size: .76rem; }
  .tip { margin-top: 10px; font-size: .72rem; color: var(--text-muted);
         background: var(--surface); padding: 8px 10px; border-radius: var(--radius); }
  .status { margin-top: 12px; font-size: .78rem; color: var(--ok); font-weight: 600; }
  .toolbar2 { display: flex; align-items: center; justify-content: space-between;
              padding: 6px 10px; border-bottom: 1px solid var(--border); background: var(--surface); }
  .fname { font-size: .78rem; color: var(--text); font-weight: 600; }
  .render { padding: 10px; background: #fff; }
  .render :global(svg) { max-width: 100%; height: auto; display: block; margin: 0 auto; }
</style>
