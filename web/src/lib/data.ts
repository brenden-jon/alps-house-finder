import type { Commune, Listing, Meta } from './types';

const BASE = process.env.NEXT_PUBLIC_BASE_PATH ?? '';

export interface AppData {
  listings: Listing[];
  communes: Commune[];
  meta: Meta;
}

let cached: Promise<AppData> | null = null;

export function loadData(): Promise<AppData> {
  if (!cached) {
    cached = (async () => {
      const [listings, communes, meta] = await Promise.all([
        fetch(`${BASE}/data/listings.json`).then((r) => r.json()),
        fetch(`${BASE}/data/communes.json`).then((r) => r.json()),
        fetch(`${BASE}/data/meta.json`).then((r) => r.json()),
      ]);
      return { listings, communes, meta };
    })();
  }
  return cached;
}

export const fmtEur = (n: number) =>
  n >= 1_000_000 ? `€${(n / 1_000_000).toFixed(2)}M` : `€${Math.round(n / 1000)}k`;
