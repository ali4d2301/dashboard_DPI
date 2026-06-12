const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
const CONFIGURED_API_BASE_URL = import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL;
const API_BASE_URLS = import.meta.env.DEV
  ? Array.from(new Set([CONFIGURED_API_BASE_URL, DEFAULT_API_BASE_URL, "http://localhost:8000"]))
  : [CONFIGURED_API_BASE_URL];
const REQUEST_TIMEOUT_MS = 15000;

async function requestFromBase(baseUrl, path) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  const response = await fetch(`${baseUrl}${path}`, {
    signal: controller.signal,
  }).finally(() => window.clearTimeout(timeoutId));

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const error = new Error(payload.detail || `Erreur API ${response.status}`);
    error.isApiHttpError = true;
    throw error;
  }

  return response.json();
}

async function request(path) {
  let lastError = null;

  for (const baseUrl of API_BASE_URLS) {
    try {
      return await requestFromBase(baseUrl, path);
    } catch (error) {
      if (error.isApiHttpError || !import.meta.env.DEV) {
        throw error;
      }
      lastError = error;
    }
  }

  throw lastError || new Error("Impossible de joindre l'API locale.");
}

function queryString(params = {}) {
  const query = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, value);
    }
  });

  const serialized = query.toString();
  return serialized ? `?${serialized}` : "";
}

export function getHealth() {
  return request("/api/health");
}

export function getOverview(region = "") {
  return request(`/api/overview${queryString({ region })}`);
}

export function getDashboardSnapshot(region = "") {
  return request(`/api/dashboard-snapshot${queryString({ region })}`);
}

export function getRows(limit = 25, offset = 0, region = "") {
  return request(`/api/rows${queryString({ limit, offset, region })}`);
}

export function getGroupedValues(column, limit = 12, region = "") {
  return request(`/api/group-by/${encodeURIComponent(column)}${queryString({ limit, region })}`);
}

export function getPerformanceValues(column, limit = 12, region = "") {
  return request(`/api/performance-by/${encodeURIComponent(column)}${queryString({ limit, region })}`);
}

export function getDeploymentReferenceGroups(region = "") {
  return request(`/api/deployment-reference-groups${queryString({ region })}`);
}

export function getOperationalByBailleur(limit = 6, region = "") {
  return request(`/api/operational-by-bailleur${queryString({ limit, region })}`);
}

export function getDistrictDetails(limit = 200, region = "") {
  return request(`/api/district-details${queryString({ limit, region })}`);
}
