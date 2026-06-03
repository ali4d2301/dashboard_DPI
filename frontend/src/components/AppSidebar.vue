<script setup>
import disdLogoUrl from "../assets/disd-logo.png";

defineProps({
  collapsed: {
    type: Boolean,
    default: false,
  },
  activeTab: {
    type: String,
    default: "overview",
  },
});

const emit = defineEmits(["toggle", "navigate"]);
</script>

<template>
  <aside :class="['sidebar', { 'is-collapsed': collapsed }]">
    <div class="sidebar-head">
      <div class="brand-logo">
        <img :src="disdLogoUrl" alt="Direction de l'Informatique et de la Santé Digitale" />
      </div>

      <button
        class="sidebar-toggle"
        type="button"
        :aria-label="collapsed ? 'Agrandir la barre latérale' : 'Réduire la barre latérale'"
        :title="collapsed ? 'Agrandir' : 'Réduire'"
        @click="emit('toggle')"
      >
        <span class="toggle-lines" aria-hidden="true">
          <i></i>
          <i></i>
          <i></i>
        </span>
      </button>
    </div>

    <nav class="side-nav" aria-label="Navigation principale">
      <a
        :class="{ active: activeTab === 'overview' }"
        href="#"
        title="Vue générale"
        @click.prevent="emit('navigate', 'overview')"
      >
        <span aria-hidden="true">⌂</span>
        <strong class="nav-label">Vue générale</strong>
      </a>
      <a
        :class="{ active: activeTab === 'details' }"
        href="#"
        title="Données détaillées"
        @click.prevent="emit('navigate', 'details')"
      >
        <span aria-hidden="true">≡</span>
        <strong class="nav-label">Données détaillées</strong>
      </a>
      <a
        :class="{ active: activeTab === 'about' }"
        href="#"
        title="À propos"
        @click.prevent="emit('navigate', 'about')"
      >
        <span aria-hidden="true">ⓘ</span>
        <strong class="nav-label">À propos</strong>
      </a>
    </nav>
  </aside>
</template>
