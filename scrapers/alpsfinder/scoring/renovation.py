"""Renovation-need heuristic from French listing text. Coarse by design —
the point is consistent ranking and an all-in price estimate, not a quote."""

import re

HEAVY_KEYWORDS = [
    "à rénover entièrement", "entièrement à rénover", "à réhabiliter", "gros travaux",
    "à rénover", "grange", "ferme à rénover", "ruine", "gros oeuvre", "à restaurer",
]
LIGHT_KEYWORDS = [
    "travaux à prévoir", "prévoir des travaux", "à rafraîchir", "rafraîchissement",
    "à moderniser", "cuisine à refaire", "quelques travaux", "à actualiser",
]
NONE_KEYWORDS = [
    "entièrement rénové", "rénové avec goût", "refait à neuf", "rénovation complète",
    "rénové en 20", "neuf", "récent", "parfait état", "excellent état",
]

COST_PER_M2 = {"heavy": 1500, "light": 600, "none": 0}


def assess(title: str | None, description: str | None, dpe: str | None,
           area_m2: float | None) -> tuple[str, int]:
    """Returns (flag, estimated_cost_eur)."""
    text = " ".join(filter(None, [title, description])).lower()
    text = re.sub(r"\s+", " ", text)

    flag = None
    if any(k in text for k in NONE_KEYWORDS):
        flag = "none"
    if any(k in text for k in LIGHT_KEYWORDS):
        flag = "light"
    if any(k in text for k in HEAVY_KEYWORDS):
        flag = "heavy"  # heavy wins if both mentioned

    per_m2 = None
    if flag is None:
        if dpe in ("F", "G"):
            flag, per_m2 = "light", 400  # energy renovation at minimum
        else:
            flag, per_m2 = "none", 0
    if per_m2 is None:
        per_m2 = COST_PER_M2[flag]

    area = area_m2 or 100
    return flag, int(per_m2 * area)
