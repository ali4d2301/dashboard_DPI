<script setup>
import { computed, ref, watch } from "vue";

const props = defineProps({
  payload: {
    type: Object,
    default: () => ({ items: [], total: 0 }),
  },
  title: {
    type: String,
    default: "Détail par district sanitaire",
  },
});

const pageSize = 6;
const currentPage = ref(1);
const sortKey = ref("district");
const sortDirection = ref("asc");

const districtSorter = new Intl.Collator("fr", {
  sensitivity: "base",
  ignorePunctuation: true,
  numeric: true,
});

const sortAccessors = {
  district: { type: "text", value: (row) => row.district || "" },
  supported: { type: "number", value: (row) => row.supported },
  deployed: { type: "number", value: (row) => row.deployed },
  deploymentRate: { type: "number", value: (row) => row.deploymentRate },
  functional: { type: "number", value: (row) => row.functional },
  partial: { type: "number", value: (row) => row.partial },
  nonFunctional: { type: "number", value: (row) => row.nonFunctional },
  gap: { type: "number", value: (row) => row.gap },
};

const items = computed(() => {
  const accessor = sortAccessors[sortKey.value] || sortAccessors.district;
  const direction = sortDirection.value === "asc" ? 1 : -1;

  return [...(props.payload?.items || [])].sort((first, second) => {
    const firstValue = accessor.value(first);
    const secondValue = accessor.value(second);
    let result =
      accessor.type === "text"
        ? districtSorter.compare(firstValue || "", secondValue || "")
        : Number(firstValue || 0) - Number(secondValue || 0);

    if (result === 0) {
      result = districtSorter.compare(first.district || "", second.district || "");
    }

    return result * direction;
  });
});
const totalRows = computed(() => items.value.length);
const pageCount = computed(() => Math.max(Math.ceil(totalRows.value / pageSize), 1));
const startIndex = computed(() => (currentPage.value - 1) * pageSize);
const endIndex = computed(() => Math.min(startIndex.value + pageSize, totalRows.value));
const visibleRows = computed(() => items.value.slice(startIndex.value, endIndex.value));

watch(totalRows, () => {
  currentPage.value = 1;
});

function goToPage(page) {
  currentPage.value = Math.min(Math.max(page, 1), pageCount.value);
}

function previousPage() {
  goToPage(currentPage.value - 1);
}

function nextPage() {
  goToPage(currentPage.value + 1);
}

function sortBy(key) {
  if (sortKey.value === key) {
    sortDirection.value = sortDirection.value === "asc" ? "desc" : "asc";
  } else {
    sortKey.value = key;
    sortDirection.value = "asc";
  }

  currentPage.value = 1;
}

function sortIcon(key) {
  if (sortKey.value !== key) return "↕";
  return sortDirection.value === "asc" ? "▲" : "▼";
}

function sortButtonLabel(label, key) {
  const nextDirection = sortKey.value === key && sortDirection.value === "asc" ? "décroissant" : "croissant";
  return `Trier ${label} par ordre ${nextDirection}`;
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString("fr-FR");
}

function formatRate(value) {
  return Number(value || 0).toLocaleString("fr-FR", { maximumFractionDigits: 1 });
}

function countWithRate(count, rate) {
  return `${formatNumber(count)} (${formatRate(rate)}%)`;
}
</script>

<template>
  <article class="panel table-panel district-detail-panel">
    <h2>{{ title }}</h2>

    <div class="district-table-wrap">
      <table class="district-table">
        <colgroup>
          <col class="district-col-name" />
          <col class="district-col-small" />
          <col class="district-col-small" />
          <col class="district-col-rate" />
          <col class="district-col-status" />
          <col class="district-col-status-wide" />
          <col class="district-col-status" />
          <col class="district-col-gap" />
        </colgroup>
        <thead>
          <tr>
            <th rowspan="2">
              <button
                type="button"
                :class="['district-sort-button', { active: sortKey === 'district' }]"
                :aria-label="sortButtonLabel('District sanitaire', 'district')"
                @click="sortBy('district')"
              >
                <span>District sanitaire</span>
                <b aria-hidden="true">{{ sortIcon("district") }}</b>
              </button>
            </th>
            <th rowspan="2">
              <button
                type="button"
                :class="['district-sort-button', { active: sortKey === 'supported' }]"
                :aria-label="sortButtonLabel('Sites ciblés', 'supported')"
                @click="sortBy('supported')"
              >
                <span>Sites ciblés</span>
                <b aria-hidden="true">{{ sortIcon("supported") }}</b>
              </button>
            </th>
            <th rowspan="2">
              <button
                type="button"
                :class="['district-sort-button', { active: sortKey === 'deployed' }]"
                :aria-label="sortButtonLabel('Sites déployés', 'deployed')"
                @click="sortBy('deployed')"
              >
                <span>Sites déployés</span>
                <b aria-hidden="true">{{ sortIcon("deployed") }}</b>
              </button>
            </th>
            <th rowspan="2">
              <button
                type="button"
                :class="['district-sort-button', { active: sortKey === 'deploymentRate' }]"
                :aria-label="sortButtonLabel('Taux de déploiement', 'deploymentRate')"
                @click="sortBy('deploymentRate')"
              >
                <span>Taux de déploiement</span>
                <b aria-hidden="true">{{ sortIcon("deploymentRate") }}</b>
              </button>
            </th>
            <th class="status-heading" colspan="3">Statut opérationnel (sur sites déployés)</th>
            <th class="district-gap-heading" rowspan="2">
              <button
                type="button"
                :class="['district-sort-button', { active: sortKey === 'gap' }]"
                :aria-label="sortButtonLabel('Gap à combler', 'gap')"
                @click="sortBy('gap')"
              >
                <span>Gap à combler</span>
                <b aria-hidden="true">{{ sortIcon("gap") }}</b>
              </button>
            </th>
          </tr>
          <tr>
            <th>
              <button
                type="button"
                :class="['district-sort-button', { active: sortKey === 'functional' }]"
                :aria-label="sortButtonLabel('Fonctionnels', 'functional')"
                @click="sortBy('functional')"
              >
                <span>Fonctionnels</span>
                <b aria-hidden="true">{{ sortIcon("functional") }}</b>
              </button>
            </th>
            <th>
              <button
                type="button"
                :class="['district-sort-button', { active: sortKey === 'partial' }]"
                :aria-label="sortButtonLabel('Partiellement fonctionnels', 'partial')"
                @click="sortBy('partial')"
              >
                <span>Partiellement fonctionnels</span>
                <b aria-hidden="true">{{ sortIcon("partial") }}</b>
              </button>
            </th>
            <th>
              <button
                type="button"
                :class="['district-sort-button', { active: sortKey === 'nonFunctional' }]"
                :aria-label="sortButtonLabel('Non fonctionnels', 'nonFunctional')"
                @click="sortBy('nonFunctional')"
              >
                <span>Non fonctionnels</span>
                <b aria-hidden="true">{{ sortIcon("nonFunctional") }}</b>
              </button>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!visibleRows.length">
            <td class="district-empty" colspan="8">Aucune donnée disponible</td>
          </tr>
          <tr v-for="row in visibleRows" :key="`${row.region}-${row.district}`">
            <td class="district-name">{{ row.district }}</td>
            <td>{{ formatNumber(row.supported) }}</td>
            <td>{{ formatNumber(row.deployed) }}</td>
            <td>{{ formatRate(row.deploymentRate) }}%</td>
            <td>{{ countWithRate(row.functional, row.functionalRate) }}</td>
            <td>{{ countWithRate(row.partial, row.partialRate) }}</td>
            <td>{{ countWithRate(row.nonFunctional, row.nonFunctionalRate) }}</td>
            <td class="district-gap-value">{{ countWithRate(row.gap, row.gapRate) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <footer v-if="totalRows" class="district-pagination">
      <div class="page-controls">
        <button type="button" aria-label="Page précédente" :disabled="currentPage === 1" @click="previousPage">
          ‹
        </button>
        <span class="page-indicator">{{ currentPage }}/{{ pageCount }}</span>
        <button type="button" aria-label="Page suivante" :disabled="currentPage === pageCount" @click="nextPage">
          ›
        </button>
      </div>
      <span> Affichage de {{ startIndex + 1 }} à {{ endIndex }} sur {{ totalRows }} districts </span>
    </footer>
  </article>
</template>
