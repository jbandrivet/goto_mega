#!/usr/bin/env python3
"""
Générateur automatique de PCB KiCad pour le projet Goto-Andrivet.
Version Haute Puissance 36V avec :
- PORT USB-A FEMELLE HORIZONTAL POUR LE PORT USB HOST DU TEENSY 4.1
- CIRCUIT BUCK 36V -> 5V 100% DISCRET ET INTÉGRÉ AU PCB (LM2596-5.0)
- 4 Drivers TMC5160 HV (4A max) et condensateurs 470uF/63V
- 4 Borniers à vis moteurs orientés vers le haut (extérieur)
- Bornier d'alimentation 36V orienté vers la gauche (extérieur)
- Connecteurs Raquette DIN et GPS orientés vers la droite (extérieur)
- Port Micro-USB du Teensy orienté vers le flanc extérieur
- Raquette ergonomique avec écran LCD intégré
"""

import os
import shutil
import json
import pcbnew

LIB_TEENSY = "/home/jean-baptiste/kicad_libs/Teensy.pretty"
LIB_HEADER = "/usr/share/kicad/footprints/Connector_PinHeader_2.54mm.pretty"
LIB_SOCKET = "/usr/share/kicad/footprints/Connector_PinSocket_2.54mm.pretty"
LIB_SWITCH = "/usr/share/kicad/footprints/Button_Switch_THT.pretty"
LIB_BUZZER = "/usr/share/kicad/footprints/Buzzer_Beeper.pretty"
LIB_TERMINAL = "/usr/share/kicad/footprints/TerminalBlock_Phoenix.pretty"
LIB_CAP = "/usr/share/kicad/footprints/Capacitor_THT.pretty"
LIB_DIODE = "/usr/share/kicad/footprints/Diode_THT.pretty"
LIB_INDUCTOR = "/usr/share/kicad/footprints/Inductor_THT.pretty"
LIB_TO = "/usr/share/kicad/footprints/Package_TO_SOT_THT.pretty"
LIB_HOLE = "/usr/share/kicad/footprints/MountingHole.pretty"
LIB_USB = "/usr/share/kicad/footprints/Connector_USB.pretty"

def add_outline_and_holes(board, width_mm, height_mm):
    coords = [
        (0, 0),
        (width_mm, 0),
        (width_mm, height_mm),
        (0, height_mm),
        (0, 0)
    ]
    for i in range(len(coords) - 1):
        line = pcbnew.PCB_SHAPE(board)
        line.SetShape(pcbnew.SHAPE_T_SEGMENT)
        line.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(coords[i][0]), pcbnew.FromMM(coords[i][1])))
        line.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(coords[i+1][0]), pcbnew.FromMM(coords[i+1][1])))
        line.SetLayer(pcbnew.Edge_Cuts)
        line.SetWidth(pcbnew.FromMM(0.15))
        board.Add(line)

    hole_positions = [
        (5, 5),
        (width_mm - 5, 5),
        (5, height_mm - 5),
        (width_mm - 5, height_mm - 5)
    ]
    for idx, (hx, hy) in enumerate(hole_positions, 1):
        hole = pcbnew.FootprintLoad(LIB_HOLE, "MountingHole_3.2mm_M3")
        if hole:
            hole.SetReference(f"H{idx}")
            hole.SetValue("M3 Fixation")
            hole.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(hx), pcbnew.FromMM(hy)))
            board.Add(hole)

def add_rect_silk(board, x1, y1, x2, y2, layer=pcbnew.F_SilkS, width_mm=0.15):
    pts = [(x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)]
    for i in range(len(pts) - 1):
        line = pcbnew.PCB_SHAPE(board)
        line.SetShape(pcbnew.SHAPE_T_SEGMENT)
        line.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(pts[i][0]), pcbnew.FromMM(pts[i][1])))
        line.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(pts[i+1][0]), pcbnew.FromMM(pts[i+1][1])))
        line.SetLayer(layer)
        line.SetWidth(pcbnew.FromMM(width_mm))
        board.Add(line)

def add_label(board, text, x_mm, y_mm, size_mm=1.0, layer=pcbnew.F_SilkS):
    txt = pcbnew.PCB_TEXT(board)
    txt.SetText(text)
    txt.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x_mm), pcbnew.FromMM(y_mm)))
    txt.SetLayer(layer)
    txt.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(size_mm), pcbnew.FromMM(size_mm)))
    board.Add(txt)

def connect_pad(fp, pad_num, net):
    for pad in fp.Pads():
        if pad.GetNumber() == str(pad_num):
            pad.SetNet(net)

def create_monture_pcb_36v(output_dir):
    os.makedirs(output_dir, exist_ok=True)
    board = pcbnew.BOARD()

    net_names = [
        "GND", "+36V", "+5V", "SW_NODE",
        "USB_HOST_DP", "USB_HOST_DM",
        "AZ_STEP", "AZ_DIR", "AZ_EN",
        "ALT_STEP", "ALT_DIR", "ALT_EN",
        "DEROT_STEP", "DEROT_DIR", "DEROT_EN",
        "FOCUS_STEP", "FOCUS_DIR", "FOCUS_EN",
        "AZ_1A", "AZ_1B", "AZ_2A", "AZ_2B",
        "ALT_1A", "ALT_1B", "ALT_2A", "ALT_2B",
        "DEROT_1A", "DEROT_1B", "DEROT_2A", "DEROT_2B",
        "FOCUS_1A", "FOCUS_1B", "FOCUS_2A", "FOCUS_2B",
        "RAQUETTE_TX", "RAQUETTE_RX",
        "GPS_TX", "GPS_RX",
        "BUZZER"
    ]
    nets = {}
    for name in net_names:
        net = pcbnew.NETINFO_ITEM(board, name)
        board.Add(net)
        nets[name] = net

    W, H = 150, 110
    add_outline_and_holes(board, W, H)

    add_label(board, "GOTO-ANDRIVET : MONTURE 36V / 4A (USB-B & TMC5160 HV)", 20, 4, size_mm=1.1)

    # =========================================================================
    # 1. CIRCUIT BUCK STEP-DOWN 36V -> 5V 100% INTÉGRÉ AU PCB (LM2596-5.0 DISCRET)
    # =========================================================================
    add_rect_silk(board, 6, 62, 44, 106, width_mm=0.2)
    add_label(board, "[ BUCK 36V->5V 3A ]", 8, 64, size_mm=0.7)

    # Bornier à vis entrée 36V (Bord gauche, centré à Y=55mm, orienté 270°)
    pwr36 = pcbnew.FootprintLoad(LIB_TERMINAL, "TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal")
    pwr36.SetReference("J_PWR_36V")
    pwr36.SetValue("ALIM 36V DC")
    pwr36.SetOrientationDegrees(270)
    pwr36.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(8), pcbnew.FromMM(55)))
    board.Add(pwr36)
    add_label(board, "<- ENTREE 36V", 14, 50, size_mm=0.8)
    add_label(board, "GND (Pin 1)", 14, 55, size_mm=0.6)
    add_label(board, "+36V (Pin 2)", 14, 60, size_mm=0.6)
    connect_pad(pwr36, 1, nets["GND"])
    connect_pad(pwr36, 2, nets["+36V"])

    c_in = pcbnew.FootprintLoad(LIB_CAP, "CP_Radial_D8.0mm_P3.50mm")
    c_in.SetReference("C_IN")
    c_in.SetValue("100uF 50V")
    c_in.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(20), pcbnew.FromMM(72)))
    board.Add(c_in)
    add_label(board, "C_IN 50V", 16, 67, size_mm=0.6)
    connect_pad(c_in, 1, nets["+36V"])
    connect_pad(c_in, 2, nets["GND"])

    lm2596 = pcbnew.FootprintLoad(LIB_TO, "TO-220-5_Vertical")
    lm2596.SetReference("U_LM2596")
    lm2596.SetValue("LM2596-5.0")
    lm2596.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(18), pcbnew.FromMM(84)))
    board.Add(lm2596)
    add_label(board, "LM2596-5.0", 12, 79, size_mm=0.7)
    connect_pad(lm2596, 1, nets["+36V"])
    connect_pad(lm2596, 2, nets["SW_NODE"])
    connect_pad(lm2596, 3, nets["GND"])
    connect_pad(lm2596, 4, nets["+5V"])
    connect_pad(lm2596, 5, nets["GND"])

    d_schottky = pcbnew.FootprintLoad(LIB_DIODE, "D_DO-201AD_P15.24mm_Horizontal")
    d_schottky.SetReference("D_SCHOTTKY")
    d_schottky.SetValue("1N5822 (3A)")
    d_schottky.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(14), pcbnew.FromMM(94)))
    board.Add(d_schottky)
    add_label(board, "DIODE 1N5822", 13, 97, size_mm=0.6)
    connect_pad(d_schottky, 1, nets["SW_NODE"])
    connect_pad(d_schottky, 2, nets["GND"])

    inductor = pcbnew.FootprintLoad(LIB_INDUCTOR, "L_Radial_D12.5mm_P7.00mm_Fastron_09HCP")
    inductor.SetReference("L_BUCK")
    inductor.SetValue("33uH 3A")
    inductor.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(33), pcbnew.FromMM(82)))
    board.Add(inductor)
    add_label(board, "L 33uH", 30, 76, size_mm=0.6)
    connect_pad(inductor, 1, nets["SW_NODE"])
    connect_pad(inductor, 2, nets["+5V"])

    c_out = pcbnew.FootprintLoad(LIB_CAP, "CP_Radial_D8.0mm_P3.50mm")
    c_out.SetReference("C_OUT")
    c_out.SetValue("220uF 16V")
    c_out.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(33), pcbnew.FromMM(96)))
    board.Add(c_out)
    add_label(board, "C_OUT 16V", 27, 101, size_mm=0.6)
    connect_pad(c_out, 1, nets["+5V"])
    connect_pad(c_out, 2, nets["GND"])

    c_dec = pcbnew.FootprintLoad(LIB_CAP, "C_Disc_D5.0mm_W2.5mm_P5.00mm")
    c_dec.SetReference("C_DEC")
    c_dec.SetValue("100nF")
    c_dec.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(20), pcbnew.FromMM(102)))
    board.Add(c_dec)
    connect_pad(c_dec, 1, nets["+5V"])
    connect_pad(c_dec, 2, nets["GND"])

    # =========================================================================
    # 2. 4 DRIVERS MOTEURS TMC5160 HV (4A MAX) PARFAITEMENT CENTRES (X=30, 60, 90, 120)
    # =========================================================================
    driver_axes = [
        ("AZ", "MOTEUR AZ (36V/4A)", 30, "AZ_STEP", "AZ_DIR", "AZ_EN", "AZ_1B", "AZ_1A", "AZ_2A", "AZ_2B"),
        ("ALT", "MOTEUR ALT (36V/4A)", 60, "ALT_STEP", "ALT_DIR", "ALT_EN", "ALT_1B", "ALT_1A", "ALT_2A", "ALT_2B"),
        ("DEROT", "DEROTATEUR (36V/4A)", 90, "DEROT_STEP", "DEROT_DIR", "DEROT_EN", "DEROT_1B", "DEROT_1A", "DEROT_2A", "DEROT_2B"),
        ("FOCUS", "FOCUSEUR (36V/4A)", 120, "FOCUS_STEP", "FOCUS_DIR", "FOCUS_EN", "FOCUS_1B", "FOCUS_1A", "FOCUS_2A", "FOCUS_2B")
    ]

    for axis_name, axis_label, cx, s_net, d_net, e_net, m_1b, m_1a, m_2a, m_2b in driver_axes:
        m_term = pcbnew.FootprintLoad(LIB_TERMINAL, "TerminalBlock_Phoenix_MKDS-1,5-4-5.08_1x04_P5.08mm_Horizontal")
        m_term.SetReference(f"M_{axis_name}")
        m_term.SetValue(f"MOTEUR {axis_name}")
        m_term.SetOrientationDegrees(180)
        m_term.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(cx + 7.62), pcbnew.FromMM(8)))
        board.Add(m_term)

        # Encadrement sérigraphie clair pour Bobine 1 (Gauche) et Bobine 2 (Droite)
        add_rect_silk(board, cx - 10.0, 13.5, cx - 0.5, 17.5, width_mm=0.15)
        add_rect_silk(board, cx + 0.5, 13.5, cx + 10.0, 17.5, width_mm=0.15)

        # Repères sous chaque borne
        add_label(board, "1B", cx - 8.5, 14.7, size_mm=0.7)
        add_label(board, "1A", cx - 3.5, 14.7, size_mm=0.7)
        add_label(board, "2A", cx + 1.5, 14.7, size_mm=0.7)
        add_label(board, "2B", cx + 6.5, 14.7, size_mm=0.7)

        # Identification explicite des bobines
        add_label(board, "BOBINE 1", cx - 9.2, 16.5, size_mm=0.55)
        add_label(board, "BOBINE 2", cx + 1.3, 16.5, size_mm=0.55)

        # Repères au-dessus vers la sortie des fils
        add_label(board, "^ BOBINE 1 ^", cx - 9.5, 2.0, size_mm=0.55)
        add_label(board, "^ BOBINE 2 ^", cx + 1.0, 2.0, size_mm=0.55)

        # Nom de l'axe
        add_label(board, axis_label, cx - 11, 19.5, size_mm=0.8)

        connect_pad(m_term, 1, nets[m_2b])
        connect_pad(m_term, 2, nets[m_2a])
        connect_pad(m_term, 3, nets[m_1a])
        connect_pad(m_term, 4, nets[m_1b])

        drv_y = 36
        sock_l = pcbnew.FootprintLoad(LIB_SOCKET, "PinSocket_1x08_P2.54mm_Vertical")
        sock_l.SetReference(f"DRV_{axis_name}_L")
        sock_l.SetValue("Logique")
        sock_l.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(cx - 7.62), pcbnew.FromMM(drv_y)))
        board.Add(sock_l)
        connect_pad(sock_l, 1, nets[e_net])
        connect_pad(sock_l, 7, nets[s_net])
        connect_pad(sock_l, 8, nets[d_net])

        sock_r = pcbnew.FootprintLoad(LIB_SOCKET, "PinSocket_1x08_P2.54mm_Vertical")
        sock_r.SetReference(f"DRV_{axis_name}_R")
        sock_r.SetValue("Puissance")
        sock_r.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(cx + 7.62), pcbnew.FromMM(drv_y)))
        board.Add(sock_r)
        connect_pad(sock_r, 1, nets["GND"])
        connect_pad(sock_r, 2, nets["+5V"])
        connect_pad(sock_r, 3, nets[m_2b])
        connect_pad(sock_r, 4, nets[m_2a])
        connect_pad(sock_r, 5, nets[m_1a])
        connect_pad(sock_r, 6, nets[m_1b])
        connect_pad(sock_r, 7, nets["GND"])
        connect_pad(sock_r, 8, nets["+36V"])

        add_rect_silk(board, cx - 8.5, drv_y - 10, cx + 8.5, drv_y + 10, width_mm=0.2)
        add_label(board, f"TMC5160 {axis_name}", cx - 6, drv_y - 1, size_mm=0.7)

        cap = pcbnew.FootprintLoad(LIB_CAP, "CP_Radial_D8.0mm_P3.50mm")
        cap.SetReference(f"C_{axis_name}")
        cap.SetValue("470uF 63V")
        cap.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(cx), pcbnew.FromMM(49)))
        board.Add(cap)
        connect_pad(cap, 1, nets["+36V"])
        connect_pad(cap, 2, nets["GND"])

    # =========================================================================
    # 3. TEENSY 4.1 PARFAITEMENT CENTRE HORIZONTALEMENT (X=75mm, Y=70mm)
    # =========================================================================
    teensy = pcbnew.FootprintLoad(LIB_TEENSY, "Teensy41")
    teensy.SetReference("U1")
    teensy.SetValue("Teensy 4.1")
    teensy.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(75), pcbnew.FromMM(70)))
    board.Add(teensy)
    add_label(board, "<- MICRO-USB", 41, 69, size_mm=0.8)

    connect_pad(teensy, 1, nets["GND"])
    connect_pad(teensy, 4, nets["AZ_STEP"])
    connect_pad(teensy, 5, nets["AZ_DIR"])
    connect_pad(teensy, 6, nets["AZ_EN"])
    connect_pad(teensy, 7, nets["ALT_STEP"])
    connect_pad(teensy, 8, nets["ALT_DIR"])
    connect_pad(teensy, 9, nets["ALT_EN"])
    connect_pad(teensy, 10, nets["DEROT_STEP"])
    connect_pad(teensy, 11, nets["DEROT_DIR"])
    connect_pad(teensy, 12, nets["DEROT_EN"])
    connect_pad(teensy, 13, nets["FOCUS_STEP"])
    connect_pad(teensy, 14, nets["FOCUS_DIR"])
    connect_pad(teensy, 35, nets["FOCUS_EN"])

    # Broches USB Host du Teensy 4.1
    connect_pad(teensy, 55, nets["+5V"])         # 5V USB
    connect_pad(teensy, 56, nets["USB_HOST_DM"]) # D-
    connect_pad(teensy, 57, nets["USB_HOST_DP"]) # D+
    connect_pad(teensy, 58, nets["GND"])         # GND

    # =========================================================================
    # 4. CONNECTEUR USB-B FEMELLE PARFAITEMENT CENTRE (X=75mm, Y=110mm)
    # =========================================================================
    usb_b = pcbnew.FootprintLoad(LIB_USB, "USB_B_OST_USB-B1HSxx_Horizontal")
    usb_b.SetReference("J_USB_PC")
    usb_b.SetValue("USB-B Liaison PC")
    # Rotation 270° pour orienter l'ouverture vers le bas (+Y extérieur)
    # Centré exactement à X=75.0mm (X_pos = 75.0 + 1.25 = 76.25mm)
    # Affleurant au bord bas Y=110mm (Y_pos = 110 - 15.12 = 94.88 -> 95mm)
    usb_b.SetOrientationDegrees(270)
    usb_b.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(76.25), pcbnew.FromMM(95)))
    board.Add(usb_b)
    add_label(board, "USB-B (LIAISON PC)", 61, 89, size_mm=0.8)
    add_label(board, "V PRISE USB-B VERS LE BAS V", 62, 108, size_mm=0.6)
    connect_pad(usb_b, 1, nets["+5V"])          # Pin 1 = VBUS (+5V)
    connect_pad(usb_b, 2, nets["USB_HOST_DM"])   # Pin 2 = D-
    connect_pad(usb_b, 3, nets["USB_HOST_DP"])   # Pin 3 = D+
    connect_pad(usb_b, 4, nets["GND"])           # Pin 4 = GND
    connect_pad(usb_b, 5, nets["GND"])           # Shield tabs = GND

    # =========================================================================
    # 5. CONNECTEURS PÉRIPHÉRIQUES FLANC DROIT (ALIGNÉS VERTICALEMENT AVEC REPERES)
    # =========================================================================
    # Connecteur vers Raquette (Centré à Y=45mm)
    raq = pcbnew.FootprintLoad(LIB_HEADER, "PinHeader_1x04_P2.54mm_Vertical")
    raq.SetReference("J_RAQUETTE")
    raq.SetValue("VERS RAQUETTE")
    raq.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(142), pcbnew.FromMM(45 - 3.81)))
    board.Add(raq)
    add_label(board, "[ RAQUETTE ]", 125, 38.5, size_mm=0.8)
    add_label(board, "1: GND", 133, 41.2, size_mm=0.65)
    add_label(board, "2: +5V", 133, 43.7, size_mm=0.65)
    add_label(board, "3: RX",  134, 46.3, size_mm=0.65)
    add_label(board, "4: TX",  134, 48.8, size_mm=0.65)
    connect_pad(raq, 1, nets["GND"])
    connect_pad(raq, 2, nets["+5V"])
    connect_pad(raq, 3, nets["RAQUETTE_RX"])
    connect_pad(raq, 4, nets["RAQUETTE_TX"])

    # Connecteur vers Module GPS (Centré à Y=65mm)
    gps = pcbnew.FootprintLoad(LIB_HEADER, "PinHeader_1x04_P2.54mm_Vertical")
    gps.SetReference("J_GPS")
    gps.SetValue("GPS SERIAL4")
    gps.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(142), pcbnew.FromMM(65 - 3.81)))
    board.Add(gps)
    add_label(board, "[ GPS SERIAL ]", 123, 58.5, size_mm=0.8)
    add_label(board, "1: RX <- TX", 127, 61.2, size_mm=0.65)
    add_label(board, "2: TX -> RX", 127, 63.7, size_mm=0.65)
    add_label(board, "3: +5V",      133, 66.3, size_mm=0.65)
    add_label(board, "4: GND",      133, 68.8, size_mm=0.65)
    connect_pad(gps, 1, nets["GPS_RX"])
    connect_pad(gps, 2, nets["GPS_TX"])
    connect_pad(gps, 3, nets["+5V"])
    connect_pad(gps, 4, nets["GND"])

    buz = pcbnew.FootprintLoad(LIB_BUZZER, "Buzzer_12x9.5RM7.6")
    buz.SetReference("BZ1")
    buz.SetValue("Buzzer")
    buz.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(138), pcbnew.FromMM(88)))
    board.Add(buz)
    add_label(board, "BUZZER", 134, 80, size_mm=0.7)
    connect_pad(buz, 1, nets["BUZZER"])
    connect_pad(buz, 2, nets["GND"])

    # Guide de câblage sérigraphié sur le PCB
    add_rect_silk(board, 88, 93, 145, 107, width_mm=0.15)
    add_label(board, "GUIDE CABLAGE MOTEURS :", 90, 95, size_mm=0.65)
    add_label(board, "- BOBINE 1 = GAUCHE [1B, 1A]", 90, 98, size_mm=0.55)
    add_label(board, "- BOBINE 2 = DROITE [2A, 2B]", 90, 101, size_mm=0.55)
    add_label(board, "* Tester au multimetre : ~1-3 Ohms par paire", 90, 104, size_mm=0.5)

    connect_pad(teensy, 36, nets["RAQUETTE_TX"])
    connect_pad(teensy, 37, nets["RAQUETTE_RX"])
    connect_pad(teensy, 38, nets["GPS_RX"])
    connect_pad(teensy, 39, nets["GPS_TX"])
    connect_pad(teensy, 42, nets["BUZZER"])
    connect_pad(teensy, 47, nets["GND"])
    connect_pad(teensy, 48, nets["+5V"])

    board.BuildConnectivity()

    pcb_path = os.path.join(output_dir, "monture.kicad_pcb")
    pcbnew.SaveBoard(pcb_path, board)

    pro_path = os.path.join(output_dir, "monture.kicad_pro")
    with open(pro_path, "w") as f:
        json.dump({"meta": {"filename": "monture.kicad_pro", "version": 1}, "boards": ["monture.kicad_pcb"], "sheets": []}, f, indent=2)

    print(f"[OK] PCB Monture 36V avec USB-A Host créé : {pcb_path}")


def create_raquette_pcb(output_dir):
    os.makedirs(output_dir, exist_ok=True)
    board = pcbnew.BOARD()

    net_names = [
        "GND", "+5V",
        "RAQ_TX", "RAQ_RX",
        "I2C_SDA", "I2C_SCL",
        "BTN_UP", "BTN_DOWN", "BTN_LEFT", "BTN_RIGHT", "BTN_ENTER"
    ]
    nets = {}
    for name in net_names:
        net = pcbnew.NETINFO_ITEM(board, name)
        board.Add(net)
        nets[name] = net

    W, H = 105, 165
    add_outline_and_holes(board, W, H)

    add_label(board, "GOTO-ANDRIVET : TELECOMMANDE RAQUETTE", 18, 5, size_mm=1.3)
    add_label(board, "Afficheur LCD 2004 / 1602 I2C & Teensy 4.1", 20, 8, size_mm=0.9)

    lcd_cx = W / 2.0
    lcd_cy = 40.0

    add_rect_silk(board, lcd_cx - 49, lcd_cy - 30, lcd_cx + 49, lcd_cy + 30, width_mm=0.2)
    add_rect_silk(board, lcd_cx - 38.5, lcd_cy - 13, lcd_cx + 38.5, lcd_cy + 13, width_mm=0.15)
    add_label(board, "[ FENETRE LCD 2004 (20x4) / 1602 ]", lcd_cx - 30, lcd_cy - 1, size_mm=1.0)

    lcd_holes_2004 = [
        (lcd_cx - 46.5, lcd_cy - 27.5),
        (lcd_cx + 46.5, lcd_cy - 27.5),
        (lcd_cx - 46.5, lcd_cy + 27.5),
        (lcd_cx + 46.5, lcd_cy + 27.5)
    ]
    for idx, (hx, hy) in enumerate(lcd_holes_2004, 1):
        hole = pcbnew.FootprintLoad(LIB_HOLE, "MountingHole_3.2mm_M3")
        if hole:
            hole.SetReference(f"HLCD_{idx}")
            hole.SetValue("M3 Entretoise LCD")
            hole.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(hx), pcbnew.FromMM(hy)))
            board.Add(hole)

    lcd_conn = pcbnew.FootprintLoad(LIB_HEADER, "PinHeader_1x04_P2.54mm_Vertical")
    lcd_conn.SetReference("J_LCD_I2C")
    lcd_conn.SetValue("LCD Backpack I2C")
    lcd_conn.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(12), pcbnew.FromMM(14)))
    board.Add(lcd_conn)
    add_label(board, "I2C LCD", 8, 9, size_mm=0.9)
    add_label(board, "GND VCC SDA SCL", 4, 19, size_mm=0.7)
    connect_pad(lcd_conn, 1, nets["GND"])
    connect_pad(lcd_conn, 2, nets["+5V"])
    connect_pad(lcd_conn, 3, nets["I2C_SDA"])
    connect_pad(lcd_conn, 4, nets["I2C_SCL"])

    grove = pcbnew.FootprintLoad(LIB_HEADER, "PinHeader_1x04_P2.54mm_Vertical")
    grove.SetReference("J_GROVE")
    grove.SetValue("Grove I2C Aux")
    grove.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(93), pcbnew.FromMM(14)))
    board.Add(grove)
    add_label(board, "GROVE I2C", 87, 9, size_mm=0.9)
    add_label(board, "SCL SDA VCC GND", 84, 19, size_mm=0.7)
    connect_pad(grove, 1, nets["I2C_SCL"])
    connect_pad(grove, 2, nets["I2C_SDA"])
    connect_pad(grove, 3, nets["+5V"])
    connect_pad(grove, 4, nets["GND"])

    teensy = pcbnew.FootprintLoad(LIB_TEENSY, "Teensy41")
    teensy.SetReference("U1")
    teensy.SetValue("Teensy 4.1")
    teensy.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(lcd_cx), pcbnew.FromMM(92)))
    board.Add(teensy)
    add_label(board, "<- USB TEENSY 4.1", lcd_cx - 40, 91, size_mm=0.9)

    btn_cx = lcd_cx
    btn_cy = 135.0
    btn_spacing = 15.0

    buttons = [
        ("SW_UP", "HAUT", btn_cx, btn_cy - btn_spacing, "BTN_UP"),
        ("SW_LEFT", "GAUCHE", btn_cx - btn_spacing, btn_cy, "BTN_LEFT"),
        ("SW_ENTER", "ENTER / OK", btn_cx, btn_cy, "BTN_ENTER"),
        ("SW_RIGHT", "DROITE", btn_cx + btn_spacing, btn_cy, "BTN_RIGHT"),
        ("SW_DOWN", "BAS", btn_cx, btn_cy + btn_spacing, "BTN_DOWN")
    ]
    for ref, val, bx, by, sig_net in buttons:
        btn = pcbnew.FootprintLoad(LIB_SWITCH, "SW_PUSH_6mm")
        btn.SetReference(ref)
        btn.SetValue(val)
        btn.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(bx), pcbnew.FromMM(by)))
        board.Add(btn)
        add_label(board, val, bx - 4, by - 4, size_mm=0.7)
        connect_pad(btn, 1, nets["GND"])
        connect_pad(btn, 2, nets[sig_net])

    add_rect_silk(board, btn_cx - 25, btn_cy - 22, btn_cx + 25, btn_cy + 22, width_mm=0.2)

    din = pcbnew.FootprintLoad(LIB_HEADER, "PinHeader_1x04_P2.54mm_Vertical")
    din.SetReference("J_DIN")
    din.SetValue("CABLE MONTURE")
    din.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(lcd_cx), pcbnew.FromMM(158)))
    board.Add(din)
    add_label(board, "V CABLE VERS MONTURE (BAS) V", lcd_cx - 24, 154, size_mm=0.8)
    connect_pad(din, 1, nets["GND"])
    connect_pad(din, 2, nets["+5V"])
    connect_pad(din, 3, nets["RAQ_TX"])
    connect_pad(din, 4, nets["RAQ_RX"])

    connect_pad(teensy, 1, nets["GND"])
    connect_pad(teensy, 2, nets["RAQ_RX"])
    connect_pad(teensy, 3, nets["RAQ_TX"])
    connect_pad(teensy, 8, nets["BTN_UP"])
    connect_pad(teensy, 9, nets["BTN_DOWN"])
    connect_pad(teensy, 10, nets["BTN_LEFT"])
    connect_pad(teensy, 11, nets["BTN_RIGHT"])
    connect_pad(teensy, 12, nets["BTN_ENTER"])
    connect_pad(teensy, 40, nets["I2C_SDA"])
    connect_pad(teensy, 41, nets["I2C_SCL"])
    connect_pad(teensy, 47, nets["GND"])
    connect_pad(teensy, 48, nets["+5V"])

    board.BuildConnectivity()

    pcb_path = os.path.join(output_dir, "raquette.kicad_pcb")
    pcbnew.SaveBoard(pcb_path, board)

    pro_path = os.path.join(output_dir, "raquette.kicad_pro")
    with open(pro_path, "w") as f:
        json.dump({"meta": {"filename": "raquette.kicad_pro", "version": 1}, "boards": ["raquette.kicad_pcb"], "sheets": []}, f, indent=2)

    print(f"[OK] PCB Raquette créé : {pcb_path}")


if __name__ == "__main__":
    local_dir = "/home/jean-baptiste/GotoAndrivet_PCB"
    usb_dir = "/run/media/jean-baptiste/6E91-2E1D/perso/astronomie/gotos/goto_andrivet/pcb"

    print("--- Génération PCB Monture 36V / 4A (Avec USB-A Host) ---")
    create_monture_pcb_36v(os.path.join(local_dir, "monture"))

    print("--- Génération PCB Raquette ---")
    create_raquette_pcb(os.path.join(local_dir, "raquette"))

    repo_dir = "/home/jean-baptiste/goto_andrivet/pcb"
    print("--- Synchronisation avec le dépôt local ---")
    try:
        os.makedirs(repo_dir, exist_ok=True)
        shutil.copytree(local_dir, repo_dir, dirs_exist_ok=True)
        print(f"[OK] Fichiers synchronisés avec le dépôt : {repo_dir}")
    except Exception as e:
        print(f"[ERREUR] Échec de la synchronisation dépôt : {e}")

    print("--- Copie sur la clé USB ---")
    try:
        os.makedirs(usb_dir, exist_ok=True)
        shutil.copytree(local_dir, usb_dir, dirs_exist_ok=True)
        print(f"[OK] Fichiers copiés avec succès sur la clé USB : {usb_dir}")
    except Exception as e:
        print(f"[ERREUR] Échec de la copie USB : {e}")

    print("\nTerminé avec succès !")
