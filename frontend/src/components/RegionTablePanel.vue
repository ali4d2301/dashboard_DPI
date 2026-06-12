<script setup>
import { computed } from "vue";

const props = defineProps({
  items: {
    type: Array,
    default: () => [],
  },
  title: {
    type: String,
    default: "Situation par type d'établissement (Vue nationale)",
  },
});

const totals = computed(() =>
  props.items.reduce(
    (acc, item) => {
      acc.supported += item.supported;
      acc.deployed += item.deployed;
      acc.functional += item.functional;
      acc.nonFunctional += item.nonFunctional;
      return acc;
    },
    { supported: 0, deployed: 0, functional: 0, nonFunctional: 0 },
  ),
);

const totalDeploymentRate = computed(() => percent(totals.value.deployed, totals.value.supported));
const totalUtilizationRate = computed(() => percent(totals.value.functional, totals.value.deployed));

function formatNumber(value) {
  return Number(value || 0).toLocaleString("fr-FR");
}

function formatRate(value) {
  return Number(value || 0).toLocaleString("fr-FR", { maximumFractionDigits: 1 });
}

function percent(value, total) {
  if (!total) return 0;
  return (value / total) * 100;
}
</script>

<template>
  <article class="panel region-table-panel">
    <h2>{{ title }}</h2>
    <div class="performance-table-wrap">
      <table class="performance-table">
        <thead>
          <tr>
            <th>Type d'établissement</th>
            <th>Nombre</th>
            <th>Taux de déploiement</th>
            <th>Taux d'utilisation</th>
            <th>Sites non utilisés</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!items.length">
            <td class="empty-performance" colspan="5">Aucune donnée disponible</td>
          </tr>
          <tr v-for="item in items" :key="item.label">
            <td><strong>{{ item.label }}</strong></td>
            <td class="count-cell">{{ formatNumber(item.supported) }}</td>
            <td>
              <div class="progress-cell">
                <strong>
                  <span class="rate-percent">{{ formatRate(item.deploymentRate) }}%</span>
                  <span class="rate-count">({{ formatNumber(item.deployed) }})</span>
                </strong>
                <span class="progress-track">
                  <i :style="{ width: `${Math.min(item.deploymentRate, 100)}%` }"></i>
                </span>
              </div>
            </td>
            <td>
              <div class="progress-cell">
                <strong>
                  <span class="rate-percent">{{ formatRate(item.functionalityRate) }}%</span>
                  <span class="rate-count">({{ formatNumber(item.functional) }})</span>
                </strong>
                <span class="progress-track">
                  <i :style="{ width: `${Math.min(item.functionalityRate, 100)}%` }"></i>
                </span>
              </div>
            </td>
            <td class="non-functional">{{ formatNumber(item.nonFunctional) }}</td>
          </tr>
        </tbody>
        <tfoot v-if="items.length">
          <tr>
            <td>TOTAL</td>
            <td class="count-cell">{{ formatNumber(totals.supported) }}</td>
            <td class="total-rate">
              <span class="rate-percent">{{ formatRate(totalDeploymentRate) }}%</span>
              <span class="rate-count">({{ formatNumber(totals.deployed) }})</span>
            </td>
            <td class="total-rate">
              <span class="rate-percent">{{ formatRate(totalUtilizationRate) }}%</span>
              <span class="rate-count">({{ formatNumber(totals.functional) }})</span>
            </td>
            <td class="non-functional">{{ formatNumber(totals.nonFunctional) }}</td>
          </tr>
        </tfoot>
      </table>
    </div>
  </article>
</template>
