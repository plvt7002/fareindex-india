/**
 * FareIndex India API Client
 * Connects to the FastAPI backend endpoints.
 */

const API_BASE = import.meta.env.VITE_API_URL || '';

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  try {
    const res = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!res.ok) {
      let errorDetail = `HTTP ${res.status} ${res.statusText}`;
      try {
        const errorJson = await res.json();
        if (errorJson.detail) {
          errorDetail = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail);
        }
      } catch {
        // use fallback status text
      }
      throw new Error(errorDetail);
    }

    return await res.json();
  } catch (err) {
    console.error(`API Error on ${endpoint}:`, err);
    throw err;
  }
}

export const api = {
  // System Health
  getHealth: () => request('/api/health'),
  getRoot: () => request('/api/health'),

  // Routes
  getRoutes: () => request('/api/routes'),
  getRoutesSummary: (route = null) =>
    request(route ? `/api/routes/summary?route=${encodeURIComponent(route)}` : '/api/routes/summary'),

  // Indices
  getNationalIndex: () => request('/api/index/national'),
  getRouteIndex: (route) => request(`/api/index/route/${encodeURIComponent(route)}`),

  // Longitudinal Trends & Phase 8A Distribution & Movement Bridge
  getRouteTrend: (route, bucket = '7D') =>
    request(`/api/trend/route/${encodeURIComponent(route)}?bucket=${encodeURIComponent(bucket)}`),
  getRouteMovement: (route) =>
    request(`/api/movement/route/${encodeURIComponent(route)}`),
  getMatchedPairsRatio: () =>
    request('/api/movement/matched-pairs/ratio'),
  getRouteBookingCurve: (route) =>
    request(`/api/booking-curve/route/${encodeURIComponent(route)}`),
  getRouteDistribution: (route, bucket = '7D') =>
    request(`/api/distribution/route/${encodeURIComponent(route)}?bucket=${encodeURIComponent(bucket)}`),
  getCollectionHealth: () => request('/api/health/collection'),

  // Analytics
  getBookingCurve: (route = null) =>
    request(route ? `/api/analytics/booking-curve?route=${encodeURIComponent(route)}` : '/api/analytics/booking-curve'),
  getAirlineAnalytics: (route = null) =>
    request(route ? `/api/analytics/airlines?route=${encodeURIComponent(route)}` : '/api/analytics/airlines'),
  getLatestPrices: (route, fareType = null) =>
    request(fareType ? `/api/prices/latest?route=${encodeURIComponent(route)}&fare_type=${encodeURIComponent(fareType)}` : `/api/prices/latest?route=${encodeURIComponent(route)}`),

  // Admin / Scraping
  getScrapeStatus: () => request('/api/admin/scrape-status'),
  scrapeNow: () => request('/api/admin/scrape-now', { method: 'POST' }),
  rebuildIndex: () => request('/api/admin/rebuild-index', { method: 'POST' }),
};
