# Commune knowledge base schema

One YAML file per candidate commune. Loaded with `alpsfinder load-communes` (upsert by `insee_code`).

```yaml
insee_code: "74236"          # official INSEE code (string!)
name: "Saint-Gervais-les-Bains"
slug: saint-gervais-les-bains  # optional, defaults to filename
department: "74"             # 74 Haute-Savoie, 73 Savoie
postal_codes: ["74170"]
lat: 45.8925                 # village center
lon: 6.7112
village_alt_m: 810
resort:
  name: "Evasion Mont-Blanc"
  top_alt_m: 2353            # highest lift-served point — climate-safety key number
  base_alt_m: 850
  lift_drive_min: 5          # minutes from village center to main lift
  slope_access_notes: "free text: ski-in/ski-out zones, ski bus, gondola from town..."
geneva_drive_min: 70         # typical drive to Geneva airport
ratings:                     # 0-10 curated judgment, one-line justification in notes
  ski: 7                     # resort size/quality/snow-reliability composite
  backcountry: 8
  summer: 9                  # hiking, nature, summer activities
  charm: 8                   # aesthetics, authenticity (vs purpose-built resort)
  village_life: 8            # year-round shops/restaurants/school/community
  license_risk: 6            # 10 = no restrictions, 0 = quota/change-of-use like Chamonix
license_notes: >
  Cited facts on meublé de tourisme rules: quota? change-of-use? Le Meur adoption?
rental:
  est_weekly_rate_winter_eur: 2200
  est_weekly_rate_summer_eur: 1300
  est_occupancy_weeks: 16
  notes: "free text + sources"
portal_ids:                  # resolved once, cached here
  bienici_zone_id: null
  pap_geo_id: null
notes: "anything else"
updated_at: "2026-07-17"
```

Conventions:
- Objective fields (INSEE, altitudes, drive times) must be real; ratings are judgment calls
  with justification; anything unverified gets "— verify" in the notes.
- `license_risk` is the dimension that most needs periodic re-research (Le Meur law
  adoption moves quarterly). Keep `updated_at` honest.
