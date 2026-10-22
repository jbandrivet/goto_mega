#!/usr/bin/env python3
"""
Fichiers de fabrication des trois cartes, à relancer après chaque modification d'un PCB routé.

Pour chaque carte (monture, monture_ext, raquette), écrit dans pcb/fabrication/ :
- <carte>_gerber.zip      : Gerber et perçages, à envoyer tel quel au fabricant (JLCPCB, PCBWay...)
- <carte>_composants.csv  : liste des composants, regroupés par valeur et empreinte
et, à côté du PCB, ses vues 3D : <carte>_3d.png (dessus) et <carte>_perspective.jpg.

Il faut KiCad (kicad-cli et le module pcbnew). Le site du projet reprend ces fichiers.
"""

import csv
import io
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from collections import defaultdict
from pathlib import Path

import pcbnew

ICI = Path(__file__).resolve().parent
SORTIE = ICI / "fabrication"
CARTES = ("monture", "monture_ext", "raquette")
COUCHES = "F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts"
DATE_ZIP = (2026, 1, 1, 0, 0, 0)     # date fixe : le zip ne change que si les Gerber changent

# Pièces mécaniques : leur valeur dans le PCB dit à quoi elles servent (« MOTEUR AZ », « HAUT »...),
# la liste des composants dit quoi acheter. Les autres gardent leur valeur (100uF 63V, 74ACT125...).
DESIGNATIONS = {
    "TerminalBlock_Phoenix_MKDS-1,5-4-5.08_1x04_P5.08mm_Horizontal": "Bornier à vis 4 points, pas 5,08 mm",
    "TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal": "Bornier à vis 2 points, pas 5,08 mm",
    "TerminalBlock_Phoenix_PT-1,5-4-3.5-H_1x04_P3.50mm_Horizontal": "Bornier à vis 4 points, pas 3,5 mm",
    "PinHeader_1x04_P2.54mm_Vertical": "Barrette mâle 1 x 4, pas 2,54 mm",
    "PinSocket_1x08_P2.54mm_Vertical": "Barrette femelle 1 x 8, pas 2,54 mm (support StepStick)",
    "SW_PUSH_6mm": "Bouton poussoir 6 x 6 mm, 4,3 mm de haut (boutons imprimés calés dessus)",
    "BarrelJack_Horizontal": "Jack d'alimentation 12 V",
    "Buzzer_12x9.5RM7.6": "Buzzer 12 mm",
    "R_Array_SIP5": "Réseau de résistances 4 x 10 kOhm, commun broche 1 (SIP5)",
    "Fuse_Littelfuse_372_D8.50mm": "Fusible TR5 temporisé 4 A (Littelfuse 372) et son support",
    "TO-220-3_Vertical": "Double diode Schottky MBR20100CT, 100 V 2 x 10 A, cathode commune (TO-220)",
    "TO-92_Inline_Wide": "Transistor NPN PN2222A (TO-92, brochage E B C)",
    "D_DO-35_SOD27_P2.54mm_Vertical_AnodeUp": "Diode 1N4148",
    "SOT-23_Handsoldering": "MOSFET canal N BSS138 (SOT-23)",
}


def designation_achat(empreinte, valeur):
    if empreinte.startswith("R_Axial"):
        return f"Résistance {valeur[:-1] + ' kOhm' if valeur.endswith('k') else valeur + ' Ohm'}, 1/4 W"
    return DESIGNATIONS.get(empreinte, valeur)


def kicad_cli(*args):
    subprocess.run(["kicad-cli", *args], check=True, stdout=subprocess.DEVNULL)


def gerbers(pcb, nom):
    with tempfile.TemporaryDirectory() as tmp:
        kicad_cli("pcb", "export", "gerbers", "--layers", COUCHES, "-o", tmp, str(pcb))
        kicad_cli("pcb", "export", "drill", "--format", "excellon", "--excellon-separate-th",
                  "--generate-map", "--map-format", "gerberx2", "-o", tmp + "/", str(pcb))
        with zipfile.ZipFile(SORTIE / f"{nom}_gerber.zip", "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted(Path(tmp).iterdir()):
                # la date de création écrite par KiCad changerait le zip à chaque passage
                texte = re.sub(r"(?m)^.*(CreationDate|TF\.CreationDate|; DRILL file .* date ).*\n", "",
                               f.read_text(errors="replace"))
                info = zipfile.ZipInfo(f.name, DATE_ZIP)
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, texte)


def composants(pcb, nom):
    """Regroupe par (valeur, empreinte). Les trous de fixation et les ponts à souder ne sont pas des
    composants à acheter : KiCad les marque « exclu de la nomenclature » ou « carte seulement »."""
    board = pcbnew.LoadBoard(str(pcb))
    groupes = defaultdict(list)
    for f in board.GetFootprints():
        if f.GetAttributes() & (pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_BOARD_ONLY) \
                or f.GetReference().startswith(("H", "JP_")):
            continue
        empreinte = str(f.GetFPID().GetLibItemName())
        groupes[(designation_achat(empreinte, f.GetValue()), empreinte)].append(f.GetReference())
    tampon = io.StringIO()
    w = csv.writer(tampon, delimiter=";", lineterminator="\n")
    w.writerow(("Désignation", "Quantité", "Repères", "Empreinte"))
    for (designation, empreinte), refs in sorted(groupes.items()):
        w.writerow((designation, len(refs), " ".join(sorted(refs)), empreinte))
    (SORTIE / f"{nom}_composants.csv").write_text(tampon.getvalue(), encoding="utf-8")


def vues_3d(pcb, nom):
    kicad_cli("pcb", "render", "-w", "1600", "-h", "1200", "--quality", "high",
              "-o", str(pcb.with_name(f"{nom}_3d.png")), str(pcb))
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "p.png"
        kicad_cli("pcb", "render", "-w", "1600", "-h", "1200", "--quality", "high", "--perspective",
                  "--rotate", "-40,0,-25", "--zoom", "0.9", "--background", "opaque", "-o", str(png), str(pcb))
        from PIL import Image
        Image.open(png).convert("RGB").resize((1200, 900), Image.LANCZOS) \
            .save(pcb.with_name(f"{nom}_perspective.jpg"), quality=85, optimize=True)


if __name__ == "__main__":
    SORTIE.mkdir(exist_ok=True)
    cartes = sys.argv[1:] or CARTES
    for nom in cartes:
        pcb = ICI / nom / f"{nom}.kicad_pcb"
        gerbers(pcb, nom)
        composants(pcb, nom)
        vues_3d(pcb, nom)
        print(f"[OK] {nom}")
    sys.stdout.flush()
    os._exit(0)      # pcbnew plante parfois à la fermeture de Python
