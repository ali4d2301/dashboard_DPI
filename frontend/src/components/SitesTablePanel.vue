<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { getRows } from "../services/api";
import { bailleurColor } from "../utils/bailleurColors";

const props = defineProps({
  totalSites: {
    type: Number,
    default: 0,
  },
  lastUpdate: {
    type: String,
    default: "",
  },
});

const API_PAGE_SIZE = 5000;
const LEGACY_API_PAGE_SIZE = 200;
const ROW_CACHE_TTL_MS = 5 * 60 * 1000;
const ROW_CACHE_STORAGE_KEY = "dpi-dashboard-sites-cache-v1";
const FILTER_KEYS = [
  "region_sanitaire",
  "district_sanitaire",
  "bailleur",
  "statut_deploiement",
  "statut_operationnel",
  "motif_principal",
];
const REGION_DISPLAY_NAMES = {
  abidjan1: "ABIDJAN 1",
  abidjan2: "ABIDJAN 2",
  agnebytiassa: "AGNÉBY-TIASSA",
  bagoue: "BAGOUÉ",
  belier: "BÉLIER",
  bere: "BÉRÉ",
  gbeke: "GBÊKÊ",
  gbokle: "GBÔKLÉ",
  goh: "GÔH",
  grandponts: "GRANDS-PONTS",
  guemon: "GUÉMON",
  hautsassandra: "HAUT-SASSANDRA",
  indeniedjuablin: "INDÉNIÉ-DJUABLIN",
  indenieduablin: "INDÉNIÉ-DJUABLIN",
  lohdjiboua: "LÔH-DJIBOUA",
  marahoue: "MARAHOUÉ",
  me: "MÉ",
  nzi: "N'ZI",
  sanpedro: "SAN-PÉDRO",
  sudcomoe: "SUD-COMOÉ",
};
const initialRowsCache = readStoredRowsCache();
let sitesRowsCache = initialRowsCache || { rows: [], totalRows: 0, expiresAt: 0 };
let sitesRowsPromise = null;

const loading = ref(!sitesRowsCache.rows.length);
const error = ref("");
const allRows = ref(sitesRowsCache.rows);
const totalRowCount = ref(sitesRowsCache.totalRows || sitesRowsCache.rows.length);
const search = ref("");
const currentPage = ref(1);
const pageSize = ref(20);
const sortKey = ref("id");
const sortDirection = ref("asc");
const openFilter = ref("");
const resizingColumn = ref(null);
const selectedRowIds = ref(new Set());
const filters = ref({
  region_sanitaire: "all",
  district_sanitaire: "all",
  bailleur: "all",
  statut_deploiement: "all",
  statut_operationnel: "all",
  motif_principal: "all",
});

const filterLabels = {
  region_sanitaire: "Région sanitaire",
  district_sanitaire: "District sanitaire",
  bailleur: "Bailleur",
  statut_deploiement: "Statut de déploiement",
  statut_operationnel: "Statut opérationnel",
  motif_principal: "Motif principal",
};

const columns = [
  { key: "id", label: "ID", width: 84, minWidth: 58 },
  { key: "etablissement_sanitaire", label: "Établissement sanitaire", width: 240, minWidth: 140 },
  { key: "region_sanitaire", label: "Région sanitaire", width: 150, minWidth: 96 },
  { key: "district_sanitaire", label: "District sanitaire", width: 150, minWidth: 96 },
  { key: "type_etablissement", label: "Type d'établissement", width: 180, minWidth: 110 },
  { key: "bailleur", label: "Bailleur", width: 120, minWidth: 82 },
  { key: "statut_deploiement", label: "Statut de déploiement", width: 158, minWidth: 100 },
  { key: "date_deploiement", label: "Date de déploiement", width: 144, minWidth: 96 },
  { key: "statut_operationnel", label: "Statut opérationnel", width: 160, minWidth: 106 },
  { key: "motif_principal", label: "Motif principal", width: 160, minWidth: 96 },
  { key: "point_focal", label: "Point focal", width: 150, minWidth: 96 },
  { key: "observation", label: "Observation", width: 220, minWidth: 110 },
  { key: "date_modification", label: "Date de mise à jour", width: 146, minWidth: 96 },
];

const columnWidths = ref(
  columns.reduce((acc, column) => {
    acc[column.key] = column.width;
    return acc;
  }, {}),
);

const filterOptions = computed(() => {
  return FILTER_KEYS.reduce((acc, key) => {
    const values = new Map();
    allRows.value.forEach((row) => {
      if (
        key === "district_sanitaire" &&
        filters.value.region_sanitaire !== "all" &&
        String(row.region_sanitaire ?? "") !== filters.value.region_sanitaire
      ) {
        return;
      }

      const value = row[key];
      if (value === null || value === undefined || value === "") return;
      values.set(String(value), key === "region_sanitaire" ? formatRegionLabel(value) : displayText(value));
    });

    acc[key] = Array.from(values, ([value, label]) => ({ value, label })).sort((a, b) =>
      a.label.localeCompare(b.label, "fr"),
    );
    return acc;
  }, {});
});

const filteredRows = computed(() => {
  const query = normalize(search.value);

  return allRows.value.filter((row) => {
    const matchesFilters = FILTER_KEYS.every((key) => {
      return filters.value[key] === "all" || String(row[key] ?? "") === filters.value[key];
    });

    if (!matchesFilters) return false;
    if (!query) return true;

    return [
      row.id,
      row.etablissement_sanitaire,
      row.region_sanitaire,
      row.district_sanitaire,
      row.type_etablissement,
      row.bailleur,
      row.point_focal,
      observationValue(row),
    ].some((value) => normalize(displayText(value)).includes(query));
  });
});

const sortedRows = computed(() => {
  const direction = sortDirection.value === "asc" ? 1 : -1;

  return [...filteredRows.value].sort((a, b) => {
    const first = sortableValue(rowValue(a, sortKey.value));
    const second = sortableValue(rowValue(b, sortKey.value));

    if (typeof first === "number" && typeof second === "number") {
      return (first - second) * direction;
    }

    return String(first).localeCompare(String(second), "fr", { numeric: true }) * direction;
  });
});

const pageCount = computed(() => Math.max(Math.ceil(sortedRows.value.length / pageSize.value), 1));
const startIndex = computed(() => (currentPage.value - 1) * pageSize.value);
const endIndex = computed(() => Math.min(startIndex.value + pageSize.value, sortedRows.value.length));
const visibleRows = computed(() => sortedRows.value.slice(startIndex.value, endIndex.value));
const tablePixelWidth = computed(
  () => columns.reduce((total, column) => total + (columnWidths.value[column.key] || column.width), 0),
);
const effectiveLastUpdate = computed(() => {
  const dates = allRows.value
    .map((row) => row.date_modification || row.date_import)
    .filter(Boolean)
    .sort();

  return dates.at(-1) || props.lastUpdate;
});

const hasActiveFilters = computed(() => {
  return search.value.trim() || FILTER_KEYS.some((key) => filters.value[key] !== "all");
});
const selectedRowsCount = computed(() => selectedRowIds.value.size);

watch([filteredRows, pageSize], () => {
  currentPage.value = 1;
});

watch([() => filters.value.region_sanitaire, filterOptions], () => {
  const selectedDistrict = filters.value.district_sanitaire;
  if (selectedDistrict === "all") return;

  const districtStillAvailable = filterOptions.value.district_sanitaire?.some(
    (option) => option.value === selectedDistrict,
  );

  if (!districtStillAvailable) {
    filters.value.district_sanitaire = "all";
  }
});

watch(pageCount, () => {
  currentPage.value = Math.min(currentPage.value, pageCount.value);
});

watch(allRows, () => {
  const availableIds = new Set(allRows.value.map((row) => rowKey(row)));
  selectedRowIds.value = new Set([...selectedRowIds.value].filter((id) => availableIds.has(id)));
});

onMounted(() => {
  loadAllRows();
  document.addEventListener("click", closeFilterDropdown);
});

onBeforeUnmount(() => {
  document.removeEventListener("click", closeFilterDropdown);
  stopColumnResize();
});

function readStoredRowsCache() {
  if (typeof window === "undefined") return null;

  try {
    const rawCache = window.sessionStorage.getItem(ROW_CACHE_STORAGE_KEY);
    if (!rawCache) return null;

    const payload = JSON.parse(rawCache);
    if (!payload || !Array.isArray(payload.rows) || Number(payload.expiresAt || 0) <= Date.now()) {
      window.sessionStorage.removeItem(ROW_CACHE_STORAGE_KEY);
      return null;
    }

    return {
      rows: payload.rows,
      totalRows: Number(payload.totalRows || payload.rows.length),
      expiresAt: Number(payload.expiresAt),
    };
  } catch {
    return null;
  }
}

function persistRowsCache(payload) {
  if (typeof window === "undefined") return;

  try {
    window.sessionStorage.setItem(ROW_CACHE_STORAGE_KEY, JSON.stringify(payload));
  } catch {
    // The table is usable even when browser storage is full or unavailable.
  }
}

function applyRowsCache(payload) {
  allRows.value = payload.rows;
  totalRowCount.value = payload.totalRows || payload.rows.length;
}

async function loadAllRows() {
  if (sitesRowsCache.rows.length && sitesRowsCache.expiresAt > Date.now()) {
    applyRowsCache(sitesRowsCache);
    loading.value = false;
    error.value = "";
    return;
  }

  loading.value = true;
  error.value = "";

  try {
    sitesRowsPromise = sitesRowsPromise || fetchDetailedRows(Number(props.totalSites || 0));
    const payload = await sitesRowsPromise;

    applyRowsCache(payload);
  } catch (loadError) {
    error.value = loadError.message || "Impossible de charger les données détaillées.";
  } finally {
    loading.value = false;
    sitesRowsPromise = null;
  }
}

async function fetchDetailedRows(fallbackTotal = 0) {
  const firstBatch = await getRowsWithFallback(API_PAGE_SIZE, 0);
  const firstRows = firstBatch.rows || [];
  const batchSize = Number(firstBatch.limit || API_PAGE_SIZE);
  const knownTotalRows = Number(firstBatch.total_rows || fallbackTotal || 0);
  let rows = firstRows;

  if (knownTotalRows && rows.length < knownTotalRows) {
    const offsets = [];
    for (let offset = batchSize; offset < knownTotalRows; offset += batchSize) {
      offsets.push(offset);
    }

    const batches = await Promise.all(offsets.map((offset) => getRowsWithFallback(batchSize, offset)));
    rows = [
      ...rows,
      ...batches
        .sort((a, b) => Number(a.offset || 0) - Number(b.offset || 0))
        .flatMap((batch) => batch.rows || []),
    ];
  } else if (!knownTotalRows && firstRows.length === batchSize) {
    let offset = batchSize;
    let nextBatch = await getRowsWithFallback(batchSize, offset);

    while ((nextBatch.rows || []).length) {
      rows = [...rows, ...(nextBatch.rows || [])];
      if ((nextBatch.rows || []).length < batchSize) break;
      offset += batchSize;
      nextBatch = await getRowsWithFallback(batchSize, offset);
    }
  }

  sitesRowsCache = {
    rows,
    totalRows: knownTotalRows || rows.length,
    expiresAt: Date.now() + ROW_CACHE_TTL_MS,
  };
  persistRowsCache(sitesRowsCache);

  return sitesRowsCache;
}

async function getRowsWithFallback(limit, offset) {
  try {
    return await getRows(limit, offset);
  } catch (loadError) {
    if (limit <= LEGACY_API_PAGE_SIZE) throw loadError;
    return getRows(LEGACY_API_PAGE_SIZE, offset);
  }
}

function setSort(key) {
  if (sortKey.value === key) {
    sortDirection.value = sortDirection.value === "asc" ? "desc" : "asc";
    return;
  }

  sortKey.value = key;
  sortDirection.value = key.includes("date") ? "desc" : "asc";
}

function sortMarker(key) {
  if (sortKey.value !== key) return "↕";
  return sortDirection.value === "asc" ? "↑" : "↓";
}

function columnWidth(key) {
  return `${columnWidths.value[key] || columns.find((column) => column.key === key)?.width || 120}px`;
}

function startColumnResize(event, key) {
  const column = columns.find((item) => item.key === key);
  if (!column) return;

  event.preventDefault();
  event.stopPropagation();
  stopColumnResize();

  resizingColumn.value = {
    key,
    startX: event.clientX,
    startWidth: columnWidths.value[key] || column.width,
    minWidth: column.minWidth || 72,
  };
  document.body.classList.add("is-resizing-site-table");
  document.addEventListener("mousemove", handleColumnResize);
  document.addEventListener("mouseup", stopColumnResize);
}

function handleColumnResize(event) {
  if (!resizingColumn.value) return;

  const { key, startX, startWidth, minWidth } = resizingColumn.value;
  const nextWidth = Math.max(minWidth, Math.min(startWidth + event.clientX - startX, 620));
  columnWidths.value = { ...columnWidths.value, [key]: Math.round(nextWidth) };
}

function stopColumnResize() {
  resizingColumn.value = null;
  document.removeEventListener("mousemove", handleColumnResize);
  document.removeEventListener("mouseup", stopColumnResize);
  document.body?.classList.remove("is-resizing-site-table");
}

function resetFilters() {
  search.value = "";
  FILTER_KEYS.forEach((key) => {
    filters.value[key] = "all";
  });
  closeFilterDropdown();
}

function filterOptionList(key) {
  return [{ value: "all", label: "Tous" }, ...(filterOptions.value[key] || [])];
}

function selectedFilterLabel(key) {
  if (filters.value[key] === "all") return "Tous";
  return filterOptions.value[key]?.find((option) => option.value === filters.value[key])?.label || displayText(filters.value[key]);
}

function toggleFilterDropdown(key) {
  openFilter.value = openFilter.value === key ? "" : key;
}

function selectFilterOption(key, value) {
  filters.value[key] = value;
  closeFilterDropdown();
}

function closeFilterDropdown() {
  openFilter.value = "";
}

function goToPage(page) {
  currentPage.value = Math.min(Math.max(Number(page), 1), pageCount.value);
}

function previousPage() {
  goToPage(currentPage.value - 1);
}

function nextPage() {
  goToPage(currentPage.value + 1);
}

function rowKey(row) {
  return String(
    row.id ??
      [
        row.etablissement_sanitaire,
        row.region_sanitaire,
        row.district_sanitaire,
        row.date_modification || row.date_import,
      ].join("|"),
  );
}

function isRowSelected(row) {
  return selectedRowIds.value.has(rowKey(row));
}

function selectRow(row, event) {
  const key = rowKey(row);
  const rowIsAlreadySelected = selectedRowIds.value.has(key);

  if (rowIsAlreadySelected) {
    const nextSelection = new Set(selectedRowIds.value);
    nextSelection.delete(key);
    selectedRowIds.value = nextSelection;
  } else if (event.ctrlKey || event.metaKey) {
    selectedRowIds.value = new Set([...selectedRowIds.value, key]);
  } else {
    selectedRowIds.value = new Set([key]);
  }
}

function exportRows() {
  const exportedColumns = columns.map((column) => column.key);
  const header = columns.map((column) => column.label).join(";");
  const body = sortedRows.value.map((row) =>
    exportedColumns
      .map((key) => `"${displayText(rowValue(row, key)).replace(/"/g, '""')}"`)
      .join(";"),
  );
  const blob = new Blob([[header, ...body].join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "données-détaillées-dpi.csv";
  link.click();
  URL.revokeObjectURL(url);
}

function sortableValue(value) {
  if (!value) return "";
  if (isDateLike(value)) return new Date(value).getTime();
  return displayText(value);
}

function rowValue(row, key) {
  if (key === "observation") return observationValue(row);
  return row[key];
}

function observationValue(row) {
  return (
    row.observation ??
    row.observations ??
    row.commentaire ??
    row.commentaires ??
    row.remarque ??
    row.remarques ??
    ""
  );
}

function isDateLike(value) {
  return /^\d{4}-\d{2}-\d{2}/.test(String(value));
}

function normalize(value = "") {
  return String(value)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

function normalizeKey(value = "") {
  return String(value)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-zA-Z0-9]/g, "")
    .toLowerCase();
}

function formatRegionLabel(value) {
  return REGION_DISPLAY_NAMES[normalizeKey(value)] || displayText(value);
}

function displayText(value, fallback = "-") {
  if (value === null || value === undefined || value === "") return fallback;

  return String(value)
    .replaceAll("\u00c3\u00a9", "é")
    .replaceAll("\u00c3\u00a8", "è")
    .replaceAll("\u00c3\u00aa", "ê")
    .replaceAll("\u00c3\u00ab", "ë")
    .replaceAll("\u00c3\u2030", "É")
    .replaceAll("\u00c3\u00a0", "à")
    .replaceAll("\u00c3\u00a2", "â")
    .replaceAll("\u00c3\u00b4", "ô")
    .replaceAll("\u00c3\u00ae", "î")
    .replaceAll("\u00c3\u00af", "ï")
    .replaceAll("\u00c3\u00a7", "ç")
    .replaceAll("\u00e2\u20ac\u2122", "'");
}

function statusClass(value, type) {
  const normalized = normalize(displayText(value));

  if (type === "deployment") {
    if (normalized.includes("deploy")) return "is-green";
    if (normalized.includes("cours")) return "is-amber";
    return "is-slate";
  }

  if (normalized === "fonctionnel") return "is-green";
  if (normalized.includes("partiellement")) return "is-yellow";
  if (normalized.includes("non fonctionnel")) return "is-red";
  return "is-slate";
}

function bailleurStyle(value) {
  return { background: bailleurColor(displayText(value)), color: "#ffffff" };
}

function formatDate(value) {
  if (!value) return "-";
  const [datePart] = String(value).split("T");
  const parts = datePart.split("-");
  if (parts.length !== 3) return displayText(value);
  return `${parts[2]}/${parts[1]}/${parts[0]}`;
}

function formatDateTime(value) {
  if (!value) return "-";
  const [datePart, timePart = ""] = String(value).split("T");
  const formattedDate = formatDate(datePart);
  const [hour = "00", minute = "00"] = timePart.split(":");
  return `${formattedDate} ${hour}:${minute}`;
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString("fr-FR");
}
</script>

<template>
  <section class="site-details-page">
    <header class="site-details-header">
      <div>
        <h1>Données détaillées</h1>
        <p>Liste détaillée des sites DPI</p>
      </div>

      <div class="site-details-actions">
        <div class="site-action-buttons">
          <button type="button" @click="exportRows">⇩ Exporter</button>
        </div>
        <span>Dernière mise à jour : <strong>{{ formatDateTime(effectiveLastUpdate) }}</strong></span>
      </div>
    </header>

    <div class="site-filter-grid">
      <div
        v-for="key in FILTER_KEYS"
        :key="key"
        :class="['site-filter-field', { 'is-open': openFilter === key, 'has-value': filters[key] !== 'all' }]"
        @click.stop
      >
        <span class="site-filter-label">{{ filterLabels[key] }}</span>
        <button
          class="site-filter-control"
          type="button"
          :aria-expanded="openFilter === key"
          @click="toggleFilterDropdown(key)"
        >
          <span class="site-filter-value">{{ selectedFilterLabel(key) }}</span>
          <i aria-hidden="true">⌄</i>
        </button>

        <div v-if="openFilter === key" class="site-filter-menu" role="listbox">
          <button
            v-for="option in filterOptionList(key)"
            :key="option.value"
            type="button"
            :class="{ selected: filters[key] === option.value }"
            role="option"
            :aria-selected="filters[key] === option.value"
            @click="selectFilterOption(key, option.value)"
          >
            <span>{{ option.label }}</span>
            <b v-if="filters[key] === option.value" aria-hidden="true">✓</b>
          </button>
        </div>
      </div>
    </div>

    <div class="site-table-toolbar">
      <label class="site-search-field">
        <input v-model="search" type="search" placeholder="Rechercher un établissement..." />
        <span aria-hidden="true">⌕</span>
      </label>

      <button
        class="site-reset-button"
        type="button"
        :disabled="!hasActiveFilters"
        @click="resetFilters"
      >
        ⟳ Réinitialiser
      </button>

      <div class="site-table-meta">
        <span>{{ formatNumber(sortedRows.length) }} sites au total</span>
      </div>
    </div>

    <div v-if="error" class="site-details-error">{{ error }}</div>

    <div class="site-table-frame">
      <table
        class="site-details-table"
        :style="{ width: `${tablePixelWidth}px`, minWidth: `${tablePixelWidth}px` }"
      >
        <colgroup>
          <col
            v-for="column in columns"
            :key="column.key"
            :style="{ width: columnWidth(column.key) }"
          />
        </colgroup>
        <thead>
          <tr>
            <th
              v-for="column in columns"
              :key="column.key"
              :class="{ 'site-establishment-heading': column.key === 'etablissement_sanitaire' }"
            >
              <div class="site-th-content">
                <button class="site-sort-button" type="button" @click="setSort(column.key)">
                  <span>{{ column.label }}</span>
                  <i>{{ sortMarker(column.key) }}</i>
                </button>
                <span
                  class="site-column-resizer"
                  role="separator"
                  aria-orientation="vertical"
                  :aria-label="`Redimensionner ${column.label}`"
                  @mousedown="startColumnResize($event, column.key)"
                ></span>
              </div>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td :colspan="columns.length" class="site-empty-row">Chargement des sites...</td>
          </tr>
          <tr v-else-if="!visibleRows.length">
            <td :colspan="columns.length" class="site-empty-row">Aucun site ne correspond aux filtres.</td>
          </tr>
          <tr
            v-for="row in visibleRows"
            v-else
            :key="rowKey(row)"
            :class="{ 'is-selected': isRowSelected(row) }"
            @click="selectRow(row, $event)"
          >
            <td class="site-id">{{ displayText(row.id) }}</td>
            <td class="site-name">{{ displayText(row.etablissement_sanitaire) }}</td>
            <td>{{ formatRegionLabel(row.region_sanitaire) }}</td>
            <td>{{ displayText(row.district_sanitaire) }}</td>
            <td>{{ displayText(row.type_etablissement) }}</td>
            <td>
              <span class="site-bailleur-badge" :style="bailleurStyle(row.bailleur)">
                {{ displayText(row.bailleur) }}
              </span>
            </td>
            <td>
              <span :class="['site-status-badge', statusClass(row.statut_deploiement, 'deployment')]">
                {{ displayText(row.statut_deploiement) }}
              </span>
            </td>
            <td>{{ formatDate(row.date_deploiement) }}</td>
            <td>
              <span :class="['site-status-badge', statusClass(row.statut_operationnel, 'operational')]">
                {{ displayText(row.statut_operationnel) }}
              </span>
            </td>
            <td class="site-reason">{{ displayText(row.motif_principal) }}</td>
            <td>{{ displayText(row.point_focal) }}</td>
            <td class="site-observation">{{ displayText(observationValue(row)) }}</td>
            <td>{{ formatDate(row.date_modification || row.date_import) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <footer class="site-details-footer">
      <div class="site-footer-meta">
        <span>Affichage de {{ startIndex + 1 }} à {{ endIndex }} sur {{ formatNumber(sortedRows.length) }} sites</span>
        <b v-if="selectedRowsCount">{{ selectedRowsCount }} sélectionnée{{ selectedRowsCount > 1 ? "s" : "" }}</b>
      </div>

      <div class="site-footer-pagination">
        <button type="button" aria-label="Page précédente" :disabled="currentPage === 1" @click="previousPage">‹</button>
        <span class="site-page-indicator">{{ currentPage }}/{{ pageCount }}</span>
        <button type="button" aria-label="Page suivante" :disabled="currentPage === pageCount" @click="nextPage">›</button>
      </div>
    </footer>
  </section>
</template>
