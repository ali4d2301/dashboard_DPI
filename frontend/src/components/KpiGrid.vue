<script setup>
defineProps({
  kpis: {
    type: Array,
    default: () => [],
  },
});

function formatNumber(value) {
  return Number(value || 0).toLocaleString("fr-FR");
}
</script>

<template>
  <section class="metrics-grid">
    <article v-for="kpi in kpis" :key="kpi.label" :class="['metric-card', `metric-${kpi.color}`]">
      <div :class="['metric-icon', kpi.color]">
        <svg v-if="kpi.icon === 'building'" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M4 21h16" />
          <path d="M6 21V7.2c0-.7.5-1.2 1.2-1.2h9.6c.7 0 1.2.5 1.2 1.2V21" />
          <path d="M9 21v-4h6v4" />
          <path d="M9 9h1.5M13.5 9H15M9 12h1.5M13.5 12H15" />
          <path d="M10.5 3.5h3" />
          <path d="M12 2v3" />
        </svg>
        <svg v-else-if="kpi.icon === 'broadcast'" viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="12" r="3" />
          <path d="M8.1 8.1a5.5 5.5 0 0 0 0 7.8" />
          <path d="M15.9 8.1a5.5 5.5 0 0 1 0 7.8" />
          <path d="M5.3 5.3a9.5 9.5 0 0 0 0 13.4" />
          <path d="M18.7 5.3a9.5 9.5 0 0 1 0 13.4" />
        </svg>
        <svg v-else-if="kpi.icon === 'check'" viewBox="0 0 24 24" aria-hidden="true">
          <path d="m5 12.5 4.2 4.2L19 6.8" />
        </svg>
        <svg v-else-if="kpi.icon === 'triangle'" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 4 21 20H3L12 4Z" />
        </svg>
      </div>
      <div class="metric-copy">
        <span>{{ kpi.label }}</span>
        <strong>{{ formatNumber(kpi.value) }}</strong>
        <small v-if="kpi.hint">{{ kpi.hint }}</small>
      </div>
      <footer>
        <span>{{ kpi.footer }}</span>
        <div class="metric-progress" aria-hidden="true">
          <i :class="kpi.color" :style="{ width: `${Math.min(kpi.rate, 100)}%` }"></i>
        </div>
      </footer>
    </article>
  </section>
</template>
