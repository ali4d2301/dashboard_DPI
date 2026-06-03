<script setup>
import { computed } from "vue";

const props = defineProps({
  payload: {
    type: Object,
    default: () => ({ items: [], statuses: [] }),
  },
});

const statusColors = {
  Déployé: "#39b960",
  "En cours": "#ffc72c",
  "Non démarré": "#9aa6b5",
  "Non renseigné": "#c6d1dd",
};

const items = computed(() => props.payload.items || []);
const statuses = computed(() => props.payload.statuses || []);

function colorFor(status, index) {
  return statusColors[status] || ["#1477d3", "#ff8f3d", "#805ad5"][index % 3];
}

function formatRate(value) {
  return Number(value || 0).toLocaleString("fr-FR", { maximumFractionDigits: 1 });
}
</script>

<template>
  <article class="panel reference-stack-panel">
    <div class="reference-stack-header">
      <h2>Statut de déploiement par catégorie d'établissement</h2>
    </div>

    <div class="reference-stack-chart">
      <div class="stack-bars">
        <div v-for="item in items" :key="item.label" class="stack-category">
          <div class="stack-column" :aria-label="item.label">
            <i
              v-for="(status, index) in item.statuses"
              :key="status.label"
              :style="{
                height: `${status.rate}%`,
                background: colorFor(status.label, index),
              }"
              :title="`${status.label}: ${formatRate(status.rate)}%`"
            >
              <span v-if="status.rate >= 8">{{ formatRate(status.rate) }}%</span>
            </i>
          </div>
          <strong>{{ item.label }}</strong>
        </div>
      </div>
    </div>

    <div class="stack-legend">
      <span v-for="(status, index) in statuses" :key="status">
        <i :style="{ background: colorFor(status, index) }"></i>{{ status }}
      </span>
    </div>
  </article>
</template>
