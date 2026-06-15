<script>
  import { onMount } from 'svelte'
  import { bike, updateSection } from '../lib/store.js'
  import { fetchTubes, fetchMaterials, exportTubes } from '../lib/api.js'

  // paroi éditable par membre → champ FrameGeometry correspondant
  const WALL_FIELD = {
    top_tube: 'top_tube_wall', down_tube: 'down_tube_wall', seat_tube: 'seat_tube_wall',
    head_tube: 'head_tube_wall', chainstay: 'chainstay_wall', seatstay: 'seatstay_wall',
  }

  let materials = []
  let adhesives = []
  let res = null
  let testMoment = 0
  let testTube = 'down_tube'
  let adhesive = 'dp460'

  $: f = $bike?.frame ?? {}
  const upd = patch => updateSection('frame', patch)

  onMount(async () => {
    const m = await fetchMaterials()
    materials = m.materials ?? []
    adhesives = m.adhesives ?? []
  })

  // Recalcule à chaque changement de design ou de paramètre de test/adhésif
  async function refresh(b, mom, tube, adh) {
    if (!b) return
    res = await fetchTubes(b, mom, tube, adh)
  }
  $: refresh($bike, testMoment, testTube, adhesive)

  const fmtMat = k => (materials.find(m => m.key === k)?.label) ?? k
</script>

<section class="panel">
  <h3>Tubes &amp; Lugs</h3>
  <p class="hint">
    Pour chaque tube : Ø extérieur / <strong>intérieur</strong> / paroi, longueur, matériau,
    propriétés de section (A, I, Z), masse, et capacité <strong>INDICATIVE</strong> (limite
    élastique + jonction collée lug-and-bond). Pré-dimensionnement / comparaison matériaux —
    le dimensionnement <strong>fatigue / impact</strong> (ISO 4210-6) reste au bureau d'études.
  </p>

  <fieldset>
    <legend>Matériaux</legend>
    <label>Matériau des tubes
      <select value={f.frame_material ?? 'alu_6061_t6'}
        on:change={e => upd({ frame_material: e.target.value })}>
        {#each materials as m}<option value={m.key}>{m.label}</option>{/each}
      </select>
    </label>
    <label>Matériau des manchons (lugs CNC)
      <select value={f.lug_material ?? 'alu_7075_t6'}
        on:change={e => upd({ lug_material: e.target.value })}>
        {#each materials as m}<option value={m.key}>{m.label}</option>{/each}
      </select>
    </label>
    <label>Adhésif de collage
      <select bind:value={adhesive}>
        {#each adhesives as a}<option value={a.key}>{a.label} (τ_adm {a.tau_adm} MPa)</option>{/each}
      </select>
    </label>
    {#if res}
      <p class="mp">
        Tubes <strong>{fmtMat(res.frame_material)}</strong> · lugs
        <strong>{res.lug_material_props?.label ?? res.lug_material}</strong>
        {#if res.lug_material_props?.re}(Re {res.lug_material_props.re} MPa){/if}
        · masse tubes ≈ <strong>{res.total_mass_g} g</strong>
      </p>
    {/if}
  </fieldset>

  {#if res}
    <fieldset>
      <legend>Tubes — Ø, paroi, section, masse</legend>
      <table>
        <thead>
          <tr><th>Tube</th><th>Ø ext</th><th>Ø int</th><th>paroi</th><th>L</th>
              <th>A mm²</th><th>Z mm³</th><th>masse</th><th title="moment de flexion à la limite élastique — INDICATIF">M_y N·m</th></tr>
        </thead>
        <tbody>
          {#each res.tubes as t}
            <tr title={t.note}>
              <td>{t.label}</td>
              <td class="num">{t.od}</td>
              <td class="num">{t.id}</td>
              <td class="num wall">
                <input type="number" step="0.1" min="0.4" value={t.wall}
                  on:change={e => upd({ [WALL_FIELD[t.member]]: +e.target.value })} />
              </td>
              <td class="num">{t.length}</td>
              <td class="num">{t.area_mm2}</td>
              <td class="num">{t.modulus_mm3}</td>
              <td class="num">{t.mass_g} g</td>
              <td class="num">{t.moment_yield_nm || '—'}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </fieldset>

    <fieldset>
      <legend>Jonctions collées (lug-and-bond) — INDICATIF · {adhesives.find(a => a.key === res.adhesive)?.label ?? res.adhesive}, τ_adm {res.bond_tau_adm} MPa</legend>
      <table>
        <thead>
          <tr><th>Tube</th><th title="longueur d'insertion conseillée L = Re·paroi/τ">insertion L</th>
              <th>surface collée</th><th title="effort de cisaillement admissible = τ·π·OD·L">cisaillement adm.</th></tr>
        </thead>
        <tbody>
          {#each res.tubes as t}
            <tr>
              <td>{t.label}</td>
              <td class="num">{t.bond_length_mm ? t.bond_length_mm + ' mm' : '—'}</td>
              <td class="num">{t.bond_area_mm2 ? Math.round(t.bond_area_mm2) + ' mm²' : '—'}</td>
              <td class="num">{t.bond_shear_n ? Math.round(t.bond_shear_n) + ' N' : '—'}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </fieldset>

    <fieldset>
      <legend>Test de résistance (INDICATIF)</legend>
      <div class="testrow">
        <label class="inl">Moment de flexion (N·m)
          <input type="number" step="10" min="0" bind:value={testMoment} />
        </label>
        <label class="inl">sur le tube
          <select bind:value={testTube}>
            {#each res.tubes as t}<option value={t.member}>{t.label}</option>{/each}
          </select>
        </label>
      </div>
      {#if res.load_case && res.load_case.sigma_mpa !== undefined}
        <div class="verdict" class:ok={res.load_case.ok} class:no={!res.load_case.ok}>
          σ = <strong>{res.load_case.sigma_mpa} MPa</strong> vs Re {res.load_case.re_mpa} MPa
          → FS = <strong>{res.load_case.fs}</strong>
          {res.load_case.ok ? '✓ (FS ≥ 2)' : '✗ FS insuffisant (cible ≥ 2)'}
        </div>
        <p class="sub">Critère ductile von Mises, statique 1er ordre. Joint collé conseillé sur ce tube :
          insertion L ≈ {res.load_case.bond_length_mm} mm.</p>
      {:else if testMoment > 0}
        <p class="sub">Matériau sans limite élastique scalaire (carbone) — test von Mises non applicable.</p>
      {:else}
        <p class="sub">Saisir un moment pour évaluer σ et le facteur de sécurité.</p>
      {/if}
    </fieldset>

    <div class="exp">
      <span>Export :</span>
      <button on:click={() => exportTubes($bike, 'csv', testMoment, testTube, adhesive)}>CSV</button>
      <button on:click={() => exportTubes($bike, 'json', testMoment, testTube, adhesive)}>JSON</button>
      <button on:click={() => exportTubes($bike, 'summary', testMoment, testTube, adhesive)}>Résumé</button>
    </div>

    {#each (res.notes ?? []) as n}<p class="note">• {n}</p>{/each}
  {:else}
    <p class="hint">Chargement…</p>
  {/if}
</section>

<style>
  .hint { font-size: 12px; color: #667; line-height: 1.45; margin: 4px 0 10px; }
  .mp { font-size: 12px; color: #445; margin: 8px 0 0; line-height: 1.4; }
  table { width: 100%; border-collapse: collapse; font-size: 11px; }
  th { text-align: right; color: #889; font-weight: 600; border-bottom: 1px solid #e2e6ec; padding: 2px 3px; }
  th:first-child, td:first-child { text-align: left; }
  td { padding: 2px 3px; border-bottom: 1px solid #eef1f5; }
  td.num, .num { text-align: right; white-space: nowrap; }
  td.wall input { width: 46px; padding: 1px 3px; font-size: 11px; text-align: right;
                  border: 1px solid #c5ccd6; border-radius: 4px; }
  .testrow { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 8px; }
  label.inl { display: flex; flex-direction: column; font-size: 11.5px; color: #556; gap: 3px; }
  label.inl input, label.inl select { font-size: 12px; padding: 3px 5px; }
  .verdict { font-size: 12.5px; padding: 6px 9px; border-radius: 6px; border: 1px solid; }
  .verdict.ok { background: #eaf7ee; border-color: #b6e0c2; color: #1d6b34; }
  .verdict.no { background: #fdecea; border-color: #f3c0bb; color: #a02014; }
  .sub { font-size: 11px; color: #778; margin: 6px 0 0; line-height: 1.4; }
  .exp { display: flex; align-items: center; gap: 6px; font-size: 12px; margin: 12px 0 6px; }
  .exp button { padding: 3px 8px; border: 1px solid #c5ccd6; border-radius: 5px;
                background: #f6f8fa; cursor: pointer; }
  .note { font-size: 11px; color: #778; line-height: 1.4; margin: 6px 0 0; }
</style>
