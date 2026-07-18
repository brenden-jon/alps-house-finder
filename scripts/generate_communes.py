"""Generate commune YAMLs for all villages within ~10 min of a lift in a 2500m+ ski area.

Threshold: resort top >= 2450m (catches Grand Massif 2480 / Les Contamines 2487 /
La Clusaz 2477 borderliners). Ratings are first-pass judgment seeds marked
'— verify'; INSEE codes need a verification pass (wrong codes only degrade DVF/
notaires matching, portals match by name+postal). Existing hand-written YAMLs are
never overwritten.

Row: (insee, name, dept, postal, lat, lon, village_alt, resort, top, base,
      lift_min, geneva_min, ski, bc, summer, charm, life, license, wk_winter,
      wk_summer, occ_weeks, note)
"""

import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "communes"

ROWS = [
    # Chamonix valley satellites (Chamonix itself hand-written)
    ("74143","Les Houches","74","74310",45.8908,6.7987,1000,"Chamonix valley (Grands Montets 3275 via valley)",3275,1000,8,70,7,9,9,7,8,2,2200,1400,18,"Same 1-permit quota as Chamonix. — verify"),
    ("74266","Servoz","74","74310",45.9267,6.7654,814,"Chamonix valley gateway",3275,1000,12,65,6,8,9,8,6,6,1500,1000,14,"Quieter, cheaper Chamonix access. — verify"),
    ("74290","Vallorcine","74","74660",46.0331,6.9331,1260,"Balme/Le Tour + Grands Montets 10min",3275,1260,8,85,6,9,8,8,4,7,1500,900,13,"Border village, Swiss side access. — verify"),
    # Grand Massif (Samoëns hand-written)
    ("74190","Morillon","74","74440",46.0855,6.6829,700,"Grand Massif",2480,700,3,60,7,7,8,8,6,7,1600,900,15,"Own gondola, cheaper than Samoëns. — verify"),
    ("74273","Sixt-Fer-à-Cheval","74","74740",46.0567,6.7771,760,"Grand Massif (Sixt sector)",2480,760,8,70,6,8,10,9,5,7,1400,900,13,"Cirque du Fer-à-Cheval, plus beau village. — verify"),
    ("74014","Arâches-la-Frasse (Les Carroz)","74","74300",46.0264,6.6335,1140,"Grand Massif (Les Carroz/Flaine)",2480,1140,2,55,7,7,8,7,7,7,1800,1000,15,"Balcony village, closest Flaine access. — verify"),
    # Val Montjoie
    ("74085","Les Contamines-Montjoie","74","74170",45.8221,6.7276,1164,"Les Contamines-Hauteluce (Aiguille Croche 2487)",2487,1164,3,80,7,9,9,8,6,6,1900,1100,15,"High north-facing bowl, authentic village. — verify"),
    # Aravis (La Clusaz hand-written)
    ("74160","Manigod","74","74230",45.8697,6.3742,950,"La Clusaz-Manigod (Balme 2477 via domain)",2477,1450,8,60,7,7,8,9,6,7,1500,900,14,"Cheaper Clusaz backdoor, Col de la Croix Fry. — verify"),
    ("74239","Saint-Jean-de-Sixt","74","74450",45.9228,6.4113,960,"Aravis hub (Clusaz lifts 5min)",2477,960,5,55,6,7,8,7,6,7,1300,800,13,"Between Clusaz and Grand-Bornand. — verify"),
    # Espace Killy
    ("73304","Val-d'Isère","73","73150",45.4489,6.9803,1850,"Val d'Isère (Espace Killy 3450)",3450,1850,2,165,10,10,7,7,7,4,3800,1300,20,"Top-tier resort; expensive; watch STR debate. — verify"),
    ("73296","Tignes","73","73320",45.4681,6.9061,2100,"Tignes (Espace Killy 3450)",3450,1550,2,160,10,9,6,4,5,5,3200,1100,20,"Purpose-built (except Brévières/Boisses). — verify"),
    # Paradiski + La Rosière
    ("73054","Bourg-Saint-Maurice","73","73700",45.6181,6.7692,840,"Les Arcs (funicular, 3226)",3226,840,5,140,8,8,7,7,9,7,1500,900,15,"Real town, funicular to Arc 1600, Eurostar. — verify"),
    ("73138","Landry","73","73210",45.5744,6.7345,800,"Paradiski (Vanoise Express side)",3250,800,8,140,8,8,7,7,5,7,1400,850,14,"Peisey access village. — verify"),
    ("73197","Peisey-Nancroix","73","73210",45.5497,6.7561,1300,"Paradiski (Vanoise Express)",3250,1300,5,145,8,9,8,8,5,7,1900,1000,15,"Authentic + Paradiski link hub. — verify"),
    ("73323","Villaroger","73","73640",45.5875,6.8664,1090,"Les Arcs (chairlift from village)",3226,1090,2,145,7,9,7,8,4,8,1600,850,14,"Sleepy hamlet with own Arcs lift. — verify"),
    ("73176","Montvalezan (La Rosière)","73","73700",45.6306,6.8494,1850,"Espace San Bernardo (2800)",2800,1175,3,145,7,8,7,7,5,7,1900,900,15,"Sunny, family, Italy link. — verify"),
    ("73285","Séez","73","73700",45.6236,6.8006,904,"La Rosière lifts 10min",2800,904,10,140,6,7,7,7,6,7,1200,800,13,"Baroque village below La Rosière. — verify"),
    ("73006","Aime-la-Plagne","73","73210",45.5544,6.6486,690,"La Plagne (3250)",3250,690,10,135,8,7,7,6,7,7,1300,800,14,"Valley town, Plagne access. — verify"),
    ("73150","La Plagne Tarentaise","73","73210",45.5069,6.6778,1250,"La Plagne (3250)",3250,1250,3,140,8,7,7,5,5,6,2200,900,17,"Macot + villages; mixed purpose-built. — verify"),
    ("73071","Champagny-en-Vanoise","73","73350",45.4592,6.7128,1250,"La Plagne (Champagny gondola)",3250,1250,3,150,8,8,9,8,5,7,1800,950,15,"Vanoise balcony, quiet Plagne backdoor. — verify"),
    # Trois Vallées
    ("73227","Courchevel (Saint-Bon)","73","73120",45.4153,6.6344,1300,"Les 3 Vallées (3230)",3230,1300,3,140,10,8,7,6,6,5,3500,1200,19,"Le Praz/village levels more authentic. — verify"),
    ("73015","Les Allues (Méribel)","73","73550",45.4342,6.5661,1100,"Les 3 Vallées",3230,1100,5,140,9,8,7,7,6,5,2800,1100,18,"Les Allues village vs Méribel station. — verify"),
    ("73257","Les Belleville (St-Martin)","73","73440",45.3814,6.5069,1450,"Les 3 Vallées",3230,1450,2,150,9,8,7,8,6,6,2400,1000,17,"St-Martin-de-Belleville = charm pick. — verify"),
    ("73194","Orelle","73","73140",45.2089,6.5369,900,"Les 3 Vallées (Orelle gondola 3230)",3230,900,2,165,8,7,6,6,5,8,1300,700,14,"Maurienne backdoor to Val Thorens. — verify"),
    ("73024","Les Avanchers-Valmorel","73","73260",45.4614,6.4442,1250,"Valmorel Grand Domaine (2550)",2550,1250,3,120,7,7,7,8,5,7,1600,850,14,"Trad-style resort, hamlets below. — verify"),
    # Maurienne (Val-Cenis & Bonneval hand-written)
    ("73023","Aussois","73","73500",45.2278,6.7414,1500,"Aussois (2750)",2750,1500,3,160,6,8,8,8,6,8,1300,800,13,"Fortified village, Vanoise south. — verify"),
    ("73157","Modane (Valfréjus)","73","73500",45.2,6.6667,1100,"Valfréjus (2737)",2737,1550,10,160,6,7,6,5,7,8,1100,600,12,"TGV town; Valfréjus above. — verify"),
    ("73322","Villarodin-Bourget (La Norma)","73","73500",45.2158,6.7019,1350,"La Norma (2750)",2750,1350,5,160,6,7,7,7,4,8,1200,700,12,"Car-free family station. — verify"),
    ("73306","Valloire","73","73450",45.1653,6.4297,1430,"Galibier-Thabor (2600)",2600,1430,2,150,7,8,8,8,7,7,1600,900,15,"Real village + Tour de France cols. — verify"),
    ("73307","Valmeinier","73","73450",45.1836,6.4767,1500,"Galibier-Thabor (2600)",2600,1500,3,150,6,7,7,6,4,8,1300,700,13,"Quieter Valloire twin. — verify"),
    ("73280","Saint-Sorlin-d'Arves","73","73530",45.2178,6.2311,1550,"Les Sybelles (2620)",2620,1550,3,145,7,7,7,8,5,8,1300,750,13,"Aiguilles d'Arves scenery. — verify"),
    ("73269","Saint-Jean-d'Arves","73","73530",45.2331,6.2542,1550,"Les Sybelles",2620,1550,5,145,6,7,7,7,4,8,1200,700,12,"Scattered hamlets, sunny. — verify"),
    ("73121","Fontcouverte-la-Toussuire","73","73300",45.2547,6.2903,1750,"Les Sybelles",2620,1750,2,140,6,6,6,5,4,8,1300,700,13,"Purpose-built plateau station. — verify"),
    ("73318","Villarembert (Le Corbier)","73","73300",45.2397,6.2853,1550,"Les Sybelles",2620,1550,3,140,6,6,6,4,4,8,1200,650,13,"1970s station; cheap entry. — verify"),
    ("73235","Saint-François-Longchamp","73","73130",45.4167,6.3667,1650,"Grand Domaine (2550)",2550,1650,3,125,6,6,6,5,4,8,1200,650,12,"Col de la Madeleine. — verify"),
    # Oisans (38)
    ("38191","Huez (Alpe d'Huez)","38","38750",45.0908,6.0669,1860,"Alpe d'Huez Grand Domaine (3330)",3330,1450,2,170,9,8,7,5,6,6,2200,1000,17,"Legendary + Sarenne glacier. — verify"),
    ("38527","Vaujany","38","38114",45.1558,6.0781,1250,"Alpe d'Huez GD (cable car)",3330,1250,3,175,8,8,7,8,5,7,1800,900,15,"Hydro-rich trad village, huge cable car. — verify"),
    ("38289","Oz-en-Oisans","38","38114",45.1281,6.0703,1350,"Alpe d'Huez GD",3330,1350,3,175,7,7,7,7,4,7,1500,800,14,"Quiet forest-side gondolas. — verify"),
    ("38020","Auris-en-Oisans","38","38142",45.0553,6.0836,1600,"Alpe d'Huez GD",3330,1600,3,175,7,7,7,6,4,8,1300,700,13,"Sunny balcony, cheap. — verify"),
    ("38253","Les Deux Alpes","38","38860",45.0119,6.1236,1650,"Les 2 Alpes (3600 glacier)",3600,1300,2,170,8,8,7,5,6,6,1900,900,16,"Highest skiable glacier in France. — verify"),
    ("38548","Villard-Reculas","38","38114",45.0947,6.0378,1500,"Alpe d'Huez GD",3330,1500,3,170,7,7,7,7,3,8,1300,700,13,"Tiny balcony hamlet. — verify"),
    # Briançonnais / Écrins (05) — La Grave, Névache, Vallouise hand-written
    ("05023","Briançon","05","05100",44.8992,6.6428,1326,"Serre Chevalier (2800)",2800,1200,8,190,8,8,8,8,9,7,1300,900,15,"UNESCO Vauban city, real year-round life. — verify"),
    ("05133","Saint-Chaffrey (Chantemerle)","05","05330",44.9236,6.6072,1350,"Serre Chevalier",2800,1350,2,190,8,8,8,7,6,7,1600,900,15,"Core SC access. — verify"),
    ("05161","La Salle-les-Alpes (Villeneuve)","05","05240",44.9439,6.5622,1400,"Serre Chevalier",2800,1400,2,190,8,8,8,7,6,7,1700,950,15,"SC center, old village above. — verify"),
    ("05079","Le Monêtier-les-Bains","05","05220",44.9758,6.5089,1500,"Serre Chevalier",2800,1500,3,195,8,9,8,9,6,7,1800,1000,15,"Thermal baths + prettiest SC village. — verify"),
    ("05085","Montgenèvre","05","05100",44.9319,6.7264,1860,"Montgenèvre/Via Lattea (2700)",2700,1860,2,195,7,8,7,6,5,7,1700,800,15,"Border resort, Milky Way access. — verify"),
    ("05181","Villar-d'Arêne","05","05480",45.0403,6.3403,1650,"La Grave 5min",3550,1650,7,180,6,9,8,8,4,8,1100,700,11,"La Grave's quieter neighbor. — verify"),
    ("05110","Puy-Saint-Vincent","05","05290",44.8283,6.4831,1400,"Puy-Saint-Vincent (2700)",2700,1400,2,215,7,8,8,6,4,8,1400,800,13,"North-facing snow-sure family hill. — verify"),
    # Southern Alps
    ("05177","Vars","05","05560",44.5758,6.6842,1650,"Forêt Blanche (2750)",2750,1650,3,210,7,7,7,6,5,7,1500,800,14,"Big south domain w/ Risoul. — verify"),
    ("05119","Risoul","05","05600",44.6272,6.6389,1850,"Forêt Blanche",2750,1850,3,205,7,7,7,5,4,8,1300,700,13,"Cheaper Forêt Blanche side. — verify"),
    ("05096","Orcières","05","05170",44.6867,6.3253,1450,"Orcières Merlette (2725)",2725,1850,8,200,6,7,7,6,5,8,1300,750,13,"Champsaur family resort. — verify"),
    ("05098","Les Orres","05","05200",44.5083,6.5539,1550,"Les Orres (2720)",2720,1550,3,200,7,6,7,5,4,8,1300,700,13,"Serre-Ponçon lake views. — verify"),
    ("05157","Saint-Véran","05","05350",44.7014,6.8703,2040,"Beauregard/Queyras (2800)",2800,2040,3,210,5,8,9,10,4,8,1200,800,13,"Highest village in Europe; heritage rules. — verify"),
    ("05077","Molines-en-Queyras","05","05350",44.7267,6.8514,1750,"Queyras (2800)",2800,1750,5,210,5,8,8,8,4,8,1100,700,12,"Queyras larch valleys. — verify"),
    ("04006","Allos (La Foux)","04","04260",44.2358,6.6278,1400,"Espace Lumière (2600)",2600,1800,10,220,7,7,8,7,4,8,1300,750,13,"Val d'Allos + lake. — verify"),
    ("04226","Uvernet-Fours (Pra Loup)","04","04400",44.3644,6.6103,1600,"Espace Lumière (2600)",2600,1600,3,220,7,7,7,5,4,8,1400,750,13,"Pra Loup 1600/1500. — verify"),
    ("06073","Isola","06","06420",44.1869,7.0508,875,"Isola 2000 (2610)",2610,2000,10,230,7,6,7,6,4,8,1400,700,13,"Nice 1h30; village low, station high. — verify"),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    written = skipped = 0
    for r in ROWS:
        (insee, name, dept, postal, lat, lon, alt, resort, top, base, lift_min,
         gva, ski, bc, summ, charm, life, lic, wkw, wks, occ, note) = r
        slug = (name.lower().replace("(", "").replace(")", "").replace("'", " ")
                .replace("é", "e").replace("è", "e").replace("ê", "e").replace("ë", "e")
                .replace("ç", "c").replace("î", "i").replace("ô", "o").replace("â", "a")
                .strip().replace(" ", "-").replace("--", "-"))
        path = OUT / f"{slug}.yaml"
        if path.exists():
            skipped += 1
            continue
        path.write_text(f"""insee_code: "{insee}"
name: "{name.split('(')[0].strip()}"
department: "{dept}"
postal_codes: ["{postal}"]
lat: {lat}
lon: {lon}
village_alt_m: {alt}
resort:
  name: "{resort}"
  top_alt_m: {top}
  base_alt_m: {base}
  lift_drive_min: {lift_min}
geneva_drive_min: {gva}
ratings:
  ski: {ski}
  backcountry: {bc}
  summer: {summ}
  charm: {charm}
  village_life: {life}
  license_risk: {lic}
license_notes: >
  Auto-generated first pass — no Le Meur restrictions researched yet, verify.
  National registration applies.
rental:
  est_weekly_rate_winter_eur: {wkw}
  est_weekly_rate_summer_eur: {wks}
  est_occupancy_weeks: {occ}
  notes: "{note}"
portal_ids: {{}}
notes: >
  AUTO-GENERATED batch entry (2500m+ sweep). INSEE code and ratings need a
  verification pass. {note}
updated_at: "2026-07-18"
""")
        written += 1
    print(f"written {written}, skipped(existing) {skipped}")


if __name__ == "__main__":
    sys.exit(main())
