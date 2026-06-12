<script setup>
defineProps({
  functionalCount: { type: Number, default: 0 },
  partialCount: { type: Number, default: 0 },
  nonFunctionalCount: { type: Number, default: 0 },
  deployedCount: { type: Number, default: 0 },
  functionalRate: { type: Number, default: 0 },
  partialRate: { type: Number, default: 0 },
});

function formatNumber(value) {
  return Number(value || 0).toLocaleString("fr-FR");
}

function formatRate(value) {
  return Number(value || 0).toLocaleString("fr-FR", { maximumFractionDigits: 1 });
}
</script>

<template>
  <article class="panel donut-panel">
    <h2>Statut opérationnel (sur sites déployés)</h2>
    <div class="donut-layout">
      <div
        class="donut"
        :style="{
          '--green': `${functionalRate}%`,
          '--yellow': `${functionalRate + partialRate}%`,
        }"
      >
        <strong>{{ formatRate(functionalRate) }}%</strong>
      </div>
      <div class="status-list">
        <span><i class="green"></i>Utilisés <strong>{{ formatNumber(functionalCount) }}</strong></span>
        <span><i class="yellow"></i>Partiellement utilisés <strong>{{ formatNumber(partialCount) }}</strong></span>
        <span><i class="red"></i>Non utilisés <strong>{{ formatNumber(nonFunctionalCount) }}</strong></span>
        <b>Total : {{ formatNumber(deployedCount) }}</b>
      </div>
    </div>
  </article>
</template>
