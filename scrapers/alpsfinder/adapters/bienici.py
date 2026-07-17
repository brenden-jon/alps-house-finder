"""Bien'ici adapter — unofficial public JSON API.

Search: GET https://www.bienici.com/realEstateAds.json?filters=<urlencoded JSON>
Zone resolution: GET https://res.bienici.com/suggest.json?q=<name> (returns insee_code + zoneIds).
Both verified working 2026-07. Unofficial: expect drift; parser is fixture-tested.
"""

import json
from collections.abc import Iterator

from ..http import PoliteSession
from ..models import RawListing
from .base import SourceAdapter

SUGGEST_URL = "https://res.bienici.com/suggest.json"
SEARCH_URL = "https://www.bienici.com/realEstateAds.json"
PAGE_SIZE = 24
MAX_PRICE = 900_000  # hard budget ceiling; scoring applies the all-in filter
ZONE_TTL_S = 30 * 24 * 3600


class BienIciAdapter(SourceAdapter):
    code = "bienici"
    name = "Bien'ici"
    base_url = "https://www.bienici.com"

    def __init__(self):
        self.http = PoliteSession(self.code)

    def resolve_zone_id(self, commune: dict) -> str | None:
        """Find the Bien'ici zoneId for a commune, matching by INSEE code."""
        portal_ids = json.loads(commune.get("portal_ids") or "{}")
        if portal_ids.get("bienici_zone_id"):
            return str(portal_ids["bienici_zone_id"])
        results = self.http.get_json(SUGGEST_URL, {"q": commune["name"]}, ttl_s=ZONE_TTL_S)
        for r in results:
            if r.get("type") == "city" and r.get("insee_code") == commune["insee_code"]:
                zone_ids = r.get("zoneIds") or []
                return str(zone_ids[0]) if zone_ids else None
        return None

    def fetch(self, communes: list[dict]) -> Iterator[RawListing]:
        zone_ids = []
        for c in communes:
            zid = self.resolve_zone_id(c)
            if zid:
                zone_ids.append(zid)
            else:
                print(f"  bienici: no zoneId found for {c['name']} — skipped")
        if not zone_ids:
            return

        seen: set[str] = set()
        frm = 0
        while True:
            filters = {
                "size": PAGE_SIZE,
                "from": frm,
                "filterType": "buy",
                "propertyType": ["house", "flat"],
                "maxPrice": MAX_PRICE,
                "page": frm // PAGE_SIZE + 1,
                "sortBy": "publicationDate",
                "sortOrder": "desc",
                "onTheMarket": [True],
                "zoneIdsByTypes": {"zoneIds": zone_ids},
            }
            data = self.http.get_json(SEARCH_URL, {"filters": json.dumps(filters)})
            ads = data.get("realEstateAds", [])
            total = data.get("total", 0)
            for ad in ads:
                listing = self._parse_ad(ad)
                if listing and listing.external_id not in seen:
                    seen.add(listing.external_id)
                    yield listing
            frm += PAGE_SIZE
            if frm >= total or not ads:
                break

    @staticmethod
    def _parse_ad(ad: dict) -> RawListing | None:
        # "programme" = new-build program with price/surface RANGES (arrays) — skip
        if ad.get("propertyType") == "programme" or isinstance(ad.get("price"), list):
            return None
        if ad.get("transactionType") not in (None, "buy"):
            return None
        price = ad.get("price")
        if not price:
            return None

        blur = ad.get("blurInfo") or {}
        pos = blur.get("position") or {}
        photos = []
        for p in ad.get("photos") or []:
            url = p.get("url_photo") or p.get("url")
            if url:
                photos.append(url)

        return RawListing(
            external_id=str(ad["id"]),
            url=f"https://www.bienici.com/annonce/{ad['id']}",
            title=ad.get("title"),
            description=ad.get("description"),
            property_type_raw=ad.get("propertyType"),
            price_eur=int(price),
            area_m2=ad.get("surfaceArea"),
            land_m2=ad.get("landSurfaceArea"),
            rooms=ad.get("roomsQuantity"),
            bedrooms=ad.get("bedroomsQuantity"),
            dpe=(ad.get("energyClassification") or None),
            lat=pos.get("lat"),
            lon=pos.get("lon"),
            geo_blurred=blur.get("type") != "exact",
            commune_name=ad.get("city"),
            postal_code=ad.get("postalCode"),
            agency_name=ad.get("accountDisplayName"),
            photo_urls=photos[:12],
            raw=ad,
        )
