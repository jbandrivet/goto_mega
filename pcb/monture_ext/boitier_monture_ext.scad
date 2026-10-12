// ============================================================================
// BOITIER PARAMÉTRIQUE POUR MONTURE GOTO-ANDRIVET - CARTE DRIVERS EXTERNES
// Conçu pour impression 3D (PLA / PETG / ABS)
// ============================================================================

$fn = 40;

// Dimensions du PCB
pcb_w = 150;
pcb_h = 110;
pcb_thick = 1.6;

// Paramètres du boîtier
wall = 2.5;         // Épaisseur des parois
clearance = 1.5;    // Jeu autour du PCB
standoff_h = 5.0;   // Hauteur des entretoises sous le PCB
box_h = 35.0;       // Hauteur totale du boîtier (pas de modules drivers : 35mm dégagent le TO-220 LM2596)
lid_thick = 2.5;    // Épaisseur du couvercle

inner_w = pcb_w + 2 * clearance;
inner_h = pcb_h + 2 * clearance;
outer_w = inner_w + 2 * wall;
outer_h = inner_h + 2 * wall;

// Positions des 4 trous de fixation PCB M3 (relatifs au coin inférieur gauche interne)
pcb_holes = [
    [clearance + 5, clearance + 5],
    [clearance + pcb_w - 5, clearance + 5],
    [clearance + 5, clearance + pcb_h - 5],
    [clearance + pcb_w - 5, clearance + pcb_h - 5]
];

// ----------------------------------------------------------------------------
// 1. CORPS INFÉRIEUR (BASE DU BOÎTIER)
// ----------------------------------------------------------------------------
module boitier_base() {
    difference() {
        union() {
            difference() {
        // Volume extérieur avec coins arrondis
        hull() {
            translate([3, 3, 0]) cylinder(r=3, h=box_h);
            translate([outer_w - 3, 3, 0]) cylinder(r=3, h=box_h);
            translate([3, outer_h - 3, 0]) cylinder(r=3, h=box_h);
            translate([outer_w - 3, outer_h - 3, 0]) cylinder(r=3, h=box_h);
        }

        // Évidement intérieur
        translate([wall, wall, wall])
            cube([inner_w, inner_h, box_h + 1]);

        // --- DÉCOUPES DE PASSAGE DES CONNECTEURS EXTÉRIEURS (PARFAITEMENT CENTRÉES SUR LE PCB) ---

        // Repère : Y_scad = 110 - Y_kicad. Les empreintes KiCad ont leur origine sur la pastille 1,
        // pas au centre du composant : toujours centrer une découpe sur le CENTRE du corps.

        // A. 4 Ouvertures sur le bord haut (Y = max), une par axe : bornier puissance J_VM (5,08 mm)
        //    et bornier signaux J_SIG (3,5 mm) côte à côte, corps de cx-13,67 à cx+13,67
        //    (cx = 27.5 / 59.17 / 90.83 / 122.5 dans build_kicad_pcbs.py, EXT_AXIS_X). Jeu 0,75 mm.
        axis_x = [27.5, 59.17, 90.83, 122.5];
        for (ax = axis_x) {
            translate([wall + clearance + ax - 14.42, outer_h - wall - 1, wall + standoff_h])
                cube([28.84, wall + 2, 14]);
        }

        // B. (Trou USB-B supprimé à la demande de l'utilisateur - pas de connecteur USB-B sur le PCB)

        // C. Flanc gauche (X = 0) : Entrée 36V, jack 12V et câble micro-USB du Teensy
        // Bornier 36V (pastilles Y_kicad 55.0 / 60.08, corps centré Y_kicad ~57.3 -> Y_scad 52.7)
        translate([-1, wall + clearance + 52.7 - 7, wall + standoff_h])
            cube([wall + 2, 14, 12]);
        // Jack 12V (corps centré Y_kicad 40.0 -> Y_scad 70.0). Le jack dépasse du bord du PCB de 1,7 mm :
        // encoche ouverte jusqu'en haut pour pouvoir descendre la carte dans le boîtier
        translate([-1, wall + clearance + 70.0 - 6, wall + standoff_h])
            cube([wall + 2, 12, box_h - wall - standoff_h + 1]);
        // Câble micro-USB du Teensy (USB à Y_kicad 70.0 -> Y_scad 40.0), de la face du PCB
        // jusqu'au-dessus d'un Teensy monté sur supports femelles
        translate([-1, wall + clearance + 40.0 - 6.5, wall + standoff_h + pcb_thick])
            cube([wall + 2, 13, 18.4]);

        // D. Flanc droit (X = max) : Raquette, GPS et port série PC
        // Connecteur Raquette (pastilles Y_kicad 41.19..48.81, centre 45.0 -> Y_scad 65.0)
        translate([outer_w - wall - 1, wall + clearance + 65.0 - 8, wall + standoff_h])
            cube([wall + 2, 16, 12]);
        // Connecteur GPS (pastilles Y_kicad 61.19..68.81, centre 65.0 -> Y_scad 45.0)
        translate([outer_w - wall - 1, wall + clearance + 45.0 - 8, wall + standoff_h])
            cube([wall + 2, 16, 12]);
        // Connecteur PC SERIAL (pastilles Y_kicad 16.0..23.62, centre 19.81 -> Y_scad 90.19)
        translate([outer_w - wall - 1, wall + clearance + 90.19 - 8, wall + standoff_h])
            cube([wall + 2, 16, 12]);

        // E. Trous de vis de fixation du couvercle dans les 4 coins
        corners = [
        [wall + 1.5, wall + 1.5],
        [outer_w - wall - 1.5, wall + 1.5],
        [wall + 1.5, outer_h - wall - 1.5],
        [outer_w - wall - 1.5, outer_h - wall - 1.5]
    ];
        for (c = corners) {
            translate([c[0], c[1], box_h - 12])
                cylinder(d=2.8, h=15); // Trou pour vis M3 taraudée
        }
    }

    // Piliers / Entretoises de support pour visser le PCB
    for (p = pcb_holes) {
        translate([wall + p[0], wall + p[1], wall - 0.2]) {
            difference() {
                cylinder(d=7.0, h=standoff_h + 0.2);
                translate([0, 0, -0.1])
                    cylinder(d=2.8, h=standoff_h + 1); // Trou vis PCB M3
            }
        }
    }

    // Renforts de coins pour les vis de fermeture du couvercle
    corners = [
        [wall + 1.5, wall + 1.5],
        [outer_w - wall - 1.5, wall + 1.5],
        [wall + 1.5, outer_h - wall - 1.5],
        [outer_w - wall - 1.5, outer_h - wall - 1.5]
    ];
    for (c = corners) {
        translate([c[0], c[1], wall - 0.2]) {
            difference() {
                cylinder(d=6.0, h=box_h - wall + 0.2);
                translate([0, 0, box_h - wall - 12])
                    cylinder(d=2.8, h=13);
            }
        }
    }
        }
        // Dégagement garanti des coins pour insertion du PCB
        translate([wall + clearance - 0.5, wall + clearance - 0.5, wall + standoff_h])
            cube([pcb_w + 1.0, pcb_h + 1.0, pcb_thick + 1.5]);
    }
}

// ----------------------------------------------------------------------------
// 2. COUVERCLE SUPÉRIEUR (sans grille : pas de drivers dans le boîtier)
// ----------------------------------------------------------------------------
module boitier_couvercle() {
    difference() {
        union() {
            // Plaque du couvercle
            hull() {
                translate([3, 3, 0]) cylinder(r=3, h=lid_thick);
                translate([outer_w - 3, 3, 0]) cylinder(r=3, h=lid_thick);
                translate([3, outer_h - 3, 0]) cylinder(r=3, h=lid_thick);
                translate([outer_w - 3, outer_h - 3, 0]) cylinder(r=3, h=lid_thick);
            }
            // Rebord d'emboîtement intérieur
            translate([wall + 0.3, wall + 0.3, lid_thick])
                difference() {
                    cube([inner_w - 0.6, inner_h - 0.6, 2.5]);
                    translate([2, 2, -0.5])
                        cube([inner_w - 4.6, inner_h - 4.6, 4]);
                }
        }

        // Trous de passage de vis M3 chanfreinés dans les 4 coins
        corners = [
        [wall + 1.5, wall + 1.5],
        [outer_w - wall - 1.5, wall + 1.5],
        [wall + 1.5, outer_h - wall - 1.5],
        [outer_w - wall - 1.5, outer_h - wall - 1.5]
    ];
        for (c = corners) {
            translate([c[0], c[1], -1]) {
                cylinder(d=3.4, h=lid_thick + 5);
                cylinder(d1=6.5, d2=3.4, h=2.5); // Fraisage tête de vis
            }
        }

    }
}

// ----------------------------------------------------------------------------
// CHOIX DU MODELE A AFFICHER / RENDRE
// Passer 'mode' à "base", "couvercle", ou "ensemble"
// ----------------------------------------------------------------------------
mode = "ensemble";

if (mode == "base") {
    boitier_base();
} else if (mode == "couvercle") {
    boitier_couvercle();
} else {
    // Vue assemblée éclatée
    color([0.2, 0.2, 0.2]) boitier_base();
    color([0.3, 0.5, 0.8, 0.85])
        translate([0, 0, box_h + 15])
            boitier_couvercle();
}
