// ============================================================================
// BOITIER ERGONOMIQUE POUR TÉLÉCOMMANDE RAQUETTE GOTO-ANDRIVET
// Conçu pour impression 3D (PLA / PETG / ABS)
// ============================================================================

$fn = 40;

// Dimensions du PCB
pcb_w = 105;
pcb_h = 165;

// Paramètres du boîtier
wall = 2.5;
clearance = 1.5;
standoff_h = 5.0;
base_h = 16.0;      // Hauteur coque arrière
top_h = 14.0;       // Hauteur face avant

inner_w = pcb_w + 2 * clearance;
inner_h = pcb_h + 2 * clearance;
outer_w = inner_w + 2 * wall;
outer_h = inner_h + 2 * wall;

// Centre X de la raquette
cx = outer_w / 2.0;

// ----------------------------------------------------------------------------
// 1. COQUE ARRIÈRE (BASE DU BOÎTIER)
// ----------------------------------------------------------------------------
module raquette_base() {
    difference() {
        // Forme extérieure arrondie et ergonomique en main
        hull() {
            translate([6, 6, 0]) cylinder(r=6, h=base_h);
            translate([outer_w - 6, 6, 0]) cylinder(r=6, h=base_h);
            translate([6, outer_h - 6, 0]) cylinder(r=6, h=base_h);
            translate([outer_w - 6, outer_h - 6, 0]) cylinder(r=6, h=base_h);
        }

        // Cavité intérieure
        translate([wall, wall, wall])
            cube([inner_w, inner_h, base_h + 1]);

        // Encoche de passage du câble vers la monture en bas au centre
        translate([cx - 5, -1, wall + standoff_h])
            cube([10, wall + 2, 10]);

        // Trous filetés M3 dans les 4 coins pour la fermeture
        corners = [
            [wall + 4, wall + 4],
            [outer_w - wall - 4, wall + 4],
            [wall + 4, outer_h - wall - 4],
            [outer_w - wall - 4, outer_h - wall - 4]
        ];
        for (c = corners) {
            translate([c[0], c[1], base_h - 10])
                cylinder(d=2.8, h=12);
        }
    }

    // Piliers de fixation du PCB
    pcb_holes = [
        [clearance + 5, clearance + 5],
        [clearance + pcb_w - 5, clearance + 5],
        [clearance + 5, clearance + pcb_h - 5],
        [clearance + pcb_w - 5, clearance + pcb_h - 5]
    ];
    for (p = pcb_holes) {
        translate([wall + p[0], wall + p[1], wall]) {
            difference() {
                cylinder(d=7.0, h=standoff_h);
                cylinder(d=2.8, h=standoff_h + 1);
            }
        }
    }

    // Renforts des 4 coins
    corners = [
        [wall + 4, wall + 4],
        [outer_w - wall - 4, wall + 4],
        [wall + 4, outer_h - wall - 4],
        [outer_w - wall - 4, outer_h - wall - 4]
    ];
    for (c = corners) {
        translate([c[0], c[1], wall]) {
            difference() {
                cylinder(d=8.0, h=base_h - wall);
                translate([0, 0, base_h - wall - 10])
                    cylinder(d=2.8, h=11);
            }
        }
    }
}

// ----------------------------------------------------------------------------
// 2. FACE AVANT (FENÊTRE ÉCRAN LCD + OUVERTURES DES TOUCHES D-PAD)
// ----------------------------------------------------------------------------
module raquette_face_avant() {
    difference() {
        union() {
            // Façade avec bords arrondis
            hull() {
                translate([6, 6, 0]) cylinder(r=6, h=top_h);
                translate([outer_w - 6, 6, 0]) cylinder(r=6, h=top_h);
                translate([6, outer_h - 6, 0]) cylinder(r=6, h=top_h);
                translate([outer_w - 6, outer_h - 6, 0]) cylinder(r=6, h=top_h);
            }
        }

        // Évidement interne
        translate([wall, wall, -1])
            cube([inner_w, inner_h, top_h - wall + 1]);

        // A. Fenêtre de l'Écran LCD 2004 / 1602 avec chanfrein esthétique
        // Centrée à Y = wall + clearance + 40
        lcd_y = wall + clearance + 40;
        translate([cx - 38, lcd_y - 13, -1]) {
            cube([76, 26, top_h + 2]);
        }

        // B. 5 Trous circulaires pour les boutons du D-Pad (10 mm pour capuchons)
        btn_y = wall + clearance + 135;
        btn_spacing = 15;
        buttons = [
            [cx, btn_y - btn_spacing],              // HAUT
            [cx - btn_spacing, btn_y],              // GAUCHE
            [cx, btn_y],                            // ENTER / OK
            [cx + btn_spacing, btn_y],              // DROITE
            [cx, btn_y + btn_spacing]               // BAS
        ];
        for (b = buttons) {
            translate([b[0], b[1], -1])
                cylinder(d=10.0, h=top_h + 2);
        }

        // C. Trous de passage des 4 vis de fermeture M3 chanfreinées
        corners = [
            [wall + 4, wall + 4],
            [outer_w - wall - 4, wall + 4],
            [wall + 4, outer_h - wall - 4],
            [outer_w - wall - 4, outer_h - wall - 4]
        ];
        for (c = corners) {
            translate([c[0], c[1], -1]) {
                cylinder(d=3.4, h=top_h + 2);
                translate([0, 0, top_h - 2])
                    cylinder(d1=3.4, d2=6.5, h=2.5);
            }
        }
    }
}

// ----------------------------------------------------------------------------
// CHOIX DU MODELE
// ----------------------------------------------------------------------------
mode = "ensemble";

if (mode == "base") {
    raquette_base();
} else if (mode == "face_avant") {
    raquette_face_avant();
} else {
    color([0.25, 0.25, 0.25]) raquette_base();
    color([0.85, 0.85, 0.85, 0.9])
        translate([0, 0, base_h + 15])
            raquette_face_avant();
}
