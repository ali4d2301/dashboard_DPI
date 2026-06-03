<script setup>
defineProps({
  title: {
    type: String,
    default: "Tableau de bord - Suivi DPI",
  },
  lastUpdate: {
    type: String,
    default: "",
  },
  subtitle: {
    type: String,
    default: "Vue nationale",
  },
});

function formatDate(value) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}
</script>

<template>
  <header class="topbar">
    <div class="topbar-title">
      <h1>{{ title }}</h1>
      <p v-if="subtitle">{{ subtitle }}</p>
    </div>

    <div class="topbar-meta">
      <div class="update-chip">
        <span>Dernière mise à jour<strong>{{ formatDate(lastUpdate) }}</strong></span>
      </div>
    </div>
  </header>
</template>
