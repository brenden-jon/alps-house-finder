"""Scoring engine: 12 normalized dimensions per listing (0..1), stored unweighted.

Commune-inherited: ski_access, altitude_security, backcountry, summer, charm,
village_life, geneva_access, license_safety.
Listing-specific: rental_yield, price_value, space_fit, condition.
Weighted totals are computed at read time (CLI rank / dashboard sliders).
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .. import trends
from . import renovation

WEIGHTS_FILE = Path(__file__).parent / "weights_default.yaml"

SKI_IN_OUT_KEYWORDS = ["skis aux pieds", "ski aux pieds", "retour skis", "pied des pistes",
                       "ski-in", "ski in ski out", "front de neige", "départ skis"]


def load_config() -> dict:
    return yaml.safe_load(WEIGHTS_FILE.read_text())


def _interp(x: float, knots: list[tuple[float, float]]) -> float:
    """Piecewise-linear interpolation over sorted (x, y) knots, clamped."""
    if x <= knots[0][0]:
        return knots[0][1]
    if x >= knots[-1][0]:
        return knots[-1][1]
    for (x0, y0), (x1, y1) in zip(knots, knots[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return knots[-1][1]


def score_all(conn: sqlite3.Connection) -> int:
    now = datetime.now(timezone.utc).isoformat()
    communes = {r["insee_code"]: dict(r) for r in conn.execute("SELECT * FROM communes")}
    listings = conn.execute(
        "SELECT * FROM listings WHERE status IN ('active','hidden')"
    ).fetchall()

    n = 0
    for l in listings:
        c = communes.get(l["commune_insee"])
        scores = _score_listing(conn, dict(l), c)
        # persist renovation assessment on the listing row
        flag, cost = scores.pop("_renovation")
        conn.execute(
            "UPDATE listings SET renovation_flag=?, renovation_cost_est_eur=? WHERE id=?",
            (flag, cost, l["id"]),
        )
        for dim, (score, detail) in scores.items():
            conn.execute(
                """INSERT INTO listing_scores (listing_id, dimension, score, detail, computed_at)
                   VALUES (?,?,?,?,?)
                   ON CONFLICT(listing_id, dimension) DO UPDATE SET
                     score=excluded.score, detail=excluded.detail, computed_at=excluded.computed_at""",
                (l["id"], dim, round(score, 3), detail, now),
            )
        n += 1
    conn.commit()
    return n


def _score_listing(conn, l: dict, c: dict | None) -> dict:
    scores: dict = {}
    text = " ".join(filter(None, [l.get("title"), l.get("description")])).lower()

    flag, renov_cost = renovation.assess(l.get("title"), l.get("description"),
                                         l.get("dpe_letter"), l.get("area_m2"))
    scores["_renovation"] = (flag, renov_cost)
    all_in = (l.get("price_eur") or 0) + renov_cost

    if c is None:
        # unmatched commune: neutral-low commune scores so it stays visible but sinks
        for dim in ("ski_access", "altitude_security", "backcountry", "summer",
                    "charm", "village_life", "geneva_access", "license_safety"):
            scores[dim] = (0.3, "Commune not in knowledge base — add it to data/communes/")
    else:
        ski = (c.get("rating_ski") or 5) / 10
        bonus = 0.1 if any(k in text for k in SKI_IN_OUT_KEYWORDS) else 0.0
        detail = f"{c['resort_name']}: rated {c.get('rating_ski')}/10"
        if bonus:
            detail += " +0.1 ski-in/ski-out mention"
        scores["ski_access"] = (min(1.0, ski + bonus), detail)

        top = c.get("resort_top_alt_m") or 1500
        scores["altitude_security"] = (
            _interp(top, [(1800, 0.05), (2200, 0.1), (2400, 0.4), (2500, 0.55),
                          (2700, 0.85), (3000, 1.0)]),
            f"Top lift {top}m " + ("(2700m+ climate-safe)" if top >= 2700 else "(below 2700m climate bar)"),
        )
        scores["backcountry"] = ((c.get("rating_backcountry") or 5) / 10,
                                 f"Rated {c.get('rating_backcountry')}/10")
        scores["summer"] = ((c.get("rating_summer") or 5) / 10,
                            f"Rated {c.get('rating_summer')}/10")
        scores["charm"] = ((c.get("rating_charm") or 5) / 10,
                           f"Rated {c.get('rating_charm')}/10")
        scores["village_life"] = ((c.get("rating_village_life") or 5) / 10,
                                  f"Rated {c.get('rating_village_life')}/10")

        mins = c.get("geneva_drive_min") or 120
        scores["geneva_access"] = (
            _interp(mins, [(60, 1.0), (90, 0.85), (120, 0.7), (150, 0.45), (180, 0.2)]),
            f"{mins} min to Geneva airport",
        )
        scores["license_safety"] = ((c.get("rating_license_risk") or 6) / 10,
                                    (c.get("license_notes") or "").strip()[:200] or "No notes")

        # rental yield: gross annual revenue estimate / all-in price
        occ = c.get("est_occupancy_weeks") or 12
        winter = (c.get("est_weekly_rate_winter_eur") or 1500) * occ * 0.6
        summer_rev = (c.get("est_weekly_rate_summer_eur") or 800) * occ * 0.4
        # discount rental income by license risk (can't rent without a license)
        license_factor = min(1.0, ((c.get("rating_license_risk") or 6) / 10) + 0.2)
        revenue = (winter + summer_rev) * license_factor
        yield_pct = revenue / all_in * 100 if all_in else 0
        scores["rental_yield"] = (
            _interp(yield_pct, [(1, 0.05), (2, 0.2), (4, 0.6), (6, 1.0)]),
            f"~€{int(revenue):,}/yr est. gross ÷ €{all_in:,} all-in ≈ {yield_pct:.1f}% "
            f"(license factor {license_factor:.1f})",
        )

    # price value vs DVF official median
    ppm2 = (l["price_eur"] / l["area_m2"]) if (l.get("area_m2") or 0) > 15 else None
    dvf = trends.latest_median(conn, l.get("commune_insee"), l.get("property_type")) \
        if l.get("commune_insee") else None
    if ppm2 and dvf:
        ratio = ppm2 / dvf
        scores["price_value"] = (
            _interp(ratio, [(0.7, 1.0), (1.0, 0.6), (1.3, 0.3), (1.6, 0.05)]),
            f"€{int(ppm2):,}/m² vs DVF median €{dvf:,}/m² (ratio {ratio:.2f})",
        )
    elif ppm2:
        scores["price_value"] = (0.5, f"€{int(ppm2):,}/m²; no DVF baseline for commune")
    else:
        scores["price_value"] = (0.4, "No usable area — €/m² unknown")

    beds, area = l.get("bedrooms"), l.get("area_m2") or 0
    if beds:
        base = {1: 0.1, 2: 0.25, 3: 0.6}.get(beds, 1.0)
        detail = f"{beds} bedrooms"
    else:
        rooms = l.get("rooms") or 0
        base = 0.8 if rooms >= 5 else (0.5 if rooms == 4 else 0.3)
        detail = f"bedrooms unknown, {rooms} rooms"
    if area >= 140:
        base = min(1.0, base + 0.1)
        detail += f", {int(area)}m²"
    scores["space_fit"] = (base, detail + " (two families need ~4 beds)")

    dpe = l.get("dpe_letter")
    dpe_score = {"A": 1.0, "B": 1.0, "C": 1.0, "D": 0.8, "E": 0.55, "F": 0.35, "G": 0.2}.get(dpe, 0.6)
    renov_factor = {"none": 1.0, "light": 0.85, "heavy": 0.6}[flag]
    detail = f"DPE {dpe or 'unknown'}, renovation: {flag}"
    if flag != "none":
        detail += f" (~€{renov_cost:,} est.)"
    if dpe == "G":
        detail += " ⚠ DPE G = rental ban (loi Climat)"
    scores["condition"] = (dpe_score * renov_factor, detail)

    return scores


def compute_totals(conn, weights: dict | None = None, filters: dict | None = None) -> list[dict]:
    """Ranked listings with weighted totals — used by CLI rank (dashboard mirrors this in JS)."""
    cfg = load_config()
    weights = weights or cfg["weights"]
    filters = filters or cfg["filters"]

    rows = conn.execute(
        """SELECT l.*, c.name AS commune_name, c.resort_name,
                  COALESCE(l.renovation_cost_est_eur, 0) AS renov_cost
           FROM listings l LEFT JOIN communes c ON c.insee_code = l.commune_insee
           WHERE l.status = 'active'"""
    ).fetchall()
    score_rows = conn.execute("SELECT listing_id, dimension, score FROM listing_scores").fetchall()
    by_listing: dict[int, dict[str, float]] = {}
    for r in score_rows:
        by_listing.setdefault(r["listing_id"], {})[r["dimension"]] = r["score"]

    total_w = sum(weights.values())
    out = []
    for l in rows:
        all_in = l["price_eur"] + l["renov_cost"]
        if all_in > filters["max_all_in_eur"]:
            continue
        if l["bedrooms"] is not None and l["bedrooms"] < filters["min_bedrooms"]:
            continue
        if l["area_m2"] is not None and l["area_m2"] < filters.get("min_area_m2", 0):
            continue
        if l["property_type"] not in filters["property_types"]:
            continue
        text = " ".join(filter(None, [l["title"], l["description"]])).lower()
        if any(k in text for k in filters.get("exclude_keywords", [])):
            continue
        dims = by_listing.get(l["id"])
        if not dims:
            continue
        total = sum(weights.get(d, 0) * s for d, s in dims.items()) / total_w
        out.append({**dict(l), "all_in_eur": all_in, "total_score": round(total, 4),
                    "dim_scores": dims})
    out.sort(key=lambda x: -x["total_score"])
    return out
