"""
Boutons de la raquette, à imprimer en 3D : quatre flèches (haut, bas, gauche, droite) et OK.

Chaque bouton traverse son trou de 10 mm dans la face avant et appuie sur le poussoir 6 x 6 mm
(SW_PUSH_6mm) de la carte. Une collerette conique, sous la face avant, le retient
et le centre dans son trou ; le poussoir le maintient en place par en dessous.

Cotes reprises de boitier_raquette.scad et de l'assemblage boitier_raquette_assemblage.FCStd
(repère de l'assemblage : carte posée sur les entretoises, dessus de la carte à Z = 9,1).

Usage : freecadcmd boutons_raquette.py   ->  boitier_raquette_boutons.stl (les 5 boutons, à plat
sur le plateau, tête en bas : aucun support nécessaire).
Depuis FreeCAD, boutons_en_place() donne les 5 boutons à leur place dans l'assemblage.
"""

import os
import sys

import FreeCAD as App
import Part

# Face avant (boitier_raquette.scad : base_h = 16, top_h = 14, wall = 2.5)
PLAQUE_BAS = 27.5          # dessous de la face avant
PLAQUE_HAUT = 30.0         # dessus de la face avant
TROU_D = 10.0              # trous des boutons

# Poussoirs 6 x 6 mm de 4,3 mm de haut, ceux de la carte. Avec des poussoirs plus hauts (5 mm,
# 7 mm...), changer HAUTEUR_POUSSOIR et relancer le script : sinon les boutons restent enfoncés.
DESSUS_CARTE = 9.1         # 2,5 (fond) + 5 (entretoises) + 1,6 (carte)
HAUTEUR_POUSSOIR = 4.3     # du dessus de la carte au sommet du plongeur
POUSSOIR_HAUT = DESSUS_CARTE + HAUTEUR_POUSSOIR

# Centres des trous : ENTER en (cx + 3,25 ; wall + clearance + 27,75), pas de 15 mm
CX = (105 + 2 * 1.5 + 2 * 2.5) / 2.0
ENTER = (CX + 3.25, 2.5 + 1.5 + 27.75)
PAS = 15.0
BOUTONS = {
    "HAUT": (ENTER[0], ENTER[1] + PAS),
    "GAUCHE": (ENTER[0] - PAS, ENTER[1]),
    "OK": ENTER,
    "DROITE": (ENTER[0] + PAS, ENTER[1]),
    "BAS": (ENTER[0], ENTER[1] - PAS),
}

# Bouton
JEU_RADIAL = 0.3           # tête de 9,4 mm dans le trou de 10 mm
SAILLIE = 2.0              # hauteur de la tête au-dessus de la face avant
CHANFREIN = 0.5            # arête du dessus de la tête
COLLERETTE_D = 13.2        # collerette sous la face avant (1,8 mm d'écart entre deux boutons)
COLLERETTE_E = 0.8         # partie cylindrique de la collerette, sous le cône à 45°
TIGE_D = 5.0
POINTE_D = 3.2             # bout fin : reste à 2,1 mm de l'axe, à l'écart des plots du poussoir
POINTE_L = 1.5
JEU_POUSSOIR = 0.1         # au repos, entre la pointe et le plongeur
RAINURE = (2.0, 2.8, 0.5)  # bouton OK : anneau creusé sur le dessus (rayon int., rayon ext., profondeur)


def bouton(ok=False):
    """Un bouton au repos, axe en (0, 0), Z = 0 au dessous de la face avant.
    Au repos, le cône de la collerette s'appuie sur le bord du trou (diamètre 10 à Z = 0)."""
    r_tete = TROU_D / 2 - JEU_RADIAL
    haut = (PLAQUE_HAUT - PLAQUE_BAS) + SAILLIE
    bas = (POUSSOIR_HAUT + JEU_POUSSOIR) - PLAQUE_BAS          # bout de la pointe (négatif)
    z_cone = TROU_D / 2 - r_tete                                # le cône rejoint la tête à Z = 0,3
    z_coll = -(COLLERETTE_D / 2 - TROU_D / 2)                   # bas du cône, 45°
    # Profil de révolution, du bout de la pointe au dessus de la tête
    pts = [(0, bas), (POINTE_D / 2, bas), (POINTE_D / 2, bas + POINTE_L), (TIGE_D / 2, bas + POINTE_L),
           (TIGE_D / 2, z_coll - COLLERETTE_E), (COLLERETTE_D / 2, z_coll - COLLERETTE_E),
           (COLLERETTE_D / 2, z_coll), (r_tete, z_cone), (r_tete, haut - CHANFREIN),
           (r_tete - CHANFREIN, haut), (0, haut)]
    poly = Part.makePolygon([App.Vector(x, 0, z) for x, z in pts] + [App.Vector(0, 0, bas)])
    solide = Part.Face(poly).revolve(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 360)
    solide = Part.Solid(Part.Shell(solide.Faces)) if not solide.isValid() else solide
    if ok:
        r_int, r_ext, prof = RAINURE
        anneau = Part.makeCylinder(r_ext, prof + 0.1, App.Vector(0, 0, haut - prof)) \
            .cut(Part.makeCylinder(r_int, prof + 0.1, App.Vector(0, 0, haut - prof)))
        solide = solide.cut(anneau)
    return solide.removeSplitter()


def boutons_en_place():
    """Les 5 boutons au repos, dans le repère de l'assemblage."""
    return {nom: bouton(nom == "OK").translated(App.Vector(x, y, PLAQUE_BAS))
            for nom, (x, y) in BOUTONS.items()}


def plateau():
    """Les 5 boutons tête en bas, côte à côte, posés sur Z = 0 : prêts à imprimer."""
    pieces = []
    for k, nom in enumerate(BOUTONS):
        b = bouton(nom == "OK")
        b.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), 180)
        b.translate(App.Vector(k * (COLLERETTE_D + 4), 0, -b.BoundBox.ZMin))
        pieces.append(b)
    return Part.makeCompound(pieces)


def exporter_stl(chemin):
    import MeshPart
    maillage = MeshPart.meshFromShape(Shape=plateau(), LinearDeflection=0.01, AngularDeflection=0.1)
    maillage.write(chemin)
    return maillage


# freecadcmd donne au script son nom de fichier, pas "__main__" : on regarde la ligne de commande
if __name__ == "__main__" or any(a.endswith("boutons_raquette.py") for a in sys.argv):
    ici = os.path.dirname(os.path.abspath(__file__))
    m = exporter_stl(os.path.join(ici, "boitier_raquette_boutons.stl"))
    print(f"boitier_raquette_boutons.stl : {m.CountFacets} facettes")
