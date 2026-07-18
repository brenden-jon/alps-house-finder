"""SeLoger adapter — best-effort only, expected to be blocked most of the time.

SeLoger sits behind Datadome; direct requests get 403 immediately (verified
2026-07). This adapter makes ONE polite attempt per run and aborts on the first
challenge so we never hammer them. If their protection relaxes, it starts
returning data; until then the run is recorded as 'error' and the other sources
carry coverage (SeLoger inventory is overwhelmingly agency-mandated and
cross-posts to Bien'ici / Green-Acres / notaires, which we scrape fully).
"""

import re
from collections.abc import Iterator

from bs4 import BeautifulSoup

from ..http import PoliteSession
from ..models import RawListing
from .base import SourceAdapter

SEARCH_URL = "https://www.seloger.com/immobilier/achat/immo-{slug}-{dept}/"


class SeLogerAdapter(SourceAdapter):
    code = "seloger"
    name = "SeLoger"
    base_url = "https://www.seloger.com"

    def __init__(self):
        self.http = PoliteSession(self.code, min_delay=6.0, max_delay=10.0)

    def fetch(self, communes: list[dict]) -> Iterator[RawListing]:
        for c in communes:
            slug = c["slug"]
            html = self.http.get(SEARCH_URL.format(slug=slug, dept=c["department"]))
            yield from self._parse_page(html, c)

    def _parse_page(self, html: str, commune: dict) -> Iterator[RawListing]:
        soup = BeautifulSoup(html, "html.parser")
        for card in soup.select('[data-testid="sl.explore.card-container"], article[class*="Card"]'):
            link = card.select_one('a[href*="/annonces/"]')
            if not link:
                continue
            url = link["href"]
            m = re.search(r"/(\d{6,})\.htm", url)
            if not m:
                continue
            price_el = card.find(string=re.compile(r"€"))
            price = int(re.sub(r"[^\d]", "", str(price_el))) if price_el else None
            if not price:
                continue
            yield RawListing(
                external_id=m.group(1),
                url=url if url.startswith("http") else f"https://www.seloger.com{url}",
                title=link.get_text(" ", strip=True)[:120],
                price_eur=price,
                commune_name=commune["name"],
                raw={"url": url},
            )
