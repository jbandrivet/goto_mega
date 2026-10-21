"""Module de guidage de GotoAndrivet, dans l'esprit de PHD2 et d'un ASIAIR : une deuxième caméra ZWO
(lunette guide ou diviseur optique) ou une caméra de guidage simulée, choix de l'étoile, calibration
automatique des deux axes sur le capteur, guidage par impulsions envoyées par le PC à la monture (:Mg sur
la liaison USB, sans câble ST-4), courbe des erreurs et dithering entre les poses du module photo.

Les impulsions :Mg ne sont acceptées par le firmware que pendant le suivi. En AltAz elles agissent sur
l'azimut et la hauteur, dont l'orientation sur le ciel tourne : la calibration n'y reste valable que peu
de temps. Le guidage est fait pour les montures équatoriales.
"""
import math
import random
import threading
import time
import tkinter as tk
from collections import deque
from datetime import datetime
from tkinter import ttk, messagebox

import numpy as np

from photo import SimCamera, ZwoCamera, list_cameras, autostretch, field_of_view, angular_dist

SIDEREAL_AS = 15.041            # vitesse sidérale en ″ d'arc par seconde de temps


# ════════════════════════════════════════════════════════════════
#  MESURE DES ÉTOILES (numpy seul)
# ════════════════════════════════════════════════════════════════
def _blur3(d):
    """Flou 3 × 3 : un pixel chaud isolé ne ressort plus comme une étoile."""
    p = np.pad(d, 1, mode="edge")
    h, w = d.shape
    return sum(p[i:i + h, j:j + w] for i in range(3) for j in range(3)) / 9.0


def centroid(img, x, y, r=12):
    """Barycentre de l'étoile dans une boîte de demi-côté r autour de (x, y), fond retiré.
    Renvoie {x, y, snr, mass, peak, npix} ou None si rien ne sort du fond."""
    h, w = img.shape
    yy, xx = np.mgrid[0:2 * r + 1, 0:2 * r + 1]
    s = win = None
    for _ in range(3):                                     # recentrage de la boîte
        x0, y0 = int(round(x)) - r, int(round(y)) - r
        if x0 < 0 or y0 < 0 or x0 + 2 * r + 1 > w or y0 + 2 * r + 1 > h:
            return None
        win = img[y0:y0 + 2 * r + 1, x0:x0 + 2 * r + 1].astype(np.float64)
        edge = np.concatenate((win[0], win[-1], win[1:-1, 0], win[1:-1, -1]))
        bg = float(np.median(edge)); noise = 1.4826 * float(np.median(np.abs(edge - bg))) or 1.0
        s = win - bg
        s[s < 3 * noise] = 0
        mass = float(s.sum())
        if mass <= 0:
            return None
        x, y = float((s * xx).sum()) / mass + x0, float((s * yy).sum()) / mass + y0
    npix = int((s > 0).sum())
    return {"x": x, "y": y, "snr": mass / (noise * math.sqrt(max(npix, 1))), "mass": mass,
            "peak": float(win.max()), "npix": npix}


def find_stars(img, n=15, r=12, saturation=60000):
    """Étoiles utilisables pour le guidage, la plus franche d'abord : ni saturées, ni pixels chauds,
    ni trop près du bord."""
    d = _blur3(img.astype(np.float32))
    med = float(np.median(d))
    work = d.copy()
    out = []
    for _ in range(n * 4):
        i = int(np.argmax(work)); y, x = divmod(i, work.shape[1])
        if work[y, x] <= med:
            break
        work[max(0, y - r):y + r + 1, max(0, x - r):x + r + 1] = med
        c = centroid(img, x, y, r)
        if c and c["snr"] > 10 and c["npix"] >= 4 and c["peak"] < saturation:
            out.append(c)
            if len(out) >= n:
                break
    return sorted(out, key=lambda c: -c["snr"])


# ════════════════════════════════════════════════════════════════
#  CAMÉRA DE GUIDAGE SIMULÉE
# ════════════════════════════════════════════════════════════════
class SimGuideCamera(SimCamera):
    """Caméra de guidage simulée (format d'une ASI120MM) sur le vrai ciel, avec une monture imparfaite :
    erreur périodique en AD, dérive des deux axes (mise en station imparfaite) et turbulence. Les impulsions
    de guidage agissent directement sur ce pointage simulé, comme le simulateur de PHD2."""
    name = "Caméra de guidage simulée"
    max_w, max_h, pixel_um = 1280, 960, 3.75
    bins = [1, 2]

    def __init__(self, pointing, focal_mm, bright_stars=(), rotation=lambda: 0.0):
        super().__init__(self._steady, focal_mm, bright_stars, rotation)
        # La position lue à la monture est arrondie (LX200 : 1 s d'AD = 15″) : on ne la suit qu'aux GoTo,
        # sinon le ciel simulé sauterait d'un arrondi à l'autre.
        self._live, self._base = pointing, None
        self._err0 = np.zeros(2); self._err_k = 0.0
        self.seeing_px = 1.1
        self.rate = 0.5                                    # vitesse de guidage, × sidéral
        self.t0 = time.time()
        self.off = np.zeros(2)                             # ″ d'axe (AD vers l'Est, Déc vers le Nord) des impulsions
        self.pe_amp, self.pe_period = 6.0, 240.0           # erreur périodique de l'axe AD (″, s)
        self.drift = np.array((0.025, -0.035))             # ″ d'axe par seconde
        self.jitter = 0.35                                 # turbulence, ″ sur le ciel par image
        self._rng = np.random.default_rng()

    def _steady(self):
        p = self._live()
        if self._base is None or angular_dist(self._base[0], self._base[1], p[0], p[1]) > 0.05:
            self._base = p
        return self._base

    def pulse(self, direction, ms):
        v = self.rate * SIDEREAL_AS * ms / 1000.0
        self.off += {"n": (0, v), "s": (0, -v), "e": (v, 0), "w": (-v, 0)}[direction]

    def error(self, ra_h, dec_d):
        """Écart (° d'AD, ° de Déc). Impulsions, dérive et erreur périodique tournent l'axe AD : sur le ciel,
        elles valent cos(Déc) fois moins, comme sur une vraie monture. La turbulence est sur le ciel."""
        t = time.time() - self.t0
        axis = self.off + self.drift * t
        axis[0] += self.pe_amp * math.sin(2 * math.pi * t / self.pe_period)
        sky = self._rng.normal(0, self.jitter, 2)
        return np.array((axis[0] + sky[0] / max(0.05, math.cos(math.radians(dec_d))), axis[1] + sky[1])) / 3600.0


# ════════════════════════════════════════════════════════════════
#  MOTEUR DE GUIDAGE (sans Tk)
# ════════════════════════════════════════════════════════════════
DEFAULTS = {"exp": 2.0, "gain": 200, "box": 12, "scale": 3.2, "rate": 0.5,
            "ra_aggr": 0.7, "ra_hyst": 0.1, "dec_aggr": 1.0, "min_move": 0.15, "max_pulse": 2500,
            "dec_mode": "auto", "cal_dist": 25.0, "settle_px": 1.5, "settle_s": 6.0}


class Guider:
    """Poses en boucle, calibration et guidage. `pulse(direction, ms)` envoie une impulsion (n, s, e, w),
    `dec_now()` donne la déclinaison du pointage (pour la vitesse de l'AD), `emit(img, mesure)` reçoit chaque
    image et `say(texte)` les messages d'état. Tout tourne dans le fil de travail de la fenêtre."""

    def __init__(self, camera, pulse, dec_now, emit, say, abort):
        self.cam, self.pulse, self.dec_now, self.emit, self.say = camera, pulse, dec_now, emit, say
        self.abort = abort
        self.p = dict(DEFAULTS)
        self.star = None                  # (x, y) de l'étoile guide
        self.lock = self.lock0 = None     # position de verrouillage (lock0 : avant dithering)
        self.cal = None
        self.guiding = False
        self.hist = deque(maxlen=600)     # (t, AD ″, Déc ″, impulsion AD ms signée, impulsion Déc ms signée)
        self.settled = threading.Event()
        self.want_select = None           # None, "auto" ou (x, y) : choix d'étoile demandé pour l'image suivante
        self.last = None                  # dernière image
        self._ra_prev = 0.0; self._dec_dir = None; self._dec_recent = deque(maxlen=3)
        self._settle_t0 = None

    # ── Poses ────────────────────────────────────────────────
    def frame(self):
        """Une pose ; suit l'étoile guide (ou la choisit si demandé). Renvoie la mesure, None si l'étoile
        n'est pas trouvée, et lève InterruptedError si la pose est interrompue."""
        self.cam.setup(int(self.p["gain"]), 1)
        img = self.cam.expose(float(self.p["exp"]), self.abort)
        if img is None:
            raise InterruptedError
        self.last = img
        if self.want_select is not None:
            self.select(img, self.want_select); self.want_select = None
        m = None
        if self.star is not None:
            m = centroid(img, *self.star, r=int(self.p["box"]))
            if m and m["snr"] < 5:
                m = None
            if m:
                self.star = (m["x"], m["y"])
        self.emit(img, m)
        return m

    def select(self, img, where="auto"):
        """Étoile la plus franche, ou la plus proche du point cliqué (x, y)."""
        stars = find_stars(img, r=int(self.p["box"]))
        if where != "auto":
            near = [s for s in stars if math.hypot(s["x"] - where[0], s["y"] - where[1]) < 3 * self.p["box"]]
            stars = sorted(near, key=lambda s: math.hypot(s["x"] - where[0], s["y"] - where[1])) or \
                [c for c in [centroid(img, where[0], where[1], int(self.p["box"]))] if c and c["snr"] > 5]
        if not stars:
            self.star = None; return None
        self.star = (stars[0]["x"], stars[0]["y"])
        if self.guiding:
            self.lock = self.lock0 = self.star
        return stars[0]

    def _wait(self, s):
        if self.abort.wait(max(0.0, s)):
            raise InterruptedError

    def loop(self):
        while True:
            self.frame()

    # ── Calibration ──────────────────────────────────────────
    def _step_ms(self, px_per_s):
        """Durée d'impulsion pour parcourir la distance de calibration en une douzaine de pas."""
        return int(min(3000, max(200, self.p["cal_dist"] / 12.0 / max(px_per_s, 1e-3) * 1000)))

    def _leg(self, direction, step, max_steps, until_px):
        """Impulsions répétées dans une direction jusqu'à `until_px` pixels ; renvoie (départ, arrivée, pas)."""
        m = self._need_star()
        start = pos = (m["x"], m["y"])
        n = 0
        while n < max_steps and math.hypot(pos[0] - start[0], pos[1] - start[1]) < until_px:
            self.pulse(direction, step); self._wait(step / 1000.0 + 0.3)
            m = self._need_star(); pos = (m["x"], m["y"]); n += 1
            self.say(("cal_step", direction, n, math.hypot(pos[0] - start[0], pos[1] - start[1])))
        return start, pos, n

    def _back(self, direction, step, n):
        """Retour au point de départ : autant d'impulsions que l'aller, l'étoile suivie à chaque pas
        (d'un seul coup, elle sortirait de la boîte de suivi)."""
        for i in range(n):
            self.pulse(direction, step); self._wait(step / 1000.0 + 0.3)
            self._need_star()
            self.say(("cal_back", direction, i + 1, n))

    def _need_star(self):
        for _ in range(3):
            m = self.frame()
            if m:
                return m
        raise RuntimeError("star_lost")

    def calibrate(self):
        """Comme PHD2 : impulsions vers l'Ouest jusqu'à ~25 px puis retour vers l'Est, rattrapage du jeu
        en déclinaison, impulsions vers le Nord puis retour vers le Sud. On en tire la direction et la
        vitesse (px/s) de chaque axe sur le capteur."""
        if self.star is None:
            self.want_select = "auto"
        self._need_star()
        dec = self.dec_now()
        v_dec = self.p["rate"] * SIDEREAL_AS / self.p["scale"]                  # px/s attendus en Déc
        v_ra = v_dec * max(0.15, math.cos(math.radians(dec)))
        step_ra, step_dec = self._step_ms(v_ra), self._step_ms(v_dec)
        a, b, n = self._leg("w", step_ra, 40, self.p["cal_dist"])
        d_ra = (b[0] - a[0], b[1] - a[1]); l_ra = math.hypot(*d_ra)
        if l_ra < 5:
            raise RuntimeError("cal_ra")
        ra_rate = l_ra / (n * step_ra / 1000.0)
        self._back("e", step_ra, n)
        self._leg("n", step_dec, 15, 3.0)                                       # rattrapage du jeu
        a, b, n = self._leg("n", step_dec, 40, self.p["cal_dist"])
        d_dec = (b[0] - a[0], b[1] - a[1]); l_dec = math.hypot(*d_dec)
        dec_ok = l_dec >= 5
        self._back("s", step_dec, n)
        ra_ang = math.degrees(math.atan2(d_ra[1], d_ra[0]))
        dec_ang = math.degrees(math.atan2(d_dec[1], d_dec[0])) if dec_ok else ra_ang + 90
        self.cal = {"ra_vec": (d_ra[0] / l_ra, d_ra[1] / l_ra), "ra_rate": ra_rate,
                    "dec_vec": (d_dec[0] / l_dec, d_dec[1] / l_dec) if dec_ok else
                    (-d_ra[1] / l_ra, d_ra[0] / l_ra),
                    "dec_rate": l_dec / (n * step_dec / 1000.0) if dec_ok and n else 0.0, "dec_ok": dec_ok,
                    "ra_angle": ra_ang, "dec_angle": dec_ang,
                    "ortho": (dec_ang - ra_ang + 180) % 360 - 180, "dec": dec,
                    "date": datetime.now().strftime("%d/%m %H:%M")}
        return self.cal

    # ── Guidage ──────────────────────────────────────────────
    def _axes(self, dx, dy):
        """Décompose un déplacement (px) sur les deux axes calibrés, qui ne sont pas forcément orthogonaux."""
        (ax, ay), (bx, by) = self.cal["ra_vec"], self.cal["dec_vec"]
        det = ax * by - ay * bx
        if abs(det) < 1e-6:
            return dx * ax + dy * ay, dx * bx + dy * by
        return (dx * by - dy * bx) / det, (ax * dy - ay * dx) / det

    def dither(self, px):
        """Décale la position de verrouillage d'au plus `px` pixels autour de la position d'origine."""
        if not self.guiding or self.lock0 is None:
            return False
        a, r = random.uniform(0, 2 * math.pi), px * random.uniform(0.5, 1.0)
        self.lock = (self.lock0[0] + r * math.cos(a), self.lock0[1] + r * math.sin(a))
        self.settled.clear(); self._settle_t0 = None
        return True

    def rms(self, n=50):
        """(AD, Déc, total) en ″ RMS sur les n dernières mesures."""
        h = list(self.hist)[-n:]
        if not h:
            return None
        ra = math.sqrt(sum(x[1] ** 2 for x in h) / len(h)); de = math.sqrt(sum(x[2] ** 2 for x in h) / len(h))
        return ra, de, math.hypot(ra, de)

    def guide(self):
        """Boucle de guidage : écart à la position de verrouillage, décomposé sur les axes, corrigé par
        impulsions (agressivité et hystérésis en AD, changement de sens retenu en Déc)."""
        if self.cal is None:
            raise RuntimeError("no_cal")
        if self.star is None:
            self.want_select = "auto"
        m = self._need_star()
        self.lock = self.lock0 = (m["x"], m["y"])
        self.guiding = True; self.settled.clear(); self._settle_t0 = None
        self._ra_prev = 0.0; self._dec_dir = None; self._dec_recent.clear()
        lost = 0
        try:
            while True:
                m = self.frame()
                if not m:
                    lost += 1
                    self.say(("lost", lost))
                    if lost >= 6:
                        raise RuntimeError("star_lost")
                    continue
                lost = 0
                self._correct(m)
        finally:
            self.guiding = False
            self.settled.set()

    def _correct(self, m):
        p, cal = self.p, self.cal
        dx, dy = m["x"] - self.lock[0], m["y"] - self.lock[1]
        ra_px, dec_px = self._axes(dx, dy)
        c0 = max(0.15, math.cos(math.radians(cal["dec"])))
        ra_rate = cal["ra_rate"] * max(0.15, math.cos(math.radians(self.dec_now()))) / c0
        # AD : agressivité et hystérésis, impulsion vers l'Est si l'étoile a filé dans le sens « Ouest »
        corr = (1 - p["ra_hyst"]) * ra_px * p["ra_aggr"] + p["ra_hyst"] * self._ra_prev
        self._ra_prev = corr
        ra_ms = 0
        if abs(corr) >= p["min_move"]:
            ra_ms = int(min(p["max_pulse"], abs(corr) / ra_rate * 1000))
        # Déc : on ne change de sens qu'après trois écarts de suite dans le nouveau sens
        dec_ms = 0; d_dir = None
        if cal["dec_ok"] and p["dec_mode"] != "off":
            dc = dec_px * p["dec_aggr"]
            if abs(dc) >= p["min_move"]:
                d_dir = "s" if dc > 0 else "n"
            self._dec_recent.append(d_dir)
            if d_dir and self._dec_dir and d_dir != self._dec_dir and \
                    not (len(self._dec_recent) == 3 and all(x == d_dir for x in self._dec_recent)):
                d_dir = None
            if d_dir and p["dec_mode"] in ("n", "s") and d_dir != p["dec_mode"]:
                d_dir = None
            if d_dir:
                self._dec_dir = d_dir
                dec_ms = int(min(p["max_pulse"], abs(dc) / cal["dec_rate"] * 1000))
        t0 = time.time()
        if ra_ms >= 20:
            self.pulse("e" if corr > 0 else "w", ra_ms)
        else:
            ra_ms = 0
        if dec_ms >= 20:
            self.pulse(d_dir, dec_ms)
        else:
            dec_ms = 0
        self.hist.append((time.time(), ra_px * p["scale"], dec_px * p["scale"],
                          ra_ms if corr > 0 else -ra_ms, dec_ms if d_dir == "s" else -dec_ms))
        # stabilisation après un dithering
        if math.hypot(dx, dy) <= p["settle_px"]:
            if self._settle_t0 is None:
                self._settle_t0 = time.time()
            elif time.time() - self._settle_t0 >= p["settle_s"]:
                self.settled.set()
        else:
            self._settle_t0 = None
        self.say(("guide",))
        self._wait(max(ra_ms, dec_ms) / 1000.0 - (time.time() - t0))         # impulsions finies avant la pose


# ════════════════════════════════════════════════════════════════
#  FENÊTRE
# ════════════════════════════════════════════════════════════════
TEXTS = {
    "fr": {
        "title": "GotoAndrivet — Guidage", "camera": "Caméra de guidage", "sim": "Caméra de guidage simulée",
        "connect": "Connecter", "disconnect": "Déconnecter", "focal": "Focale de guidage (mm) :",
        "scale": "{sc:.2f}″/px · champ {w:.2f}° × {h:.2f}°", "exposure": "Pose (s) :", "gain": "Gain :",
        "output": "Corrections", "out_note": "Envoyées par le PC à la monture (:Mg sur USB), sans câble ST-4.",
        "rate": "Vitesse (× sidéral) :", "apply": "Appliquer", "settings": "Réglages",
        "ra_aggr": "Agressivité AD (%) :", "dec_aggr": "Agressivité Déc (%) :", "min_move": "Seuil (px) :",
        "max_pulse": "Impulsion max (ms) :", "dec_mode": "Guidage Déc :",
        "dec_modes": ("Auto", "Nord seulement", "Sud seulement", "Arrêt"),
        "loop": "▶ Boucle", "auto_star": "Étoile auto", "calibrate": "Calibrer", "guide": "Guider", "stop": "■ Arrêter",
        "click": "Cliquez sur une étoile pour la choisir.",
        "no_cal": "Pas de calibration.", "cal_info": "Calibration du {date} (Déc {dec:+.0f}°)\nAD {ra:+.1f}° · {rr:.2f} px/s"
                   "\nDéc {da:+.1f}° · {dr:.2f} px/s\nAngle entre les axes : {o:+.1f}°",
        "cal_nodec": "\nDéclinaison : pas de mouvement mesuré, guidage en AD seulement.",
        "stats": "RMS AD {ra:.2f}″ · Déc {de:.2f}″ · total {t:.2f}″ ({n} images)",
        "ready": "Prêt.", "looping": "Boucle de poses.", "star": "Étoile : RSB {snr:.0f}, x {x:.1f} y {y:.1f}",
        "no_star": "Aucune étoile choisie.", "star_lost": "Étoile perdue.", "lost": "Étoile non trouvée ({n}/6)…",
        "cal_step": "Calibration {d} : pas {n}, {px:.1f} px", "cal_done": "Calibration terminée.",
        "cal_back": "Calibration, retour ({d}) : pas {n}/{m}",
        "cal_ra": "Calibration : l'étoile ne bouge pas en AD (suivi coupé, monture déconnectée, vitesse de guidage trop basse ?).",
        "guiding": "Guidage en cours.", "need_cam": "Connectez d'abord la caméra de guidage.",
        "need_cal": "Calibrez d'abord.", "need_track": "Le suivi de la monture doit être en marche (:Mg n'agit que pendant le suivi).",
        "altaz": "Monture AltAz : les impulsions agissent sur l'azimut et la hauteur, dont l'orientation tourne ; recalibrez souvent.",
        "pier": "Le côté du pilier a changé depuis la calibration : recalibrez.",
        "need_mount": "La monture n'est pas connectée : c'est elle qui reçoit les corrections.",
        "error": "Erreur : {e}", "stopped": "Arrêté.", "paused": "Guidage arrêté pour le GoTo.",
        "dither": "Dithering de {px:.1f} px…", "settled": "Stabilisé.", "rate_set": "Vitesse de guidage : {r}",
        "graph": "AD", "graph2": "Déc", "dirs": {"w": "Ouest", "e": "Est", "n": "Nord", "s": "Sud"},
        "in_use": "Cette caméra est déjà ouverte par le module photo.",
    },
    "en": {
        "title": "GotoAndrivet — Guiding", "camera": "Guide camera", "sim": "Simulated guide camera",
        "connect": "Connect", "disconnect": "Disconnect", "focal": "Guide focal length (mm):",
        "scale": "{sc:.2f}″/px · field {w:.2f}° × {h:.2f}°", "exposure": "Exposure (s):", "gain": "Gain:",
        "output": "Corrections", "out_note": "Sent by the PC to the mount (:Mg over USB), no ST-4 cable.",
        "rate": "Rate (× sidereal):", "apply": "Apply", "settings": "Settings",
        "ra_aggr": "RA aggressiveness (%):", "dec_aggr": "Dec aggressiveness (%):", "min_move": "Min move (px):",
        "max_pulse": "Max pulse (ms):", "dec_mode": "Dec guiding:",
        "dec_modes": ("Auto", "North only", "South only", "Off"),
        "loop": "▶ Loop", "auto_star": "Auto star", "calibrate": "Calibrate", "guide": "Guide", "stop": "■ Stop",
        "click": "Click a star to select it.",
        "no_cal": "No calibration.", "cal_info": "Calibration of {date} (Dec {dec:+.0f}°)\nRA {ra:+.1f}° · {rr:.2f} px/s"
                   "\nDec {da:+.1f}° · {dr:.2f} px/s\nAngle between axes: {o:+.1f}°",
        "cal_nodec": "\nDeclination: no motion measured, RA-only guiding.",
        "stats": "RMS RA {ra:.2f}″ · Dec {de:.2f}″ · total {t:.2f}″ ({n} frames)",
        "ready": "Ready.", "looping": "Looping exposures.", "star": "Star: SNR {snr:.0f}, x {x:.1f} y {y:.1f}",
        "no_star": "No star selected.", "star_lost": "Star lost.", "lost": "Star not found ({n}/6)…",
        "cal_step": "Calibration {d}: step {n}, {px:.1f} px", "cal_done": "Calibration done.",
        "cal_back": "Calibration, back {d}: step {n}/{m}",
        "cal_ra": "Calibration: the star does not move in RA (tracking off, mount disconnected, guide rate too low?).",
        "guiding": "Guiding.", "need_cam": "Connect the guide camera first.",
        "need_cal": "Calibrate first.", "need_track": "Mount tracking must be on (:Mg only works while tracking).",
        "altaz": "AltAz mount: pulses move azimuth and altitude, whose orientation rotates; recalibrate often.",
        "pier": "The pier side changed since calibration: recalibrate.",
        "need_mount": "The mount is not connected: it receives the corrections.",
        "error": "Error: {e}", "stopped": "Stopped.", "paused": "Guiding stopped for the GoTo.",
        "dither": "Dithering by {px:.1f} px…", "settled": "Settled.", "rate_set": "Guide rate: {r}",
        "graph": "RA", "graph2": "Dec", "dirs": {"w": "West", "e": "East", "n": "North", "s": "South"},
        "in_use": "This camera is already open in the photo module.",
    },
}
DEC_MODES = ("auto", "n", "s", "off")


class GuideWindow(tk.Toplevel):
    """Fenêtre de guidage. `app` fournit cfg, mount, et les méthodes guide_* / photo_* de la carte du ciel."""

    def __init__(self, app, colors):
        super().__init__(app)
        self.app, self.cfg, self.c = app, app.cfg, colors
        self.t = TEXTS.get(self.cfg.get("language", "fr"), TEXTS["fr"])
        self.title(self.t["title"]); self.geometry("1250x820"); self.minsize(1000, 680)
        self.configure(bg=colors["BG"])
        self.camera = None; self.guider = None
        self.abort = threading.Event(); self.busy = False; self.mode = None
        self._img = None; self._meas = None; self._tkimg = None; self._disp = None
        self._build()
        self.protocol("WM_DELETE_WINDOW", self.close)
        self._refresh_cameras(); self._update_scale(); self._show_cal()
        if self.cfg.get("mount_type", "AltAz") == "AltAz":
            self._status(self.t["altaz"])

    # ── Construction ──────────────────────────────────────────
    def _frame(self, parent, title):
        f = ttk.LabelFrame(parent, text=f" {title} ", padding=4); f.pack(fill=tk.X, padx=6, pady=3); return f

    def _row(self, parent):
        r = tk.Frame(parent, bg=self.c["BG2"]); r.pack(fill=tk.X, pady=1); return r

    def _lbl(self, parent, text, width=20):
        tk.Label(parent, text=text, bg=self.c["BG2"], fg=self.c["DIM"], font=self.c["FS"], width=width,
                 anchor="w").pack(side=tk.LEFT)

    def _note(self, parent, fg=None):
        l = tk.Label(parent, text="", bg=self.c["BG2"], fg=fg or self.c["DIM"], font=self.c["FS"], justify="left",
                     anchor="w", wraplength=330)
        l.pack(fill=tk.X); return l

    def _spin(self, parent, var, lo, hi, inc, width=7):
        ttk.Spinbox(parent, from_=lo, to=hi, increment=inc, textvariable=var, width=width,
                    font=self.c["FS"]).pack(side=tk.LEFT, padx=2)

    def _build(self):
        c, t = self.c, self.t
        left = tk.Frame(self, bg=c["BG2"], width=370); left.pack(side=tk.LEFT, fill=tk.Y); left.pack_propagate(False)
        right = tk.Frame(self, bg=c["BG"]); right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        f = self._frame(left, t["camera"])
        r = self._row(f)
        self.v_cam = tk.StringVar()
        self.cb_cam = ttk.Combobox(r, textvariable=self.v_cam, state="readonly", width=21, font=c["FS"])
        self.cb_cam.pack(side=tk.LEFT, padx=2)
        ttk.Button(r, text="↺", width=3, command=self._refresh_cameras).pack(side=tk.LEFT, padx=2)
        self.b_conn = ttk.Button(r, text=t["connect"], command=self._toggle_camera); self.b_conn.pack(side=tk.LEFT, padx=2)
        self.l_info = self._note(f)
        r = self._row(f); self._lbl(r, t["focal"], 23)
        self.v_focal = tk.StringVar(value=f"{float(self.cfg.get('guide_focal_mm', 240)):g}")
        e = ttk.Entry(r, textvariable=self.v_focal, width=6, font=c["FS"]); e.pack(side=tk.LEFT, padx=2)
        e.bind("<FocusOut>", lambda ev: self._update_scale()); e.bind("<Return>", lambda ev: self._update_scale())
        self.l_scale = self._note(f, c["ACC"])
        r = self._row(f); self._lbl(r, t["exposure"], 9)
        self.v_exp = tk.DoubleVar(value=float(self.cfg.get("guide_exposure", 2.0)))
        self._spin(r, self.v_exp, 0.1, 10, 0.5, 5)
        self._lbl(r, t["gain"], 6)
        self.v_gain = tk.IntVar(value=int(self.cfg.get("guide_gain", 200)))
        self._spin(r, self.v_gain, 0, 600, 10, 5)

        f = self._frame(left, t["output"])
        self._note(f).configure(text=t["out_note"])
        r = self._row(f); self._lbl(r, t["rate"], 21)
        self.v_rate = tk.DoubleVar(value=float(self.cfg.get("guide_rate", 0.5)))
        self._spin(r, self.v_rate, 0.1, 1.0, 0.05, 5)
        ttk.Button(r, text=t["apply"], command=self._apply_rate).pack(side=tk.LEFT, padx=2)

        f = self._frame(left, t["settings"])
        self.v_set = {}
        for key, lo, hi, inc, default in (("ra_aggr", 10, 100, 5, 70), ("dec_aggr", 10, 100, 5, 100),
                                          ("min_move", 0.05, 2.0, 0.05, 0.15), ("max_pulse", 100, 5000, 100, 2500)):
            r = self._row(f); self._lbl(r, t[key], 21)
            v = (tk.DoubleVar if key == "min_move" else tk.IntVar)(value=self.cfg.get("guide_" + key, default))
            self.v_set[key] = v
            self._spin(r, v, lo, hi, inc, 6)
        r = self._row(f); self._lbl(r, t["dec_mode"], 14)
        self.v_decmode = tk.StringVar()
        self.cb_dec = ttk.Combobox(r, textvariable=self.v_decmode, values=t["dec_modes"], state="readonly", width=16, font=c["FS"])
        self.cb_dec.pack(side=tk.LEFT, padx=2)
        mode = self.cfg.get("guide_dec_mode", "auto")
        self.v_decmode.set(t["dec_modes"][DEC_MODES.index(mode) if mode in DEC_MODES else 0])

        f = self._frame(left, t["guide"])
        r = self._row(f)
        for i, (key, cmd, style) in enumerate((("loop", self._loop, "TButton"), ("auto_star", self._auto_star, "TButton"),
                                                ("calibrate", self._calibrate, "TButton"))):
            r.columnconfigure(i, weight=1, uniform="g")
            ttk.Button(r, text=t[key], style=style, command=cmd).grid(row=0, column=i, sticky="ew", padx=1)
        r = self._row(f)
        ttk.Button(r, text=t["guide"], style="GoTo.TButton", command=self._guide).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)
        ttk.Button(r, text=t["stop"], style="Stop.TButton", command=self.stop).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)
        self.l_star = self._note(f, c["TXT"]); self.l_star.configure(text=t["click"])
        self.l_cal = self._note(f)
        self.l_stats = tk.Label(f, text="", bg=c["BG2"], fg=c["GRN"], font=("Helvetica", 11, "bold"), anchor="w",
                                justify="left", wraplength=330)
        self.l_stats.pack(fill=tk.X, pady=2)

        self.canvas = tk.Canvas(right, bg="#000000", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=4, pady=(4, 2))
        self.canvas.bind("<Configure>", lambda e: self._show())
        self.canvas.bind("<Button-1>", self._click)
        self.graph = tk.Canvas(right, bg="#060a12", height=210, highlightthickness=0)
        self.graph.pack(fill=tk.X, padx=4, pady=2)
        self.graph.bind("<Configure>", lambda e: self._plot())
        sb = tk.Frame(right, bg=c["BG"]); sb.pack(fill=tk.X)
        self.l_status = tk.Label(sb, text=t["ready"], bg=c["BG"], fg=c["DIM"], font=c["FS"], anchor="w")
        self.l_status.pack(side=tk.LEFT, padx=8, pady=2)

    # ── Caméra ───────────────────────────────────────────────
    def _refresh_cameras(self):
        names = list_cameras() + [self.t["sim"]]
        self.cb_cam.configure(values=names)
        if self.v_cam.get() not in names:
            # par défaut, une caméra autre que celle du module photo
            used = self.app.photo_camera_name()
            free = [n for n in names if n != used]
            self.v_cam.set(free[0] if free else names[0])

    def _focal(self):
        try: return max(1.0, float(self.v_focal.get().replace(",", ".")))
        except ValueError: return 240.0

    def _scale(self):
        cam = self.camera or SimGuideCamera
        return field_of_view(cam.pixel_um, 1, cam.max_w, cam.max_h, self._focal())

    def _update_scale(self):
        self.cfg.set("guide_focal_mm", self._focal())
        sc, w, h = self._scale()
        self.l_scale.configure(text=self.t["scale"].format(sc=sc, w=w, h=h))

    def _toggle_camera(self):
        if self.camera:
            self.stop(); self._after_idle(self._disconnect); return
        try:
            name = self.v_cam.get()
            if name == self.t["sim"]:
                self.camera = SimGuideCamera(self._pointing, self._focal, self.app.photo_bright_stars(),
                                             rotation=lambda: float(self.cfg.get("guide_sim_rotation", 23.0)))
                self.camera.rate = float(self.v_rate.get())
            else:
                if name == self.app.photo_camera_name():
                    messagebox.showwarning(self.t["title"], self.t["in_use"], parent=self); return
                self.camera = ZwoCamera(list_cameras().index(name))
        except Exception as e:
            self.camera = None; messagebox.showerror(self.t["title"], self.t["error"].format(e=e), parent=self); return
        cam = self.camera
        self.guider = Guider(cam, self._pulse, self._dec_now, self._emit, self._say, self.abort)
        saved = self.cfg.get("guide_cal")
        if saved and saved.get("camera") == cam.name and abs(saved.get("focal", 0) - self._focal()) < 1:
            self.guider.cal = {k: (tuple(v) if isinstance(v, list) else v) for k, v in saved.items()}
        self.l_info.configure(text=f"{cam.name} · {cam.max_w} × {cam.max_h} px · {cam.pixel_um:.2f} µm")
        self.b_conn.configure(text=self.t["disconnect"])
        self._update_scale(); self._show_cal()
        if not cam.simulated:
            r = self.app.guide_rate()
            if r: self.v_rate.set(r)

    def _disconnect(self):
        if self.camera:
            self.camera.close()
        self.camera = None; self.guider = None
        self.b_conn.configure(text=self.t["connect"]); self.l_info.configure(text="")

    def _pointing(self):
        return self.app.photo_pointing() or self.app.photo_sky_center()

    def _dec_now(self):
        return self._pointing()[1]

    def _pulse(self, direction, ms):
        """Envoie une impulsion : à la caméra simulée, sinon à la monture par le PC (:Mg)."""
        if self.camera.simulated:
            self.camera.pulse(direction, ms)
        else:
            self.app.guide_pulse(direction, ms)

    # ── Fil de travail ───────────────────────────────────────
    def _ui(self, fn):
        try: self.after(0, fn)
        except (tk.TclError, RuntimeError): pass

    def _after_idle(self, fn, tries=60):
        """Exécute fn quand le fil de travail s'est arrêté."""
        if self.busy and tries:
            self.after(100, lambda: self._after_idle(fn, tries - 1))
        else:
            fn()

    def _params(self):
        g = self.guider
        sc, _, _ = self._scale()
        dm = self.t["dec_modes"].index(self.v_decmode.get()) if self.v_decmode.get() in self.t["dec_modes"] else 0
        g.p.update({"exp": float(self.v_exp.get()), "gain": int(self.v_gain.get()), "scale": sc,
                    "rate": float(self.v_rate.get()), "ra_aggr": self.v_set["ra_aggr"].get() / 100.0,
                    "dec_aggr": self.v_set["dec_aggr"].get() / 100.0, "min_move": self.v_set["min_move"].get(),
                    "max_pulse": self.v_set["max_pulse"].get(), "dec_mode": DEC_MODES[dm]})
        for k in ("ra_aggr", "dec_aggr", "min_move", "max_pulse"):
            self.cfg.set("guide_" + k, self.v_set[k].get())
        self.cfg.set("guide_exposure", g.p["exp"]); self.cfg.set("guide_gain", g.p["gain"])
        self.cfg.set("guide_dec_mode", DEC_MODES[dm]); self.cfg.set("guide_rate", g.p["rate"])

    def _start(self, mode, job, msg=None):
        """Lance un mode (boucle, calibration, guidage), après l'arrêt du précédent."""
        if not self.camera:
            messagebox.showwarning(self.t["title"], self.t["need_cam"], parent=self); return
        try:
            self._params()
        except (tk.TclError, ValueError) as e:
            self._status(self.t["error"].format(e=e)); return
        if self.busy:
            self.abort.set(); self._after_idle(lambda: self._start(mode, job, msg)); return
        self.busy = True; self.mode = mode; self.abort.clear()
        if msg:
            self._status(msg)

        def work():
            try:
                job()
            except InterruptedError:
                self._ui(lambda: self._status(self.t["stopped"]))
            except RuntimeError as e:
                key = str(e)
                self._ui(lambda: self._status(self.t.get(key, self.t["error"].format(e=key))))
                if key == "star_lost":
                    self._ui(lambda: messagebox.showwarning(self.t["title"], self.t["star_lost"], parent=self))
            except Exception as e:
                self._ui(lambda err=e: self._status(self.t["error"].format(e=err)))
            finally:
                self.busy = False; self.mode = None
                self._ui(self._show_stats)
        threading.Thread(target=work, daemon=True, name="guidage").start()

    def stop(self):
        self.abort.set()

    def _loop(self):
        self._start("loop", self.guider.loop if self.guider else None, self.t["looping"])

    def _auto_star(self):
        """Choisit l'étoile la plus franche sur la prochaine image (lance la boucle si besoin)."""
        if not self.guider:
            return self._start("loop", None)
        self.guider.want_select = "auto"
        if not self.busy:
            self._loop()

    def _click(self, e):
        if not self._disp or self._img is None or not self.guider:
            return
        ox, oy, k = self._disp
        where = ((e.x - ox) / k, (e.y - oy) / k)
        if self.busy:
            self.guider.want_select = where
        else:
            self.guider.select(self._img, where); self._show()

    def _checks_mount(self):
        """Monture connectée et suivi en marche : elle reçoit les impulsions :Mg."""
        if self.camera and self.camera.simulated:
            return True
        if not self.app.mount.state.connected:
            messagebox.showwarning(self.t["title"], self.t["need_mount"], parent=self); return False
        if not self.app.mount.state.tracking:
            messagebox.showwarning(self.t["title"], self.t["need_track"], parent=self); return False
        return True

    def _calibrate(self):
        if not self.guider:
            return self._start("calib", None)
        if not self._checks_mount():
            return
        def job():
            cal = self.guider.calibrate()
            cal.update({"camera": self.camera.name, "focal": self._focal(), "pier": self.app.guide_pier_side()})
            self.cfg.set("guide_cal", cal)
            self._ui(lambda: (self._show_cal(), self._status(self.t["cal_done"])))
            self.guider.loop()
        self._start("calib", job)

    def _guide(self):
        if not self.guider:
            return self._start("guide", None)
        if not self.guider.cal:
            messagebox.showwarning(self.t["title"], self.t["need_cal"], parent=self); return
        if not self._checks_mount():
            return
        pier = self.guider.cal.get("pier")
        if pier and pier != self.app.guide_pier_side():
            messagebox.showwarning(self.t["title"], self.t["pier"], parent=self); return
        self.guider.hist.clear()
        self._start("guide", self.guider.guide, self.t["guiding"])

    def _apply_rate(self):
        r = round(float(self.v_rate.get()), 2)
        self.cfg.set("guide_rate", r)
        if self.camera and self.camera.simulated:
            self.camera.rate = r
        resp = self.app.set_guide_rate(r)
        self._status(self.t["rate_set"].format(r=f"{r:.2f} ({resp or '—'})"))

    # ── API pour la carte et le module photo ─────────────────
    def is_guiding(self):
        return bool(self.guider and self.guider.guiding)

    def pause_for_goto(self):
        """Un GoTo emporte l'étoile guide : on arrête le guidage (la calibration reste)."""
        if self.is_guiding():
            self.abort.set(); self._status(self.t["paused"])

    def dither(self, px, timeout=90.0):
        """Dithering puis attente de la stabilisation ; appelé depuis le fil du module photo."""
        g = self.guider
        if not (g and g.dither(px)):
            return False
        self._ui(lambda: self._status(self.t["dither"].format(px=px)))
        ok = g.settled.wait(timeout) and g.guiding
        if ok:
            self._ui(lambda: self._status(self.t["settled"]))
        return ok

    # ── Affichage ────────────────────────────────────────────
    def _emit(self, img, m):
        self._img, self._meas = img, m
        self._ui(self._refresh)

    def _say(self, msg):
        kind = msg[0]
        if kind == "cal_step":
            self._ui(lambda: self._status(self.t["cal_step"].format(d=self.t["dirs"][msg[1]], n=msg[2], px=msg[3])))
        elif kind == "cal_back":
            self._ui(lambda: self._status(self.t["cal_back"].format(d=self.t["dirs"][msg[1]], n=msg[2], m=msg[3])))
        elif kind == "lost":
            self._ui(lambda: self._status(self.t["lost"].format(n=msg[1])))
        elif kind == "guide":
            self._ui(lambda: (self._plot(), self._show_stats()))

    def _refresh(self):
        self._show()
        m = self._meas
        if m:
            self.l_star.configure(text=self.t["star"].format(snr=m["snr"], x=m["x"], y=m["y"]))
        elif self.guider and self.guider.star is None:
            self.l_star.configure(text=self.t["click"])

    def _show(self):
        img = self._img
        if img is None:
            return
        try:
            from PIL import Image, ImageTk
        except ImportError:
            return
        W, H = max(self.canvas.winfo_width(), 50), max(self.canvas.winfo_height(), 50)
        pic = Image.fromarray(autostretch(img))
        k = min(W / pic.width, H / pic.height)
        pic = pic.resize((max(1, int(pic.width * k)), max(1, int(pic.height * k))), Image.LANCZOS)
        self._tkimg = ImageTk.PhotoImage(pic)
        ox, oy = (W - pic.width) / 2, (H - pic.height) / 2
        self._disp = (ox, oy, pic.width / img.shape[1])
        cv = self.canvas
        cv.delete("all")
        cv.create_image(ox, oy, image=self._tkimg, anchor="nw")
        g = self.guider
        if not g:
            return
        s = self._disp[2]
        if g.star:
            x, y = ox + g.star[0] * s, oy + g.star[1] * s
            r = max(10, g.p["box"] * s)
            cv.create_rectangle(x - r, y - r, x + r, y + r, outline="#2ee86a", width=1.5)
        if g.guiding and g.lock:
            x, y = ox + g.lock[0] * s, oy + g.lock[1] * s
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                cv.create_line(x + dx * 5, y + dy * 5, x + dx * 22, y + dy * 22, fill="#ffd400")

    def _plot(self):
        """Courbe des écarts AD (bleu) et Déc (rouge) en ″, avec les impulsions en barres."""
        cv = self.graph
        cv.delete("all")
        W, H = cv.winfo_width(), cv.winfo_height()
        if W < 50:
            return
        h = list(self.guider.hist)[-150:] if self.guider else []
        lim = max([2.0] + [abs(v) * 1.2 for x in h for v in (x[1], x[2])])
        lim = min(lim, 30.0)
        y0, ky = H / 2, (H / 2 - 14) / lim
        step = 1 if lim <= 4 else (2 if lim <= 10 else 5)
        for v in range(-int(lim), int(lim) + 1):
            if v % step == 0:
                yy = y0 - v * ky
                cv.create_line(40, yy, W, yy, fill="#1a2840" if v else "#33507a")
                cv.create_text(36, yy, text=f"{v}″", fill="#4a6a8a", font=("Helvetica", 8), anchor="e")
        cv.create_text(48, 8, text=self.t["graph"], fill="#4fa3ff", font=("Helvetica", 9, "bold"), anchor="w")
        cv.create_text(80, 8, text=self.t["graph2"], fill="#ff5a5a", font=("Helvetica", 9, "bold"), anchor="w")
        if len(h) < 2:
            return
        dx = (W - 44) / 149.0
        mp = max(1.0, max(abs(x[3]) for x in h), max(abs(x[4]) for x in h))
        for i, x in enumerate(h):                                   # impulsions
            xx = 44 + i * dx
            if x[3]: cv.create_line(xx - 1, y0, xx - 1, y0 - x[3] / mp * 30, fill="#24456e", width=2)
            if x[4]: cv.create_line(xx + 1, y0, xx + 1, y0 - x[4] / mp * 30, fill="#6e2430", width=2)
        for idx, col in ((1, "#4fa3ff"), (2, "#ff5a5a")):
            pts = []
            for i, x in enumerate(h):
                pts += [44 + i * dx, y0 - max(-lim, min(lim, x[idx])) * ky]
            cv.create_line(*pts, fill=col, width=1.5)

    def _show_stats(self):
        g = self.guider
        r = g.rms() if g else None
        self.l_stats.configure(text=self.t["stats"].format(ra=r[0], de=r[1], t=r[2], n=min(50, len(g.hist))) if r else "")

    def _show_cal(self):
        cal = self.guider.cal if self.guider else None
        if not cal:
            self.l_cal.configure(text=self.t["no_cal"]); return
        txt = self.t["cal_info"].format(date=cal["date"], dec=cal["dec"], ra=cal["ra_angle"], rr=cal["ra_rate"],
                                        da=cal["dec_angle"], dr=cal["dec_rate"], o=cal["ortho"])
        self.l_cal.configure(text=txt + ("" if cal["dec_ok"] else self.t["cal_nodec"]))

    def _status(self, txt):
        self.l_status.configure(text=txt)

    def close(self):
        self.abort.set()
        for _ in range(60):
            if not self.busy: break
            self.update(); time.sleep(0.05)
        if self.camera:
            self.camera.close(); self.camera = None
        self.destroy()
