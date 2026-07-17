"""Cross-portal dedupe: is this RawListing the same property as an existing listing?

Blocking: same commune, price within 3% OR area within 3 m².
Scoring: price/area/bedrooms/GPS/description-similarity/agency. Attach at >= 0.6.
"""

import sqlite3

from rapidfuzz import fuzz

from .models import RawListing

ATTACH_THRESHOLD = 0.6


def find_duplicate(conn: sqlite3.Connection, raw: RawListing, insee: str | None) -> int | None:
    if not insee or not raw.price_eur:
        return None
    candidates = conn.execute(
        """SELECT id, price_eur, area_m2, bedrooms, lat, lon, geo_precision, description
           FROM listings WHERE commune_insee=? AND status != 'gone'
           AND (ABS(price_eur - ?) <= price_eur * 0.03
                OR (area_m2 IS NOT NULL AND ? IS NOT NULL AND ABS(area_m2 - ?) <= 3))""",
        (insee, raw.price_eur, raw.area_m2, raw.area_m2),
    ).fetchall()

    best_id, best_score = None, 0.0
    for c in candidates:
        score = 0.0
        if c["price_eur"] and abs(c["price_eur"] - raw.price_eur) <= c["price_eur"] * 0.01:
            score += 0.35
        if c["area_m2"] and raw.area_m2 and abs(c["area_m2"] - raw.area_m2) <= 2:
            score += 0.25
        if c["bedrooms"] and raw.bedrooms and c["bedrooms"] == raw.bedrooms:
            score += 0.10
        if (c["lat"] and raw.lat and not raw.geo_blurred and c["geo_precision"] == "exact"):
            # ~250 m in degrees
            if abs(c["lat"] - raw.lat) < 0.00225 and abs(c["lon"] - raw.lon) < 0.0032:
                score += 0.15
        if c["description"] and raw.description:
            sim = fuzz.token_set_ratio(c["description"][:600], raw.description[:600])
            if sim >= 85:
                score += 0.30
        if score > best_score:
            best_id, best_score = c["id"], score

    if best_score >= ATTACH_THRESHOLD:
        return best_id
    return None
