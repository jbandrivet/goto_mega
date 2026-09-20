// ============================================================================
// BOITIER PARAMÉTRIQUE POUR MONTURE GOTO-ANDRIVET (36V / 4A)
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
box_h = 32.0;       // Hauteur totale interne du boîtier
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

        // --- DÉCOUPES DE PASSAGE DES CONNECTEURS EXTÉRIEURS (PARFAITEMENT CENTRÉES) ---

        // A. 4 Ouvertures Moteurs sur le bord haut (Y = max, centrés à X = 30, 60, 90, 120)
        motor_x = [30, 60, 90, 120];
        for (mx = motor_x) {
            translate([wall + clearance + mx - 11, outer_h - wall - 1, wall + standoff_h])
                cube([22, wall + 2, 14]);
        }

        // B. Bord bas (Y = 0) : Connecteur USB-B Femelle (Parfaitement centré à X = 75.0mm)
        translate([wall + clearance + 75.0 - 7.5, -1, wall + standoff_h])
            cube([15.0, wall + 2, 13.0]);

        // C. Flanc gauche (X = 0) : Entrée 36V (Centré verticalement à Y = 55.0mm)
        translate([-1, wall + clearance + 55.0 - 7, wall + standoff_h])
            cube([wall + 2, 14, 12]);

        // D. Flanc droit (X = max) : Raquette DIN et GPS (Centrés symétriquement autour de Y = 55mm)
        // Connecteur Raquette (Y_kicad = 45mm -> Y_scad = 110 - 45 = 65mm)
        translate([outer_w - wall - 1, wall + clearance + 65.0 - 8, wall + standoff_h])
            cube([wall + 2, 16, 12]);
        // Connecteur GPS (Y_kicad = 65mm -> Y_scad = 110 - 65 = 45mm)
        translate([outer_w - wall - 1, wall + clearance + 45.0 - 8, wall + standoff_h])
            cube([wall + 2, 16, 12]);

        // E. Trous de vis de fixation du couvercle dans les 4 coins
        corners = [
            [wall + 4, wall + 4],
            [outer_w - wall - 4, wall + 4],
            [wall + 4, outer_h - wall - 4],
            [outer_w - wall - 4, outer_h - wall - 4]
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
        [wall + 4, wall + 4],
        [outer_w - wall - 4, wall + 4],
        [wall + 4, outer_h - wall - 4],
        [outer_w - wall - 4, outer_h - wall - 4]
    ];
    for (c = corners) {
        translate([c[0], c[1], wall - 0.2]) {
            difference() {
                cylinder(d=8.0, h=box_h - wall + 0.2);
                translate([0, 0, box_h - wall - 12])
                    cylinder(d=2.8, h=13);
            }
        }
    }
}

// ----------------------------------------------------------------------------
// 2. COUVERCLE SUPÉRIEUR (AVEC GRILLE D'AÉRATION DES DRIVERS TMC5160)
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
            [wall + 4, wall + 4],
            [outer_w - wall - 4, wall + 4],
            [wall + 4, outer_h - wall - 4],
            [outer_w - wall - 4, outer_h - wall - 4]
        ];
        for (c = corners) {
            translate([c[0], c[1], -1]) {
                cylinder(d=3.4, h=lid_thick + 5);
                // Le couvercle est modélisé à l'envers (face extérieure à Z=0)
                // On place la base large (d1=6.5) exactement à Z=0 (donc Z=+1 dans le translate -1)
                translate([0, 0, 1])
                    cylinder(d1=6.5, d2=3.4, h=2.5); // Fraisage tête de vis
            }
        }

        // Grilles d'aération au-dessus des 4 drivers TMC5160 pour dissipation thermique
        // Les drivers sont à Y_kicad = 36mm -> Y_scad = 110 - 36 = 74mm
        for (cx = [30, 60, 90, 120]) {
            for (gy = [-12 : 4 : 12]) {
                translate([wall + clearance + cx - 9, wall + clearance + 74 + gy, -1])
                    cube([18, 2.2, lid_thick + 2]);
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
