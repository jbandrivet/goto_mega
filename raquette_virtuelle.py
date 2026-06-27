#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk
import serial
import serial.tools.list_ports
import time
import math
import sys
import os
from datetime import datetime, timezone

# Ajouter le répertoire courant au chemin d'importation
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from goto_universal import ALL_CATALOGS, Astro, Settings
import ephem

class VirtualTeensyApp(tk.Tk):
    def __init__(self):
        super().__init__()
        # Charger les paramètres globaux (coordonnées GPS du site)
        self.cfg = Settings()
        lang = self.cfg.get("language", "fr")
        if lang == "en":
            self.title("Virtual T4.1 Hand Controller")
        else:
            self.title("Raquette T4.1 Virtuelle")
        self.geometry("380x540")
        self.configure(bg="#c0c0c0")
        self.resizable(False, False)
        
        self.lat = self.cfg.get("latitude", 45.764)
        self.lon = self.cfg.get("longitude", 4.836)
        self.alt_min = self.cfg.get("alt_min_deg", 2.0)
        
        # Connexion série
        self.ser = None
        self.port = ""
        self.sim_mode = False
        
        # Coordonnées simulées (utilisées si sim_mode est True)
        self.sim_ra = 12.0      # Heures
        self.sim_dec = 45.0     # Degrés
        self.sim_slewing = False
        self.sim_tracking = True
        
        # Variables de télémétrie courantes (affichées à l'écran)
        self.current_ra = "12:00:00"
        self.current_dec = "+45*00:00"
        self.is_slewing = False
        self.target_ra = None
        self.target_dec = None
        
        # Chargement de la base de données céleste
        self.db_cat = {}
        self.load_db()
        
        # États de l'interface graphique (raquette)
        self.UI_MAIN = 0
        self.UI_CAT_SELECT = 1
        self.UI_OBJECT_LIST = 2
        self.UI_OBJECT_INFO = 3
        self.UI_SLEWING = 4
        self.UI_SETTINGS = 5
        self.UI_SPEED = 6
        self.UI_MESSAGE = 7
        self.UI_BEEP = 8
        self.UI_MOTOR_POWER = 9
        self.UI_LANGUAGE = 10
        self.UI_MOUNT = 11
        self.UI_RATIO_AZ = 12
        self.UI_RATIO_ALT = 13
        self.UI_ALIGN_CENTER = 14
        
        self.motor_power = True
        self.temp_motor_power = True
        self.temp_lang = "fr"
        self.temp_mount_type = 0
        self.temp_ratio_az = self.cfg.get("gear_ratio_az", 750.0)
        self.temp_ratio_alt = self.cfg.get("gear_ratio_alt", 750.0)
        
        self.state = self.UI_MAIN
        self.is_align_workflow = False
        
        self.catalogs = ["Messier", "NGC", "IC", "Caldwell", "Systeme Solaire", "Étoiles"]
        self.cat_idx = 0
        
        self.obj_list = []
        self.obj_idx = 0
        self.current_cat_name = None
        
        self.settings_sel = 0
        self.current_speed = 2.0
        self.buzzer_on = True
        self.temp_speed = 2.0
        self.temp_buzzer_on = True
        
        self.msg_until = 0
        self.msg_return_state = 0
        self.is_connected = False
        
        # File d'attente pour commandes asynchrones (GoTo)
        self.cmd_queue = []
        
        # États des touches clavier / boutons souris pour le déplacement continu (slew)
        self.press_active = {"UP": False, "DOWN": False, "LEFT": False, "RIGHT": False}
        self.key_release_timers = {"UP": None, "DOWN": None, "LEFT": None, "RIGHT": None}
        
        # Construction de l'interface graphique
        self.build_ui()
        
        # Bindings clavier locaux et globaux (pour garantir la capture sous tout gestionnaire de fenêtres)
        self.bind("<KeyPress>", self.on_key_press)
        self.bind("<KeyRelease>", self.on_key_release)
        self.bind_all("<KeyPress>", self.on_key_press)
        self.bind_all("<KeyRelease>", self.on_key_release)
        
        # Liaison clavier supplémentaire sur tous les boutons pour intercepter les touches s'ils prennent le focus
        for btn in (self.b_up, self.b_down, self.b_left, self.b_right):
            btn.bind("<KeyPress>", self.on_key_press)
            btn.bind("<KeyRelease>", self.on_key_release)
        
        # Permettre le défilement par molette de souris sur l'application
        self.bind("<MouseWheel>", self.on_mouse_wheel)  # Windows/macOS
        self.bind("<Button-4>", self.on_mouse_wheel)    # Linux scroll up
        self.bind("<Button-5>", self.on_mouse_wheel)    # Linux scroll down
        
        # Forcer le rendu de la fenêtre et réclamer le focus clavier immédiatement après affichage
        self.update()
        self.focus_force()
        self.after(150, lambda: self.focus_set())
        
        # Démarrage des boucles d'arrière-plan
        self.check_connection_loop()
        self.telemetry_loop()
        self.update_lcd()

    def load_db(self):
        try:
            now = datetime.now(timezone.utc)
            obs = ephem.Observer()
            obs.lat = str(self.lat)
            obs.lon = str(self.lon)
            obs.date = now
            
            planets = [
                ("Soleil", ephem.Sun()),
                ("Lune", ephem.Moon()),
                ("Mercure", ephem.Mercury()),
                ("Venus", ephem.Venus()),
                ("Mars", ephem.Mars()),
                ("Jupiter", ephem.Jupiter()),
                ("Saturne", ephem.Saturn()),
                ("Uranus", ephem.Uranus()),
                ("Neptune", ephem.Neptune()),
            ]
            
            sys_sol = []
            for i, (name, p) in enumerate(planets):
                p.compute(obs)
                ra = float(p.ra) * 12.0 / math.pi
                dec = float(p.dec) * 180.0 / math.pi
                mag = getattr(p, 'mag', 0)
                sys_sol.append({"id": i, "ra": ra, "dec": dec, "mag": round(mag,1), "type": "Planete", "name": name, "cat": "SysSol", "num": name})
                
            self.db_cat = {}
            for k, v in ALL_CATALOGS.items():
                self.db_cat[k] = v
            self.db_cat["Systeme Solaire"] = sys_sol
            
        except Exception as e:
            print(f"Erreur chargement base de donnees: {e}")
            self.db_cat = {}
            self.catalogs = ["Erreur DB"]

    def build_ui(self):
        # Fonts
        f_title = ("MS Sans Serif", 10, "bold")
        f_label = ("MS Sans Serif", 9)
        f_lcd = ("Courier New", 13, "bold")
        
        # 1. Custom Active Window Title Bar (Win95 look)
        title_bar = tk.Frame(self, bg="#000080", height=24) # Dark blue
        title_bar.pack(fill="x", side="top", padx=2, pady=2)
        title_bar.pack_propagate(False)

        title_lbl = tk.Label(title_bar, text=" Raquette Virtuelle T4.1", bg="#000080", fg="white", font=f_title, anchor="w")
        title_lbl.pack(side="left", fill="both", expand=True)

        close_btn = tk.Button(title_bar, text="X", bg="#c0c0c0", fg="black", font=("Arial", 8, "bold"), bd=1, relief="raised", command=self.destroy, width=2, height=1)
        close_btn.pack(side="right", padx=2, pady=2)

        # Main window inner container with a 3D sunken border
        main_border = tk.Frame(self, bg="#c0c0c0", bd=2, relief="raised")
        main_border.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        main_container = tk.Frame(main_border, bg="#c0c0c0")
        main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # Connection status in a sunken box
        conn_frame = tk.Frame(main_container, bg="white", bd=2, relief="sunken", height=24)
        conn_frame.pack(fill="x", pady=(0, 5))
        conn_frame.pack_propagate(False)
        self.conn_lbl = tk.Label(conn_frame, text="Recherche port USB...", bg="white", fg="red", font=f_label, anchor="w", padx=5)
        self.conn_lbl.pack(fill="both", expand=True)
        
        # Boîtier de l'écran LCD (sunken border)
        lcd_case = tk.Frame(main_container, bg="#c0c0c0", bd=2, relief="sunken")
        lcd_case.pack(pady=10, fill="x")
        
        # Écran LCD matriciel retro rouge
        lcd_frame = tk.Frame(lcd_case, bg="#ff0000", padx=10, pady=10)
        lcd_frame.pack(fill="both", expand=True)
        
        self.lcd_lines = []
        for i in range(2):
            lbl = tk.Label(
                lcd_frame, 
                text=" "*16, 
                bg="#ff0000", 
                fg="#000000", 
                font=f_lcd, 
                width=16, 
                anchor="w", 
                padx=2, 
                pady=1
            )
            lbl.pack(fill="x")
            self.lcd_lines.append(lbl)
            
        # Clavier physique (Boutons)
        pad_frame = tk.Frame(main_container, bg="#c0c0c0")
        pad_frame.pack(pady=10, fill="both", expand=True)
        
        # Grid D-Pad (Direction)
        dpad_container = tk.Frame(pad_frame, bg="#c0c0c0")
        dpad_container.pack(side="top", pady=5)
        
        # Décoration D-Pad
        dpad_bg = tk.Frame(dpad_container, bg="#c0c0c0", bd=2, relief="sunken")
        dpad_bg.pack(padx=5, pady=5)
        
        # Boutons D-Pad
        btn_style = {
            "font": ("MS Sans Serif", 12, "bold"),
            "bg": "#c0c0c0",
            "fg": "black",
            "activebackground": "#d9d9d9",
            "activeforeground": "black",
            "bd": 2,
            "relief": tk.RAISED,
            "width": 4,
            "height": 2,
            "highlightthickness": 0,
            "takefocus": False
        }
        
        # UP
        self.b_up = tk.Button(dpad_bg, text="▲", **btn_style)
        self.b_up.grid(row=0, column=1, padx=4, pady=4)
        
        # LEFT
        self.b_left = tk.Button(dpad_bg, text="◀", **btn_style)
        self.b_left.grid(row=1, column=0, padx=4, pady=4)
        
        # CENTER (Bouton central faisant office de touche validation ENTER)
        self.b_center = tk.Button(dpad_bg, text="◆", **btn_style)
        self.b_center.configure(command=lambda: self.handle_btn("ENTER"))
        self.b_center.grid(row=1, column=1, padx=4, pady=4)
        
        # RIGHT
        self.b_right = tk.Button(dpad_bg, text="▶", **btn_style)
        self.b_right.grid(row=1, column=2, padx=4, pady=4)
        
        # DOWN
        self.b_down = tk.Button(dpad_bg, text="▼", **btn_style)
        self.b_down.grid(row=2, column=1, padx=4, pady=4)
        
        # Liaison des événements souris (clic et relâchement) pour le déplacement manuel
        self.b_up.bind("<ButtonPress-1>", lambda e: self.on_press("UP"))
        self.b_up.bind("<ButtonRelease-1>", lambda e: self.on_release("UP"))
        
        self.b_down.bind("<ButtonPress-1>", lambda e: self.on_press("DOWN"))
        self.b_down.bind("<ButtonRelease-1>", lambda e: self.on_release("DOWN"))
        
        self.b_left.bind("<ButtonPress-1>", lambda e: self.on_press("LEFT"))
        self.b_left.bind("<ButtonRelease-1>", lambda e: self.on_release("LEFT"))
        
        self.b_right.bind("<ButtonPress-1>", lambda e: self.on_press("RIGHT"))
        self.b_right.bind("<ButtonRelease-1>", lambda e: self.on_release("RIGHT"))
        
        # Ajout d'effet hover interactif pour les boutons
        for btn in (self.b_up, self.b_down, self.b_left, self.b_right, self.b_center):
            btn.bind("<Enter>", lambda e, b=btn: self.on_btn_hover(b))
            btn.bind("<Leave>", lambda e, b=btn: self.on_btn_leave(b))

    def on_btn_hover(self, btn):
        btn.configure(bg="#d9d9d9")

    def on_btn_leave(self, btn):
        btn.configure(bg="#c0c0c0")

    # Mappage des touches du clavier PC (insensible à la casse)
    def keysym_to_btn(self, keysym):
        k = keysym.lower()
        if k == "up": return "UP"
        if k == "down": return "DOWN"
        if k == "left": return "LEFT"
        if k == "right": return "RIGHT"
        if k in ("return", "kp_enter", "space", "enter"): return "ENTER"
        if k in ("escape", "backspace"): return "BACK"
        return None

    def on_key_press(self, event):
        btn = self.keysym_to_btn(event.keysym)
        if not btn: return
        
        # Si c'est une touche de direction
        if btn in ("UP", "DOWN", "LEFT", "RIGHT"):
            if self.state == self.UI_MAIN:
                # Annuler le timer de relâchement s'il y en a un (anti-rebond du repeat OS)
                if self.key_release_timers[btn] is not None:
                    self.after_cancel(self.key_release_timers[btn])
                    self.key_release_timers[btn] = None
                
                # Déclencher l'action si elle n'est pas déjà active
                if not self.press_active[btn]:
                    self.on_press(btn)
            else:
                # Dans les menus, la navigation se fait par impulsion simple
                if not self.press_active[btn]:
                    self.press_active[btn] = True
                    self.handle_btn(btn)
        elif btn == "ENTER":
            self.handle_btn("ENTER")
        elif btn == "BACK":
            self.handle_btn("LEFT")
            
        return "break"

    def on_key_release(self, event):
        btn = self.keysym_to_btn(event.keysym)
        if not btn: return
        
        if btn in ("UP", "DOWN", "LEFT", "RIGHT"):
            if self.state == self.UI_MAIN:
                # Anti-rebond (debounce) : attend 50ms pour confirmer le relâchement réel
                if self.key_release_timers[btn] is not None:
                    self.after_cancel(self.key_release_timers[btn])
                self.key_release_timers[btn] = self.after(50, lambda b=btn: self.trigger_key_release(b))
            else:
                self.press_active[btn] = False
                
        return "break"

    def trigger_key_release(self, btn):
        self.key_release_timers[btn] = None
        self.on_release(btn)

    def on_mouse_wheel(self, event):
        # Gestion du scroll molette souris sur les listes (Catalogs, Objects, Settings)
        if self.state in (self.UI_CAT_SELECT, self.UI_OBJECT_LIST, self.UI_SETTINGS):
            if event.num == 4 or event.delta > 0:
                self.handle_btn("UP")
            elif event.num == 5 or event.delta < 0:
                self.handle_btn("DOWN")

    def check_connection_loop(self):
        if not hasattr(self, 'conn_state'):
            self.conn_state = "disconnected"
            self.conn_start_time = 0
            self.conn_port = ""

        if not self.is_connected:
            if self.conn_state == "disconnected":
                ports = [p.device for p in serial.tools.list_ports.comports()]
                arduino_ports = [p for p in ports if "USB" in p or "ACM" in p]
                if arduino_ports:
                    port = arduino_ports[0]
                    try:
                        self.ser = serial.Serial(port, 38400, timeout=0.5)
                        self.conn_state = "connecting"
                        self.conn_start_time = time.time()
                        self.conn_port = port
                        self.conn_lbl.config(text=f"Connexion: {port}...", fg="#ffcc00")
                    except Exception as e:
                        if hasattr(self, 'ser') and self.ser:
                            try: self.ser.close()
                            except: pass
                        self.ser = None
                else:
                    # Mode simulation automatique si aucun matériel physique n'est détecté
                    self.is_connected = True
                    self.sim_mode = True
                    self.port = "SIMULATEUR"
                    self.conn_lbl.config(text="Connecte: SIMULATEUR", fg="#00e5ff")
                    self.update_lcd()
            
            elif self.conn_state == "connecting":
                # Attendre 2.2 secondes pour que l'Arduino ait terminé sa phase de reboot
                if time.time() - self.conn_start_time > 2.2:
                    try:
                        self.ser.reset_input_buffer()
                        self.ser.write(b":GVP#")
                        resp = self.ser.read_until(b"#").decode('ascii', errors='ignore')
                        if "OnStep" in resp or "On-Step" in resp or "GotoUniversal" in resp or resp.strip():
                            self.is_connected = True
                            self.sim_mode = False
                            self.port = self.conn_port
                            self.conn_lbl.config(text=f"Connecte: {self.conn_port}", fg="#39ff14")
                            self.conn_state = "connected"
                            self.sync_clock()
                            self.update_lcd()
                        else:
                            self.ser.close()
                            self.ser = None
                            self.conn_state = "disconnected"
                    except Exception as e:
                        if self.ser:
                            try: self.ser.close()
                            except: pass
                        self.ser = None
                        self.conn_state = "disconnected"

        # Relancer la boucle toutes les 250ms pendant la phase de connexion pour rester réactif
        if not self.is_connected or self.conn_state == "connecting":
            self.after(250, self.check_connection_loop)
        elif not self.sim_mode:
            self.after(2000, self.check_connection_loop)

    def sync_clock(self):
        if self.is_connected and self.ser and not self.sim_mode:
            try:
                now = datetime.now()
                # 1. Date
                self.ser.write(f":SC{now.month:02d}/{now.day:02d}/{now.year%100:02d}#".encode('ascii'))
                time.sleep(0.1)
                
                # 2. Time
                self.ser.write(f":SL{now.hour:02d}:{now.minute:02d}:{now.second:02d}#".encode('ascii'))
                time.sleep(0.1)
                
                # 3. Timezone
                utc_offset = -time.timezone / 3600.0
                if time.daylight and time.localtime().tm_isdst:
                    utc_offset = -time.altzone / 3600.0
                sign = '+' if utc_offset >= 0 else '-'
                self.ser.write(f":SG{sign}{int(abs(utc_offset)):02d}#".encode('ascii'))
                time.sleep(0.1)
                
                # 4. Slew speed
                self.ser.write(b":Bv#")
                time.sleep(0.1)
                if self.ser.in_waiting:
                    speed_raw = self.ser.read_until(b"#").decode('ascii', errors='ignore').strip('#')
                    try:
                        self.current_speed = int(speed_raw) / 10.0
                        print(f"Slew speed synchronized from Arduino EEPROM: {self.current_speed} deg/s")
                    except:
                        pass
                
                # Vider le tampon de réception
                if self.ser.in_waiting:
                    self.ser.read(self.ser.in_waiting)
                print("PC clock synchronized with Arduino OnStep.")
            except Exception as e:
                print(f"Error synchronizing clock: {e}")

    def telemetry_loop(self):
        if self.is_connected:
            if self.sim_mode:
                # Boucle de simulation locale de la monture
                if self.is_slewing and self.target_ra is not None:
                    # Rapprocher le télescope simulé de la cible
                    dist_ra = self.target_ra - self.sim_ra
                    dist_dec = self.target_dec - self.sim_dec
                    step_size = self.current_speed * 0.1 # Vitesse par pas de 100ms
                    
                    # Déplacement angulaire 2D
                    dist = math.hypot(dist_ra, dist_dec)
                    if dist <= step_size:
                        self.sim_ra = self.target_ra
                        self.sim_dec = self.target_dec
                        self.is_slewing = False
                        if self.state == self.UI_SLEWING:
                            self.state = self.UI_MAIN
                    else:
                        self.sim_ra += (dist_ra / dist) * step_size
                        self.sim_dec += (dist_dec / dist) * step_size
                
                # Déplacement manuel continu simulé
                man_step = 0.5 # Degrés par pas de 100ms
                if self.press_active["UP"]: self.sim_dec = min(90.0, self.sim_dec + man_step)
                if self.press_active["DOWN"]: self.sim_dec = max(-90.0, self.sim_dec - man_step)
                if self.press_active["LEFT"]: self.sim_ra = (self.sim_ra + man_step/15.0) % 24.0
                if self.press_active["RIGHT"]: self.sim_ra = (self.sim_ra - man_step/15.0) % 24.0
                
                # Formatage des données de simulation
                self.current_ra = Astro.fmt_ra_lx(self.sim_ra)
                self.current_dec = Astro.fmt_dec_lx(self.sim_dec)
                self.update_lcd()
            else:
                # Mode réel série
                if not self.cmd_queue and self.state in (self.UI_MAIN, self.UI_SLEWING):
                    try:
                        self.ser.write(b":GR#")
                        resp = self.ser.read_until(b"#").decode('ascii', errors='ignore').strip('#')
                        if resp: self.current_ra = resp
                        
                        self.ser.write(b":GD#")
                        resp = self.ser.read_until(b"#").decode('ascii', errors='ignore').strip('#')
                        if resp: self.current_dec = resp
                        
                        self.ser.write(b":GBE#")
                        resp = self.ser.read_until(b"#").decode('ascii', errors='ignore').strip('#')
                        if resp:
                            parts = resp.split(',')
                            if len(parts) >= 8:
                                self.is_slewing = (parts[1] == '1')
                                if self.is_slewing:
                                    if self.state != self.UI_SLEWING:
                                        self.state = self.UI_SLEWING
                                    # Recouvrer les coordonnées cibles depuis le Mega
                                    try:
                                        self.ser.write(b":Gr#")
                                        t_ra = self.ser.read_until(b"#").decode('ascii', errors='ignore').strip('#')
                                        if t_ra:
                                            self.target_ra = Astro.parse_ra(t_ra)
                                        
                                        self.ser.write(b":Gd#")
                                        t_dec = self.ser.read_until(b"#").decode('ascii', errors='ignore').strip('#')
                                        if t_dec:
                                            self.target_dec = Astro.parse_dec(t_dec)
                                    except Exception:
                                        pass
                                elif not self.is_slewing and self.state == self.UI_SLEWING:
                                    if getattr(self, "is_align_workflow", False):
                                        self.state = self.UI_ALIGN_CENTER
                                        self.is_align_workflow = False
                                    else:
                                        self.state = self.UI_MAIN
                        
                        self.update_lcd()
                    except Exception as e:
                        pass
                
        self.after(100, self.telemetry_loop) # Vitesse de rafraîchissement 100ms pour une réactivité optimale
        
    def process_queue(self):
        if not self.is_connected: return
        if self.sim_mode:
            is_goto = any(":MS#" in c for c in self.cmd_queue)
            self.cmd_queue.clear()
            if is_goto:
                self.is_slewing = True
                if getattr(self, "is_align_workflow", False):
                    self.after(3000, self.finish_sim_slew)  # Simulate slew delay
                if self.state != self.UI_MESSAGE:
                    self.state = self.UI_SLEWING
            self.update_lcd()
            return

    def finish_sim_slew(self):
        self.is_slewing = False
        if getattr(self, "is_align_workflow", False):
            self.state = self.UI_ALIGN_CENTER
            self.is_align_workflow = False
        else:
            self.state = self.UI_MAIN
        self.update_lcd()
            
        if not self.cmd_queue: return
        cmd = self.cmd_queue.pop(0)
        try:
            self.ser.write(cmd.encode('ascii'))
            self.after(150, self.finish_queue_cmd)
        except Exception:
            self.is_connected = False
            self.cmd_queue.clear()

    def finish_queue_cmd(self):
        if not self.is_connected: return
        try:
            if self.ser.in_waiting:
                self.ser.read(self.ser.in_waiting)
        except:
            pass
        if self.cmd_queue:
            self.process_queue()
        else:
            if self.state != self.UI_MESSAGE:
                self.state = self.UI_SLEWING
            self.update_lcd()

    def send_cmd(self, cmd):
        if self.is_connected:
            if self.sim_mode:
                # Traiter les commandes manuelles du simulateur
                if cmd == ":Mn#": self.press_active["UP"] = True
                elif cmd == ":Ms#": self.press_active["DOWN"] = True
                elif cmd == ":Me#": self.press_active["LEFT"] = True
                elif cmd == ":Mw#": self.press_active["RIGHT"] = True
                elif cmd in (":Q#", ":Qn#", ":Qs#", ":Qe#", ":Qw#"):
                    if cmd in (":Q#", ":Qn#"): self.press_active["UP"] = False
                    if cmd in (":Q#", ":Qs#"): self.press_active["DOWN"] = False
                    if cmd in (":Q#", ":Qe#"): self.press_active["LEFT"] = False
                    if cmd in (":Q#", ":Qw#"): self.press_active["RIGHT"] = False
                    self.is_slewing = False
            else:
                try:
                    self.ser.write(cmd.encode('ascii'))
                except Exception:
                    self.is_connected = False
                    self.conn_lbl.config(text="Deconnecte", fg="#ff3b30")

    def on_press(self, btn):
        if self.state in (self.UI_MAIN, self.UI_ALIGN_CENTER):
            if self.is_connected:
                if not self.press_active.get(btn, False):
                    self.press_active[btn] = True
                    # Configurer l'aspect visuel pressé du bouton
                    if btn == "UP":
                        self.b_up.configure(relief=tk.SUNKEN, bg="#d9d9d9")
                        self.send_cmd(":Mn#")
                    elif btn == "DOWN":
                        self.b_down.configure(relief=tk.SUNKEN, bg="#d9d9d9")
                        self.send_cmd(":Ms#")
                    elif btn == "LEFT":
                        self.b_left.configure(relief=tk.SUNKEN, bg="#d9d9d9")
                        self.send_cmd(":Me#")
                    elif btn == "RIGHT":
                        self.b_right.configure(relief=tk.SUNKEN, bg="#d9d9d9")
                        self.send_cmd(":Mw#")
        else:
            # Dans les autres états, un clic équivaut à handle_btn
            self.handle_btn(btn)

    def on_release(self, btn):
        if self.state in (self.UI_MAIN, self.UI_ALIGN_CENTER):
            # Rétablir le relief des boutons
            if btn == "UP": self.b_up.configure(relief=tk.RAISED, bg="#c0c0c0")
            elif btn == "DOWN": self.b_down.configure(relief=tk.RAISED, bg="#c0c0c0")
            elif btn == "LEFT": self.b_left.configure(relief=tk.RAISED, bg="#c0c0c0")
            elif btn == "RIGHT": self.b_right.configure(relief=tk.RAISED, bg="#c0c0c0")
            
            if self.is_connected and self.press_active.get(btn, False):
                self.press_active[btn] = False
                if btn == "UP": self.send_cmd(":Qn#")
                elif btn == "DOWN": self.send_cmd(":Qs#")
                elif btn == "LEFT": self.send_cmd(":Qe#")
                elif btn == "RIGHT": self.send_cmd(":Qw#")
        else:
            self.press_active[btn] = False

    def set_msg(self, l0, l1, l2, l3, duration_ms, return_state):
        self.lcd_lines[0].config(text=f"{l0:<16}"[:16])
        self.lcd_lines[1].config(text=f"{l1:<16}"[:16])
        self.state = self.UI_MESSAGE
        self.msg_return_state = return_state
        self.msg_until = time.time() + duration_ms/1000.0
        self.after(duration_ms, self.check_msg_timeout)
        
    def check_msg_timeout(self):
        if self.state == self.UI_MESSAGE and time.time() >= self.msg_until:
            self.state = self.msg_return_state
            self.update_lcd()

    def update_lcd(self):
        if self.state == self.UI_MESSAGE: return
        
        l0 = l1 = " "*16
        lang = self.cfg.get("language", "fr")
        
        if self.state == self.UI_MAIN:
            ra_short = self.current_ra[:5].replace(':', 'h')
            dec_short = self.current_dec[:6].replace('*', '°')
            l0 = f"R{ra_short} D{dec_short}"[:16]
            if self.is_connected:
                stat = "OK" if not self.sim_mode else "SIMU"
                l1 = f"MNT {stat} [ENT=MNU]"[:16]
            else:
                l1 = "OFFLINE         "
            
        elif self.state == self.UI_CAT_SELECT:
            l0 = "[ CHOIX CATALOG]" if lang == "fr" else "[ SELECT CATAL.]"
            cat_name = self.catalogs[self.cat_idx]
            count = len(self.db_cat.get(cat_name, []))
            disp_cat = cat_name
            if lang == "en":
                if cat_name == "Systeme Solaire": disp_cat = "Solar Sys"
                elif cat_name == "Étoiles": disp_cat = "Stars"
            l1 = f">{disp_cat[:9]:<9}({count})"[:16]
            
        elif self.state == self.UI_OBJECT_LIST:
            cat_name = self.catalogs[self.cat_idx]
            disp_cat = cat_name
            if lang == "en":
                if cat_name == "Systeme Solaire": disp_cat = "Sol"
                elif cat_name == "Étoiles": disp_cat = "Star"
            else:
                disp_cat = disp_cat[:3]
                
            l0 = f"[{disp_cat}] {len(self.obj_list)}obj"[:16]
            
            if len(self.obj_list) == 0:
                l1 = " Aucun objet    " if lang == "fr" else " No object      "
            else:
                o = self.obj_list[self.obj_idx]
                name = o.get('name', f"{o.get('cat')} {o.get('num')}")
                if name == f"{o.get('cat')} {o.get('num')}": name = f"{disp_cat} {o.get('num')}"
                vis_star = "*" if o.get("visible", False) else ""
                mag_str = f"m{o.get('mag')}" if o.get('mag') else ""
                l1 = f">{name[:8]}{vis_star} {mag_str}"[:16]
                
        elif self.state == self.UI_OBJECT_INFO:
            o = self.obj_list[self.obj_idx]
            name = o.get('name', f"{o.get('cat')} {o.get('num')}")
            vis_star = "*" if o.get("visible", False) else ""
            l0 = f">{name[:14]:<14}{vis_star}"[:16]
            l1 = "E=GOTO  >=SYNC  "
            
        elif self.state == self.UI_SLEWING:
            anim_chars = ['*', '+', 'x', '+']
            anim = anim_chars[int(time.time() * 4) % 4]
            l0 = f"GOTO {anim}        " if lang == "fr" else f"SLEWING {anim}     "
            if self.target_ra is not None:
                try:
                    c_ra = Astro.parse_ra(self.current_ra)
                    c_dec = Astro.parse_dec(self.current_dec)
                    dist = Astro.angular_dist(c_ra, c_dec, self.target_ra, self.target_dec)
                    eta = dist / self.current_speed
                    l1 = f"E:{int(eta)}s D:{dist:.1f}°"[:16]
                except:
                    l1 = " Patientez...   " if lang == "fr" else " Please wait... "
            else:
                l1 = " Patientez...   " if lang == "fr" else " Please wait... "
                
        elif self.state == self.UI_ALIGN_CENTER:
            o = self.obj_list[self.obj_idx]
            name = o.get('name', f"{o.get('cat')} {o.get('num')}")
            l0 = f"Centrez {name[:8]}"[:16].ljust(16) if lang == "fr" else f"Center {name[:9]}"[:16].ljust(16)
            l1 = "   ENT=SYNC     "[:16]
            
        elif self.state == self.UI_SETTINGS:
            l0 = "[ MENU ]        " if lang == "fr" else "[ MENU ]        "
            az_str = " Ratio AZ" if self.cfg.get("mount_type", "AltAz") == "AltAz" else " Ratio RA"
            alt_str = " Ratio ALT" if self.cfg.get("mount_type", "AltAz") == "AltAz" else " Ratio DEC"
            
            if lang == "en":
                az_str = " AZ Ratio" if self.cfg.get("mount_type", "AltAz") == "AltAz" else " RA Ratio"
                alt_str = " ALT Ratio" if self.cfg.get("mount_type", "AltAz") == "AltAz" else " DEC Ratio"
                
            opts = [" Catalogues", " Vitesse", " Bips", " Alignement", " Parking", " Type Monture", az_str, alt_str, " Alim Moteurs", " Langue"] if lang == "fr" else [" Catalogs", " Speed", " Beeps", " Alignment", " Parking", " Mount Type", az_str, alt_str, " Motor Power", " Language"]
            l1 = f">{opts[self.settings_sel][1:]:15}"[:16]
            
        elif self.state == self.UI_SPEED:
            l0 = "[ VITESSE GOTO ]" if lang == "fr" else "[ GOTO SPEED ]  "
            l1 = f"> {self.temp_speed:.1f} deg/s   "[:16]
            
        elif self.state == self.UI_BEEP:
            l0 = "[ BIP BUZZER ]  " if lang == "fr" else "[ BEEP BUZZER ] "
            state_str = "ON" if self.temp_buzzer_on else "OFF"
            l1 = f"> {state_str}         "[:16]
            
        elif self.state == self.UI_MOTOR_POWER:
            l0 = "[ ALIM MOTEURS ]" if lang == "fr" else "[ MOTOR POWER ] "
            status = ("ACTIVE" if self.temp_motor_power else "OFF") if lang == "fr" else ("ON" if self.temp_motor_power else "OFF")
            l1 = f"> {status:<14}"[:16]
                
        elif self.state == self.UI_LANGUAGE:
            l0 = "[ LANGUE ]      " if lang == "fr" else "[ LANGUAGE ]    "
            l1 = f">{('FRANCAIS' if self.temp_lang == 'fr' else 'ENGLISH'):15}"[:16]
            
        elif self.state == self.UI_MOUNT:
            l0 = "[ TYPE MONTURE ]" if lang == "fr" else "[ MOUNT TYPE ]  "
            mount_str = "AltAz" if self.temp_mount_type == 0 else ("ForkEq" if self.temp_mount_type == 1 else "GermanEq")
            l1 = f"> {mount_str:13}"[:16]
            
        elif self.state == self.UI_RATIO_AZ:
            is_altaz = (self.cfg.get("mount_type", "AltAz") == "AltAz")
            lbl = "RATIO AZ" if is_altaz else "RATIO RA"
            if lang == "en": lbl = "AZ RATIO" if is_altaz else "RA RATIO"
            l0 = f"[ {lbl} ]"[:16].ljust(16)
            l1 = f"> {self.temp_ratio_az:.1f}         "[:16]
            
        elif self.state == self.UI_RATIO_ALT:
            is_altaz = (self.cfg.get("mount_type", "AltAz") == "AltAz")
            lbl = "RATIO ALT" if is_altaz else "RATIO DEC"
            if lang == "en": lbl = "ALT RATIO" if is_altaz else "DEC RATIO"
            l0 = f"[ {lbl} ]"[:16].ljust(16)
            l1 = f"> {self.temp_ratio_alt:.1f}         "[:16]
                
        self.lcd_lines[0].config(text=f"{l0:<16}"[:16])
        self.lcd_lines[1].config(text=f"{l1:<16}"[:16])

    def get_visible_stars(self):
        try:
            now = datetime.now(timezone.utc)
            obs = ephem.Observer()
            obs.lat = str(self.lat)
            obs.lon = str(self.lon)
            obs.date = now
            stars = self.db_cat.get("Étoiles", [])
            visible = []
            for s in stars:
                body = ephem.FixedBody()
                body._ra = s['ra'] * math.pi / 12.0
                body._dec = s['dec'] * math.pi / 180.0
                body.compute(obs)
                alt = float(body.alt) * 180.0 / math.pi
                if 15.0 < alt < 80.0:
                    visible.append(s)
            visible.sort(key=lambda x: x.get('mag', 10.0))
            return visible if visible else stars
        except:
            return self.db_cat.get("Étoiles", [])

    def get_catalog_with_visibility(self, cat_name):
        try:
            now = datetime.now(timezone.utc)
            obs = ephem.Observer()
            obs.lat = str(self.lat)
            obs.lon = str(self.lon)
            obs.date = now
            raw_list = self.db_cat.get(cat_name, [])
            enriched = []
            for s in raw_list:
                s_copy = s.copy()
                body = ephem.FixedBody()
                body._ra = s['ra'] * math.pi / 12.0
                body._dec = s['dec'] * math.pi / 180.0
                body.compute(obs)
                if (float(body.alt) * 180.0 / math.pi) > self.alt_min:
                    s_copy['visible'] = True
                else:
                    s_copy['visible'] = False
                enriched.append(s_copy)
            
            if cat_name not in ("Systeme Solaire", "Étoiles"):
                enriched.sort(key=lambda x: int(x.get('num', 0)) if str(x.get('num','0')).isdigit() else 0)
                
            return enriched
        except Exception as e:
            print(f"ERROR in get_catalog_with_visibility: {e}")
            return self.db_cat.get(cat_name, [])

    def handle_btn(self, btn):
        if self.state == self.UI_MESSAGE:
            self.state = self.msg_return_state
            self.msg_until = 0
            self.update_lcd()
            return
            
        if self.state == self.UI_MAIN:
            if btn == "ENTER":
                self.settings_sel = 0
                self.state = self.UI_SETTINGS
                
        elif self.state == self.UI_CAT_SELECT:
            if btn == "LEFT":
                self.state = self.UI_MAIN
            elif btn == "UP":
                self.cat_idx = (self.cat_idx - 1) % len(self.catalogs)
            elif btn == "DOWN":
                self.cat_idx = (self.cat_idx + 1) % len(self.catalogs)
            elif btn in ("ENTER", "RIGHT"):
                cat_name = self.catalogs[self.cat_idx]
                if cat_name == "Étoiles":
                    stars = self.get_visible_stars()
                    for s in stars: s['visible'] = True
                    self.obj_list = stars
                else:
                    self.obj_list = self.get_catalog_with_visibility(cat_name)
                self.obj_idx = 0
                if self.obj_list:
                    self.state = self.UI_OBJECT_LIST
                
        elif self.state == self.UI_OBJECT_LIST:
            if btn == "UP":
                self.obj_idx = (self.obj_idx - 1) % len(self.obj_list) if self.obj_list else 0
            elif btn == "DOWN":
                self.obj_idx = (self.obj_idx + 1) % len(self.obj_list) if self.obj_list else 0
            elif btn == "LEFT":
                self.state = self.UI_CAT_SELECT
            elif btn in ("RIGHT", "ENTER"):
                if self.obj_list:
                    self.state = self.UI_OBJECT_INFO
                    
        elif self.state == self.UI_OBJECT_INFO:
            if btn == "LEFT":
                self.is_align_workflow = False
                self.state = self.UI_OBJECT_LIST
            elif btn == "UP":
                self.obj_idx = (self.obj_idx - 1) % len(self.obj_list) if self.obj_list else 0
            elif btn == "DOWN":
                self.obj_idx = (self.obj_idx + 1) % len(self.obj_list) if self.obj_list else 0
            elif btn == "RIGHT":
                if self.is_connected:
                    o = self.obj_list[self.obj_idx]
                    if not o.get('visible', False):
                        lang = self.cfg.get("language", "fr")
                        self.set_msg(" SOUS HORIZON ! " if lang=="fr" else " BELOW HORIZON! ", "                ", "", "", 2000, self.UI_OBJECT_INFO)
                        return
                        
                    self.target_ra = o['ra']
                    self.target_dec = o['dec']
                    ra_str = Astro.fmt_ra_lx(o['ra'])
                    dec_str = Astro.fmt_dec_lx(o['dec'])
                    
                    self.cmd_queue = [f":Sr{ra_str}#", f":Sd{dec_str}#", ":CM#"]
                    self.process_queue()
                    
                    lang = self.cfg.get("language", "fr")
                    if lang == "en":
                        self.set_msg("  SYNCHRONIZED  ", "                ", "", "", 1500, self.UI_MAIN)
                    else:
                        self.set_msg("  SYNCHRONISE   ", "                ", "", "", 1500, self.UI_MAIN)
                else:
                    lang = self.cfg.get("language", "fr")
                    if lang == "en":
                        self.set_msg(" ERROR: ", " NOT CONNECTED ", "", "", 2000, self.UI_OBJECT_INFO)
                    else:
                        self.set_msg(" ERREUR: ", " NON CONNECTE ", "", "", 2000, self.UI_OBJECT_INFO)
                    return
            elif btn == "ENTER":
                if self.is_connected:
                    o = self.obj_list[self.obj_idx]
                    if not o.get('visible', False):
                        lang = self.cfg.get("language", "fr")
                        self.set_msg(" SOUS HORIZON ! " if lang=="fr" else " BELOW HORIZON! ", "                ", "", "", 2000, self.UI_OBJECT_INFO)
                        return
                        
                    self.target_ra = o['ra']
                    self.target_dec = o['dec']
                    ra_str = Astro.fmt_ra_lx(o['ra'])
                    dec_str = Astro.fmt_dec_lx(o['dec'])
                    
                    self.cmd_queue = [f":Sr{ra_str}#", f":Sd{dec_str}#", ":MS#"]
                    self.process_queue()
                else:
                    lang = self.cfg.get("language", "fr")
                    if lang == "en":
                        self.set_msg(" ERROR: ", " NOT CONNECTED ", "", "", 2000, self.UI_OBJECT_INFO)
                    else:
                        self.set_msg(" ERREUR: ", " NON CONNECTE ", "", "", 2000, self.UI_OBJECT_INFO)
                    return
                    
        elif self.state == self.UI_ALIGN_CENTER:
            if btn == "LEFT":
                self.state = self.UI_MAIN
            elif btn == "ENTER":
                if self.is_connected:
                    o = self.obj_list[self.obj_idx]
                    self.target_ra = o['ra']
                    self.target_dec = o['dec']
                    ra_str = Astro.fmt_ra_lx(o['ra'])
                    dec_str = Astro.fmt_dec_lx(o['dec'])
                    
                    self.cmd_queue = [f":Sr{ra_str}#", f":Sd{dec_str}#", ":CM#"]
                    self.process_queue()
                    
                    lang = self.cfg.get("language", "fr")
                    if lang == "en":
                        self.set_msg("  SYNCHRONIZED  ", "                ", "", "", 1500, self.UI_MAIN)
                    else:
                        self.set_msg("  SYNCHRONISE   ", "                ", "", "", 1500, self.UI_MAIN)
                    
        elif self.state == self.UI_SLEWING:
            if btn in ("LEFT", "ENTER"):
                self.send_cmd(":Q#")
                self.cmd_queue.clear()
                self.state = self.UI_MAIN
                
        elif self.state == self.UI_SETTINGS:
            if btn == "LEFT":
                self.state = self.UI_MAIN
            elif btn == "UP":
                self.settings_sel = (self.settings_sel - 1) % 10
            elif btn == "DOWN":
                self.settings_sel = (self.settings_sel + 1) % 10
            elif btn in ("ENTER", "RIGHT"):
                lang = self.cfg.get("language", "fr")
                if self.settings_sel == 0:
                    self.cat_idx = 0
                    self.state = self.UI_CAT_SELECT
                elif self.settings_sel == 1:
                    self.temp_speed = self.current_speed
                    self.state = self.UI_SPEED
                elif self.settings_sel == 2:
                    self.temp_buzzer_on = self.buzzer_on
                    self.state = self.UI_BEEP
                elif self.settings_sel == 3:
                    # Alignment: Propose best star
                    stars = self.get_visible_stars()
                    if stars:
                        for s in stars: s['visible'] = True
                        self.obj_list = stars
                        self.obj_idx = 0
                        self.state = self.UI_OBJECT_INFO
                        self.is_align_workflow = True
                    else:
                        lang = self.cfg.get("language", "fr")
                        self.set_msg(" AUCUNE ETOILE  " if lang=="fr" else " NO STAR FOUND  ", " VISIBLE        ", "", "", 1500, self.UI_SETTINGS)
                elif self.settings_sel == 4:
                    self.send_cmd(":hP#")
                    if lang == "en":
                        self.set_msg("  PARKING...    ", "                ", "", "", 1500, self.UI_MAIN)
                    else:
                        self.set_msg("  PARKING...    ", "                ", "", "", 1500, self.UI_MAIN)
                elif self.settings_sel == 5:
                    self.state = self.UI_MOUNT
                elif self.settings_sel == 6:
                    self.state = self.UI_RATIO_AZ
                elif self.settings_sel == 7:
                    self.state = self.UI_RATIO_ALT
                elif self.settings_sel == 8:
                    self.temp_motor_power = getattr(self, "motor_power", True)
                    self.state = self.UI_MOTOR_POWER
                elif self.settings_sel == 9:
                    self.temp_lang = lang
                    self.state = self.UI_LANGUAGE
                    
        elif self.state == self.UI_SPEED:
            if btn == "LEFT":
                self.state = self.UI_SETTINGS
            elif btn == "UP":
                self.temp_speed += 0.5
                if self.temp_speed > 25.0: self.temp_speed = 25.0
            elif btn == "DOWN":
                self.temp_speed -= 0.5
                if self.temp_speed < 0.5: self.temp_speed = 0.5
            elif btn == "ENTER":
                self.current_speed = self.temp_speed
                self.send_cmd(f":BV {int(self.current_speed * 10)}#")
                lang = self.cfg.get("language", "fr")
                if lang == "en":
                    self.set_msg("  SPEED ADJUSTED ", f"   {self.current_speed:.1f} deg/s OK  ", "", "", 1200, self.UI_SETTINGS)
                else:
                    self.set_msg("  VITESSE REGL.  ", f"   {self.current_speed:.1f} deg/s OK  ", "", "", 1200, self.UI_SETTINGS)
                
        elif self.state == self.UI_BEEP:
            if btn == "LEFT":
                self.state = self.UI_SETTINGS
            elif btn in ("UP", "DOWN"):
                self.temp_buzzer_on = not self.temp_buzzer_on
            elif btn == "ENTER":
                self.buzzer_on = self.temp_buzzer_on
                cmd = ":Bb1#" if self.buzzer_on else ":Bb0#"
                self.send_cmd(cmd)
                lang = self.cfg.get("language", "fr")
                if lang == "en":
                    self.set_msg("    BEEP SET.    ", "", "", "", 1200, self.UI_SETTINGS)
                else:
                    self.set_msg("    BIP REGL.    ", "", "", "", 1200, self.UI_SETTINGS)
                    
        elif self.state == self.UI_MOTOR_POWER:
            if btn == "LEFT":
                self.state = self.UI_SETTINGS
            elif btn in ("UP", "DOWN"):
                self.temp_motor_power = not self.temp_motor_power
            elif btn == "ENTER":
                self.motor_power = self.temp_motor_power
                lang = self.cfg.get("language", "fr")
                if self.motor_power:
                    self.send_cmd(":ME#")
                    if lang == "en":
                        self.set_msg(" MOTORS ENABLED  ", "", "", "", 1200, self.UI_SETTINGS)
                    else:
                        self.set_msg(" MOTEURS ACTIFS  ", "", "", "", 1200, self.UI_SETTINGS)
                else:
                    self.send_cmd(":MD#")
                    if lang == "en":
                        self.set_msg(" MOTORS DISABLED ", "", "", "", 1200, self.UI_SETTINGS)
                    else:
                        self.set_msg(" ALIM COUPEE     ", "", "", "", 1200, self.UI_SETTINGS)
                        
        elif self.state == self.UI_LANGUAGE:
            if btn == "LEFT":
                self.state = self.UI_SETTINGS
            elif btn in ("UP", "DOWN"):
                self.temp_lang = "fr" if self.temp_lang == "en" else "en"
            elif btn == "ENTER":
                self.cfg.set("language", self.temp_lang)
                self.cfg.save()
                if self.temp_lang == "en":
                    self.title("Virtual T4.1 Hand Controller")
                    self.set_msg(" LANGUAGE SAVED  ", "", "", "", 1200, self.UI_SETTINGS)
                else:
                    self.title("Raquette T4.1 Virtuelle")
                    self.set_msg(" LANGUE ENREG.   ", "", "", "", 1200, self.UI_SETTINGS)
        
        elif self.state == self.UI_MOUNT:
            if btn == "LEFT":
                self.state = self.UI_SETTINGS
            elif btn in ("UP", "DOWN"):
                self.temp_mount_type = (self.temp_mount_type + 1) % 3
            elif btn == "ENTER":
                if self.temp_mount_type == 0: self.send_cmd(":BMa#")
                elif self.temp_mount_type == 1: self.send_cmd(":BMe#")
                else: self.send_cmd(":BMg#")
                self.cfg.set("mount_type", ["AltAz", "ForkEq", "GermanEq"][self.temp_mount_type])
                self.cfg.save()
                lang = self.cfg.get("language", "fr")
                if lang == "en":
                    self.set_msg(" MOUNT SET      ", "                ", "", "", 1500, self.UI_SETTINGS)
                else:
                    self.set_msg(" MONTURE REGLEE ", "                ", "", "", 1500, self.UI_SETTINGS)
                    
        elif self.state == self.UI_RATIO_AZ:
            if btn == "LEFT":
                self.state = self.UI_SETTINGS
            elif btn == "UP":
                self.temp_ratio_az += 10.0
            elif btn == "DOWN":
                self.temp_ratio_az -= 10.0
                if self.temp_ratio_az < 10.0: self.temp_ratio_az = 10.0
            elif btn == "ENTER":
                self.send_cmd(f":BGa{self.temp_ratio_az}#")
                self.cfg.set("gear_ratio_az", self.temp_ratio_az)
                self.cfg.save()
                lang = self.cfg.get("language", "fr")
                is_altaz = (self.cfg.get("mount_type", "AltAz") == "AltAz")
                lbl = "RATIO AZ" if is_altaz else "RATIO RA"
                if lang == "en": lbl = "AZ RATIO" if is_altaz else "RA RATIO"
                self.set_msg(f" {lbl} OK".ljust(16), "", "", "", 1500, self.UI_SETTINGS)
                
        elif self.state == self.UI_RATIO_ALT:
            if btn == "LEFT":
                self.state = self.UI_SETTINGS
            elif btn == "UP":
                self.temp_ratio_alt += 10.0
            elif btn == "DOWN":
                self.temp_ratio_alt -= 10.0
                if self.temp_ratio_alt < 10.0: self.temp_ratio_alt = 10.0
            elif btn == "ENTER":
                self.send_cmd(f":BGe{self.temp_ratio_alt}#")
                self.cfg.set("gear_ratio_alt", self.temp_ratio_alt)
                self.cfg.save()
                lang = self.cfg.get("language", "fr")
                is_altaz = (self.cfg.get("mount_type", "AltAz") == "AltAz")
                lbl = "RATIO ALT" if is_altaz else "RATIO DEC"
                if lang == "en": lbl = "ALT RATIO" if is_altaz else "DEC RATIO"
                self.set_msg(f" {lbl} OK".ljust(16), "", "", "", 1500, self.UI_SETTINGS)
                
        self.update_lcd()

if __name__ == "__main__":
    app = VirtualTeensyApp()
    app.mainloop()