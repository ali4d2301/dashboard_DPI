const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const REQUEST_TIMEOUT_MS = 15000;

async function request(path) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  const response = await fetch(`${API_BASE_URL}${path}`, {
    signal: controller.signal,
  }).finally(() => window.clearTimeout(timeoutId));

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || `Erreur API ${response.status}`);
  }

  return response.json();
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
