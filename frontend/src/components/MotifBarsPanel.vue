<script setup>
import { computed, ref } from "vue";

const props = defineProps({
  items: {
    type: Array,
    default: () => [],
  },
});

const hoveredItem = ref(null);
const tooltipPosition = ref({ x: 0, y: 0, align: "right" });

const totalCount = computed(() =>
  props.items.reduce((sum, item) => sum + Number(item.count || 0), 0),
);

const tooltipStyle = computed(() => ({
  left: `${tooltipPosition.value.x}px`,
  top: `${tooltipPosition.value.y}px`,
}));

const hoveredShare = computed(() => {
  if (!hoveredItem.value || !totalCount.value) return 0;
  return (Number(hoveredItem.value.count || 0) / totalCount.value) * 100;
});

function showTooltip(item, event) {
  hoveredItem.value = item;
  updateTooltipPosition(event);
}

function updateTooltipPosition(event) {
  const panel = event.currentTarget.closest(".motif-panel");
  if (!panel) return;

  const rect = panel.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;

  tooltipPosition.value = {
    x,
    y,
    align: x > rect.width * 0.56 ? "left" : "right",
  };
}

function hideTooltip() {
  hoveredItem.value = null;
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString("fr-FR");
}

function formatRate(value) {
  return Number(value || 0).toLocaleString("fr-FR", { maximumFractionDigits: 1 });
}
</script>

<template>
  <article class="panel motif-panel">
    <h2>Principaux motifs de non-utilisation</h2>
    <div class="horizontal-bars">
      <div
        v-for="item in items"
        :key="item.label"
        class="reason-row"
        @mouseenter="showTooltip(item, $event)"
        @mousemove="updateTooltipPosition"
        @mouseleave="hideTooltip"
      >
        <span>{{ item.label }}</span>
        <span class="reason-track">
          <i :style="{ width: `${item.width}%` }"></i>
        </span>
        <strong>{{ item.count }}</strong>
      </div>
    </div>

    <div
      v-if="hoveredItem"
      :class="['motif-tooltip', { 'is-left': tooltipPosition.align === 'left' }]"
      :style="tooltipStyle"
    >
      <strong>{{ hoveredItem.label }}</strong>
      <div>
        <span>Nombre</span>
        <b>{{ formatNumber(hoveredItem.count) }}</b>
      </div>
      <div>
        <span>Part</span>
        <b>{{ formatRate(hoveredShare) }}%</b>
      </div>
    </div>
  </article>
</template>
