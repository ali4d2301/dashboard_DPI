<script setup>
defineProps({
  regions: {
    type: Array,
    default: () => [],
  },
});
</script>

<template>
  <article class="panel bar-panel">
    <h2>Taux de déploiement par région sanitaire</h2>
    <div class="vertical-chart">
      <div v-for="region in regions.slice(0, 12)" :key="region.label" class="column-bar">
        <strong>{{ region.rate }}%</strong>
        <i :style="{ height: `${region.rate}%` }"></i>
        <span>{{ region.label }}</span>
      </div>
    </div>
  </article>
</template>
