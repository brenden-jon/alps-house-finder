"""Shared ingest pipeline: RawListings from any adapter -> SQLite.

Handles upsert, price-change tracking, commune matching, seen/gone detection.
Cross-portal dedupe is applied at listing creation (see dedupe.py).
"""

import json
import sqlite3
from datetime import datetime, timezone

from .communes import CommuneMatcher
from .http import BotBlocked
from .models import RawListing, normalize_property_type

GONE_AFTER_MISSED_RUNS = 2


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_or_create_source(conn: sqlite3.Connection, adapter) -> int:
    row = conn.execute("SELECT id FROM sources WHERE code=?", (adapter.code,)).fetchone()
    if row:
        return row["id"]
    cur = conn.execute(
        "INSERT INTO sources (code, name, base_url) VALUES (?,?,?)",
        (adapter.code, adapter.name, adapter.base_url),
    )
    return cur.lastrowid


def run_scrape(conn: sqlite3.Connection, adapter, communes: list[dict]) -> dict:
    source_id = get_or_create_source(conn, adapter)
    matcher = CommuneMatcher(conn)
    started = now_iso()
    cur = conn.execute(
        "INSERT INTO scrape_runs (source_id, started_at, status) VALUES (?,?,'running')",
        (source_id, started),
    )
    run_id = cur.lastrowid
    conn.commit()

    stats = {"seen": 0, "new": 0, "updated": 0, "gone": 0}
    seen_external_ids: set[str] = set()
    status, error = "ok", None
    try:
        for raw in adapter.fetch(communes):
            _ingest_one(conn, source_id, raw, matcher, stats)
            seen_external_ids.add(raw.external_id)
            stats["seen"] += 1
            if stats["seen"] % 50 == 0:
                conn.commit()
        conn.commit()
        stats["gone"] = _mark_gone(conn, source_id, seen_external_ids)
    except BotBlocked as e:
        status, error = "error", str(e)
    except Exception as e:  # noqa: BLE001 — record and continue other sources
        status, error = "error", f"{type(e).__name__}: {e}"

    conn.execute(
        """UPDATE scrape_runs SET finished_at=?, status=?, ads_seen=?, ads_new=?,
           ads_updated=?, ads_gone=?, error=? WHERE id=?""",
        (now_iso(), status, stats["seen"], stats["new"], stats["updated"],
         stats["gone"], error, run_id),
    )
    conn.commit()
    return {"run_id": run_id, "status": status, "error": error, **stats}


def _ingest_one(conn, source_id: int, raw: RawListing, matcher: CommuneMatcher, stats: dict):
    now = now_iso()
    existing = conn.execute(
        "SELECT id, listing_id, price_eur FROM listing_sources WHERE source_id=? AND external_id=?",
        (source_id, raw.external_id),
    ).fetchone()

    if existing:
        conn.execute(
            "UPDATE listing_sources SET last_seen_at=?, missed_runs=0, is_active=1, url=? WHERE id=?",
            (now, raw.url, existing["id"]),
        )
        if raw.price_eur and raw.price_eur != existing["price_eur"]:
            conn.execute(
                "INSERT INTO price_history (listing_source_id, price_eur, observed_at) VALUES (?,?,?)",
                (existing["id"], raw.price_eur, now),
            )
            conn.execute(
                "UPDATE listing_sources SET price_eur=? WHERE id=?",
                (raw.price_eur, existing["id"]),
            )
            conn.execute(
                "UPDATE listings SET price_eur=?, last_seen_at=? WHERE id=?",
                (raw.price_eur, now, existing["listing_id"]),
            )
            stats["updated"] += 1
        else:
            conn.execute(
                "UPDATE listings SET last_seen_at=?, status=CASE WHEN status='gone' THEN 'active' ELSE status END WHERE id=?",
                (now, existing["listing_id"]),
            )
        return

    insee = matcher.match(
        insee=raw.insee_code, postal=raw.postal_code, name=raw.commune_name,
        lat=raw.lat if not raw.geo_blurred else None,
        lon=raw.lon if not raw.geo_blurred else None,
    )
    text = " ".join(filter(None, [raw.title, raw.description]))
    prop_type = normalize_property_type(raw.property_type_raw, text)

    # Cross-portal dedupe: try to attach to an existing listing first
    from .dedupe import find_duplicate  # local import to avoid cycle
    listing_id = find_duplicate(conn, raw, insee)

    if listing_id is None:
        geo_precision = (
            "commune_centroid" if raw.lat is None
            else ("approx" if raw.geo_blurred else "exact")
        )
        cur = conn.execute(
            """INSERT INTO listings (commune_insee, commune_name_raw, title, description,
               property_type, price_eur, area_m2, land_m2, rooms, bedrooms, dpe_letter,
               lat, lon, geo_precision, first_seen_at, last_seen_at, status)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, 'active')""",
            (insee, raw.commune_name, raw.title, raw.description, prop_type,
             raw.price_eur, raw.area_m2, raw.land_m2, raw.rooms, raw.bedrooms,
             raw.dpe, raw.lat, raw.lon, geo_precision, now, now),
        )
        listing_id = cur.lastrowid
        stats["new"] += 1

    cur = conn.execute(
        """INSERT INTO listing_sources (listing_id, source_id, external_id, url, agency_name,
           price_eur, raw_json, first_seen_at, last_seen_at) VALUES (?,?,?,?,?,?,?,?,?)""",
        (listing_id, source_id, raw.external_id, raw.url, raw.agency_name,
         raw.price_eur, json.dumps(raw.raw, ensure_ascii=False), now, now),
    )
    conn.execute(
        "INSERT INTO price_history (listing_source_id, price_eur, observed_at) VALUES (?,?,?)",
        (cur.lastrowid, raw.price_eur, now),
    )
    for i, url in enumerate(raw.photo_urls):
        conn.execute(
            "INSERT OR IGNORE INTO photos (listing_id, url, position) VALUES (?,?,?)",
            (listing_id, url, i),
        )


def _mark_gone(conn, source_id: int, seen_ids: set[str]) -> int:
    """After a COMPLETE run: bump missed_runs for unseen ads, deactivate after threshold."""
    rows = conn.execute(
        "SELECT id, external_id, listing_id, missed_runs FROM listing_sources "
        "WHERE source_id=? AND is_active=1",
        (source_id,),
    ).fetchall()
    gone = 0
    for r in rows:
        if r["external_id"] in seen_ids:
            continue
        missed = r["missed_runs"] + 1
        active = 0 if missed >= GONE_AFTER_MISSED_RUNS else 1
        conn.execute(
            "UPDATE listing_sources SET missed_runs=?, is_active=? WHERE id=?",
            (missed, active, r["id"]),
        )
        if not active:
            still_active = conn.execute(
                "SELECT COUNT(*) c FROM listing_sources WHERE listing_id=? AND is_active=1",
                (r["listing_id"],),
            ).fetchone()["c"]
            if still_active == 0:
                conn.execute(
                    "UPDATE listings SET status='gone' WHERE id=? AND status='active'",
                    (r["listing_id"],),
                )
                gone += 1
    conn.commit()
    return gone
