<script>
  import { svg, loading, error, calc } from './lib/store.js'
</script>

<div class="renderer-wrap">
  {#if $loading}
    <div class="overlay">
      <span class="spinner"></span>
    </div>
  {/if}

  {#if $error}
    <div class="error-banner">{$error}</div>
  {/if}

  {#if $svg}
    <div class="svg-container">
      {@html $svg}
    </div>
  {:else if !$loading}
    <div class="placeholder">Chargement du rendu...</div>
  {/if}

  {#if $calc}
    <div class="calc-strip">
      <span title="Reach">R {$calc.reach?.toFixed(0)} mm</span>
      <span title="Stack">S {$calc.stack?.toFixed(0)} mm</span>
      <span title="Trail">Trail {$calc.trail?.toFixed(0)} mm</span>
      <span title="Empattement">WB {$calc.wheelbase?.toFixed(0)} mm</span>
      <span title="Hauteur BB">BB ↑{$calc.bb_height?.toFixed(0)} mm</span>
      <span title="Front center">FC {$calc.front_center?.toFixed(0)} mm</span>
      <span title="Top tube eff.">TT {$calc.tt_effective?.toFixed(0)} mm</span>
      <span title="Angle selle effectif">STA* {$calc.effective_sta?.toFixed(1)}°</span>
      <span title="Wheel flop">WF {$calc.wheel_flop?.toFixed(1)}</span>
    </div>
  {/if}
</div>

<style>
  .renderer-wrap {
    position: relative;
    display: flex;
    flex-direction: column;
    height: 100%;
    background: #1a1a2e;
    border-radius: 4px;
    overflow: hidden;
  }
  .svg-container {
    flex: 1;
    overflow: hidden;
  }
  .svg-container :global(svg) {
    width: 100%;
    height: 100%;
  }
  .overlay {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(0,0,0,.4);
    z-index: 10;
  }
  .spinner {
    width: 32px; height: 32px;
    border: 3px solid #444;
    border-top-color: #e8851a;
    border-radius: 50%;
    animation: spin .7s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .error-banner {
    background: #c0392b;
    color: #fff;
    padding: 6px 12px;
    font-size: .8rem;
  }
  .placeholder {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #555;
    font-size: .9rem;
  }
  .calc-strip {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
    padding: 6px 12px;
    background: #16213e;
    border-top: 1px solid #2a2a4a;
    font-size: .75rem;
    color: #8ecae6;
  }
  .calc-strip span {
    white-space: nowrap;
    cursor: default;
  }
</style>
