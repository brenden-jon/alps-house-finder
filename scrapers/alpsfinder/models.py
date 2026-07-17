from dataclasses import dataclass, field


@dataclass
class RawListing:
    """A listing as parsed from one source, before ingest/dedupe."""

    external_id: str
    url: str
    title: str | None = None
    description: str | None = None
    property_type_raw: str | None = None
    price_eur: int | None = None
    area_m2: float | None = None
    land_m2: float | None = None
    rooms: int | None = None
    bedrooms: int | None = None
    dpe: str | None = None
    lat: float | None = None
    lon: float | None = None
    geo_blurred: bool = False
    commune_name: str | None = None
    postal_code: str | None = None
    insee_code: str | None = None
    agency_name: str | None = None
    photo_urls: list[str] = field(default_factory=list)
    raw: dict = field(default_factory=dict)


PROPERTY_TYPE_MAP = {
    # normalized: house | chalet | apartment | farmhouse | land | other
    "house": "house",
    "maison": "house",
    "villa": "house",
    "chalet": "chalet",
    "flat": "apartment",
    "apartment": "apartment",
    "appartement": "apartment",
    "ferme": "farmhouse",
    "farmhouse": "farmhouse",
    "grange": "farmhouse",
    "terrain": "land",
    "land": "land",
}


def normalize_property_type(raw: str | None, text: str = "") -> str:
    if raw:
        t = PROPERTY_TYPE_MAP.get(raw.strip().lower())
        if t:
            # portals label chalets as "house"; sniff the text
            if t == "house" and "chalet" in text.lower():
                return "chalet"
            return t
    lower = text.lower()
    for kw, t in (("chalet", "chalet"), ("ferme", "farmhouse"), ("appartement", "apartment"), ("maison", "house")):
        if kw in lower:
            return t
    return "other"
