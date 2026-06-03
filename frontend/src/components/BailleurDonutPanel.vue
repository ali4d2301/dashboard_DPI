<script setup>
import { computed, ref } from "vue";
import { bailleurColor } from "../utils/bailleurColors";

const props = defineProps({
  items: {
    type: Array,
    default: () => [],
  },
});

const chart = {
  cx: 276,
  cy: 128,
  outerRadius: 126,
  innerRadius: 78,
};
const hoveredSegment = ref(null);
const tooltipPosition = ref({ x: 0, y: 0 });

const total = computed(() => props.items.reduce((sum, item) => sum + Number(item.count || 0), 0));

const segments = computed(() => {
  let cursor = 0;

  return props.items.map((item, index) => {
    const value = total.value ? (Number(item.count || 0) / total.value) * 100 : 0;
    const segment = {
      ...item,
      color: bailleurColor(item.label),
      start: cursor,
      end: cursor + value,
      rate: value,
    };
    cursor += value;
    return segment;
  });
});

const annotatedSegments = computed(() =>
  segments.value.map((segment, index) => {
    const gap = 2.1;
    const startAngle = segment.start * 3.6 + gap;
    const endAngle = segment.end * 3.6 - gap;
    const middleAngle = (startAngle + endAngle) / 2;
    const layout = labelLayout(segment.label, index);

    return {
      ...segment,
      path: describeDonutSegment(
        chart.cx,
        chart.cy,
        chart.outerRadius,
        chart.innerRadius,
        startAngle,
        endAngle,
      ),
      connectorPath: describeConnector(middleAngle, layout),
      labelX: layout.x,
      labelY: layout.y,
      textAnchor: layout.anchor,
    };
  }),
);

const tooltipSide = computed(() => (tooltipPosition.value.x > chart.cx ? "left" : "right"));

function formatNumber(value) {
  return Number(value || 0).toLocaleString("fr-FR");
}

function formatRate(value) {
  return Number(value || 0).toLocaleString("fr-FR", { maximumFractionDigits: 1 });
}

function showTooltip(segment, event) {
  hoveredSegment.value = segment;
  if (event) {
    moveTooltip(event);
    return;
  }

  tooltipPosition.value = {
    x: segment.textAnchor === "end" ? segment.labelX + 8 : segment.labelX - 8,
    y: segment.labelY + 8,
  };
}

function moveTooltip(event) {
  const stage = event.currentTarget.closest(".bailleur-donut-stage");
  if (!stage) return;

  const bounds = stage.getBoundingClientRect();
  tooltipPosition.value = {
    x: event.clientX - bounds.left,
    y: event.clientY - bounds.top,
  };
}

function hideTooltip() {
  hoveredSegment.value = null;
}

function normalizeKey(value = "") {
  return value
    .toString()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function labelLayout(label, index) {
  const layouts = {
    "non couvert": {
      x: 429,
      y: 119,
      anchor: "start",
      angle: 90,
      elbow: { x: 412, y: 128 },
      end: { x: 425, y: 128 },
    },
    "ucps bm": {
      x: 145,
      y: 218,
      anchor: "end",
      angle: 218,
      elbow: { x: 174, y: 221 },
      end: { x: 153, y: 221 },
    },
    padci: {
      x: 111,
      y: 96,
      anchor: "end",
      angle: 292,
      elbow: { x: 149, y: 93 },
      end: { x: 119, y: 93 },
    },
    prtds: {
      x: 218,
      y: -18,
      anchor: "middle",
      angle: 338,
      elbow: { x: 222, y: -2 },
      end: { x: 218, y: -5 },
    },
  };

  return (
    layouts[normalizeKey(label)] || {
      x: 334,
      y: 54 + index * 32,
      anchor: "start",
      angle: 70 + index * 26,
      elbow: null,
      end: null,
    }
  );
}

function describeConnector(angle, layout) {
  const calloutAngle = layout.angle ?? angle;
  const start = polarToCartesian(chart.cx, chart.cy, chart.outerRadius + 3, calloutAngle);
  const elbow = layout.elbow || polarToCartesian(chart.cx, chart.cy, chart.outerRadius + 17, calloutAngle);
  const end =
    layout.end ||
    (layout.anchor === "start"
      ? { x: layout.x - 10, y: elbow.y }
      : { x: layout.x + 10, y: elbow.y });

  return `M ${start.x} ${start.y} L ${elbow.x} ${elbow.y} L ${end.x} ${end.y}`;
}

function describeDonutSegment(cx, cy, outerRadius, innerRadius, startAngle, endAngle) {
  const outerStart = polarToCartesian(cx, cy, outerRadius, startAngle);
  const outerEnd = polarToCartesian(cx, cy, outerRadius, endAngle);
  const innerEnd = polarToCartesian(cx, cy, innerRadius, endAngle);
  const innerStart = polarToCartesian(cx, cy, innerRadius, startAngle);
  const largeArcFlag = endAngle - startAngle > 180 ? 1 : 0;

  return [
    `M ${outerStart.x} ${outerStart.y}`,
    `A ${outerRadius} ${outerRadius} 0 ${largeArcFlag} 1 ${outerEnd.x} ${outerEnd.y}`,
    `L ${innerEnd.x} ${innerEnd.y}`,
    `A ${innerRadius} ${innerRadius} 0 ${largeArcFlag} 0 ${innerStart.x} ${innerStart.y}`,
    "Z",
  ].join(" ");
}

function polarToCartesian(cx, cy, radius, angle) {
  const radians = (angle * Math.PI) / 180;
  return {
    x: Number((cx + radius * Math.sin(radians)).toFixed(2)),
    y: Number((cy - radius * Math.cos(radians)).toFixed(2)),
  };
}
</script>

<template>
  <article class="panel bailleur-donut-panel">
    <h2>Répartition des établissements par bailleur</h2>

    <div class="bailleur-donut-layout">
      <div class="bailleur-donut-stage">
        <svg class="bailleur-donut-svg" viewBox="0 0 520 260" role="img" aria-label="Répartition des établissements par bailleur">
          <g class="donut-connectors">
            <path
              v-for="segment in annotatedSegments"
              :key="`${segment.label}-line`"
              :d="segment.connectorPath"
              :stroke="segment.color"
            />
          </g>

          <g class="donut-ring">
            <path
              v-for="segment in annotatedSegments"
              :key="segment.label"
              class="donut-segment"
              :class="{
                'is-active': hoveredSegment?.label === segment.label,
                'is-muted': hoveredSegment && hoveredSegment.label !== segment.label,
              }"
              :d="segment.path"
              :fill="segment.color"
              tabindex="0"
              :aria-label="`${segment.label}: ${formatNumber(segment.count)} établissements, ${formatRate(segment.rate)}%`"
              @pointerenter="showTooltip(segment, $event)"
              @pointermove="moveTooltip"
              @pointerleave="hideTooltip"
              @focus="showTooltip(segment)"
              @blur="hideTooltip"
            />
          </g>

          <circle class="donut-center" :cx="chart.cx" :cy="chart.cy" r="75" />
          <text class="donut-total" :x="chart.cx" :y="chart.cy - 5" text-anchor="middle">
            <tspan class="donut-total-label" :x="chart.cx" dy="-4">TOTAL</tspan>
            <tspan class="donut-total-value" :x="chart.cx" dy="31">{{ formatNumber(total) }}</tspan>
          </text>

          <g class="donut-callouts">
            <text
              v-for="segment in annotatedSegments"
              :key="`${segment.label}-label`"
              class="donut-callout"
              :x="segment.labelX"
              :y="segment.labelY"
              :text-anchor="segment.textAnchor"
            >
              <tspan class="donut-callout-label" :x="segment.labelX">{{ segment.label }}</tspan>
              <tspan class="donut-callout-rate" :x="segment.labelX" dy="17">{{ formatRate(segment.rate) }}%</tspan>
            </text>
          </g>
        </svg>

        <div
          v-if="hoveredSegment"
          class="donut-hover-tooltip"
          :class="`is-${tooltipSide}`"
          :style="{
            left: `${tooltipPosition.x}px`,
            top: `${tooltipPosition.y}px`,
            '--tooltip-color': hoveredSegment.color,
          }"
        >
          <strong>{{ hoveredSegment.label }}</strong>
          <span>
            <b>{{ formatNumber(hoveredSegment.count) }}</b>
            établissements · {{ formatRate(hoveredSegment.rate) }}%
          </span>
        </div>
      </div>
    </div>
  </article>
</template>
