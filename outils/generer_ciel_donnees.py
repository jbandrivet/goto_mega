#!/usr/bin/env python3
"""Génère ciel_donnees.py (étoiles, noms et lignes de constellations) pour la carte du ciel.

Sources téléchargées par ce script :
  - Yale Bright Star Catalogue, 5e éd. (Hoffleit & Warren 1991), CDS VizieR V/50 : positions
    J2000, magnitude V et indice B-V des étoiles jusqu'à la magnitude 6,5 ;
  - Hipparcos (ESA 1997), CDS VizieR I/239 : positions des étoiles qui portent les lignes
    de constellations et les noms propres, ramenées à l'époque J2000 par leur mouvement propre ;
  - Stellarium, culture du ciel « modern » (CC BY-SA 4.0) : lignes des 88 constellations
    et noms propres des étoiles ;
  - OpenNGC (Mattia Verga, CC BY-SA 4.0) : objets NGC et IC, plus l'addendum (Messier et
    Caldwell hors NGC/IC) : positions J2000, type, magnitude, taille et angle de position.

Usage : python3 outils/generer_ciel_donnees.py  (écrit ciel_donnees.py à la racine du dépôt)
"""
import csv, io, json, math, re, sys, urllib.parse, urllib.request
from pathlib import Path

TAP = "https://tapvizier.cds.unistra.fr/TAPVizieR/tap/sync"
STELLARIUM = "https://raw.githubusercontent.com/Stellarium/stellarium/master/skycultures/modern/index.json"
MAG_MAX = 6.5
OPENNGC = "https://raw.githubusercontent.com/mattiaverga/OpenNGC/master/database_files/{}.csv"
DSO_MAG_MAX = 12.0
OUT = Path(__file__).resolve().parent.parent / "ciel_donnees.py"

# Catalogue Caldwell (Patrick Moore, 1995) : numéro -> objet OpenNGC
CALDWELL = {
    1: "NGC0188", 2: "NGC0040", 3: "NGC4236", 4: "NGC7023", 5: "IC0342", 6: "NGC6543", 7: "NGC2403",
    8: "NGC0559", 9: "C009", 10: "NGC0663", 11: "NGC7635", 12: "NGC6946", 13: "NGC0457", 14: "C014",
    15: "NGC6826", 16: "NGC7243", 17: "NGC0147", 18: "NGC0185", 19: "IC5146", 20: "NGC7000",
    21: "NGC4449", 22: "NGC7662", 23: "NGC0891", 24: "NGC1275", 25: "NGC2419", 26: "NGC4244",
    27: "NGC6888", 28: "NGC0752", 29: "NGC5005", 30: "NGC7331", 31: "IC0405", 32: "NGC4631",
    33: "NGC6992", 34: "NGC6960", 35: "NGC4889", 36: "NGC4559", 37: "NGC6882", 38: "NGC4565",
    39: "NGC2392", 40: "NGC3626", 41: "C041", 42: "NGC7006", 43: "NGC7814", 44: "NGC7479",
    45: "NGC5248", 46: "NGC2261", 47: "NGC6934", 48: "NGC2775", 49: "NGC2237", 50: "NGC2239",
    51: "IC1613", 52: "NGC4697", 53: "NGC3115", 54: "NGC2506", 55: "NGC7009", 56: "NGC0246",
    57: "NGC6822", 58: "NGC2360", 59: "NGC3242", 60: "NGC4038", 61: "NGC4039", 62: "NGC0247",
    63: "NGC7293", 64: "NGC2362", 65: "NGC0253", 66: "NGC5694", 67: "NGC1097", 68: "NGC6729",
    69: "NGC6302", 70: "NGC0300", 71: "NGC2477", 72: "NGC0055", 73: "NGC1851", 74: "NGC3132",
    75: "NGC6124", 76: "NGC6231", 77: "NGC5128", 78: "NGC6541", 79: "NGC3201", 80: "NGC5139",
    81: "NGC6352", 82: "NGC6193", 83: "NGC4945", 84: "NGC5286", 85: "IC2391", 86: "NGC6397",
    87: "NGC1261", 88: "NGC5823", 89: "NGC6087", 90: "NGC2867", 91: "NGC3532", 92: "NGC3372",
    93: "NGC6752", 94: "NGC4755", 95: "NGC6025", 96: "NGC2516", 97: "NGC3766", 98: "NGC4609",
    99: "C099", 100: "IC2944", 101: "NGC6744", 102: "IC2602", 103: "NGC2070", 104: "NGC0362",
    105: "NGC4833", 106: "NGC0104", 107: "NGC6101", 108: "NGC4372", 109: "NGC3195",
}

# Noms français usuels (désignation OpenNGC -> nom)
NOMS_FR = {
    "NGC1952": "Nébuleuse du Crabe", "NGC6405": "Amas du Papillon", "NGC6475": "Amas de Ptolémée",
    "NGC6523": "Nébuleuse de la Lagune", "NGC6705": "Amas du Canard sauvage", "NGC6205": "Grand Amas d'Hercule",
    "NGC6611": "Nébuleuse de l'Aigle", "NGC6618": "Nébuleuse Oméga", "NGC6514": "Nébuleuse Trifide",
    "IC4715": "Petit Nuage du Sagittaire", "NGC6853": "Nébuleuse de l'Haltère", "NGC0224": "Galaxie d'Andromède",
    "NGC0598": "Galaxie du Triangle", "NGC1976": "Grande Nébuleuse d'Orion", "NGC2632": "Amas de la Ruche",
    "NGC5194": "Galaxie du Tourbillon", "NGC6720": "Nébuleuse de l'Anneau", "NGC5055": "Galaxie du Tournesol",
    "NGC4826": "Galaxie de l'Œil noir", "NGC0650": "Petite Haltère", "NGC3031": "Galaxie de Bode",
    "NGC3034": "Galaxie du Cigare", "NGC5236": "Galaxie du Moulinet austral", "NGC4486": "Virgo A",
    "NGC3587": "Nébuleuse du Hibou", "NGC5457": "Galaxie du Moulinet", "NGC5866": "Galaxie du Fuseau",
    "NGC4594": "Galaxie du Sombrero", "NGC0104": "47 Toucan", "NGC0253": "Galaxie du Sculpteur",
    "NGC0457": "Amas du Hibou", "NGC0869": "Double Amas (h Persée)", "NGC0884": "Double Amas (χ Persée)",
    "NGC0891": "Galaxie de l'Aiguille d'argent", "NGC1316": "Fornax A", "NGC1499": "Nébuleuse Californie",
    "NGC2024": "Nébuleuse de la Flamme", "NGC2237": "Nébuleuse de la Rosette", "NGC2244": "Amas de la Rosette",
    "NGC2264": "Amas de l'Arbre de Noël", "NGC2360": "Amas de Caroline", "NGC2392": "Nébuleuse de l'Esquimau",
    "NGC2736": "Nébuleuse du Crayon", "NGC3115": "Galaxie du Fuseau", "NGC3132": "Nébuleuse des Huit Éclats",
    "NGC3242": "Fantôme de Jupiter", "NGC3372": "Nébuleuse de la Carène", "NGC3532": "Amas du Puits aux souhaits",
    "NGC3918": "Planétaire bleue", "NGC4038": "Galaxies des Antennes", "NGC4039": "Galaxies des Antennes",
    "NGC4565": "Galaxie de l'Aiguille", "NGC4631": "Galaxie de la Baleine", "NGC4755": "Boîte à bijoux",
    "NGC5128": "Centaurus A", "NGC5139": "Oméga du Centaure", "NGC6543": "Nébuleuse de l'Œil de chat",
    "NGC6826": "Nébuleuse clignotante", "NGC6888": "Nébuleuse du Croissant", "NGC6946": "Galaxie du Feu d'artifice",
    "NGC6960": "Dentelles du Cygne (ouest)", "NGC6992": "Dentelles du Cygne (est)", "NGC7000": "Nébuleuse Amérique du Nord",
    "NGC7009": "Nébuleuse Saturne", "NGC7293": "Nébuleuse de l'Hélice", "NGC7662": "Nébuleuse du Flocon de neige",
    "NGC7789": "Rose de Caroline", "IC0405": "Nébuleuse de l'Étoile flamboyante", "IC0434": "Nébuleuse de la Tête de cheval",
    "IC1396": "Nébuleuse de la Trompe d'éléphant", "IC1805": "Nébuleuse du Cœur", "IC1848": "Nébuleuse de l'Âme",
    "IC2391": "Amas d'Omicron des Voiles", "IC2602": "Pléiades du Sud", "IC2944": "Amas de λ Centaure",
    "IC5146": "Nébuleuse du Cocon", "NGC2070": "Nébuleuse de la Tarentule", "NGC7635": "Nébuleuse de la Bulle",
    "NGC7023": "Nébuleuse de l'Iris", "NGC2261": "Nébuleuse variable de Hubble", "NGC6302": "Nébuleuse de l'Insecte",
    "NGC6992": "Dentelles du Cygne (est)", "NGC0292": "Petit Nuage de Magellan", "NGC1435": "Nébuleuse de Mérope",
    "NGC2068": "Nébuleuse M78", "NGC6720": "Nébuleuse de l'Anneau", "NGC7027": "Nébuleuse du Bijou",
    "C009": "Nébuleuse de la Caverne", "C014": "Double Amas de Persée", "C041": "Hyades", "C099": "Sac à Charbon",
    "ESO056-115": "Grand Nuage de Magellan", "Cl399": "Amas du Cintre", "B033": "Tête de cheval (nébuleuse obscure)",
}

# Cas particuliers d'OpenNGC
MESSIER_EXTRA = {"NGC5866": 102}          # M102 : identification discutée, NGC 5866 par convention
DESIGNATION = {"NGC2239": "NGC 2244",     # OpenNGC range NGC 2244 (amas de la Rosette, C50) en doublon de NGC 2239
               "NGC6882": "NGC 6885"}     # et NGC 6885 (C37) en doublon de NGC 6882 : on garde le nom usuel
MAG = {"NGC6882": 5.7}                    # magnitude de NGC 6885 selon le catalogue Caldwell (OpenNGC : 14,1)
TYPES_MESSIER = {"**": "DS", "Other": "Ast"}   # M40 (étoile double), M73 (astérisme)

# Types OpenNGC -> types de l'appli (les autres, étoiles, doublons, objets inexistants, sont ignorés)
TYPES = {"G": "Gal", "GPair": "Gal", "GTrpl": "Gal", "GGroup": "Gal", "OCl": "OC", "GCl": "GC", "PN": "PN",
         "Neb": "Neb", "HII": "Neb", "EmN": "Neb", "RfN": "Neb", "Cl+N": "Neb", "DrkN": "Neb", "SNR": "SNR",
         "*Ass": "Ast"}

GREEK = {"Alp": "α", "Bet": "β", "Gam": "γ", "Del": "δ", "Eps": "ε", "Zet": "ζ", "Eta": "η", "The": "θ",
         "Iot": "ι", "Kap": "κ", "Lam": "λ", "Mu": "μ", "Nu": "ν", "Xi": "ξ", "Omi": "ο", "Pi": "π",
         "Rho": "ρ", "Sig": "σ", "Tau": "τ", "Ups": "υ", "Phi": "φ", "Chi": "χ", "Psi": "ψ", "Ome": "ω"}
SUP = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")

# Noms français des 88 constellations (abréviation IAU -> nom)
FR = {
    "And": "Andromède", "Ant": "Machine pneumatique", "Aps": "Oiseau de paradis", "Aqr": "Verseau",
    "Aql": "Aigle", "Ara": "Autel", "Ari": "Bélier", "Aur": "Cocher", "Boo": "Bouvier", "Cae": "Burin",
    "Cam": "Girafe", "Cnc": "Cancer", "CVn": "Chiens de chasse", "CMa": "Grand Chien", "CMi": "Petit Chien",
    "Cap": "Capricorne", "Car": "Carène", "Cas": "Cassiopée", "Cen": "Centaure", "Cep": "Céphée",
    "Cet": "Baleine", "Cha": "Caméléon", "Cir": "Compas", "Col": "Colombe", "Com": "Chevelure de Bérénice",
    "CrA": "Couronne australe", "CrB": "Couronne boréale", "Crv": "Corbeau", "Crt": "Coupe",
    "Cru": "Croix du Sud", "Cyg": "Cygne", "Del": "Dauphin", "Dor": "Dorade", "Dra": "Dragon",
    "Equ": "Petit Cheval", "Eri": "Éridan", "For": "Fourneau", "Gem": "Gémeaux", "Gru": "Grue",
    "Her": "Hercule", "Hor": "Horloge", "Hya": "Hydre", "Hyi": "Hydre mâle", "Ind": "Indien",
    "Lac": "Lézard", "Leo": "Lion", "LMi": "Petit Lion", "Lep": "Lièvre", "Lib": "Balance", "Lup": "Loup",
    "Lyn": "Lynx", "Lyr": "Lyre", "Men": "Table", "Mic": "Microscope", "Mon": "Licorne", "Mus": "Mouche",
    "Nor": "Règle", "Oct": "Octant", "Oph": "Ophiuchus", "Ori": "Orion", "Pav": "Paon", "Peg": "Pégase",
    "Per": "Persée", "Phe": "Phénix", "Pic": "Peintre", "Psc": "Poissons", "PsA": "Poisson austral",
    "Pup": "Poupe", "Pyx": "Boussole", "Ret": "Réticule", "Sge": "Flèche", "Sgr": "Sagittaire",
    "Sco": "Scorpion", "Scl": "Sculpteur", "Sct": "Écu de Sobieski", "Ser": "Serpent", "Sex": "Sextant",
    "Tau": "Taureau", "Tel": "Télescope", "Tri": "Triangle", "TrA": "Triangle austral", "Tuc": "Toucan",
    "UMa": "Grande Ourse", "UMi": "Petite Ourse", "Vel": "Voiles", "Vir": "Vierge", "Vol": "Poisson volant",
    "Vul": "Petit Renard",
}


def tap(query):
    data = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": query}).encode()
    with urllib.request.urlopen(urllib.request.Request(TAP, data=data), timeout=180) as r:
        return list(csv.DictReader(io.StringIO(r.read().decode("utf-8"))))


def bayer(name):
    """« 92Alp Cet » -> « α Cet », « 13    Aur » -> « 13 Aur », vide si rien."""
    m = re.match(r"^\s*(\d*)\s*([A-Z][a-z]{1,2})?(\d)?\s*([A-Z][A-Za-z]{2})?\s*$", name or "")
    if not m or not m.group(4):
        return ""
    flam, grk, idx, con = m.groups()
    if grk and grk in GREEK:
        return f"{GREEK[grk]}{(idx or '').translate(SUP)} {con}"
    return f"{flam} {con}" if flam else ""


def designation(name):
    """« NGC0224 » -> « NGC 224 », « IC0434 » -> « IC 434 », autres inchangés."""
    m = re.match(r"^(NGC|IC)0*(\d+)(.*)$", name)
    return f"{m.group(1)} {m.group(2)}{m.group(3)}" if m else name


def sexa(v, hours):
    sign = -1 if v.strip().startswith("-") else 1
    a, b, c = (float(x) for x in v.replace("+", "").replace("-", "").split(":"))
    return sign * (a + b / 60 + c / 3600)


def openngc():
    rows = []
    for f in ("NGC", "addendum"):
        with urllib.request.urlopen(OPENNGC.format(f), timeout=180) as r:
            rows += list(csv.DictReader(io.StringIO(r.read().decode("utf-8")), delimiter=";"))
    return rows


def main():
    print("BSC5 (VizieR V/50)…")
    bsc = tap('SELECT HR, Name, HD, RAJ2000, DEJ2000, Vmag, "B-V" FROM "V/50/catalog" '
              f'WHERE Vmag IS NOT NULL AND RAJ2000 IS NOT NULL AND Vmag <= {MAG_MAX}')
    print(len(bsc), "étoiles")
    print("Stellarium (culture « modern »)…")
    with urllib.request.urlopen(STELLARIUM, timeout=120) as r:
        sky = json.load(r)

    hips = set()
    for c in sky["constellations"]:
        for line in c["lines"]:
            hips.update(int(h) for h in line)
    names_hip = {int(k.split()[1]): v[0]["english"] for k, v in sky["common_names"].items() if k.startswith("HIP ")}
    print("Hipparcos (VizieR I/239)…")
    hip_rows = tap('SELECT HIP, HD, Vmag, RAhms, DEdms, RAICRS, DEICRS, pmRA, pmDE FROM "I/239/hip_main" WHERE HIP IN (%s)'
                   % ",".join(map(str, sorted(hips | set(names_hip)))))
    hip = {}
    for r in hip_rows:
        if r["RAICRS"] and r["DEICRS"]:
            ra, dec = float(r["RAICRS"]), float(r["DEICRS"])
        else:   # deux étoiles sans solution astrométrique (ξ UMa, ξ Sco) : position sexagésimale du catalogue
            h, m, sec = map(float, r["RAhms"].split()); d, dm, ds = map(float, r["DEdms"].replace("+", "").split())
            ra = 15 * (h + m / 60 + sec / 3600); dec = math.copysign(abs(d) + dm / 60 + ds / 3600, -1 if r["DEdms"].strip().startswith("-") else 1)
        dt = 2000.0 - 1991.25        # époque Hipparcos J1991.25 -> J2000
        pmra = float(r["pmRA"] or 0) / 3.6e6 / math.cos(math.radians(dec)); pmde = float(r["pmDE"] or 0) / 3.6e6
        hip[int(r["HIP"])] = (((ra + pmra * dt) % 360) / 15.0, dec + pmde * dt, float(r["Vmag"] or 99))
    missing = hips - set(hip)
    if missing:
        sys.exit(f"HIP sans position : {sorted(missing)[:10]}")
    stars = []
    for r in bsc:
        bv = r["B-V"].strip()
        stars.append([float(r["RAJ2000"]) / 15.0, float(r["DEJ2000"]), float(r["Vmag"]),
                      float(bv) if bv else 0.6, "", bayer(r["Name"])])
    # Nom propre -> étoile du BSC la plus proche en position et en magnitude (à moins de 0,1°).
    # Par numéro HD, le nom d'une étoile double tombait parfois sur la compagne faible (Izar).
    for h, nm in names_hip.items():
        ra, dec, vmag = hip[h]
        best, cost = None, 9e9
        for st in stars:
            d = math.degrees(math.acos(max(-1.0, min(1.0,
                math.sin(math.radians(dec)) * math.sin(math.radians(st[1])) +
                math.cos(math.radians(dec)) * math.cos(math.radians(st[1])) * math.cos(math.radians(15 * (ra - st[0])))))))
            if d < 0.1 and d * 10 + abs(st[2] - vmag) < cost:
                best, cost = st, d * 10 + abs(st[2] - vmag)
        if best is not None and not best[4]:
            best[4] = nm
    stars.sort(key=lambda s: s[2])

    consts = []
    for c in sky["constellations"]:
        abbr = c["id"].split()[-1]
        lines = [[(round(hip[int(h)][0], 5), round(hip[int(h)][1], 4)) for h in line] for line in c["lines"]]
        consts.append((abbr, c["common_name"]["native"], FR.get(abbr, c["common_name"]["native"]),
                       c["common_name"].get("english", c["common_name"]["native"]), lines))
    consts.sort()
    assert len(consts) == 88 and all(c[0] in FR for c in consts)

    print("OpenNGC…")
    caldwell_of = {v: k for k, v in CALDWELL.items()}
    dso = []
    for r in openngc():
        name = r["Name"]
        messier = int(r["M"]) if r["M"] else MESSIER_EXTRA.get(name, 0)
        typ = TYPES.get(r["Type"]) or (TYPES_MESSIER.get(r["Type"]) if messier else None)
        if not typ or not r["RA"] or not r["Dec"]:
            continue
        mag = MAG.get(name, next((float(r[k]) for k in ("V-Mag", "B-Mag") if r[k]), None))
        caldwell = caldwell_of.get(name, 0)
        nebula = typ in ("Neb", "SNR", "PN")
        if not (messier or caldwell or (mag is not None and mag <= DSO_MAG_MAX)
                or (mag is None and nebula and not name.startswith(("ESO", "UGC", "PGC")))):
            continue
        common = r["Common names"].split(",")[0].strip() if r["Common names"] else ""
        maj = float(r["MajAx"]) if r["MajAx"] else 0.0
        mnr = float(r["MinAx"]) if r["MinAx"] else maj
        pa = float(r["PosAng"]) if r["PosAng"] else None
        dso.append((DESIGNATION.get(name, designation(name)), round(sexa(r["RA"], True), 5), round(sexa(r["Dec"], False), 4),
                    mag, typ, round(maj, 1), round(mnr, 1), pa, messier, caldwell, NOMS_FR.get(name, ""), common))
    missing = sorted(set(range(1, 111)) - {d[8] for d in dso})
    missing_c = sorted(set(CALDWELL) - {d[9] for d in dso})
    print(f"{len(dso)} objets ; Messier manquants : {missing} ; Caldwell manquants : {missing_c}")
    dso.sort(key=lambda d: (d[0][:3], d[0]))

    with open(OUT, "w", encoding="utf-8") as f:
        f.write('"""Données de la carte du ciel, générées par outils/generer_ciel_donnees.py : ne pas modifier à la main.\n\n'
                "Étoiles : Yale Bright Star Catalogue, 5e éd. (Hoffleit & Warren 1991), via CDS VizieR V/50,\n"
                f"jusqu'à la magnitude {MAG_MAX}. Positions J2000 (heures, degrés), magnitude V, indice B-V.\n"
                "Lignes de constellations et noms propres : Stellarium, culture du ciel « modern »\n"
                "(https://stellarium.org), licence CC BY-SA 4.0 ; extrémités des lignes placées d'après\n"
                "Hipparcos (ESA 1997, CDS VizieR I/239), ramenées à J2000. Noms français des constellations ajoutés.\n"
                "Ciel profond : OpenNGC (Mattia Verga, https://github.com/mattiaverga/OpenNGC), licence CC BY-SA 4.0 ;\n"
                f"objets NGC/IC jusqu'à la magnitude {DSO_MAG_MAX}, nébuleuses, Messier et Caldwell ; noms français ajoutés.\n"
                '"""\n\n')
        f.write("# (ra_h, dec_d, vmag, b_v, nom propre, désignation de Bayer ou de Flamsteed), triées par magnitude\n")
        f.write("STARS = [\n")
        for ra, dec, mag, bv, nm, bay in stars:
            f.write(f"({ra:.5f},{dec:.4f},{mag:.2f},{bv:.2f},{nm!r},{bay!r}),\n")
        f.write("]\n\n# (abréviation IAU, nom latin, nom français, nom anglais, lignes [[(ra_h, dec_d), ...], ...])\n")
        f.write("CONSTELLATIONS = [\n")
        for abbr, latin, fr, en, lines in consts:
            f.write(f"({abbr!r},{latin!r},{fr!r},{en!r},{lines!r}),\n")
        f.write("]\n\n# Ciel profond (OpenNGC) : (désignation, ra_h, dec_d, magnitude ou None, type, grand axe et petit axe en\n"
                "# minutes d'arc, angle de position ou None, numéro Messier, numéro Caldwell, nom français, nom anglais)\n")
        f.write("DSO = [\n")
        for d in dso:
            f.write(repr(d) + ",\n")
        f.write("]\n")
    print(f"{OUT} : {len(stars)} étoiles ({sum(1 for s in stars if s[4])} nommées), {len(consts)} constellations, "
          f"{len(dso)} objets du ciel profond")


if __name__ == "__main__":
    main()
