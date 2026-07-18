"""Short-term rental market evidence per commune (best-effort, failure-tolerated).

Scrapes the Airbnb search page's embedded JSON (data-deferred-state) for one
winter week and one summer week per commune: active listing count near the
commune center and median nightly rate. Coordinates from map results are used
to drop listings that belong to neighboring towns the search radius caught.

Quarterly/coarse by design: dashboard evidence + a better rental_yield input
than pure guesses. If Airbnb changes markup, the run logs an error and scoring
falls back to the curated YAML seeds.
"""

import json
import re
import sqlite3
import unicodedata
from datetime import date, timedelta
from statistics import median

from .http import PoliteSession

SEARCH_URL = "https://fr.airbnb.com/s/{query}/homes"
MAX_KM = 7.0

NIGHTLY_RE = re.compile(r"(\d+)\s*nuits?\s*x\s*([\d\s\xa0.,]+)\s*€")
LABEL_RE = re.compile(r"([\d\s\xa0.,]+)\s*[€$]|[€$]\s?([\d,.\s\xa0]+)")


def _next_weeks() -> tuple[tuple[str, str], tuple[str, str]]:
    """A Saturday-to-Saturday week in the coming February and August."""
    today = date.today()

    def sat_week(year: int, month: int) -> tuple[str, str]:
        d = date(year, month, 1)
        while d.weekday() != 5:  # Saturday
            d += timedelta(days=1)
        d += timedelta(days=7)  # second Saturday: mid-month, high season
        return d.isoformat(), (d + timedelta(days=7)).isoformat()

    feb_year = today.year if today.month < 2 else today.year + 1
    aug_year = today.year if today.month < 8 else today.year + 1
    return sat_week(feb_year, 2), sat_week(aug_year, 8)


def _extract_listings(html: str) -> list[dict]:
    out = []
    for m in re.finditer(
        r'<script id="data-deferred-state-\d+"[^>]*type="application/json">(.*?)</script>',
        html, re.S,
    ):
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        stack = [data]
        while stack:
            cur = stack.pop()
            if isinstance(cur, dict):
                if "demandStayListing" in cur and "structuredDisplayPrice" in cur:
                    out.append(cur)
                else:
                    stack.extend(cur.values())
            elif isinstance(cur, list):
                stack.extend(cur)
    return out


def _parse_listing(item: dict) -> tuple[float | None, float | None, int | None]:
    """Returns (lat, lon, nightly_price_eur)."""
    price = None
    dsl = item.get("demandStayListing") or {}
    coord = (dsl.get("location") or {}).get("coordinate") or {}
    lat, lon = coord.get("latitude"), coord.get("longitude")

    sdp = item.get("structuredDisplayPrice") or {}
    # best signal: the price-detail line "7 nuits x 209,58 €"
    m = NIGHTLY_RE.search(json.dumps(sdp, ensure_ascii=False))
    if m:
        nightly = m.group(2).replace("\xa0", "").replace(" ", "").replace(",", ".")
        try:
            price = int(float(nightly))
        except ValueError:
            price = None
    else:
        line = sdp.get("primaryLine") or {}
        label = " ".join(
            str(line.get(k, "")) for k in ("accessibilityLabel", "price", "discountedPrice")
        )
        m = LABEL_RE.search(label)
        if m:
            digits = re.sub(r"[^\d]", "", (m.group(1) or m.group(2) or ""))
            if digits:
                price = int(digits)
                # label may be the stay total rather than nightly
                if "total" in label.lower() and price > 900:
                    price = round(price / 7)
    return lat, lon, price


def _km(lat1, lon1, lat2, lon2) -> float:
    return (((lat1 - lat2) * 111) ** 2 + ((lon1 - lon2) * 78) ** 2) ** 0.5


def snapshot_all(conn: sqlite3.Connection, communes: list[dict]) -> int:
    http = PoliteSession("airbnb", min_delay=4.0, max_delay=8.0, cache_ttl_s=45 * 24 * 3600)
    winter, summer = _next_weeks()
    today = date.today().isoformat()
    written = 0

    for c in communes:
        results = {}
        for season, (checkin, checkout) in (("winter", winter), ("summer", summer)):
            plain = "".join(ch for ch in unicodedata.normalize("NFD", c["name"])
                            if unicodedata.category(ch) != "Mn")
            query = f"{plain}--France".replace(" ", "-")
            try:
                html = http.get(
                    SEARCH_URL.format(query=query),
                    {"checkin": checkin, "checkout": checkout, "adults": 4},
                )
            except Exception as e:
                print(f"  airbnb: {c['name']} {season}: {e}")
                continue
            prices = []
            n_local = 0
            for item in _extract_listings(html):
                lat, lon, price = _parse_listing(item)
                if lat and c.get("lat") and _km(lat, lon, c["lat"], c["lon"]) > MAX_KM:
                    continue
                n_local += 1
                if price and 30 <= price <= 5000:
                    prices.append(price)
            results[season] = {
                "count": n_local,
                "median": int(median(prices)) if len(prices) >= 3 else None,
            }

        if not results:
            continue
        conn.execute(
            """INSERT INTO str_snapshots (commune_insee, snapshot_date, active_listing_count,
                 median_nightly_winter_eur, median_nightly_summer_eur, source_notes)
               VALUES (?,?,?,?,?,?)
               ON CONFLICT(commune_insee, snapshot_date) DO UPDATE SET
                 active_listing_count=excluded.active_listing_count,
                 median_nightly_winter_eur=excluded.median_nightly_winter_eur,
                 median_nightly_summer_eur=excluded.median_nightly_summer_eur,
                 source_notes=excluded.source_notes""",
            (
                c["insee_code"], today,
                max(r["count"] for r in results.values()),
                (results.get("winter") or {}).get("median"),
                (results.get("summer") or {}).get("median"),
                f"Airbnb first-page sample, winter wk {winter[0]}, summer wk {summer[0]}, <={int(MAX_KM)}km of center",
            ),
        )
        conn.commit()
        written += 1
    return written
