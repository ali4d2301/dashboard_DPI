<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";
import topology from "../assets/cdi_regions_hdx.json";

const props = defineProps({
  regions: {
    type: Array,
    default: () => [],
  },
  selectedRegion: {
    type: String,
    default: "",
  },
  regionSummary: {
    type: Object,
    default: () => ({}),
  },
});

const emit = defineEmits(["select-region"]);

const WIDTH = 420;
const HEIGHT = 500;
const PADDING = 18;
const MIN_ZOOM = 1;
const MAX_ZOOM = 4;
const ZOOM_STEP = 1.25;

const zoom = ref(1);
const viewBox = ref({ x: 0, y: 0, width: WIDTH, height: HEIGHT });
const panState = ref(null);
const didPan = ref(false);
const hoveredFeature = ref(null);
const tooltipPosition = ref({ x: 0, y: 0, align: "right" });
const isFullscreen = ref(false);
const fullscreenSnapshot = ref(null);
let previousBodyOverflow = "";
let previousDocumentOverflow = "";

const nameAliases = {
  agnebytiassa: "agnebytiassa",
  belier: "belier",
  gontougo: "gontougo",
  gbeke: "gbeke",
  goh: "goh",
  guemon: "guemon",
  hautsassandra: "hautsassandra",
  lohdjiboua: "lohdjiboua",
  nawa: "nawa",
  poro: "poro",
  sudcomoe: "sudcomoe",
  tonkpi: "tonkpi",
  abidjan1: "abidjan1",
  abidjan2: "abidjan2",
  grandponts: "grandsponts",
  indeniedjuablin: "indenieduablin",
};

const regionDisplayNames = {
  abidjan1: "Abidjan 1",
  abidjan2: "Abidjan 2",
  agnebytiassa: "Agnéby-Tiassa",
  bafing: "Bafing",
  bagoue: "Bagoué",
  belier: "Bélier",
  bere: "Béré",
  bounkani: "Bounkani",
  cavally: "Cavally",
  folon: "Folon",
  gbeke: "Gbêkê",
  gbokle: "Gbôklé",
  goh: "Gôh",
  gontougo: "Gontougo",
  grandsponts: "Grands-Ponts",
  guemon: "Guémon",
  hambol: "Hambol",
  hautsassandra: "Haut-Sassandra",
  iffou: "Iffou",
  indenieduablin: "Indénié-Djuablin",
  indeniedjuablin: "Indénié-Djuablin",
  kabadougou: "Kabadougou",
  lohdjiboua: "Lôh-Djiboua",
  marahoue: "Marahoué",
  me: "Mé",
  moronou: "Moronou",
  nawa: "Nawa",
  nzi: "N'Zi",
  poro: "Poro",
  sanpedro: "San-Pédro",
  sudcomoe: "Sud-Comoé",
  tchologo: "Tchologo",
  tonkpi: "Tonkpi",
  worodougou: "Worodougou",
};

const decodedArcs = decodeArcs(topology);
const rawFeatures = Array.from(
  topology.objects.cdi_regions_hdx.geometries.reduce((featuresByRegion, geometry) => {
    const polygons = geometryToPolygons(geometry, decodedArcs);
    const regionName = geometry.properties.ADM1_FR;
    const matchKey = normalizeName(regionName);
    const existingFeature = featuresByRegion.get(matchKey);

    if (existingFeature) {
      existingFeature.key = `${existingFeature.key}-${geometry.properties.ADM1_PCODE}`;
      existingFeature.polygons.push(...polygons);
      return featuresByRegion;
    }

    featuresByRegion.set(matchKey, {
      key: `${geometry.properties.ADM1_PCODE}-${regionName}`,
      name: displayRegionName(regionName),
      matchKey,
      polygons,
    });

    return featuresByRegion;
  }, new Map()).values(),
);

const bounds = getBounds(rawFeatures);

const mapViewBox = computed(() => {
  const box = viewBox.value;
  return `${box.x} ${box.y} ${box.width} ${box.height}`;
});

const normalizedSelectedRegion = computed(() => normalizeName(props.selectedRegion));
const isSelectionActive = computed(() => Boolean(normalizedSelectedRegion.value));
const tooltipSummary = computed(() => {
  if (!hoveredFeature.value?.dataLabel) return [];
  return props.regionSummary[hoveredFeature.value.dataLabel] || null;
});
const tooltipStyle = computed(() => ({
  left: `${tooltipPosition.value.x}px`,
  top: `${tooltipPosition.value.y}px`,
}));
const shouldShowExpandedLabels = computed(() => isFullscreen.value || zoom.value >= 1.55);

watch(isFullscreen, (active) => {
  if (active) {
    previousBodyOverflow = document.body.style.overflow;
    previousDocumentOverflow = document.documentElement.style.overflow;
    document.body.style.overflow = "hidden";
    document.documentElement.style.overflow = "hidden";
    return;
  }

  document.body.style.overflow = previousBodyOverflow;
  document.documentElement.style.overflow = previousDocumentOverflow;
});

onBeforeUnmount(() => {
  document.body.style.overflow = previousBodyOverflow;
  document.documentElement.style.overflow = previousDocumentOverflow;
});

const mapFeatures = computed(() => {
  const ratesByRegion = new Map(
    props.regions.map((region) => [normalizeName(region.label), region.rate]),
  );
  const labelsByRegion = new Map(
    props.regions.map((region) => [normalizeName(region.label), region.label]),
  );
  const labelVisibilityByRegion = new Map(
    props.regions.map((region) => [normalizeName(region.label), Boolean(region.showLabel)]),
  );

  return rawFeatures.map((feature) => {
    const projected = feature.polygons.map((polygon) =>
      polygon.map(([x, y]) => projectPoint(x, y, bounds)),
    );
    const labelPoint = featureLabelPoint(projected);
    const rate = ratesByRegion.get(feature.matchKey);
    const selected = normalizedSelectedRegion.value === feature.matchKey;
    const dataLabel = labelsByRegion.get(feature.matchKey) || "";

    return {
      ...feature,
      dataLabel,
      displayLabel: displayRegionName(dataLabel || feature.name),
      path: projected.map(polygonToPath).join(" "),
      labelPoint,
      rate,
      fillColor: rate == null ? null : rateColor(rate),
      selected,
      showLabel: selected || shouldShowExpandedLabels.value || labelVisibilityByRegion.get(feature.matchKey),
    };
  });
});

function normalizeName(value = "") {
  const normalized = value
    .toString()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-zA-Z0-9]/g, "")
    .toLowerCase();

  return nameAliases[normalized] || normalized;
}

function displayRegionName(value = "") {
  return regionDisplayNames[normalizeName(value)] || value;
}

function decodeArcs(topojson) {
  const [scaleX, scaleY] = topojson.transform.scale;
  const [translateX, translateY] = topojson.transform.translate;

  return topojson.arcs.map((arc) => {
    let x = 0;
    let y = 0;

    return arc.map(([dx, dy]) => {
      x += dx;
      y += dy;
      return [x * scaleX + translateX, y * scaleY + translateY];
    });
  });
}

function geometryToPolygons(geometry, arcs) {
  const rings = geometry.type === "Polygon" ? geometry.arcs : geometry.arcs.flat();

  return rings.map((ring) =>
    ring.flatMap((arcIndex, index) => {
      const arc = arcIndex >= 0 ? arcs[arcIndex] : [...arcs[-arcIndex - 1]].reverse();
      return index === 0 ? arc : arc.slice(1);
    }),
  );
}

function getBounds(features) {
  const points = features.flatMap((feature) => feature.polygons.flat());
  const xs = points.map(([x]) => x);
  const ys = points.map(([, y]) => y);

  return {
    minX: Math.min(...xs),
    maxX: Math.max(...xs),
    minY: Math.min(...ys),
    maxY: Math.max(...ys),
  };
}

function projectPoint(x, y, bounds) {
  const scale = Math.min(
    (WIDTH - PADDING * 2) / (bounds.maxX - bounds.minX),
    (HEIGHT - PADDING * 2) / (bounds.maxY - bounds.minY),
  );
  const mapWidth = (bounds.maxX - bounds.minX) * scale;
  const mapHeight = (bounds.maxY - bounds.minY) * scale;
  const offsetX = (WIDTH - mapWidth) / 2;
  const offsetY = (HEIGHT - mapHeight) / 2;

  return [
    offsetX + (x - bounds.minX) * scale,
    offsetY + (bounds.maxY - y) * scale,
  ];
}

function polygonToPath(points) {
  const [firstPoint, ...rest] = points;
  return `M${firstPoint[0].toFixed(2)} ${firstPoint[1].toFixed(2)} ${rest
    .map(([x, y]) => `L${x.toFixed(2)} ${y.toFixed(2)}`)
    .join(" ")} Z`;
}

function featureLabelPoint(polygons) {
  const largestPolygon = polygons.reduce(
    (best, polygon) => {
      const area = polygonArea(polygon);
      return area > best.area ? { area, polygon } : best;
    },
    { area: -1, polygon: polygons[0] },
  );

  return polygonCentroid(largestPolygon.polygon || polygons.flat());
}

function polygonArea(points) {
  return Math.abs(
    points.reduce((area, [x, y], index) => {
      const [nextX, nextY] = points[(index + 1) % points.length];
      return area + x * nextY - nextX * y;
    }, 0) / 2,
  );
}

function polygonCentroid(points) {
  const areaFactor = points.reduce((sum, [x, y], index) => {
    const [nextX, nextY] = points[(index + 1) % points.length];
    return sum + x * nextY - nextX * y;
  }, 0);

  if (!areaFactor) {
    const total = points.reduce(
      (acc, [x, y]) => {
        acc.x += x;
        acc.y += y;
        return acc;
      },
      { x: 0, y: 0 },
    );

    return {
      x: total.x / points.length,
      y: total.y / points.length,
    };
  }

  const centroid = points.reduce(
    (acc, [x, y], index) => {
      const [nextX, nextY] = points[(index + 1) % points.length];
      const cross = x * nextY - nextX * y;
      acc.x += (x + nextX) * cross;
      acc.y += (y + nextY) * cross;
      return acc;
    },
    { x: 0, y: 0 },
  );

  return {
    x: centroid.x / (3 * areaFactor),
    y: centroid.y / (3 * areaFactor),
  };
}

function rateColor(rate) {
  const boundedRate = Math.min(Math.max(Number(rate) || 0, 0), 100);
  const hue = Math.round((boundedRate / 100) * 128);
  return `hsl(${hue}, 72%, 48%)`;
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function clampViewBox(box) {
  const maxX = Math.max(WIDTH - box.width, 0);
  const maxY = Math.max(HEIGHT - box.height, 0);

  return {
    ...box,
    x: box.width >= WIDTH ? 0 : clamp(box.x, 0, maxX),
    y: box.height >= HEIGHT ? 0 : clamp(box.y, 0, maxY),
  };
}

function setZoom(nextZoom, center = null) {
  const boundedZoom = clamp(nextZoom, MIN_ZOOM, MAX_ZOOM);
  const box = viewBox.value;
  const focalPoint = center || {
    x: box.x + box.width / 2,
    y: box.y + box.height / 2,
  };
  const nextWidth = WIDTH / boundedZoom;
  const nextHeight = HEIGHT / boundedZoom;
  const ratioX = (focalPoint.x - box.x) / box.width;
  const ratioY = (focalPoint.y - box.y) / box.height;

  zoom.value = boundedZoom;
  viewBox.value = clampViewBox({
    x: focalPoint.x - ratioX * nextWidth,
    y: focalPoint.y - ratioY * nextHeight,
    width: nextWidth,
    height: nextHeight,
  });
}

function zoomIn() {
  setZoom(zoom.value * ZOOM_STEP);
}

function zoomOut() {
  setZoom(zoom.value / ZOOM_STEP);
}

function resetMapView() {
  zoom.value = 1;
  viewBox.value = { x: 0, y: 0, width: WIDTH, height: HEIGHT };
}

function toggleFullscreen() {
  if (!isFullscreen.value) {
    fullscreenSnapshot.value = {
      zoom: zoom.value,
      viewBox: { ...viewBox.value },
    };
    isFullscreen.value = true;
    return;
  }

  if (fullscreenSnapshot.value) {
    zoom.value = fullscreenSnapshot.value.zoom;
    viewBox.value = { ...fullscreenSnapshot.value.viewBox };
  }
  hideTooltip();
  panState.value = null;
  fullscreenSnapshot.value = null;
  isFullscreen.value = false;
}

function selectRegion(feature) {
  if (didPan.value) {
    didPan.value = false;
    return;
  }
  if (!feature.dataLabel) return;
  emit("select-region", feature.dataLabel);
}

function showTooltip(feature, event) {
  hoveredFeature.value = feature;
  updateTooltipPosition(event);
}

function updateTooltipPosition(event) {
  const layout = event.currentTarget.ownerSVGElement?.parentElement;
  if (!layout) return;

  const rect = layout.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;

  tooltipPosition.value = {
    x,
    y,
    align: x > rect.width * 0.58 ? "left" : "right",
  };
}

function hideTooltip() {
  hoveredFeature.value = null;
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString("fr-FR");
}

function formatRate(value) {
  return Number(value || 0).toLocaleString("fr-FR", { maximumFractionDigits: 1 });
}

function pointerToViewBox(event) {
  const rect = event.currentTarget.getBoundingClientRect();
  const box = viewBox.value;

  return {
    x: box.x + ((event.clientX - rect.left) / rect.width) * box.width,
    y: box.y + ((event.clientY - rect.top) / rect.height) * box.height,
  };
}

function handleWheel(event) {
  const factor = event.deltaY < 0 ? ZOOM_STEP : 1 / ZOOM_STEP;
  setZoom(zoom.value * factor, pointerToViewBox(event));
}

function startPan(event) {
  if (zoom.value <= MIN_ZOOM) return;

  hideTooltip();
  didPan.value = false;
  panState.value = {
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    box: { ...viewBox.value },
  };
}

function movePan(event) {
  if (!panState.value) return;

  const rect = event.currentTarget.getBoundingClientRect();
  const state = panState.value;
  const dx = ((event.clientX - state.startX) / rect.width) * state.box.width;
  const dy = ((event.clientY - state.startY) / rect.height) * state.box.height;
  didPan.value =
    didPan.value ||
    Math.abs(event.clientX - state.startX) > 4 ||
    Math.abs(event.clientY - state.startY) > 4;

  viewBox.value = clampViewBox({
    ...state.box,
    x: state.box.x - dx,
    y: state.box.y - dy,
  });
}

function endPan(event) {
  if (!panState.value) return;

  const hadPan = didPan.value;
  if (event.currentTarget.hasPointerCapture?.(panState.value.pointerId)) {
    event.currentTarget.releasePointerCapture?.(panState.value.pointerId);
  }
  panState.value = null;
  if (hadPan) {
    window.setTimeout(() => {
      didPan.value = false;
    }, 0);
  }
}
</script>

<template>
  <article :class="['panel map-panel', { 'is-fullscreen': isFullscreen }]">
    <div class="map-panel-header">
      <h2>Taux de déploiement par région sanitaire</h2>
      <button class="map-fullscreen-button" type="button" @click="toggleFullscreen">
        {{ isFullscreen ? "Réduire" : "Plein écran" }}
      </button>
    </div>
    <div class="map-layout">
      <div class="map-controls" aria-label="Contrôles de carte">
        <button type="button" title="Zoomer" @click="zoomIn">+</button>
        <button type="button" title="Dézoomer" @click="zoomOut">&minus;</button>
        <button type="button" title="Réinitialiser" @click="resetMapView">&#8635;</button>
      </div>

      <svg
        :class="['region-map', { 'is-pannable': zoom > 1, 'is-panning': panState }]"
        :viewBox="mapViewBox"
        role="img"
        aria-label="Carte des régions sanitaires de Côte d'Ivoire"
        @pointerdown="startPan"
        @pointermove="movePan"
        @pointerup="endPan"
        @pointercancel="endPan"
        @pointerleave="endPan"
        @wheel.prevent="handleWheel"
      >
        <g>
          <path
            v-for="feature in mapFeatures"
            :key="feature.key"
            :class="[
              'region-shape',
              {
                'no-data': feature.rate == null,
                'is-selected': feature.selected,
                'is-muted': isSelectionActive && !feature.selected,
              },
            ]"
            :d="feature.path"
            :style="feature.fillColor ? { fill: feature.fillColor } : null"
            @click="selectRegion(feature)"
            @pointerenter="showTooltip(feature, $event)"
            @pointermove="updateTooltipPosition"
            @pointerleave="hideTooltip"
          ></path>
        </g>
        <g class="map-labels">
          <text
            v-for="feature in mapFeatures.filter((item) => item.rate != null && item.showLabel)"
            :key="`${feature.key}-label`"
            :class="{ 'is-selected': feature.selected }"
            :x="feature.labelPoint.x"
            :y="feature.labelPoint.y"
          >
            <tspan class="label-name" :x="feature.labelPoint.x">{{ feature.name }}</tspan>
            <tspan class="label-rate" :x="feature.labelPoint.x" :dy="13">{{ feature.rate }}%</tspan>
          </text>
        </g>
      </svg>

      <div class="legend spectrum-legend" aria-label="Spectre du taux de déploiement de 0 à 100%">
        <span>0%</span>
        <i class="spectrum-bar"></i>
        <span>100%</span>
      </div>

      <div
        v-if="hoveredFeature && tooltipSummary"
        :class="['map-hover-tooltip', { 'is-left': tooltipPosition.align === 'left' }]"
        :style="tooltipStyle"
      >
        <strong>{{ hoveredFeature.displayLabel }}</strong>
        <div class="tooltip-metrics">
          <div class="tooltip-metric tooltip-metric--main">
            <span>Nombre</span>
            <b>{{ formatNumber(tooltipSummary.supported) }}</b>
          </div>
          <div class="tooltip-metric">
            <span>Taux de déploiement</span>
            <b>{{ formatRate(tooltipSummary.deploymentRate) }}%</b>
          </div>
          <div class="tooltip-metric">
            <span>Taux d'utilisation</span>
            <b>{{ formatRate(tooltipSummary.functionalityRate) }}%</b>
          </div>
        </div>
      </div>
    </div>
  </article>
</template>
