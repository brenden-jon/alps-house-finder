// Client-side ranking: mirrors scrapers/alpsfinder/scoring/engine.compute_totals.
import type { Listing, Meta } from './types';

export interface UiFilters {
  maxAllIn: number;
  minBedrooms: number;
  minArea: number;
  communes: string[]; // empty = all
  types: string[];
  hideHeavyRenovation: boolean;
  onlyStarred: boolean;
  search: string;
}

export function defaultUiFilters(meta: Meta): UiFilters {
  return {
    maxAllIn: meta.filters.max_all_in_eur,
    minBedrooms: meta.filters.min_bedrooms,
    minArea: meta.filters.min_area_m2 ?? 0,
    communes: [],
    types: meta.filters.property_types,
    hideHeavyRenovation: false,
    onlyStarred: false,
    search: '',
  };
}

export function passesFilters(
  l: Listing,
  f: UiFilters,
  meta: Meta,
  starred: Set<number>,
  hidden: Set<number>,
): boolean {
  if (l.status !== 'active' || hidden.has(l.id)) return false;
  if (f.onlyStarred && !starred.has(l.id)) return false;
  if (l.allIn > f.maxAllIn) return false;
  if (l.bedrooms !== null && l.bedrooms < f.minBedrooms) return false;
  if (l.area !== null && l.area < f.minArea) return false;
  if (!f.types.includes(l.type)) return false;
  if (f.communes.length && !f.communes.includes(l.commune ?? '')) return false;
  if (f.hideHeavyRenovation && l.renovFlag === 'heavy') return false;
  const text = `${l.title ?? ''} ${l.description ?? ''}`.toLowerCase();
  if (meta.filters.exclude_keywords.some((k) => text.includes(k))) return false;
  if (f.search && !text.includes(f.search.toLowerCase())) return false;
  return true;
}

export function totalScore(l: Listing, weights: Record<string, number>): number {
  let sum = 0;
  let wTotal = 0;
  for (const [dim, w] of Object.entries(weights)) {
    wTotal += w;
    const ds = l.scores[dim];
    if (ds) sum += w * ds.s;
  }
  return wTotal > 0 ? sum / wTotal : 0;
}

// Financial model ----------------------------------------------------------
// French buy-to-let assumptions (mid-2026): 70% LTV, ~3.4% fixed over 20 years,
// ~7.5% notary on existing property. Revenue from measured Airbnb medians when
// available (else curated seeds), discounted by license risk; 22% of revenue for
// platform/cleaning/management, 1.2% of price/yr for taxe foncière, insurance,
// charges and upkeep. A model, not advice — tune the constants here.
export const FINANCE = {
  ltv: 0.7,
  annualRate: 0.034,
  termYears: 20,
  notaryPct: 0.075,
  mgmtPct: 0.22,
  fixedPctOfPrice: 0.012,
};

export interface FinanceResult {
  equity: number; // cash in: 30% of all-in + notary
  loan: number;
  debtService: number; // per year
  grossRevenue: number;
  netRevenue: number; // after mgmt + fixed costs
  cashflow: number; // netRevenue - debtService
  principalYear1: number;
  roe: number; // (cashflow + principal repaid) / equity
}

import type { Commune } from './types';

export function computeFinance(l: Listing, c: Commune | null): FinanceResult {
  const allIn = l.allIn;
  const loan = FINANCE.ltv * allIn;
  const equity = allIn - loan + FINANCE.notaryPct * l.price;
  const r = FINANCE.annualRate / 12;
  const n = FINANCE.termYears * 12;
  const monthly = (loan * r) / (1 - Math.pow(1 + r, -n));
  const debtService = monthly * 12;

  const occ = c?.occupancyWeeks ?? 12;
  const snap = c?.str?.[0] as { median_nightly_winter_eur?: number; median_nightly_summer_eur?: number } | undefined;
  const wkWinter = snap?.median_nightly_winter_eur ? snap.median_nightly_winter_eur * 7 : c?.weeklyWinter ?? 1400;
  const wkSummer = snap?.median_nightly_summer_eur ? snap.median_nightly_summer_eur * 7 : c?.weeklySummer ?? 800;
  const licenseFactor = Math.min(1, (c?.ratings.licenseRisk ?? 6) / 10 + 0.2);
  const grossRevenue = (wkWinter * occ * 0.6 + wkSummer * occ * 0.4) * licenseFactor;

  const netRevenue = grossRevenue * (1 - FINANCE.mgmtPct) - FINANCE.fixedPctOfPrice * l.price;
  const cashflow = netRevenue - debtService;
  const principalYear1 = debtService - loan * FINANCE.annualRate;
  const roe = equity > 0 ? (cashflow + principalYear1) / equity : 0;
  return { equity, loan, debtService, grossRevenue, netRevenue, cashflow, principalYear1, roe };
}

// localStorage persistence -------------------------------------------------

const safeGet = (key: string): string | null =>
  typeof window === 'undefined' ? null : window.localStorage.getItem(key);

export function loadWeights(defaults: Record<string, number>): Record<string, number> {
  try {
    const raw = safeGet('alps.weights');
    if (raw) return { ...defaults, ...JSON.parse(raw) };
  } catch {}
  return { ...defaults };
}

export function saveWeights(w: Record<string, number>) {
  window.localStorage.setItem('alps.weights', JSON.stringify(w));
}

export function loadIdSet(key: 'alps.starred' | 'alps.hidden'): Set<number> {
  try {
    const raw = safeGet(key);
    if (raw) return new Set(JSON.parse(raw));
  } catch {}
  return new Set();
}

export function saveIdSet(key: 'alps.starred' | 'alps.hidden', s: Set<number>) {
  window.localStorage.setItem(key, JSON.stringify([...s]));
}
