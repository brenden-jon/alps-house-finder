"""immobilier.notaires.fr adapter — official notaires' public JSON API.

GET https://www.immobilier.notaires.fr/pub-services/inotr-www-annonces/v1/annonces
    ?page=0&parPage=50&departements=74&typeTransactions=VENTE
Returns annonceResumeDto[] with inseeCommune — we query per department and keep
only ads in knowledge-base communes. Often estate sales / à-rénover properties
that never reach the big portals.
"""

from collections.abc import Iterator

from ..http import PoliteSession
from ..models import RawListing
from .base import SourceAdapter

API_URL = "https://www.immobilier.notaires.fr/pub-services/inotr-www-annonces/v1/annonces"
PER_PAGE = 50
MAX_PAGES = 40

TYPE_MAP = {"MAI": "maison", "APP": "appartement", "TER": "terrain", "IMM": "maison",
            "PRO": "other", "FON": "other", "GAR": "other"}


class NotairesAdapter(SourceAdapter):
    code = "notaires"
    name = "Notaires"
    base_url = "https://www.immobilier.notaires.fr"

    def __init__(self):
        self.http = PoliteSession(self.code, min_delay=2.0, max_delay=4.0)

    def fetch(self, communes: list[dict]) -> Iterator[RawListing]:
        by_insee = {c["insee_code"] for c in communes}
        depts = sorted({c["department"] for c in communes})
        for dept in depts:
            for page in range(MAX_PAGES):
                data = self.http.get_json(API_URL, {
                    "page": page, "parPage": PER_PAGE,
                    "departements": dept, "typeTransactions": "VENTE",
                })
                ads = data.get("annonceResumeDto") or []
                for ad in ads:
                    if str(ad.get("inseeCommune")) not in by_insee:
                        continue
                    listing = self._parse_ad(ad)
                    if listing:
                        yield listing
                if len(ads) < PER_PAGE:
                    break

    @staticmethod
    def _parse_ad(ad: dict) -> RawListing | None:
        price = ad.get("prixTotal") or ad.get("prixAffiche")
        if not price or price < 20000 or ad.get("viager") == "OUI":
            return None
        type_raw = TYPE_MAP.get(ad.get("typeBien"), ad.get("typeBien"))
        if type_raw == "terrain":
            return None  # land only — out of scope
        url = ad.get("urlDetailAnnonceFr") or ad.get("urlDetailAnnonceEn")
        if not url:
            return None
        surface = ad.get("surface")
        land = ad.get("surfaceTerrain")
        # for houses the API sometimes puts plot size in `surface` — drop absurd values
        if surface and surface > 600:
            surface = None
        photos = [ad["urlPhotoPrincipale"]] if ad.get("urlPhotoPrincipale") else []
        return RawListing(
            external_id=str(ad.get("annonceId") or ad["id"]),
            url=url,
            title=f"{type_raw or 'bien'} notaire — {ad.get('communeNom')}",
            description=ad.get("descriptionFr"),
            property_type_raw=type_raw,
            price_eur=int(price),
            area_m2=float(surface) if surface else None,
            land_m2=float(land) if land else None,
            commune_name=ad.get("communeNom"),
            postal_code=ad.get("codePostal"),
            insee_code=str(ad.get("inseeCommune")),
            agency_name="Notaire",
            photo_urls=photos,
            raw=ad,
        )
