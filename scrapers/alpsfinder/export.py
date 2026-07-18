"""Export SQLite -> data/export/*.json for the static dashboard."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .db import REPO_ROOT
from .scoring.engine import load_config

EXPORT_DIR = REPO_ROOT / "data" / "export"


def export_all(conn: sqlite3.Connection) -> Path:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    cfg = load_config()

    listings = []
    rows = conn.execute(
        """SELECT l.* FROM listings l WHERE l.status IN ('active','gone')
           ORDER BY l.id"""
    ).fetchall()
    scores = {}
    for r in conn.execute("SELECT listing_id, dimension, score, detail FROM listing_scores"):
        scores.setdefault(r["listing_id"], {})[r["dimension"]] = {
            "s": r["score"], "d": r["detail"],
        }
    photos = {}
    for r in conn.execute("SELECT listing_id, url FROM photos ORDER BY listing_id, position"):
        photos.setdefault(r["listing_id"], []).append(r["url"])
    sources = {}
    for r in conn.execute(
        """SELECT ls.listing_id, s.code, s.name, ls.url, ls.agency_name, ls.is_active
           FROM listing_sources ls JOIN sources s ON s.id = ls.source_id"""
    ):
        sources.setdefault(r["listing_id"], []).append(
            {"code": r["code"], "name": r["name"], "url": r["url"],
             "agency": r["agency_name"], "active": bool(r["is_active"])})
    price_hist = {}
    for r in conn.execute(
        """SELECT ls.listing_id, ph.price_eur, ph.observed_at
           FROM price_history ph JOIN listing_sources ls ON ls.id = ph.listing_source_id
           ORDER BY ph.observed_at"""
    ):
        price_hist.setdefault(r["listing_id"], []).append([r["observed_at"][:10], r["price_eur"]])

    for l in rows:
        if l["id"] not in scores:
            continue  # unscored (e.g. just-arrived) — next run picks it up
        listings.append({
            "id": l["id"],
            "commune": l["commune_insee"],
            "communeRaw": l["commune_name_raw"],
            "title": l["title"],
            "description": l["description"],
            "type": l["property_type"],
            "price": l["price_eur"],
            "renovCost": l["renovation_cost_est_eur"] or 0,
            "renovFlag": l["renovation_flag"],
            "allIn": l["price_eur"] + (l["renovation_cost_est_eur"] or 0),
            "area": l["area_m2"],
            "land": l["land_m2"],
            "rooms": l["rooms"],
            "bedrooms": l["bedrooms"],
            "dpe": l["dpe_letter"],
            "lat": l["lat"], "lon": l["lon"], "geo": l["geo_precision"],
            "firstSeen": l["first_seen_at"][:10],
            "status": l["status"],
            "scores": scores[l["id"]],
            "photos": photos.get(l["id"], [])[:12],
            "sources": sources.get(l["id"], []),
            "priceHistory": price_hist.get(l["id"], []),
        })

    communes = []
    for c in conn.execute("SELECT * FROM communes ORDER BY name"):
        trends = [
            {"year": t["year"], "type": t["property_type"],
             "median": t["median_eur_m2"], "n": t["n_sales"]}
            for t in conn.execute(
                "SELECT * FROM commune_price_trends WHERE commune_insee=? ORDER BY year",
                (c["insee_code"],))
        ]
        strs = [dict(s) for s in conn.execute(
            "SELECT * FROM str_snapshots WHERE commune_insee=? ORDER BY snapshot_date DESC LIMIT 4",
            (c["insee_code"],))]
        communes.append({
            "insee": c["insee_code"], "name": c["name"], "slug": c["slug"],
            "dept": c["department"], "lat": c["lat"], "lon": c["lon"],
            "villageAlt": c["village_alt_m"], "resort": c["resort_name"],
            "topAlt": c["resort_top_alt_m"], "liftDriveMin": c["lift_drive_min"],
            "slopeNotes": c["slope_access_notes"], "genevaMin": c["geneva_drive_min"],
            "ratings": {
                "ski": c["rating_ski"], "backcountry": c["rating_backcountry"],
                "summer": c["rating_summer"], "charm": c["rating_charm"],
                "villageLife": c["rating_village_life"], "licenseRisk": c["rating_license_risk"],
            },
            "licenseNotes": c["license_notes"], "rentalNotes": c["rental_notes"],
            "weeklyWinter": c["est_weekly_rate_winter_eur"],
            "weeklySummer": c["est_weekly_rate_summer_eur"],
            "occupancyWeeks": c["est_occupancy_weeks"],
            "notes": c["notes"], "updatedAt": c["updated_at"][:10],
            "trends": trends, "str": strs,
        })

    meta = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "defaultWeights": cfg["weights"],
        "filters": cfg["filters"],
        "listingCount": len(listings),
    }

    (EXPORT_DIR / "listings.json").write_text(json.dumps(listings, ensure_ascii=False))
    (EXPORT_DIR / "communes.json").write_text(json.dumps(communes, ensure_ascii=False))
    (EXPORT_DIR / "meta.json").write_text(json.dumps(meta, ensure_ascii=False))
    return EXPORT_DIR
