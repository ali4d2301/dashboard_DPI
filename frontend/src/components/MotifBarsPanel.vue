<script setup>
defineProps({
  items: {
    type: Array,
    default: () => [],
  },
});
</script>

<template>
  <article class="panel motif-panel">
    <h2>Principaux motifs de non fonctionnalité</h2>
    <div class="horizontal-bars">
      <div v-for="item in items" :key="item.label" class="reason-row">
        <span>{{ item.label }}</span>
        <i :style="{ width: `${item.width}%` }"></i>
        <strong>{{ item.count }}</strong>
      </div>
    </div>
  </article>
</template>
