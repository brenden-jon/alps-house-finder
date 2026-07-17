"""Commune knowledge base: YAML files -> communes table, and listing->commune matching."""

import json
import sqlite3
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .db import REPO_ROOT

COMMUNES_DIR = REPO_ROOT / "data" / "communes"


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def norm_name(s: str) -> str:
    s = _strip_accents(s.lower().strip())
    for token in ("-", "'", "’", "."):
        s = s.replace(token, " ")
    s = " ".join(s.split())
    if s.startswith("st "):
        s = "saint " + s[3:]
    return s


def load_commune_yamls(directory: Path = COMMUNES_DIR) -> list[dict]:
    entries = []
    for f in sorted(directory.glob("*.yaml")):
        data = yaml.safe_load(f.read_text())
        if not isinstance(data, dict) or "insee_code" not in data:
            raise ValueError(f"{f.name}: not a valid commune entry")
        data["slug"] = data.get("slug") or f.stem
        entries.append(data)
    return entries


def upsert_communes(conn: sqlite3.Connection, entries: list[dict]) -> int:
    now = datetime.now(timezone.utc).isoformat()
    for e in entries:
        resort = e.get("resort") or {}
        ratings = e.get("ratings") or {}
        rental = e.get("rental") or {}
        conn.execute(
            """
            INSERT INTO communes (insee_code, name, slug, department, postal_codes, lat, lon,
              village_alt_m, resort_name, resort_top_alt_m, resort_base_alt_m, lift_drive_min,
              slope_access_notes, geneva_drive_min,
              rating_ski, rating_backcountry, rating_summer, rating_charm, rating_village_life,
              rating_license_risk, license_notes, rental_notes,
              est_weekly_rate_winter_eur, est_weekly_rate_summer_eur, est_occupancy_weeks,
              portal_ids, notes, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(insee_code) DO UPDATE SET
              name=excluded.name, slug=excluded.slug, department=excluded.department,
              postal_codes=excluded.postal_codes, lat=excluded.lat, lon=excluded.lon,
              village_alt_m=excluded.village_alt_m, resort_name=excluded.resort_name,
              resort_top_alt_m=excluded.resort_top_alt_m, resort_base_alt_m=excluded.resort_base_alt_m,
              lift_drive_min=excluded.lift_drive_min, slope_access_notes=excluded.slope_access_notes,
              geneva_drive_min=excluded.geneva_drive_min,
              rating_ski=excluded.rating_ski, rating_backcountry=excluded.rating_backcountry,
              rating_summer=excluded.rating_summer, rating_charm=excluded.rating_charm,
              rating_village_life=excluded.rating_village_life,
              rating_license_risk=excluded.rating_license_risk,
              license_notes=excluded.license_notes, rental_notes=excluded.rental_notes,
              est_weekly_rate_winter_eur=excluded.est_weekly_rate_winter_eur,
              est_weekly_rate_summer_eur=excluded.est_weekly_rate_summer_eur,
              est_occupancy_weeks=excluded.est_occupancy_weeks,
              portal_ids=excluded.portal_ids, notes=excluded.notes, updated_at=excluded.updated_at
            """,
            (
                str(e["insee_code"]), e["name"], e["slug"], str(e["department"]),
                json.dumps([str(p) for p in e.get("postal_codes", [])]),
                e.get("lat"), e.get("lon"), e.get("village_alt_m"),
                resort.get("name"), resort.get("top_alt_m"), resort.get("base_alt_m"),
                resort.get("lift_drive_min"), resort.get("slope_access_notes"),
                e.get("geneva_drive_min"),
                ratings.get("ski"), ratings.get("backcountry"), ratings.get("summer"),
                ratings.get("charm"), ratings.get("village_life"), ratings.get("license_risk"),
                e.get("license_notes"), rental.get("notes"),
                rental.get("est_weekly_rate_winter_eur"), rental.get("est_weekly_rate_summer_eur"),
                rental.get("est_occupancy_weeks"),
                json.dumps(e.get("portal_ids", {})), e.get("notes"),
                e.get("updated_at") or now,
            ),
        )
    conn.commit()
    return len(entries)


class CommuneMatcher:
    """Match a RawListing to a commune: INSEE -> postal+name -> name -> GPS nearest."""

    def __init__(self, conn: sqlite3.Connection):
        rows = conn.execute(
            "SELECT insee_code, name, postal_codes, lat, lon FROM communes"
        ).fetchall()
        self.by_insee = {r["insee_code"]: r for r in rows}
        self.by_name = {norm_name(r["name"]): r["insee_code"] for r in rows}
        self.by_postal: dict[str, list] = {}
        for r in rows:
            for p in json.loads(r["postal_codes"]):
                self.by_postal.setdefault(p, []).append(r)
        self.coords = [(r["lat"], r["lon"], r["insee_code"]) for r in rows if r["lat"]]

    def match(self, insee=None, postal=None, name=None, lat=None, lon=None) -> str | None:
        if insee and str(insee) in self.by_insee:
            return str(insee)
        if name:
            n = norm_name(name)
            if postal:
                for r in self.by_postal.get(str(postal), []):
                    if norm_name(r["name"]) == n:
                        return r["insee_code"]
            if n in self.by_name:
                return self.by_name[n]
        if postal:
            candidates = self.by_postal.get(str(postal), [])
            if len(candidates) == 1:
                return candidates[0]["insee_code"]
        if lat and lon and self.coords:
            best, best_d2 = None, None
            for clat, clon, code in self.coords:
                d2 = (clat - lat) ** 2 + ((clon - lon) * 0.7) ** 2
                if best_d2 is None or d2 < best_d2:
                    best, best_d2 = code, d2
            # ~5 km in degrees^2 (1 deg lat ~ 111 km)
            if best_d2 is not None and best_d2 < (5 / 111) ** 2:
                return best
        return None
