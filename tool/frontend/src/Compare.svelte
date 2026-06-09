<script>
  import { bike, calc, baseline, snapshotBaseline } from './lib/store.js'

  $: c = $calc
  $: b = $baseline
  $: f = $bike?.frame ?? {}

  // Lignes de comparaison : [label, valeur courante, valeur réf, unité, décimales]
  $: rows = c ? [
    ['Reach',        c.reach,        b?.calc.reach,        'mm', 0],
    ['Stack',        c.stack,        b?.calc.stack,        'mm', 0],
    ['Trail',        c.trail,        b?.calc.trail,        'mm', 1],
    ['Empattement',  c.wheelbase,    b?.calc.wheelbase,    'mm', 0],
    ['Hauteur BB',   c.bb_height,    b?.calc.bb_height,    'mm', 0],
    ['Front center', c.front_center, b?.calc.front_center, 'mm', 0],
    ['TT effectif',  c.tt_effective, b?.calc.tt_effective, 'mm', 0],
    ['STA effectif', c.effective_sta,b?.calc.effective_sta,'°', 1],
    ['Standover',    c.standover,    b?.calc.standover,    'mm', 0],
    ['Wheel flop',   c.wheel_flop,   b?.calc.wheel_flop,   '',  1],
    ['— Angle direction', f.head_angle, b?.frame.head_angle, '°', 1],
    ['— Angle selle',     f.seat_angle, b?.frame.seat_angle, '°', 1],
    ['— Bases (CS)',      f.cs,         b?.frame.cs,         'mm', 0],
    ['— BB drop',         f.bb_drop,    b?.frame.bb_drop,    'mm', 0],
    ['— Tube direction',  f.head_tube,  b?.frame.head_tube,  'mm', 0],
  ] : []

  function fmt(v, dec) { return v == null ? '—' : (+v).toFixed(dec) }
  function delta(cur, ref, dec) {
    if (cur == null || ref == null) return null
    const d = cur - ref
    return (d >= 0 ? '+' : '') + d.toFixed(dec)
  }
</script>

<div class="cmp-wrap">
  <div class="cmp-head">
    <button on:click={snapshotBaseline}>📌 Figer le design courant comme référence</button>
    {#if b}<span class="ref-name">Référence : {b.name}</span>{/if}
  </div>

  {#if !c}
    <div class="placeholder">Calcul en cours…</div>
  {:else}
    <table class="cmp">
      <thead>
        <tr>
          <th>Paramètre</th>
          <th>Courant</th>
          <th>{b ? 'Référence' : '—'}</th>
          <th>Δ</th>
        </tr>
      </thead>
      <tbody>
        {#each rows as [label, cur, ref, unit, dec]}
          {@const d = delta(cur, ref, dec)}
          <tr class:section={label.startsWith('—')}>
            <td class="l">{label.replace('— ', '')}</td>
            <td class="v">{fmt(cur, dec)} <span class="u">{unit}</span></td>
            <td class="r">{b ? fmt(ref, dec) : '—'}</td>
            <td class="d" class:pos={d && d.startsWith('+') && d !== '+0'}
                          class:neg={d && d.startsWith('-')}>
              {b && d ? `${d} ${unit}` : ''}
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
    {#if !b}
      <p class="hint">Fige une géométrie comme référence, puis modifie les paramètres : les écarts s'affichent en direct.</p>
    {/if}
  {/if}
</div>

<style>
  .cmp-wrap { height: 100%; overflow-y: auto; background: #1a1a2e; border-radius: 4px; padding: 12px; }
  .cmp-head { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
  .cmp-head button { padding: 6px 14px; background: #1e3a5f; color: #8ecae6; border: 1px solid #3a5a8f; border-radius: 4px; cursor: pointer; font-size: .8rem; }
  .ref-name { color: #e8851a; font-size: .8rem; }
  .placeholder { color: #555; }
  table.cmp { width: 100%; border-collapse: collapse; max-width: 640px; }
  table.cmp th { text-align: right; padding: 6px 10px; font-size: .72rem; color: #8ecae6; border-bottom: 1px solid #3a3a5a; text-transform: uppercase; }
  table.cmp th:first-child { text-align: left; }
  table.cmp td { padding: 4px 10px; font-size: .8rem; border-bottom: 1px solid #23233a; text-align: right; font-variant-numeric: tabular-nums; }
  table.cmp td.l { text-align: left; color: #aab; }
  table.cmp td.v { color: #fff; font-weight: 600; }
  table.cmp td.r { color: #99a; }
  .u { color: #667; font-size: .7rem; }
  tr.section td.l { color: #778; font-style: italic; }
  td.d { color: #778; }
  td.d.pos { color: #4caf50; }
  td.d.neg { color: #e8851a; }
  .hint { color: #667; font-size: .74rem; margin-top: 12px; font-style: italic; }
</style>
