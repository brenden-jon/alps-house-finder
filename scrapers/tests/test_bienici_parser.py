import json
from pathlib import Path

from alpsfinder.adapters.bienici import BienIciAdapter

FIXTURE = Path(__file__).parent / "fixtures" / "bienici_samoens.json"


def test_parse_fixture():
    data = json.loads(FIXTURE.read_text())
    ads = data["realEstateAds"]
    parsed = [BienIciAdapter._parse_ad(a) for a in ads]
    listings = [p for p in parsed if p]

    # programmes (range-priced new builds) must be skipped, normal ads kept
    assert len(listings) >= 10
    assert all(isinstance(l.price_eur, int) and l.price_eur > 0 for l in listings)
    assert all(l.external_id for l in listings)
    assert all(l.url.startswith("https://www.bienici.com/annonce/") for l in listings)

    sample = listings[0]
    assert sample.commune_name
    assert sample.photo_urls


def test_programme_skipped():
    data = json.loads(FIXTURE.read_text())
    programmes = [a for a in data["realEstateAds"] if a.get("propertyType") == "programme"]
    if programmes:
        assert BienIciAdapter._parse_ad(programmes[0]) is None
