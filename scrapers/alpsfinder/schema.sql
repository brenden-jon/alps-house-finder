PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- Curated knowledge base, loaded from data/communes/*.yaml (upsert on load)
CREATE TABLE IF NOT EXISTS communes (
  insee_code        TEXT PRIMARY KEY,
  name              TEXT NOT NULL,
  slug              TEXT UNIQUE NOT NULL,
  department        TEXT NOT NULL,
  postal_codes      TEXT NOT NULL,            -- JSON array
  lat REAL, lon REAL,
  village_alt_m     INTEGER,
  resort_name       TEXT,
  resort_top_alt_m  INTEGER,
  resort_base_alt_m INTEGER,
  lift_drive_min    INTEGER,
  slope_access_notes TEXT,
  geneva_drive_min  INTEGER,
  rating_ski        REAL,
  rating_backcountry REAL,
  rating_summer     REAL,
  rating_charm      REAL,
  rating_village_life REAL,
  rating_license_risk REAL,                   -- 10 = safe, 0 = heavily restricted
  license_notes     TEXT,
  rental_notes      TEXT,
  est_weekly_rate_winter_eur INTEGER,
  est_weekly_rate_summer_eur INTEGER,
  est_occupancy_weeks INTEGER,
  portal_ids        TEXT,                     -- JSON: {bienici_zone_id, pap_geo_id, ...}
  notes             TEXT,
  updated_at        TEXT NOT NULL
);

-- One canonical property (post-dedupe)
CREATE TABLE IF NOT EXISTS listings (
  id                INTEGER PRIMARY KEY,
  commune_insee     TEXT REFERENCES communes(insee_code),
  commune_name_raw  TEXT,
  title             TEXT,
  description       TEXT,
  property_type     TEXT,                     -- house | chalet | apartment | farmhouse | land | other
  price_eur         INTEGER NOT NULL,
  area_m2           REAL,
  land_m2           REAL,
  rooms             INTEGER,
  bedrooms          INTEGER,
  dpe_letter        TEXT,
  lat REAL, lon REAL,
  geo_precision     TEXT,                     -- exact | approx | commune_centroid
  first_seen_at     TEXT NOT NULL,
  last_seen_at      TEXT NOT NULL,
  status            TEXT NOT NULL DEFAULT 'active',  -- active | gone | hidden
  renovation_flag   TEXT,                     -- none | light | heavy
  renovation_cost_est_eur INTEGER,
  user_note         TEXT,
  user_starred      INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sources (
  id    INTEGER PRIMARY KEY,
  code  TEXT UNIQUE NOT NULL,
  name  TEXT,
  base_url TEXT
);

-- A listing as seen on one portal (cross-posting -> many rows per listing)
CREATE TABLE IF NOT EXISTS listing_sources (
  id              INTEGER PRIMARY KEY,
  listing_id      INTEGER NOT NULL REFERENCES listings(id),
  source_id       INTEGER NOT NULL REFERENCES sources(id),
  external_id     TEXT NOT NULL,
  url             TEXT NOT NULL,
  agency_name     TEXT,
  price_eur       INTEGER,
  raw_json        TEXT,
  first_seen_at   TEXT NOT NULL,
  last_seen_at    TEXT NOT NULL,
  missed_runs     INTEGER NOT NULL DEFAULT 0, -- consecutive complete runs without this ad
  is_active       INTEGER NOT NULL DEFAULT 1,
  UNIQUE(source_id, external_id)
);

CREATE TABLE IF NOT EXISTS photos (
  id INTEGER PRIMARY KEY,
  listing_id INTEGER NOT NULL REFERENCES listings(id),
  url TEXT NOT NULL,
  position INTEGER DEFAULT 0,
  UNIQUE(listing_id, url)
);

CREATE TABLE IF NOT EXISTS price_history (
  id INTEGER PRIMARY KEY,
  listing_source_id INTEGER NOT NULL REFERENCES listing_sources(id),
  price_eur INTEGER NOT NULL,
  observed_at TEXT NOT NULL
);

-- Per-dimension normalized scores (0..1); weighted total computed at read time
CREATE TABLE IF NOT EXISTS listing_scores (
  listing_id  INTEGER NOT NULL REFERENCES listings(id),
  dimension   TEXT NOT NULL,
  score       REAL NOT NULL,
  detail      TEXT,
  computed_at TEXT NOT NULL,
  PRIMARY KEY (listing_id, dimension)
);

CREATE TABLE IF NOT EXISTS scrape_runs (
  id INTEGER PRIMARY KEY,
  source_id INTEGER REFERENCES sources(id),
  started_at TEXT,
  finished_at TEXT,
  status TEXT,                                -- running | ok | error | partial
  ads_seen INTEGER DEFAULT 0,
  ads_new INTEGER DEFAULT 0,
  ads_updated INTEGER DEFAULT 0,
  ads_gone INTEGER DEFAULT 0,
  error TEXT
);

-- Official DVF transaction aggregates per commune
CREATE TABLE IF NOT EXISTS commune_price_trends (
  commune_insee TEXT NOT NULL REFERENCES communes(insee_code),
  year          INTEGER NOT NULL,
  property_type TEXT NOT NULL,                -- house | apartment
  median_eur_m2 INTEGER,
  n_sales       INTEGER,
  PRIMARY KEY (commune_insee, year, property_type)
);

-- Short-term rental market snapshots per commune
CREATE TABLE IF NOT EXISTS str_snapshots (
  commune_insee TEXT NOT NULL REFERENCES communes(insee_code),
  snapshot_date TEXT NOT NULL,
  active_listing_count INTEGER,
  median_nightly_winter_eur INTEGER,
  median_nightly_summer_eur INTEGER,
  review_velocity REAL,                       -- avg new reviews/listing/month, occupancy proxy
  registered_meubles_count INTEGER,
  source_notes TEXT,
  PRIMARY KEY (commune_insee, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_listings_commune ON listings(commune_insee);
CREATE INDEX IF NOT EXISTS idx_listings_status  ON listings(status);
CREATE INDEX IF NOT EXISTS idx_ls_listing       ON listing_sources(listing_id);
