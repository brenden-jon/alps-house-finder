"""Green-Acres adapter — server-rendered listing pages, parsed with BeautifulSoup.

Search page: https://www.green-acres.fr/immobilier/{commune-slug}
Cards carry data-advertid + base64 URL in data-o. Only the first page (~24 ads)
is fetched per commune: deeper pagination goes through an endpoint their
robots.txt disallows, so we deliberately skip it — Bien'ici is the primary
full-coverage source; this adds Green-Acres' international-buyer inventory.
"""

import base64
import re
import unicodedata
from collections.abc import Iterator

from bs4 import BeautifulSoup

from ..http import PoliteSession
from ..models import RawListing
from .base import SourceAdapter

SEARCH_URL = "https://www.green-acres.fr/immobilier/{slug}"

TYPE_FROM_URL = re.compile(r"/properties/([a-z-]+)/")


def _slug_candidates(commune: dict) -> list[str]:
    name = commune["name"].lower()
    name = "".join(c for c in unicodedata.normalize("NFD", name)
                   if unicodedata.category(c) != "Mn")
    full = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    out = [full]
    if commune.get("slug") and commune["slug"] not in out:
        out.append(commune["slug"])
    # Green-Acres sometimes uses the short town name (e.g. chamonix)
    short = full.split("-")[0]
    if len(short) > 5 and short not in out:
        out.append(short)
    return out


def _num(text: str) -> int | None:
    digits = re.sub(r"[^\d]", "", text or "")
    return int(digits) if digits else None


class GreenAcresAdapter(SourceAdapter):
    code = "greenacres"
    name = "Green-Acres"
    base_url = "https://www.green-acres.fr"

    def __init__(self):
        self.http = PoliteSession(self.code, min_delay=3.0, max_delay=6.0)

    def fetch(self, communes: list[dict]) -> Iterator[RawListing]:
        for c in communes:
            html = None
            for slug in _slug_candidates(c):
                try:
                    html = self.http.get(SEARCH_URL.format(slug=slug))
                    break
                except Exception:
                    continue
            if html is None:
                print(f"  greenacres: no page found for {c['name']} — skipped")
                continue
            yield from self._parse_page(html, c)

    def _parse_page(self, html: str, commune: dict) -> Iterator[RawListing]:
        soup = BeautifulSoup(html, "html.parser")
        for card in soup.select("div.announce-card[data-advertid]"):
            ad_id = card.get("data-advertid")
            if not ad_id:
                continue
            try:
                url = base64.b64decode(card.get("data-o", "")).decode()
            except Exception:
                url = ""
            if not url.startswith("http"):
                continue

            price_el = card.select_one(".info-price")
            price = _num(price_el.get_text()) if price_el else None
            if not price or price < 20000:
                continue

            area = rooms = bedrooms = None
            for tag in card.select(".characteristics .info-tag"):
                t = tag.get_text(" ", strip=True)
                title = (tag.get("title") or "").lower()
                if "surface" in title or "m²" in t:
                    if "€" not in t:
                        area = _num(t)
                        # some cards carry the plot size here, not living area
                        if area and area > 600:
                            area = None
                elif "pièce" in title or "pièce" in t:
                    rooms = _num(t)
                elif "chambre" in title or "chambre" in t:
                    bedrooms = _num(t)

            loc_el = card.select_one(".announce-localisation")
            loc = loc_el.get_text(strip=True) if loc_el else ""
            commune_name = loc.split("(")[0].strip() or commune["name"]

            desc_el = card.select_one(".description-details")
            description = desc_el.get_text(" ", strip=True) if desc_el else None

            agency_el = card.select_one(".agency-name, .announce-agency")
            agency = agency_el.get_text(strip=True) if agency_el else None

            photos = []
            for img in card.select("img.announce-card-img"):
                src = img.get("src") or img.get("data-lazy-src")
                if src and src.startswith("http"):
                    photos.append(src)

            m = TYPE_FROM_URL.search(url)
            type_raw = m.group(1) if m else None

            yield RawListing(
                external_id=ad_id,
                url=url,
                title=card.get("title"),
                description=description,
                property_type_raw=type_raw,
                price_eur=price,
                area_m2=float(area) if area else None,
                rooms=rooms,
                bedrooms=bedrooms,
                commune_name=commune_name,
                agency_name=agency,
                photo_urls=photos[:12],
                raw={"advertid": ad_id, "url": url, "loc": loc},
            )
