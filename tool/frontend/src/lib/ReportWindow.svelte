<script>
  // Fenêtre « Dossier de conception » : choix dessinateur / société / révision,
  // puis ouverture dans un onglet (→ Imprimer en PDF) ou téléchargement HTML.
  import { bike } from './store.js'
  import Modal from './Modal.svelte'
  import { openReport, downloadReport } from './api.js'

  let designer = 'Robinson Joubert'
  let company = 'DOM Engineering'
  let revision = 'A'
  let busy = ''
  let err = ''

  $: opts = { designer, company, revision }

  async function run(fn, tag) {
    busy = tag; err = ''
    try { await fn($bike, opts) }
    catch (e) { err = e.message ?? String(e) }
    busy = ''
  }
</script>

<Modal title="Dossier de conception" icon="📋" on:close>
  <p class="intro">
    Génère un <strong>document unique et cohérent</strong> à transmettre aux ingénieurs en
    conception : synthèse géométrie, plan coté, cinématique, tubes &amp; masses, nomenclature
    d'achat, jonctions de lugs, pivots, visserie, motorisation/batterie/transmission, fit pilote
    et rappels normatifs. À produire <strong>à partir d'une géométrie validée</strong>.
  </p>

  <div class="grid2">
    <label>Société<input type="text" bind:value={company} /></label>
    <label>Révision<input type="text" bind:value={revision} /></label>
    <label class="full">Dessinateur / responsable<input type="text" bind:value={designer} /></label>
  </div>

  <p class="warn">⚠ Pré-dimensionnement de conception. La validation structurelle / fatigue /
    impact relève d'un bureau d'études qualifié.</p>
  {#if err}<p class="err">Erreur : {err}</p>{/if}

  <svelte:fragment slot="footer">
    <span class="note">L'aperçu s'ouvre dans un onglet — utilise <em>Imprimer → PDF</em> pour diffuser.</span>
    <button class="btn ghost" on:click={() => run(downloadReport, 'dl')} disabled={!!busy}>
      {busy === 'dl' ? '…' : '⬇ Télécharger (HTML)'}</button>
    <button class="btn primary" on:click={() => run(openReport, 'open')} disabled={!!busy}>
      {busy === 'open' ? '…' : '🗎 Ouvrir le dossier'}</button>
  </svelte:fragment>
</Modal>

<style>
  .intro { font-size: .82rem; color: var(--text); line-height: 1.55; margin: 0 0 14px; }
  .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  .grid2 label { display: flex; flex-direction: column; gap: 4px; font-size: .74rem; color: var(--text-muted); }
  .grid2 label.full { grid-column: 1 / -1; }
  .warn { font-size: .76rem; color: var(--warn); background: #fffaf3; border: 1px solid #f0d9b5;
          border-radius: 6px; padding: 8px 11px; margin: 14px 0 0; }
  .err { font-size: .78rem; color: var(--no); margin: 8px 0 0; }
  .note { font-size: .72rem; color: var(--text-muted); margin-right: auto; }
  .btn { padding: 6px 13px; border-radius: var(--radius); border: 1px solid var(--border-strong);
         background: #fff; color: var(--text); cursor: pointer; font-size: .8rem; }
  .btn.ghost:hover { background: var(--accent-soft); border-color: var(--accent); color: var(--accent); }
  .btn.primary { background: var(--accent); border-color: var(--accent); color: #fff; font-weight: 600; }
  .btn.primary:hover { filter: brightness(1.06); }
  .btn:disabled { opacity: .5; cursor: not-allowed; }
</style>
