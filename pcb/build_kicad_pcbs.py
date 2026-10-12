#!/usr/bin/env python3
"""
Générateur automatique de PCB KiCad pour le projet Goto-Andrivet.

ATTENTION : ce script produit des cartes NON ROUTÉES. Le routage (Freerouting) est fait ensuite
sur pcb/monture/monture.kicad_pcb : relancer ce script puis copier sa sortie écrase ce routage.

Version Haute Puissance 36V avec :
- CIRCUIT BUCK 36V -> 5V 100% DISCRET ET INTÉGRÉ AU PCB (LM2596-5.0, diode SB560 60V)
- Jack 12V isolé du bornier 36V par la diode D_JACK
- 4 supports StepStick (TMC5160 HV, 4A max), VIO en 3,3V, condensateurs 220uF/63V
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
LIB_WIRE = "/usr/share/kicad/footprints/Connector_Wire.pretty"
LIB_SOCKET = "/usr/share/kicad/footprints/Connector_PinSocket_2.54mm.pretty"
LIB_SWITCH = "/usr/share/kicad/footprints/Button_Switch_THT.pretty"
LIB_BUZZER = "/usr/share/kicad/footprints/Buzzer_Beeper.pretty"
LIB_TERMINAL = "/usr/share/kicad/footprints/TerminalBlock_Phoenix.pretty"
LIB_JACK = "/usr/share/kicad/footprints/Connector_BarrelJack.pretty"
LIB_CAP = "/usr/share/kicad/footprints/Capacitor_THT.pretty"
LIB_DIODE = "/usr/share/kicad/footprints/Diode_THT.pretty"
LIB_INDUCTOR = "/usr/share/kicad/footprints/Inductor_THT.pretty"
LIB_TO = "/usr/share/kicad/footprints/Package_TO_SOT_THT.pretty"
LIB_HOLE = "/usr/share/kicad/footprints/MountingHole.pretty"
LIB_USB = "/usr/share/kicad/footprints/Connector_USB.pretty"
LIB_DIP = "/usr/share/kicad/footprints/Package_DIP.pretty"
LIB_RES = "/usr/share/kicad/footprints/Resistor_THT.pretty"
LIB_JUMPER = "/usr/share/kicad/footprints/Jumper.pretty"

# Classes de nets du PCB monture (écrites dans monture.kicad_pro)
DEFAULT_NETCLASS = {"name": "Default", "clearance": 0.2, "track_width": 0.2, "via_diameter": 0.6, "via_drill": 0.3,
                    "priority": 2147483647}
POWER_NETCLASS = {"name": "Puissance", "clearance": 0.3, "track_width": 1.5, "via_diameter": 1.2, "via_drill": 0.6,
                  "priority": 0}
POWER_NET_PATTERNS = ["+36V", "GND", "+5V", "SW_NODE", "JACK_IN", "*_1A", "*_1B", "*_2A", "*_2B"]

# Ponts SPI (TMC5160) : broches 2..6 du support StepStick -> bus SPI1 du Teensy.
# Pont fermé : SDI -> MOSI, SCK -> SCK, CSN -> CS de l'axe, SDO -> MISO, CLK -> GND.
SPI_SOCKET_SIGS = ("SDI", "SCK", "CSN", "SDO", "CLK")
SPI_JUMPER_DX = 3.4   # centre du pont par rapport à la rangée gauche du support

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

def add_track(board, start_x, start_y, end_x, end_y, width_mm, layer, net):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(start_x), pcbnew.FromMM(start_y)))
    t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(end_x), pcbnew.FromMM(end_y)))
    t.SetWidth(pcbnew.FromMM(width_mm))
    t.SetLayer(layer)
    t.SetNet(net)
    board.Add(t)

def add_via(board, x, y, net, size_mm=0.8, drill_mm=0.4):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
    v.SetWidth(pcbnew.FromMM(size_mm))
    v.SetDrill(pcbnew.FromMM(drill_mm))
    v.SetNet(net)
    board.Add(v)

def create_monture_pcb_36v(output_dir):
    os.makedirs(output_dir, exist_ok=True)
    board = pcbnew.BOARD()

    net_names = [
        "GND", "+36V", "+5V", "+3V3", "SW_NODE", "JACK_IN",

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
        "PC_TX", "PC_RX",
        "BUZZER"
    ]
    # Sélecteur StepStick / driver externe : nets côté supports (_INT), côté pastilles externes (_EXT)
    for ax in ("AZ", "ALT", "DEROT", "FOCUS"):
        net_names.append(f"SEL_{ax}")
        for sig in ("STEP", "DIR", "EN"):
            net_names += [f"{ax}_{sig}_INT", f"{ax}_{sig}_EXT"]
    # Bus SPI1 des TMC5160 : nets locaux broches 2..6 des supports, et bus côté Teensy
    for ax in ("AZ", "ALT", "DEROT", "FOCUS"):
        net_names += [f"{ax}_{sig}" for sig in SPI_SOCKET_SIGS] + [f"SPI_CS_{ax}"]
    net_names += ["SPI_MOSI", "SPI_SCK", "SPI_MISO"]
    nets = {}
    for name in net_names:
        net = pcbnew.NETINFO_ITEM(board, name)
        board.Add(net)
        nets[name] = net

    W, H = 150, 110
    add_outline_and_holes(board, W, H)

    add_label(board, "GOTO-ANDRIVET : MONTURE 36V - TEENSY 4.1 / STEPSTICK", 75, 108.6, size_mm=1.1)

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

    # Entrée DC Jack 12V en parallèle
    dc_jack = pcbnew.FootprintLoad(LIB_JACK, "BarrelJack_Horizontal")
    dc_jack.SetReference("J_12V")
    dc_jack.SetValue("12V Jack")
    dc_jack.SetOrientationDegrees(0)
    # Origin is at pin 1 (back of the jack). To have the opening on the left edge (X=0), we put X=12.
    dc_jack.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(12), pcbnew.FromMM(40)))
    board.Add(dc_jack)
    add_label(board, "<- ENTREE 36V", 14, 50, size_mm=0.8)
    add_label(board, "GND (Pin 1)", 14, 55, size_mm=0.6)
    add_label(board, "+36V (Pin 2)", 14, 60, size_mm=0.6)
    connect_pad(pwr36, 1, nets["GND"])
    connect_pad(pwr36, 2, nets["+36V"])

    # DC Jack connections : le jack passe par D_JACK (sinon le 36V du bornier remonte dans le bloc 12V)
    connect_pad(dc_jack, 1, nets["JACK_IN"])
    connect_pad(dc_jack, 2, nets["GND"])
    connect_pad(dc_jack, 3, nets["GND"])
    add_label(board, "ALIM 12V (JACK)", 8, 33.6, size_mm=0.8)

    d_jack = pcbnew.FootprintLoad(LIB_DIODE, "D_DO-201AD_P15.24mm_Horizontal")
    d_jack.SetReference("D_JACK")
    d_jack.SetValue("SB560 (60V 5A)")
    d_jack.SetOrientationDegrees(270)   # anode (pad 2) vers le jack, cathode (pad 1) en haut
    d_jack.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(16), pcbnew.FromMM(18)))
    board.Add(d_jack)
    add_label(board, "D_JACK", 11.2, 26, size_mm=0.6)
    connect_pad(d_jack, 1, nets["+36V"])
    connect_pad(d_jack, 2, nets["JACK_IN"])

    # C_IN au plus pres du LM2596 et hors du passage du cable micro-USB du Teensy (Y 64..76)
    c_in = pcbnew.FootprintLoad(LIB_CAP, "CP_Radial_D8.0mm_P3.50mm")
    c_in.SetReference("C_IN")
    c_in.SetValue("100uF 63V")
    c_in.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(8.5), pcbnew.FromMM(84)))
    board.Add(c_in)
    add_label(board, "C_IN 63V", 10.25, 89.4, size_mm=0.6)
    connect_pad(c_in, 1, nets["+36V"])
    connect_pad(c_in, 2, nets["GND"])

    lm2596 = pcbnew.FootprintLoad(LIB_TO, "TO-220-5_Vertical")
    lm2596.SetReference("U_LM2596")
    lm2596.SetValue("LM2596-5.0")
    lm2596.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(18), pcbnew.FromMM(84)))
    board.Add(lm2596)
    add_label(board, "LM2596-5.0", 21.4, 78.6, size_mm=0.7)
    connect_pad(lm2596, 1, nets["+36V"])
    connect_pad(lm2596, 2, nets["SW_NODE"])
    connect_pad(lm2596, 3, nets["GND"])
    connect_pad(lm2596, 4, nets["+5V"])
    connect_pad(lm2596, 5, nets["GND"])

    d_schottky = pcbnew.FootprintLoad(LIB_DIODE, "D_DO-201AD_P15.24mm_Horizontal")
    d_schottky.SetReference("D_SCHOTTKY")
    d_schottky.SetValue("SB560 (60V 5A)")   # 1N5822 = 40V seulement, trop juste sous 36V
    d_schottky.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(14), pcbnew.FromMM(94)))
    board.Add(d_schottky)
    add_label(board, "DIODE SB560", 13, 97, size_mm=0.6)
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
    c_out.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(35), pcbnew.FromMM(97)))
    board.Add(c_out)
    add_label(board, "C_OUT 16V", 36.75, 102.3, size_mm=0.6)
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
        add_label(board, axis_label, cx, 19.5, size_mm=0.8)

        connect_pad(m_term, 1, nets[m_2b])
        connect_pad(m_term, 2, nets[m_2a])
        connect_pad(m_term, 3, nets[m_1a])
        connect_pad(m_term, 4, nets[m_1b])

        # Module StepStick / Pololu : 2 rangées de 8 broches espacées de 12,7 mm (0,5")
        # Gauche (haut->bas) : EN SDI SCK CSN SDO CLK STEP DIR   (2-6 : ponts SPI, ouverts par défaut)
        # Droite (haut->bas) : VMOT GND 2B 2A 1A 1B VIO GND  (VMOT en face de EN)
        drv_y = 36
        sock_l = pcbnew.FootprintLoad(LIB_SOCKET, "PinSocket_1x08_P2.54mm_Vertical")
        sock_l.SetReference(f"DRV_{axis_name}_L")
        sock_l.SetValue("Logique")
        sock_l.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(cx - 6.35), pcbnew.FromMM(drv_y)))
        board.Add(sock_l)
        connect_pad(sock_l, 1, nets[e_net + "_INT"])   # via les tampons 74HC126 du sélecteur
        connect_pad(sock_l, 7, nets[s_net + "_INT"])
        connect_pad(sock_l, 8, nets[d_net + "_INT"])

        # Ponts à souder SPI entre les deux rangées, sous le module (ouverts = A4988, DRV8825, TMC2209...)
        x_l = cx - 6.35
        for i, sig in enumerate(SPI_SOCKET_SIGS):
            y = drv_y + 2.54 * (i + 1)
            local = nets[f"{axis_name}_{sig}"]
            bus = {"SDI": "SPI_MOSI", "SCK": "SPI_SCK", "CSN": f"SPI_CS_{axis_name}",
                   "SDO": "SPI_MISO", "CLK": "GND"}[sig]
            connect_pad(sock_l, i + 2, local)
            jp = pcbnew.FootprintLoad(LIB_JUMPER, "SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm")
            jp.SetReference(f"JP_{axis_name}_{sig}")
            jp.SetValue("SPI")
            jp.Reference().SetVisible(False)
            jp.Value().SetVisible(False)
            jp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x_l + SPI_JUMPER_DX), pcbnew.FromMM(y)))
            board.Add(jp)
            connect_pad(jp, 1, local)
            connect_pad(jp, 2, nets[bus])
            add_track(board, x_l, y, x_l + SPI_JUMPER_DX - 0.65, y, 0.25, pcbnew.F_Cu, local)
        add_label(board, "SPI", x_l + SPI_JUMPER_DX, drv_y + 1.0, size_mm=0.6)

        sock_r = pcbnew.FootprintLoad(LIB_SOCKET, "PinSocket_1x08_P2.54mm_Vertical")
        sock_r.SetReference(f"DRV_{axis_name}_R")
        sock_r.SetValue("Puissance")
        sock_r.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(cx + 6.35), pcbnew.FromMM(drv_y)))
        board.Add(sock_r)
        connect_pad(sock_r, 1, nets["+36V"])
        connect_pad(sock_r, 2, nets["GND"])
        connect_pad(sock_r, 3, nets[m_2b])
        connect_pad(sock_r, 4, nets[m_2a])
        connect_pad(sock_r, 5, nets[m_1a])
        connect_pad(sock_r, 6, nets[m_1b])
        connect_pad(sock_r, 7, nets["+3V3"])   # VIO = 3,3 V : niveau logique du Teensy
        connect_pad(sock_r, 8, nets["GND"])

        add_rect_silk(board, cx - 7.62, drv_y - 1.27, cx + 7.62, drv_y + 19.05, width_mm=0.2)
        lbl = pcbnew.PCB_TEXT(board)   # vertical, à droite des ponts SPI
        lbl.SetText(f"TMC5160 {axis_name}")
        lbl.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(cx + 2.6), pcbnew.FromMM(drv_y + 9)))
        lbl.SetLayer(pcbnew.F_SilkS)
        lbl.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.7), pcbnew.FromMM(0.7)))
        lbl.SetTextAngleDegrees(90)
        board.Add(lbl)
        add_label(board, "EN", cx - 9.0, drv_y, size_mm=0.6)
        add_label(board, "VM", cx + 9.0, drv_y, size_mm=0.6)

        # Condensateur moteur au-dessus du module (pas dessous : il n'y a que 8,5 mm sous un StepStick)
        cap = pcbnew.FootprintLoad(LIB_CAP, "CP_Radial_D10.0mm_P5.00mm")
        cap.SetReference(f"C_{axis_name}")
        cap.SetValue("220uF 63V")
        cap.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(cx - 2.5), pcbnew.FromMM(27.5)))
        board.Add(cap)
        connect_pad(cap, 1, nets["+36V"])
        connect_pad(cap, 2, nets["GND"])

        # Trous à souder pour driver externe (décalés à cx+13 pour ne pas toucher les textes du StepStick)
        ext_term = pcbnew.FootprintLoad(LIB_WIRE, "SolderWire-0.5sqmm_1x04_P4.6mm_D0.9mm_OD2.1mm")
        ext_term.SetReference(f"EXT_{axis_name}")
        ext_term.SetValue("Ext. Driver")
        ext_term.SetOrientationDegrees(90)
        ext_term.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(cx + 13.5), pcbnew.FromMM(30)))
        board.Add(ext_term)

        # Rotation 90° : pad 1 (GND) en bas à Y=30, pad 4 (EN) en haut à Y=16.2
        add_label(board, "EN", cx + 16.8, 16.2, size_mm=0.6)
        add_label(board, "STEP", cx + 16.8, 20.8, size_mm=0.6)
        add_label(board, "DIR", cx + 16.8, 25.4, size_mm=0.6)
        add_label(board, "GND", cx + 16.8, 30.0, size_mm=0.6)
        add_label(board, "DRIVER EXT. 5V", cx + 14, 33.4, size_mm=0.7)

        connect_pad(ext_term, 1, nets["GND"])
        connect_pad(ext_term, 2, nets[d_net + "_EXT"])   # via les tampons 5V 74HCT125 du sélecteur
        connect_pad(ext_term, 3, nets[s_net + "_EXT"])
        connect_pad(ext_term, 4, nets[e_net + "_EXT"])

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
    connect_pad(teensy, 43, nets["FOCUS_EN"])


    # =========================================================================
    # 5. CONNECTEURS PÉRIPHÉRIQUES FLANC DROIT (ALIGNÉS VERTICALEMENT AVEC REPERES)
    # =========================================================================
    # Connecteur vers Raquette (Centré à Y=45mm)
    raq = pcbnew.FootprintLoad(LIB_HEADER, "PinHeader_1x04_P2.54mm_Vertical")
    raq.SetReference("J_RAQUETTE")
    raq.SetValue("VERS RAQUETTE")
    raq.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(142), pcbnew.FromMM(45 - 3.81)))
    board.Add(raq)
    add_label(board, "[ RAQUETTE ]", 133.8, 38.8, size_mm=0.8)
    add_label(board, "1: GND", 133, 41.2, size_mm=0.65)
    add_label(board, "2: +5V", 133, 43.7, size_mm=0.65)
    add_label(board, "3: RX3",  134, 46.3, size_mm=0.65)
    add_label(board, "4: TX3",  134, 48.8, size_mm=0.65)
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

    # Connecteur vers PC (pastilles Y=16..23.62 : hors de la zone de vis du trou H2 à (145,5))
    pc_port = pcbnew.FootprintLoad(LIB_HEADER, "PinHeader_1x04_P2.54mm_Vertical")
    pc_port.SetReference("J_PC_SERIAL")
    pc_port.SetValue("PC SERIAL6")
    pc_port.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(142), pcbnew.FromMM(16.0)))
    board.Add(pc_port)
    add_label(board, "[ PC SERIAL ]", 142, 11.0, size_mm=0.8)
    add_label(board, "1 GND", 146.8, 16.0, size_mm=0.65)
    add_label(board, "2 +5V", 146.8, 18.54, size_mm=0.65)
    add_label(board, "3 TX6", 146.8, 21.08, size_mm=0.65)
    add_label(board, "4 RX6", 146.8, 23.62, size_mm=0.65)
    connect_pad(pc_port, 1, nets["GND"])
    connect_pad(pc_port, 2, nets["+5V"])
    connect_pad(pc_port, 3, nets["PC_RX"])
    connect_pad(pc_port, 4, nets["PC_TX"])

    buz = pcbnew.FootprintLoad(LIB_BUZZER, "Buzzer_12x9.5RM7.6")
    buz.SetReference("BZ1")
    buz.SetValue("Buzzer")
    buz.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(138), pcbnew.FromMM(88)))
    board.Add(buz)
    add_label(board, "BUZZER", 134, 80, size_mm=0.7)
    connect_pad(buz, 1, nets["BUZZER"])
    connect_pad(buz, 2, nets["GND"])

    # Guide de câblage sérigraphié sur le PCB (à droite des tampons du sélecteur)
    add_rect_silk(board, 119.5, 95, 140.8, 107, width_mm=0.15)
    add_label(board, "GUIDE CABLAGE MOTEURS :", 130.15, 96.3, size_mm=0.65)
    add_label(board, "- BOBINE 1 = GAUCHE [1B, 1A]", 130.15, 98.6, size_mm=0.55)
    add_label(board, "- BOBINE 2 = DROITE [2A, 2B]", 130.15, 100.9, size_mm=0.55)
    add_label(board, "* Tester au multimetre : ~1-3 Ohms par paire", 130.15, 103.2, size_mm=0.5)
    add_label(board, "* RX/TX = cote Teensy : croiser vers l'appareil", 130.15, 105.5, size_mm=0.5)

    # =========================================================================
    # 6. SÉLECTEUR PAR AXE STEPSTICK / DRIVER EXTERNE
    # SW_SEL (DIP x4) : OFF = StepStick (défaut), ON = driver externe ; SEL_x rappelé à +3V3 par RN_SEL.
    # 3 x 74HC126 (+3V3, OE actif haut) -> supports StepStick ; en mode externe sorties coupées et EN_INT
    # rappelé à +3V3 (module désactivé). 3 x 74HCT125 (+5V, OE actif bas) -> pastilles externes en 5 V
    # (optocoupleurs M542/DM542...). Mêmes broches Teensy : ni le plan de câblage ni le firmware ne changent.
    # Canal n -> axe n : (OE, A, Y) = (1,2,3) AZ, (4,5,6) ALT, (10,9,8) DEROT, (13,12,11) FOCUS ; 7 GND, 14 VCC.
    # =========================================================================
    sel_axes = ("AZ", "ALT", "DEROT", "FOCUS")
    sel_ch = ((1, 2, 3), (4, 5, 6), (10, 9, 8), (13, 12, 11))
    for side, value, vcc, y0 in (("INT", "74HC126", "+3V3", 90.0), ("EXT", "74HCT125", "+5V", 104.0)):
        for k, sig in enumerate(("STEP", "DIR", "EN")):
            x0 = 50.0 + 25.0 * k
            u = pcbnew.FootprintLoad(LIB_DIP, "DIP-14_W7.62mm")
            u.SetReference(f"U_{side}_{sig}")
            u.SetValue(value)
            u.SetOrientationDegrees(90)
            u.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x0), pcbnew.FromMM(y0)))
            board.Add(u)
            connect_pad(u, 7, nets["GND"])
            connect_pad(u, 14, nets[vcc])
            for ax, (oe, a, y) in zip(sel_axes, sel_ch):
                connect_pad(u, oe, nets[f"SEL_{ax}"])
                connect_pad(u, a, nets[f"{ax}_{sig}"])
                connect_pad(u, y, nets[f"{ax}_{sig}_{side}"])
            c = pcbnew.FootprintLoad(LIB_CAP, "C_Disc_D3.0mm_W1.6mm_P2.50mm")
            c.SetReference(f"C_{side}_{sig}")
            c.SetValue("100nF")
            c.SetOrientationDegrees(90)
            c.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x0 - 3.4), pcbnew.FromMM(y0 - 5.5)))
            board.Add(c)
            connect_pad(c, 1, nets["GND"])
            connect_pad(c, 2, nets[vcc])

    rn = pcbnew.FootprintLoad(LIB_RES, "R_Array_SIP9")
    rn.SetReference("RN_SEL")
    rn.SetValue("10k x8 (commun broche 1)")
    rn.SetOrientationDegrees(270)
    rn.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(108.0), pcbnew.FromMM(57.6)))
    board.Add(rn)
    connect_pad(rn, 1, nets["+3V3"])
    for i, ax in enumerate(sel_axes):
        connect_pad(rn, 2 + i, nets[f"SEL_{ax}"])
        connect_pad(rn, 6 + i, nets[f"{ax}_EN_INT"])

    sw = pcbnew.FootprintLoad(LIB_SWITCH, "SW_DIP_SPSTx04_Slide_9.78x12.34mm_W7.62mm_P2.54mm")
    sw.SetReference("SW_SEL")
    sw.SetValue("DIP x4")
    sw.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(113.0), pcbnew.FromMM(66.0)))
    board.Add(sw)
    for i, ax in enumerate(sel_axes):
        connect_pad(sw, 1 + i, nets[f"SEL_{ax}"])
        connect_pad(sw, 8 - i, nets["GND"])
    add_label(board, "SELECTEUR DRIVERS", 116.8, 62.0, size_mm=0.6)
    add_label(board, "ON = EXTERNE 5V / OFF = STEPSTICK", 117.5, 78.0, size_mm=0.5)
    for i, s in enumerate(("AZ", "ALT", "DER", "FOC")):
        add_label(board, s, 124.6, 66.0 + 2.54 * i, size_mm=0.6)
    add_label(board, "TAMPONS STEPSTICK 3,3V (74HC126)", 82.0, 80.2, size_mm=0.6)
    add_label(board, "TAMPONS DRIVERS EXTERNES 5V (74HCT125)", 82.0, 93.2, size_mm=0.6)

    # Empreinte Teensy41 : pad n (1..24) = rangée broches 0..12/24..32 (pad 1 = GND, pad 2 = broche 0,
    # pad 16 = broche 24, pad 17 = broche 25) ; pad 48 = VIN, 47 = GND, 46 = 3.3V, 45 = 23 ... 36 = 14
    connect_pad(teensy, 36, nets["RAQUETTE_TX"])   # broche 14 = TX3
    connect_pad(teensy, 37, nets["RAQUETTE_RX"])   # broche 15 = RX3
    connect_pad(teensy, 38, nets["GPS_RX"])        # broche 16 = RX4
    connect_pad(teensy, 39, nets["GPS_TX"])        # broche 17 = TX4
    connect_pad(teensy, 17, nets["PC_TX"])         # broche 25 = RX6 (reçoit le TX du PC)
    connect_pad(teensy, 16, nets["PC_RX"])         # broche 24 = TX6 (vers le RX du PC)
    connect_pad(teensy, 46, nets["+3V3"])          # 3.3V -> VIO des drivers
    # SPI1 vers les TMC5160 : MOSI1 = 26, SCK1 = 27, MISO1 = 39 (alternatif), CS = 41/40/38/37
    connect_pad(teensy, 18, nets["SPI_MOSI"])      # broche 26
    connect_pad(teensy, 19, nets["SPI_SCK"])       # broche 27
    connect_pad(teensy, 31, nets["SPI_MISO"])      # broche 39
    connect_pad(teensy, 33, nets["SPI_CS_AZ"])     # broche 41
    connect_pad(teensy, 32, nets["SPI_CS_ALT"])    # broche 40
    connect_pad(teensy, 30, nets["SPI_CS_DEROT"])  # broche 38
    connect_pad(teensy, 29, nets["SPI_CS_FOCUS"])  # broche 37
    connect_pad(teensy, 42, nets["BUZZER"])
    connect_pad(teensy, 47, nets["GND"])
    connect_pad(teensy, 48, nets["+5V"])

    board.BuildConnectivity()

    pcb_path = os.path.join(output_dir, "monture.kicad_pcb")
    pcbnew.SaveBoard(pcb_path, board)

    # Le .kicad_pro porte les classes de nets : sans la classe "Puissance", l'autorouteur
    # trace le +36V, le GND et les bobines moteur (jusqu'à 4 A) en 0,2 mm.
    pro_path = os.path.join(output_dir, "monture.kicad_pro")
    with open(pro_path, "w") as f:
        json.dump({"meta": {"filename": "monture.kicad_pro", "version": 1}, "boards": ["monture.kicad_pcb"], "sheets": [],
                   "net_settings": {"meta": {"version": 4},
                                    "classes": [DEFAULT_NETCLASS, POWER_NETCLASS],
                                    "netclass_patterns": [{"netclass": "Puissance", "pattern": p} for p in POWER_NET_PATTERNS]}},
                  f, indent=2)

    print(f"[OK] PCB Monture 36V créé : {pcb_path}")


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

    W, H = 105, 150
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
    lcd_conn.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(12), pcbnew.FromMM(100)))
    board.Add(lcd_conn)
    add_label(board, "I2C LCD", 8, 95, size_mm=0.9)
    add_label(board, "GND VCC SDA SCL", 4, 105, size_mm=0.7)
    connect_pad(lcd_conn, 1, nets["GND"])
    connect_pad(lcd_conn, 2, nets["+5V"])
    connect_pad(lcd_conn, 3, nets["I2C_SDA"])
    connect_pad(lcd_conn, 4, nets["I2C_SCL"])

    grove = pcbnew.FootprintLoad(LIB_HEADER, "PinHeader_1x04_P2.54mm_Vertical")
    grove.SetReference("J_GROVE")
    grove.SetValue("Grove I2C Aux")
    grove.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(93), pcbnew.FromMM(100)))
    board.Add(grove)
    add_label(board, "GROVE I2C", 87, 95, size_mm=0.9)
    add_label(board, "SCL SDA VCC GND", 84, 105, size_mm=0.7)
    connect_pad(grove, 1, nets["I2C_SCL"])
    connect_pad(grove, 2, nets["I2C_SDA"])
    connect_pad(grove, 3, nets["+5V"])
    connect_pad(grove, 4, nets["GND"])

    teensy = pcbnew.FootprintLoad(LIB_TEENSY, "Teensy41")
    teensy.SetReference("U1")
    teensy.SetValue("Teensy 4.1")
    teensy.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(lcd_cx), pcbnew.FromMM(85)))
    board.Add(teensy)
    add_label(board, "<- USB TEENSY 4.1", lcd_cx - 45, 85, size_mm=0.9)

    btn_cx = lcd_cx
    btn_cy = 120.0
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

    din = pcbnew.FootprintLoad(LIB_WIRE, "SolderWire-0.5sqmm_1x04_P4.8mm_D0.9mm_OD2.3mm")
    din.SetReference("J_DIN")
    din.SetValue("CABLE MONTURE")
    din.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(lcd_cx - 7.2), pcbnew.FromMM(143)))
    board.Add(din)
    add_label(board, "V CABLE VERS MONTURE (BAS) V", lcd_cx - 24, 139, size_mm=0.8)
    add_label(board, "1:GND   2:+5V   3:TX   4:RX", lcd_cx - 18, 147, size_mm=0.7)
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

    print("--- Génération PCB Monture 36V / 4A ---")
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
