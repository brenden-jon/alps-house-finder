export interface DimScore {
  s: number;
  d: string | null;
}

export interface ListingSource {
  code: string;
  name: string;
  url: string;
  agency: string | null;
  active: boolean;
}

export interface Listing {
  id: number;
  commune: string | null;
  communeRaw: string | null;
  title: string | null;
  description: string | null;
  type: string;
  price: number;
  renovCost: number;
  renovFlag: string | null;
  allIn: number;
  area: number | null;
  land: number | null;
  rooms: number | null;
  bedrooms: number | null;
  dpe: string | null;
  lat: number | null;
  lon: number | null;
  geo: string | null;
  firstSeen: string;
  status: string;
  scores: Record<string, DimScore>;
  photos: string[];
  sources: ListingSource[];
  priceHistory: [string, number][];
}

export interface TrendPoint {
  year: number;
  type: 'house' | 'apartment';
  median: number;
  n: number;
}

export interface Commune {
  insee: string;
  name: string;
  slug: string;
  dept: string;
  lat: number | null;
  lon: number | null;
  villageAlt: number | null;
  resort: string | null;
  topAlt: number | null;
  liftDriveMin: number | null;
  slopeNotes: string | null;
  genevaMin: number | null;
  ratings: {
    ski: number | null;
    backcountry: number | null;
    summer: number | null;
    charm: number | null;
    villageLife: number | null;
    licenseRisk: number | null;
  };
  licenseNotes: string | null;
  rentalNotes: string | null;
  weeklyWinter: number | null;
  weeklySummer: number | null;
  occupancyWeeks: number | null;
  notes: string | null;
  updatedAt: string;
  trends: TrendPoint[];
  str: Record<string, unknown>[];
}

export interface Meta {
  generatedAt: string;
  defaultWeights: Record<string, number>;
  filters: {
    max_all_in_eur: number;
    min_bedrooms: number;
    min_area_m2: number;
    property_types: string[];
    exclude_keywords: string[];
  };
  listingCount: number;
}

export const DIMENSIONS: { key: string; label: string }[] = [
  { key: 'ski_access', label: 'Ski access' },
  { key: 'altitude_security', label: 'Altitude safety' },
  { key: 'backcountry', label: 'Backcountry' },
  { key: 'summer', label: 'Summer' },
  { key: 'charm', label: 'Charm' },
  { key: 'village_life', label: 'Village life' },
  { key: 'geneva_access', label: 'Geneva access' },
  { key: 'license_safety', label: 'License safety' },
  { key: 'rental_yield', label: 'Rental yield' },
  { key: 'price_value', label: 'Price value' },
  { key: 'space_fit', label: 'Space' },
  { key: 'condition', label: 'Condition' },
];
