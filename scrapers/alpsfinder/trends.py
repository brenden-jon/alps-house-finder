"""DVF price trends: official French transaction data (Etalab geo-dvf), per commune.

URL: https://files.data.gouv.fr/geo-dvf/latest/csv/{year}/communes/{dept}/{insee}.csv
Redirects to S3; follow. Median €/m² per year per property type (Maison/Appartement).

To avoid double counting multi-row mutations, only mutations whose rows contain
exactly one built local of a single type are used.
"""

import csv
import io
import sqlite3
from collections import defaultdict
from statistics import median

from .http import PoliteSession

DVF_URL = "https://files.data.gouv.fr/geo-dvf/latest/csv/{year}/communes/{dept}/{insee}.csv"
YEARS = list(range(2016, 2027))
DVF_TTL_S = 30 * 24 * 3600  # official data updates twice a year


def update_trends(conn: sqlite3.Connection, communes: list[dict]) -> int:
    http = PoliteSession("dvf", min_delay=0.5, max_delay=1.5, cache_ttl_s=DVF_TTL_S)
    rows_written = 0
    for c in communes:
        for year in YEARS:
            url = DVF_URL.format(year=year, dept=c["department"], insee=c["insee_code"])
            try:
                text = http.get(url)
            except Exception:
                continue  # year not published (or commune missing) — fine
            for ptype, med, n in _aggregate(text):
                conn.execute(
                    """INSERT INTO commune_price_trends (commune_insee, year, property_type, median_eur_m2, n_sales)
                       VALUES (?,?,?,?,?)
                       ON CONFLICT(commune_insee, year, property_type) DO UPDATE SET
                         median_eur_m2=excluded.median_eur_m2, n_sales=excluded.n_sales""",
                    (c["insee_code"], year, ptype, med, n),
                )
                rows_written += 1
        conn.commit()
    return rows_written


def _aggregate(csv_text: str):
    TYPE_MAP = {"Maison": "house", "Appartement": "apartment"}
    mutations: dict[str, list[dict]] = defaultdict(list)
    for row in csv.DictReader(io.StringIO(csv_text)):
        if row.get("nature_mutation") != "Vente":
            continue
        mutations[row["id_mutation"]].append(row)

    ppm2_by_type: dict[str, list[float]] = defaultdict(list)
    for rows in mutations.values():
        built = [r for r in rows if r.get("type_local") in TYPE_MAP]
        if len(built) != 1:
            continue  # multi-lot / mixed mutation: price not attributable
        r = built[0]
        try:
            price = float(r["valeur_fonciere"])
            surface = float(r["surface_reelle_bati"])
        except (ValueError, TypeError, KeyError):
            continue
        if price < 15000 or surface < 15:
            continue
        ppm2 = price / surface
        if 300 < ppm2 < 40000:
            ppm2_by_type[TYPE_MAP[r["type_local"]]].append(ppm2)

    for ptype, values in ppm2_by_type.items():
        if len(values) >= 3:
            yield ptype, int(median(values)), len(values)


def latest_median(conn: sqlite3.Connection, insee: str, property_type: str) -> int | None:
    """Most recent yearly median with a decent sample; houses fall back to apartments."""
    for ptype in ([property_type, "apartment", "house"] if property_type else ["house", "apartment"]):
        row = conn.execute(
            """SELECT median_eur_m2 FROM commune_price_trends
               WHERE commune_insee=? AND property_type=? AND n_sales >= 5
               ORDER BY year DESC LIMIT 1""",
            (insee, "house" if ptype in ("house", "chalet", "farmhouse") else "apartment"),
        ).fetchone()
        if row:
            return row["median_eur_m2"]
    return None
