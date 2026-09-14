// ============================================================================
// BOITIER PARAMÉTRIQUE POUR MONTURE GOTO-ANDRIVET (36V / 4A)
// Conçu pour impression 3D (PLA / PETG / ABS)
// ============================================================================

$fn = 40;

// Dimensions du PCB
pcb_w = 145;
pcb_h = 100;
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

        // --- DÉCOUPES DE PASSAGE DES CONNECTEURS EXTÉRIEURS ---

        // A. 4 Ouvertures Moteurs sur le bord haut (Y = max)
        // Moteurs AZ, ALT, DEROT, FOCUS
        motor_x = [20, 54, 88, 122];
        for (mx = motor_x) {
            translate([wall + clearance + mx - 11, outer_h - wall - 1, wall + standoff_h])
                cube([22, wall + 2, 14]);
        }

        // B. Flanc gauche (X = 0) : Entrée 36V et Port USB Teensy
        // Entrée 36V
        translate([-1, wall + clearance + 56 - 7, wall + standoff_h])
            cube([wall + 2, 14, 12]);
        // Port Micro-USB Teensy
        translate([-1, wall + clearance + 75 - 7, wall + standoff_h])
            cube([wall + 2, 14, 10]);

        // C. Flanc droit (X = max) : Raquette DIN et GPS
        // Connecteur Raquette
        translate([outer_w - wall - 1, wall + clearance + 60 - 8, wall + standoff_h])
            cube([wall + 2, 16, 12]);
        // Connecteur GPS
        translate([outer_w - wall - 1, wall + clearance + 75 - 8, wall + standoff_h])
            cube([wall + 2, 16, 12]);

        // D. Trous de vis de fixation du couvercle dans les 4 coins
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
        translate([wall + p[0], wall + p[1], wall]) {
            difference() {
                cylinder(d=7.0, h=standoff_h);
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
        translate([c[0], c[1], wall]) {
            difference() {
                cylinder(d=8.0, h=box_h - wall);
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
                cylinder(d1=6.5, d2=3.4, h=2.5); // Fraisage tête de vis
            }
        }

        // Grilles d'aération au-dessus des 4 drivers TMC5160 pour dissipation thermique
        for (gx = [18, 52, 86, 120]) {
            for (gy = [0 : 5 : 25]) {
                translate([wall + clearance + gx, wall + clearance + 20 + gy, -1])
                    cube([18, 2.5, lid_thick + 2]);
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
