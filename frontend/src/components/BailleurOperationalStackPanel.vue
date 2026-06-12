<script setup>
import { computed, ref } from "vue";

const props = defineProps({
  payload: {
    type: Object,
    default: () => ({ items: [], statuses: [] }),
  },
});

const statusColors = {
  Utilisés: "#39b960",
  "Partiellement utilisés": "#ffc72c",
  "Non utilisés": "#ee3737",
  "Non déployé": "#9aa6b5",
};

const items = computed(() => props.payload.items || []);
const statuses = computed(() => props.payload.statuses || []);
const tooltip = ref(null);

function colorFor(status) {
  return statusColors[status] || "#1477d3";
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString("fr-FR");
}

function formatRate(value) {
  return Number(value || 0).toLocaleString("fr-FR", { maximumFractionDigits: 1 });
}

function legendLabelParts(status) {
  return status === "Utilisés" ? [status] : status.split(" ");
}

function updateTooltipPosition(event, item, status) {
  const chart = event.currentTarget.closest(".operational-column-chart");
  if (!chart) return;

  const bounds = chart.getBoundingClientRect();
  const rawY = event.clientY - bounds.top;
  const x = Math.min(Math.max(event.clientX - bounds.left, 96), Math.max(bounds.width - 96, 96));
  const y = Math.min(Math.max(rawY, 18), Math.max(bounds.height - 18, 18));

  tooltip.value = {
    x,
    y,
    placement: rawY < 112 ? "bottom" : "top",
    bailleur: item.label,
    total: item.total,
    label: status.label,
    count: status.count,
    rate: status.rate,
    color: colorFor(status.label),
  };
}

function hideTooltip() {
  tooltip.value = null;
}
</script>

<template>
  <article class="panel bailleur-operational-panel">
    <h2>Répartition des statuts opérationnels par bailleur</h2>

    <div class="operational-column-chart">
      <div class="operational-column-list">
        <div v-for="item in items" :key="item.label" class="operational-column-card">
          <span class="operational-total">{{ formatNumber(item.total) }}</span>
          <div class="operational-column" :aria-label="item.label">
            <i
              v-for="status in item.statuses"
              :key="status.label"
              :style="{
                height: `${status.rate}%`,
                background: colorFor(status.label),
              }"
              @mouseenter="updateTooltipPosition($event, item, status)"
              @mousemove="updateTooltipPosition($event, item, status)"
              @mouseleave="hideTooltip"
            >
              <span v-if="status.rate >= 9">{{ formatNumber(status.count) }}</span>
            </i>
          </div>
          <strong>{{ item.label }}</strong>
        </div>
      </div>

      <div class="operational-legend">
        <span v-for="status in statuses" :key="status">
          <i :style="{ background: colorFor(status) }"></i>
          <b :class="{ 'legend-label--stacked': status !== 'Utilisés' }">
            <span v-for="part in legendLabelParts(status)" :key="part">{{ part }}</span>
          </b>
        </span>
      </div>

      <div
        v-if="tooltip"
        :class="['operational-tooltip', `operational-tooltip--${tooltip.placement}`]"
        :style="{ left: `${tooltip.x}px`, top: `${tooltip.y}px` }"
      >
        <span class="operational-tooltip__status" :style="{ color: tooltip.color }">
          <i :style="{ background: tooltip.color }"></i>
          {{ tooltip.label }}
        </span>
        <strong>{{ tooltip.bailleur }}</strong>
        <div>
          <span>Total</span>
          <b>{{ formatNumber(tooltip.total) }}</b>
        </div>
        <div>
          <span>Nombre</span>
          <b>{{ formatNumber(tooltip.count) }}</b>
        </div>
        <div>
          <span>Part</span>
          <b>{{ formatRate(tooltip.rate) }}%</b>
        </div>
      </div>
    </div>
  </article>
</template>
