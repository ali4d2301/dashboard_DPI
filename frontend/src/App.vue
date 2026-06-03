<script setup>
import { computed, onMounted, ref, watch } from "vue";
import AppSidebar from "./components/AppSidebar.vue";
import BailleurDonutPanel from "./components/BailleurDonutPanel.vue";
import BailleurOperationalStackPanel from "./components/BailleurOperationalStackPanel.vue";
import DashboardHeader from "./components/DashboardHeader.vue";
import DistrictTablePanel from "./components/DistrictTablePanel.vue";
import KpiGrid from "./components/KpiGrid.vue";
import MotifBarsPanel from "./components/MotifBarsPanel.vue";
import ReferenceDeploymentStackPanel from "./components/ReferenceDeploymentStackPanel.vue";
import RegionMapPanel from "./components/RegionMapPanel.vue";
import RegionTablePanel from "./components/RegionTablePanel.vue";
import SitesTablePanel from "./components/SitesTablePanel.vue";
import { getDashboardSnapshot } from "./services/api";

const TAB_STORAGE_KEY = "dpi-dashboard-active-tab";
const VALID_TABS = new Set(["overview", "details", "about"]);

function readSavedTab() {
  try {
    const savedTab = window.localStorage.getItem(TAB_STORAGE_KEY);
    return VALID_TABS.has(savedTab) ? savedTab : "overview";
  } catch {
    return "overview";
  }
}

function saveActiveTab(tab) {
  try {
    window.localStorage.setItem(TAB_STORAGE_KEY, tab);
  } catch {
    // Storage can be unavailable in a few browser privacy modes.
  }
}

const activeTab = ref(readSavedTab());
const detailsTabMounted = ref(activeTab.value === "details");
const loading = ref(activeTab.value === "overview");
const error = ref("");
const overview = ref(null);
const rowsPayload = ref({ rows: [] });
const typePerformancePayload = ref({ items: [] });
const regionSummaryPayload = ref({});
const deploymentReferencePayload = ref({ items: [], statuses: [] });
const districtDetailsPayload = ref({ items: [], total: 0 });
const operationalBailleurPayload = ref({ items: [], statuses: [] });
const sidebarCollapsed = ref(false);
const selectedRegion = ref("");
let loadRequestId = 0;
let detailsPreloadScheduled = false;
const dashboardCache = new Map();
const regionDisplayNames = {
  abidjan1: "Abidjan 1",
  abidjan2: "Abidjan 2",
  agnebytiassa: "Agnéby-Tiassa",
  bagoue: "Bagoué",
  belier: "Bélier",
  bere: "Béré",
  gbeke: "Gbêkê",
  gbokle: "Gbôklé",
  goh: "Gôh",
  grandponts: "Grands-Ponts",
  guemon: "Guémon",
  hautsassandra: "Haut-Sassandra",
  indeniedjuablin: "Indénié-Djuablin",
  indenieduablin: "Indénié-Djuablin",
  lohdjiboua: "Lôh-Djiboua",
  marahoue: "Marahoué",
  me: "Mé",
  nzi: "N'Zi",
  sanpedro: "San-Pédro",
  sudcomoe: "Sud-Comoé",
};

const groupings = ref({
  regions: [],
  bailleurs: [],
  deployment: [],
  operational: [],
  motifs: [],
  types: [],
});

const totalRows = computed(() => overview.value?.total_rows || 0);
const rows = computed(() => rowsPayload.value?.rows || []);
const selectedRegionLabel = computed(() => formatRegionLabel(selectedRegion.value));
const activeTitle = computed(() => (activeTab.value === "about" ? "À propos du tableau de bord" : "Tableau de bord - Suivi DPI"));
const activeSubtitle = computed(() => {
  if (activeTab.value === "details") return "Données détaillées";
  if (activeTab.value === "about") return "";
  if (selectedRegion.value) return `Vue régionale - ${selectedRegionLabel.value}`;
  return "Vue nationale";
});
const establishmentTableTitle = computed(
  () => `Situation par type d'établissement${selectedRegion.value ? ` (${selectedRegionLabel.value})` : ""}`,
);
const districtTableTitle = computed(
  () => `Détail par district sanitaire${selectedRegion.value ? ` (${selectedRegionLabel.value})` : ""}`,
);

const deployedCount = computed(() => countLabel(groupings.value.deployment, "Déployé"));
const inProgressCount = computed(() => countLabel(groupings.value.deployment, "En cours"));
const notStartedCount = computed(() => Math.max(totalRows.value - deployedCount.value - inProgressCount.value, 0));
const gapToCloseCount = computed(() => Math.max(totalRows.value - deployedCount.value, 0));
const functionalCount = computed(() => countLabel(groupings.value.operational, "Fonctionnel"));
const partialCount = computed(() => countLabel(groupings.value.operational, "Partiellement fonctionnel"));
const nonFunctionalCount = computed(() => countLabel(groupings.value.operational, "Non fonctionnel"));
const deployedBase = computed(() => Math.max(deployedCount.value, 1));

const deploymentRate = computed(() => percent(deployedCount.value, totalRows.value));
const gapToCloseRate = computed(() => percent(gapToCloseCount.value, totalRows.value));
const functionalRate = computed(() => percent(functionalCount.value, deployedBase.value));
const partialRate = computed(() => percent(partialCount.value, deployedBase.value));

const regionCards = computed(() => {
  const max = Math.max(...groupings.value.regions.map((item) => item.count), 1);
  return groupings.value.regions.map((item, index) => ({
    ...item,
    rate: Math.round((item.count / max) * 100),
    tone: index % 5 === 0 ? "warning" : index % 7 === 0 ? "low" : "good",
    showLabel: index < 14,
  }));
});

const establishmentTypeRows = computed(() => {
  if (typePerformancePayload.value.items?.length) {
    return typePerformancePayload.value.items;
  }

  const groups = new Map();

  rows.value.forEach((row) => {
    const type = getEstablishmentType(row);
    const current = groups.get(type) || {
      label: type,
      supported: 0,
      deployed: 0,
      functional: 0,
      nonFunctional: 0,
    };

    current.supported += 1;
    if (isDeployed(row.statut_deploiement)) current.deployed += 1;
    if (isFunctional(row.statut_operationnel)) current.functional += 1;
    if (isNonFunctional(row.statut_operationnel)) current.nonFunctional += 1;
    groups.set(type, current);
  });

  const rowsFromLoadedSites = Array.from(groups.values())
    .map((item) => ({
      ...item,
      deploymentRate: percent(item.deployed, item.supported),
      functionalityRate: percent(item.functional, Math.max(item.deployed, 1)),
    }))
    .sort((a, b) => b.supported - a.supported)
    .slice(0, 8);

  if (rowsFromLoadedSites.length) return rowsFromLoadedSites;

  return groupings.value.types.map((item) => ({
    label: item.label,
    supported: item.count,
    deployed: 0,
    deploymentRate: 0,
    functional: 0,
    functionalityRate: 0,
    nonFunctional: 0,
  }));
});

const bailleurDonutItems = computed(() => {
  const items = groupings.value.bailleurs.filter(
    (item) => item.label && item.label !== "None" && item.label !== "null",
  );
  const mainItems = items.slice(0, 5);
  const othersCount = items.slice(5).reduce((sum, item) => sum + Number(item.count || 0), 0);

  return othersCount ? [...mainItems, { label: "Autres", count: othersCount }] : mainItems;
});

const operationalBailleurChartPayload = computed(() => {
  if (operationalBailleurPayload.value.items?.length) {
    return operationalBailleurPayload.value;
  }

  const statuses = ["Fonctionnels", "Partiellement fonctionnels", "Non fonctionnels", "Non déployé"];
  const groups = new Map();

  rows.value.forEach((row) => {
    const label = row.bailleur || "Non renseigné";
    const current =
      groups.get(label) ||
      {
        label,
        total: 0,
        counts: {
          Fonctionnels: 0,
          "Partiellement fonctionnels": 0,
          "Non fonctionnels": 0,
          "Non déployé": 0,
        },
      };

    current.total += 1;

    if (isNotDeployed(row.statut_deploiement)) {
      current.counts["Non déployé"] += 1;
    } else if (isFunctional(row.statut_operationnel)) {
      current.counts.Fonctionnels += 1;
    } else if (normalizeStatus(row.statut_operationnel).includes("partiellement")) {
      current.counts["Partiellement fonctionnels"] += 1;
    } else {
      current.counts["Non fonctionnels"] += 1;
    }

    groups.set(label, current);
  });

  return {
    statuses,
    items: Array.from(groups.values())
      .sort((a, b) => b.total - a.total)
      .slice(0, 6)
      .map((group) => ({
        label: group.label,
        total: group.total,
        statuses: statuses.map((status) => ({
          label: status,
          count: group.counts[status],
          rate: percent(group.counts[status], group.total),
        })),
      })),
  };
});

const motifBars = computed(() => {
  const displayedItems = groupings.value.motifs
    .filter((item) => item.label && item.label !== "None" && item.label !== "null")
    .slice(0, 5);
  const max = Math.max(...displayedItems.map((item) => item.count), 1);

  return displayedItems.map((item) => ({ ...item, width: Math.max((item.count / max) * 100, 6) }));
});

const lastUpdate = computed(() => {
  const dates = rows.value.map((row) => row.date_modification || row.date_import).filter(Boolean).sort();
  return dates.at(-1) || "";
});

const kpis = computed(() => [
  {
    label: "Sites ciblés",
    value: totalRows.value,
    rate: 100,
    hint: "",
    icon: "building",
    color: "blue",
    footer: selectedRegion.value ? "Base régionale" : "Base nationale",
  },
  {
    label: "Sites déployés",
    value: deployedCount.value,
    rate: deploymentRate.value,
    hint: `${formatRate(deploymentRate.value)}%`,
    icon: "broadcast",
    color: "green",
    footer: "Taux de déploiement",
  },
  {
    label: "Sites fonctionnels",
    value: functionalCount.value,
    rate: functionalRate.value,
    hint: `${formatRate(functionalRate.value)}%`,
    icon: "check",
    color: "green",
    footer: "Sur sites déployés",
  },
  {
    label: "Gap à combler",
    value: gapToCloseCount.value,
    rate: gapToCloseRate.value,
    hint: `${formatRate(gapToCloseRate.value)}%`,
    icon: "triangle",
    color: "yellow",
    footer: "Reste à déployer",
  },
]);

function getEstablishmentType(row) {
  return (
    row.type_etablissement ||
    row.type_d_etablissement ||
    row.type_etablissement_sanitaire ||
    row.type_structure ||
    row.categorie_etablissement ||
    row.categorie_structure ||
    row.niveau_etablissement ||
    "Non renseigné"
  );
}

function normalizeStatus(value = "") {
  return value
    .toString()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function isDeployed(value) {
  return normalizeStatus(value).includes("ploy");
}

function isNotDeployed(value) {
  const status = normalizeStatus(value);
  return status.includes("non demarre") || status.includes("en cours");
}

function isFunctional(value) {
  return normalizeStatus(value) === "fonctionnel";
}

function isNonFunctional(value) {
  return normalizeStatus(value).includes("non fonctionnel");
}

function countLabel(items, label) {
  return items.find((item) => item.label === label)?.count || 0;
}

function percent(value, total) {
  if (!total) return 0;
  return (value / total) * 100;
}

function formatRate(value) {
  return Number(value || 0).toLocaleString("fr-FR", { maximumFractionDigits: 1 });
}

function normalizeLabel(value = "") {
  return String(value)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-zA-Z0-9]/g, "")
    .toLowerCase();
}

function formatRegionLabel(value = "") {
  return regionDisplayNames[normalizeLabel(value)] || value;
}

async function loadDashboard() {
  const requestId = ++loadRequestId;
  const regionFilter = selectedRegion.value;
  const cacheKey = regionFilter || "__national__";
  const isInitialLoad = !overview.value;
  const shouldBlockCurrentView = activeTab.value === "overview" && isInitialLoad;

  if (dashboardCache.has(cacheKey)) {
    applyDashboardSnapshot(dashboardCache.get(cacheKey));
    loading.value = false;
    error.value = "";
    return;
  }

  loading.value = shouldBlockCurrentView;
  error.value = "";

  try {
    const snapshot = await getDashboardSnapshot(regionFilter);
    if (requestId !== loadRequestId) return;
    dashboardCache.set(cacheKey, snapshot);
    applyDashboardSnapshot(snapshot);
  } catch {
    if (requestId !== loadRequestId) return;
    error.value = "Certaines données ne sont pas disponibles pour la table actuellement connectée.";
  } finally {
    if (requestId === loadRequestId) {
      loading.value = false;
    }
  }
}

function applyDashboardSnapshot(snapshot) {
  overview.value = snapshot.overview || null;
  rowsPayload.value = snapshot.rowsPayload || { rows: [] };
  groupings.value = {
    regions: snapshot.groupings?.regions || [],
    bailleurs: snapshot.groupings?.bailleurs || [],
    deployment: snapshot.groupings?.deployment || [],
    operational: snapshot.groupings?.operational || [],
    motifs: snapshot.groupings?.motifs || [],
    types: snapshot.groupings?.types || [],
  };
  typePerformancePayload.value = snapshot.typePerformancePayload || { items: [] };
  regionSummaryPayload.value = snapshot.regionSummaryPayload || {};
  deploymentReferencePayload.value = snapshot.deploymentReferencePayload || { items: [], statuses: [] };
  districtDetailsPayload.value = snapshot.districtDetailsPayload || { items: [], total: 0 };
  operationalBailleurPayload.value = snapshot.operationalBailleurPayload || { items: [], statuses: [] };
  scheduleDetailsPreload();
}

function handleRegionSelect(regionLabel) {
  if (!regionLabel) return;
  selectedRegion.value = selectedRegion.value === regionLabel ? "" : regionLabel;
  loadDashboard();
}

function scheduleDetailsPreload() {
  if (detailsTabMounted.value || detailsPreloadScheduled || activeTab.value === "details") return;

  detailsPreloadScheduled = true;
  const mountDetailsTab = () => {
    detailsPreloadScheduled = false;
    if (!detailsTabMounted.value) {
      detailsTabMounted.value = true;
    }
  };

  if (typeof window !== "undefined" && "requestIdleCallback" in window) {
    window.requestIdleCallback(mountDetailsTab, { timeout: 2200 });
    return;
  }

  window.setTimeout(mountDetailsTab, 700);
}

watch(activeTab, (tab) => {
  saveActiveTab(tab);
  if (tab === "details") {
    detailsTabMounted.value = true;
  }

  if (tab === "overview") {
    loadDashboard();
    return;
  }

  loading.value = false;
});

onMounted(() => {
  if (activeTab.value === "overview") {
    loadDashboard();
  }
});
</script>

<template>
  <div :class="['app-frame', { 'sidebar-collapsed': sidebarCollapsed }]">
    <AppSidebar
      :active-tab="activeTab"
      :collapsed="sidebarCollapsed"
      @navigate="activeTab = $event"
      @toggle="sidebarCollapsed = !sidebarCollapsed"
    />

    <main :class="['dashboard-shell', { 'details-shell': activeTab === 'details', 'about-shell': activeTab === 'about' }]">
      <DashboardHeader
        v-if="activeTab !== 'details'"
        :title="activeTitle"
        :last-update="lastUpdate"
        :subtitle="activeSubtitle"
      />

      <section v-if="error" class="alert">
        <strong>Connexion aux données indisponible</strong>
        <span>{{ error }}</span>
      </section>

      <template v-if="activeTab === 'overview'">
        <section v-if="loading" class="state-block">Chargement des indicateurs...</section>

        <template v-else>
          <KpiGrid :kpis="kpis" />

          <section class="dashboard-grid">
            <section class="map-stack">
              <RegionMapPanel
                :regions="regionCards"
                :region-summary="regionSummaryPayload"
                :selected-region="selectedRegion"
                @select-region="handleRegionSelect"
              />
              <ReferenceDeploymentStackPanel :payload="deploymentReferencePayload" />
            </section>
            <RegionTablePanel :items="establishmentTypeRows" :title="establishmentTableTitle" />
            <section class="secondary-grid">
              <BailleurDonutPanel :items="bailleurDonutItems" />
              <BailleurOperationalStackPanel :payload="operationalBailleurChartPayload" />
              <MotifBarsPanel :items="motifBars" />
            </section>
            <DistrictTablePanel :payload="districtDetailsPayload" :title="districtTableTitle" />
          </section>
        </template>
      </template>

      <SitesTablePanel
        v-if="detailsTabMounted"
        v-show="activeTab === 'details'"
        :last-update="lastUpdate"
        :total-sites="totalRows"
      />

      <template v-if="activeTab === 'about'">
        <section class="about-page">
          <div class="about-hero">
            <p>
              Le présent tableau de bord a été conçu pour assurer le suivi du déploiement et de
              l'utilisation du <strong>Dossier Patient Informatisé (DPI)</strong> au sein des établissements
              sanitaires sur l'ensemble du territoire national.
            </p>
          </div>

          <div class="about-layout">
            <div class="about-narrative">
              <p>
                Il constitue un outil d'aide à la décision permettant aux responsables du Ministère de la
                Santé, aux partenaires techniques et financiers ainsi qu'aux équipes opérationnelles de
                disposer d'une vision consolidée et actualisée de l'état d'avancement du projet.
              </p>
              <p>
                Grâce à des indicateurs de performance, des analyses géographiques et des tableaux de
                synthèse, il facilite le suivi des activités de déploiement, l'identification des difficultés
                rencontrées sur le terrain et l'évaluation des résultats obtenus.
              </p>
              <div class="about-note">
                Les informations présentées sont alimentées à partir des données de suivi collectées auprès
                des structures sanitaires et régulièrement mises à jour afin de garantir une vision fiable de
                la progression du projet.
              </div>
            </div>

            <div class="about-capabilities">
              <h3>Le tableau de bord permet notamment de :</h3>
              <ul>
                <li><span>01</span><p>Suivre le nombre de sites ciblés, déployés et opérationnels.</p></li>
                <li><span>02</span><p>Mesurer les taux de déploiement et de fonctionnalité du DPI.</p></li>
                <li><span>03</span><p>Visualiser la répartition géographique des sites par région et district sanitaire.</p></li>
                <li><span>04</span><p>Analyser les performances des différents bailleurs et partenaires impliqués.</p></li>
                <li><span>05</span><p>Identifier les principaux motifs de non-fonctionnalité ou de fonctionnement partiel.</p></li>
                <li><span>06</span><p>Consulter les informations détaillées relatives à chaque établissement sanitaire concerné.</p></li>
              </ul>
            </div>
          </div>

          <div class="about-closing">
            <span>Transformation numérique</span>
            <p>
              À travers cet outil, le Ministère de la Santé réaffirme sa volonté d'accompagner la
              transformation numérique du système de santé, d'améliorer la qualité de l'information
              sanitaire et de renforcer la continuité des soins au bénéfice des populations.
            </p>
          </div>
        </section>
      </template>
    </main>
  </div>
</template>
