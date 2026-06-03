<script setup>
defineProps({
  items: {
    type: Array,
    default: () => [],
  },
});
</script>

<template>
  <article class="panel stacked-panel">
    <h2>Statut opérationnel par bailleur</h2>
    <div class="stack-list">
      <div v-for="item in items" :key="item.label" class="stack-row">
        <span>{{ item.label }}</span>
        <div class="stack-track">
          <i class="green" :style="{ width: `${item.width * 0.68}%` }">{{ Math.round(item.count * 0.68) }}</i>
          <i class="yellow" :style="{ width: `${item.width * 0.22}%` }">{{ Math.round(item.count * 0.22) }}</i>
          <i class="red" :style="{ width: `${item.width * 0.1}%` }">{{ Math.round(item.count * 0.1) }}</i>
        </div>
        <strong>{{ item.count }}</strong>
      </div>
    </div>
  </article>
</template>
