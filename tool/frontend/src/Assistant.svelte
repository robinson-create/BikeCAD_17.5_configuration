<script>
  import { onMount, tick } from 'svelte'
  import { bike, scheduleRefresh } from './lib/store.js'
  import { askAssistant, assistantAvailable } from './lib/api.js'

  let available = null          // null = inconnu, true/false
  let messages = []             // [{role, content, actions?}]
  let input = ''
  let busy = false
  let errorMsg = ''
  let scroller

  const SUGGESTIONS = [
    'Passe en high-pivot M620 et vérifie le dégagement moteur',
    'Calcule le sag pour une raideur de 500 N/mm',
    'Quelle raideur pour 28 % de sag ?',
    'Montre-moi les axes de roue et le chemin d\'axe arrière',
    'Cherche dans la banque : courroie Gates et belt growth',
    'Règle le reach à 480 mm et l\'angle de direction à 63,5°',
  ]

  onMount(async () => { available = await assistantAvailable() })

  async function send(text) {
    const content = (text ?? input).trim()
    if (!content || busy || !$bike) return
    input = ''
    errorMsg = ''
    messages = [...messages, { role: 'user', content }]
    busy = true
    await scrollDown()
    try {
      // On envoie l'historique texte + le vélo courant
      const history = messages.map(m => ({ role: m.role, content: m.content }))
      const res = await askAssistant(history, $bike)
      messages = [...messages, { role: 'assistant', content: res.reply, actions: res.actions ?? [] }]
      if (res.bike) scheduleRefresh(res.bike)   // applique les modifs au design
    } catch (e) {
      errorMsg = String(e.message ?? e).slice(0, 300)
    } finally {
      busy = false
      await scrollDown()
    }
  }

  async function scrollDown() {
    await tick()
    if (scroller) scroller.scrollTop = scroller.scrollHeight
  }

  function onKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }
</script>

<div class="assistant">
  {#if available === false}
    <div class="notice">
      <h3>Assistant indisponible</h3>
      <p>Définis la variable d'environnement <code>ANTHROPIC_API_KEY</code> puis relance le backend
        (<code>cd tool &amp;&amp; ./start.sh</code>) pour activer l'assistant.</p>
      <p class="dim">L'assistant pilote l'outil (géométrie, suspension, presets, bibliothèque) en langage naturel.</p>
    </div>
  {:else}
    <div class="log" bind:this={scroller}>
      {#if messages.length === 0}
        <div class="welcome">
          <h3>Assistant de conception</h3>
          <p class="dim">Décris ce que tu veux changer ; je modifie le vélo et je vérifie l'impact.</p>
          <div class="suggestions">
            {#each SUGGESTIONS as s}
              <button class="chip" on:click={() => send(s)} disabled={busy}>{s}</button>
            {/each}
          </div>
        </div>
      {/if}
      {#each messages as m}
        <div class="msg {m.role}">
          <div class="bubble">{m.content}</div>
          {#if m.actions && m.actions.length}
            <div class="actions">
              {#each m.actions as a}<span class="act">{a}</span>{/each}
            </div>
          {/if}
        </div>
      {/each}
      {#if busy}
        <div class="msg assistant"><div class="bubble dim">…réflexion &amp; calculs…</div></div>
      {/if}
      {#if errorMsg}<div class="err">⚠ {errorMsg}</div>{/if}
    </div>

    <div class="composer">
      <textarea bind:value={input} on:keydown={onKey} rows="2" disabled={busy}
        placeholder="Ex : passe en high-pivot M620 et règle le reach à 480 mm…"></textarea>
      <button class="send" on:click={() => send()} disabled={busy || !input.trim()}>Envoyer</button>
    </div>
  {/if}
</div>

<style>
  .assistant { height: 100%; display: flex; flex-direction: column; background: var(--panel); border-radius: var(--radius); }
  .log { flex: 1; overflow-y: auto; padding: 14px; display: flex; flex-direction: column; gap: 12px; }
  .welcome, .notice { color: var(--text); padding: 16px; }
  .welcome h3, .notice h3 { color: var(--brand); margin-bottom: 8px; }
  .dim { color: var(--text-muted); font-size: .82rem; }
  .suggestions { display: flex; flex-direction: column; gap: 6px; margin-top: 12px; }
  .chip { text-align: left; background: var(--surface); border: 1px solid var(--border); color: var(--text); border-radius: 6px; padding: 7px 10px; font-size: .8rem; cursor: pointer; }
  .chip:hover { background: var(--accent-soft); border-color: var(--border-strong); }
  .msg { display: flex; flex-direction: column; gap: 4px; max-width: 86%; }
  .msg.user { align-self: flex-end; align-items: flex-end; }
  .msg.assistant { align-self: flex-start; }
  .bubble { padding: 9px 12px; border-radius: 10px; font-size: .85rem; line-height: 1.4; white-space: pre-wrap; }
  .msg.user .bubble { background: var(--accent); color: #fff; }
  .msg.assistant .bubble { background: var(--surface); color: var(--text); border: 1px solid var(--border); }
  .actions { display: flex; flex-wrap: wrap; gap: 4px; }
  .act { font-size: .68rem; background: var(--ok); color: #fff; border-radius: 4px; padding: 2px 6px; font-variant-numeric: tabular-nums; }
  .err { background: var(--no); color: #fff; padding: 8px 12px; border-radius: 6px; font-size: .8rem; }
  .composer { display: flex; gap: 8px; padding: 10px; border-top: 1px solid var(--border); }
  .composer textarea { flex: 1; resize: none; background: var(--surface); color: var(--text); border: 1px solid var(--border-strong); border-radius: 6px; padding: 8px; font-size: .85rem; font-family: inherit; }
  .send { background: var(--brand); color: #fff; border: none; border-radius: 6px; padding: 0 16px; font-weight: 700; cursor: pointer; }
  .send:disabled { opacity: .5; cursor: default; }
  code { background: var(--accent-soft); padding: 1px 5px; border-radius: 3px; color: var(--accent); }
</style>
