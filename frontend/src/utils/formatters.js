const MONTHS_SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/**
 * Parses and formats ISO date (YYYY-MM-DD or ISO string) to 'D MMM YYYY', e.g. '8 Sep 2026'.
 * Returns fallback if dateStr is invalid or missing.
 */
export function formatDisplayDate(dateStr, fallback = '—') {
  if (!dateStr) return fallback;
  const cleanStr = String(dateStr).split('T')[0];
  const parts = cleanStr.split('-');
  if (parts.length === 3) {
    const year = parts[0];
    const monthIndex = parseInt(parts[1], 10) - 1;
    const day = parseInt(parts[2], 10);
    const month = MONTHS_SHORT[monthIndex] || parts[1];
    return `${day} ${month} ${year}`;
  }
  return dateStr;
}

/**
 * Parses and formats ISO date to 'D MMM', e.g. '8 Sep'.
 */
export function formatShortDate(dateStr, fallback = '') {
  if (!dateStr) return fallback;
  const cleanStr = String(dateStr).split('T')[0];
  const parts = cleanStr.split('-');
  if (parts.length === 3) {
    const monthIndex = parseInt(parts[1], 10) - 1;
    const day = parseInt(parts[2], 10);
    const month = MONTHS_SHORT[monthIndex] || parts[1];
    return `${day} ${month}`;
  }
  return dateStr;
}

/**
 * Formats a number in Indian Rupee format with optional decimals.
 */
export function formatINR(val, includeDecimals = false) {
  if (val === null || val === undefined || isNaN(val)) return '—';
  const num = Number(val);
  if (includeDecimals) {
    return `₹${num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }
  return `₹${Math.round(num).toLocaleString('en-IN')}`;
}

/**
 * Formats a percentage change with optional sign.
 */
export function formatPct(val, digits = 1, showSign = true) {
  if (val === null || val === undefined || isNaN(val)) return '—';
  const num = Number(val);
  const sign = showSign && num > 0 ? '+' : '';
  return `${sign}${num.toFixed(digits)}%`;
}

/**
 * Standardizes stops label: 'Nonstop', '1 stop', '2 stops'.
 * Prevents '1 stop stop' duplication.
 */
export function formatStops(stops) {
  if (stops === null || stops === undefined || stops === '') return 'Nonstop';
  const str = String(stops).trim().toLowerCase();
  if (str === '0' || str === 'nonstop' || str === 'non-stop' || str === 'direct') {
    return 'Nonstop';
  }
  if (str.includes('stop')) {
    if (str.startsWith('1')) return '1 stop';
    if (str.startsWith('2')) return '2 stops';
    return String(stops).trim();
  }
  const count = parseInt(str, 10);
  if (isNaN(count) || count === 0) return 'Nonstop';
  return count === 1 ? '1 stop' : `${count} stops`;
}

/**
 * Determines lead-time bucket ('7D', '14D', '21D', '30D', '60D') from travel_date and observation search_timestamp.
 */
export function getLeadTimeBucket(travelDateStr, searchTimestampStr) {
  if (!travelDateStr || !searchTimestampStr) return 'UNKNOWN';
  try {
    const obsStr = String(searchTimestampStr).slice(0, 10);
    const trvStr = String(travelDateStr).slice(0, 10);
    const obsDate = new Date(obsStr);
    const trvDate = new Date(trvStr);
    const diffDays = Math.round((trvDate.getTime() - obsDate.getTime()) / (1000 * 60 * 60 * 24));
    if (isNaN(diffDays)) return 'UNKNOWN';
    if (diffDays <= 10) return '7D';
    if (diffDays <= 17) return '14D';
    if (diffDays <= 25) return '21D';
    if (diffDays <= 45) return '30D';
    return '60D';
  } catch (e) {
    return 'UNKNOWN';
  }
}

/**
 * Maps raw backend flight observation to frontend table model.
 * Strict Contract: The flight price MUST come strictly from row.price_inr / row.observed_fare.
 * Never fall back to or populate from aggregate metrics (typical_fare, median, average).
 */
export function mapObservedFare(row) {
  if (!row) return null;
  const rawPrice = Number(row.price_inr ?? row.observed_fare);
  return {
    id: row.id,
    route: row.route,
    origin: row.origin,
    destination: row.destination,
    airline: row.airline || 'Unknown',
    departureTime: row.departure_time || '—',
    arrivalTime: row.arrival_time || '—',
    travelDate: row.travel_date || '—',
    stops: formatStops(row.stops),
    cabinClass: row.class || 'Economy',
    seatsLeft: row.seats_left || 'Available',
    price_inr: rawPrice,
    observed_fare: rawPrice,
    provenance: row.provenance || row.source || 'Scraper',
    searchTimestamp: row.search_timestamp,
    leadTimeBucket: getLeadTimeBucket(row.travel_date, row.search_timestamp),
    fareType: row.fare_type,
    domesticEligibility: row.domestic_eligibility,
  };
}

/**
 * Calculates dynamic percentiles (P10, P25, Median, P75, P90) from a list of prices.
 */
export function calculatePercentiles(prices) {
  if (!prices || prices.length === 0) {
    return { p10: 0, p25: 0, median: 0, p75: 0, p90: 0, min: 0, max: 0, count: 0 };
  }
  const valid = prices.map(Number).filter((n) => !isNaN(n) && n > 0);
  if (valid.length === 0) {
    return { p10: 0, p25: 0, median: 0, p75: 0, p90: 0, min: 0, max: 0, count: 0 };
  }
  const sorted = [...valid].sort((a, b) => a - b);
  const n = sorted.length;

  const getP = (p) => {
    const idx = (p / 100) * (n - 1);
    const lower = Math.floor(idx);
    const upper = Math.ceil(idx);
    const weight = idx - lower;
    if (upper >= n) return sorted[n - 1];
    return sorted[lower] * (1 - weight) + sorted[upper] * weight;
  };

  return {
    p10: getP(10),
    p25: getP(25),
    median: getP(50),
    p75: getP(75),
    p90: getP(90),
    min: sorted[0],
    max: sorted[n - 1],
    count: n,
  };
}

/**
 * Data-driven representative selection:
 * 1. Filter to central 80% (P10 <= price <= P90)
 * 2. Rank by ABS(price - median) so fares closest to typical are prioritized
 * 3. Returns up to `limit` rows (default 10)
 * Note: Does NOT modify any row's price_inr.
 */
export function getRepresentativeFares(fares, limit = 10) {
  if (!fares || fares.length === 0) return [];
  if (fares.length <= limit) return [...fares];

  const prices = fares.map((f) => Number(f.price_inr || 0)).filter((p) => p > 0);
  const { p10, p90, median } = calculatePercentiles(prices);

  // Central 80%
  const central = fares.filter((f) => {
    const p = Number(f.price_inr || 0);
    return p >= p10 && p <= p90;
  });

  const candidates = central.length >= limit ? central : fares;

  // Rank by distance to median
  const ranked = [...candidates].sort((a, b) => {
    const diffA = Math.abs(Number(a.price_inr || 0) - median);
    const diffB = Math.abs(Number(b.price_inr || 0) - median);
    if (Math.abs(diffA - diffB) > 0.01) {
      return diffA - diffB;
    }
    // Tie-break by price ascending, airline, departure
    if (a.price_inr !== b.price_inr) {
      return (a.price_inr || 0) - (b.price_inr || 0);
    }
    if (a.airline !== b.airline) {
      return String(a.airline).localeCompare(String(b.airline));
    }
    return String(a.departureTime).localeCompare(String(b.departureTime));
  });

  return ranked.slice(0, limit);
}


