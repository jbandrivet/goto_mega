import re

with open("raquette_virtuelle.py", "r") as f:
    code = f.read()

# Define the new update_lcd function
new_update_lcd = """
    def update_lcd(self):
        if self.state == self.UI_MESSAGE: return
        
        l0 = l1 = l2 = l3 = " "*20
        lang = self.cfg.get("language", "fr")
        
        if self.state == self.UI_MAIN:
            ra_short = self.current_ra[:8].replace(':', 'h')
            dec_short = self.current_dec[:9].replace('*', '°')
            l0 = f"RA: {ra_short}"[:20]
            l1 = f"DE: {dec_short}"[:20]
            if self.is_connected:
                stat = "EN LIGNE" if not self.sim_mode else "SIMULATEUR"
                l2 = f"ETAT: {stat}"[:20]
                l3 = "[ENT] = Menu   "[:20]
                
                try:
                    c_ra = Astro.parse_ra(self.current_ra)
                    c_dec = Astro.parse_dec(self.current_dec)
                    if getattr(self, 'target_ra', None) is not None:
                        dist = Astro.angular_dist(c_ra, c_dec, self.target_ra, self.target_dec)
                        if dist > 0.05:
                            l3 = f"Cible dist: {dist:.1f}°"[:20]
                except:
                    pass
            else:
                l2 = "ETAT: HORS LIGNE"[:20]
                l3 = ""[:20]
            
        elif self.state == self.UI_CAT_SELECT:
            l0 = "[ CHOIX CATALOGUE ]" if lang == "fr" else "[ SELECT CATALOG  ]"
            cat_name = self.catalogs[self.cat_idx]
            count = len(self.db_cat.get(cat_name, []))
            disp_cat = cat_name
            if lang == "en":
                if cat_name == "Systeme Solaire": disp_cat = "Solar System"
                elif cat_name == "Étoiles": disp_cat = "Stars"
            l1 = f"> {disp_cat[:15]}"[:20]
            l2 = f"  ({count} objets)" if lang == "fr" else f"  ({count} objects)"
            l3 = "  [HAUT/BAS] Choisir" if lang == "fr" else "  [UP/DOWN] Select"
            
        elif self.state == self.UI_OBJECT_LIST:
            cat_name = self.catalogs[self.cat_idx]
            disp_cat = cat_name
            if lang == "en":
                if cat_name == "Systeme Solaire": disp_cat = "Sol"
                elif cat_name == "Étoiles": disp_cat = "Star"
            else:
                disp_cat = disp_cat[:3]
                
            l0 = f"[{disp_cat.upper()}] {len(self.obj_list)} objets"[:20]
            
            if len(self.obj_list) == 0:
                l1 = " Aucun objet trouve" if lang == "fr" else " No object found"
            else:
                o = self.obj_list[self.obj_idx]
                name = o.get('name', f"{o.get('cat')} {o.get('num')}")
                if name == f"{o.get('cat')} {o.get('num')}": name = f"{disp_cat} {o.get('num')}"
                vis_star = "*" if o.get("visible", False) else ""
                mag_str = f" Mag: {o.get('mag')}" if o.get('mag') else ""
                l1 = f"> {name[:12]}{vis_star}"[:20]
                l2 = mag_str[:20]
                if 'ra' in o and 'dec' in o:
                    ra_str = Astro.fmt_ra_lx(o['ra'])[:5].replace(':','h')
                    dec_str = Astro.fmt_dec_lx(o['dec'])[:6].replace('*','°')
                    l3 = f"  {ra_str} {dec_str}"[:20]
                else:
                    l3 = ""
                
        elif self.state == self.UI_OBJECT_INFO:
            o = self.obj_list[self.obj_idx]
            name = o.get('name', f"{o.get('cat')} {o.get('num')}")
            vis_star = "*" if o.get("visible", False) else ""
            l0 = f"OBJET: {name[:12]}{vis_star}"[:20]
            if 'ra' in o and 'dec' in o:
                l1 = f"RA: {Astro.fmt_ra_lx(o['ra'])[:8]}"[:20]
                l2 = f"DE: {Astro.fmt_dec_lx(o['dec'])[:9]}"[:20]
            l3 = "[ENT]=GOTO  [>]=SYNC"
            
        elif self.state == self.UI_SLEWING:
            anim_chars = ['*', '+', 'x', '+']
            anim = anim_chars[int(time.time() * 4) % 4]
            if getattr(self, "is_parking_workflow", False):
                l0 = f"PARKING EN COURS {anim}" if lang == "fr" else f"PARKING IN PROG. {anim}"
                l1 = "Moteurs en route..." if lang == "fr" else "Motors running..."
                l2 = "Veuillez patienter" if lang == "fr" else "Please wait"
                l3 = "[<] Annuler" if lang == "fr" else "[<] Cancel"
            else:
                l0 = f"GOTO EN COURS... {anim}" if lang == "fr" else f"SLEWING TO CCT... {anim}"
                
                # Try to show target
                if getattr(self, 'target_ra', None) is not None:
                    try:
                        c_ra = Astro.parse_ra(self.current_ra)
                        c_dec = Astro.parse_dec(self.current_dec)
                        ra_diff = abs(c_ra - self.target_ra) * 15.0
                        if ra_diff > 180.0: ra_diff = 360.0 - ra_diff
                        dec_diff = abs(c_dec - self.target_dec)
                        dist = max(ra_diff, dec_diff)
                        v_max = self.current_speed if self.current_speed > 0 else 2.0
                        v_start = v_max * (35.0 / 500.0)
                        d_ramp = 0.5 * (v_start + v_max) * 5.0
                        if not getattr(self, "slew_stopwatch_active", False):
                            self.slew_stopwatch_active = True
                            self.slew_start_time = time.time()
                            if dist >= 2 * d_ramp:
                                coasting_dist = dist - 2 * d_ramp
                                coasting_time = coasting_dist / v_max
                                self.initial_eta = 10.0 + coasting_time
                            else:
                                self.initial_eta = 2.0 * math.sqrt(5.0 * dist / v_max) if v_max > 0 else 0
                        elapsed = time.time() - self.slew_start_time
                        eta = max(0, int(self.initial_eta - elapsed))
                        gc_dist = Astro.angular_dist(c_ra, c_dec, self.target_ra, self.target_dec)
                        
                        l1 = f"Dist restante: {gc_dist:.1f}°"[:20]
                        l2 = ""
                        l3 = "[<] Annuler GOTO" if lang == "fr" else "[<] Cancel GOTO"
                    except:
                        l1 = "Calcul en cours..."
                else:
                    l1 = "Calcul en cours..."
                
        elif self.state == self.UI_ALIGN_CENTER:
            o = self.obj_list[self.obj_idx]
            name = o.get('name', f"{o.get('cat')} {o.get('num')}")
            l0 = f"CENTREZ L'OBJET:" if lang == "fr" else "CENTER OBJECT:"
            l1 = f"> {name[:17]}"[:20]
            l2 = "Utilisez les fleches" if lang == "fr" else "Use arrow keys"
            l3 = "[ENT] Valider Sync" if lang == "fr" else "[ENT] Confirm Sync"
            
        elif self.state == self.UI_SETTINGS:
            l0 = "[ MENU REGLAGES ]" if lang == "fr" else "[ SETTINGS MENU ]"
            az_str = "Ratio AZ" if self.cfg.get("mount_type", "AltAz") == "AltAz" else "Ratio RA"
            alt_str = "Ratio ALT" if self.cfg.get("mount_type", "AltAz") == "AltAz" else "Ratio DEC"
            if lang == "en":
                az_str = "AZ Ratio" if self.cfg.get("mount_type", "AltAz") == "AltAz" else "RA Ratio"
                alt_str = "ALT Ratio" if self.cfg.get("mount_type", "AltAz") == "AltAz" else "DEC Ratio"
            opts = ["Catalogues", "Vitesse", "Bips", "Alignement", "Parking", "Type Monture", az_str, alt_str, "Alim Moteurs", "Langue"] if lang == "fr" else ["Catalogs", "Speed", "Beeps", "Alignment", "Parking", "Mount Type", az_str, alt_str, "Motor Power", "Language"]
            l1 = f"> {opts[self.settings_sel]}"[:20]
            l2 = "  " + (opts[self.settings_sel+1] if self.settings_sel+1 < len(opts) else "")[:18]
            l3 = "  [HAUT/BAS] Choisir" if lang == "fr" else "  [UP/DOWN] Select"
            
        elif self.state == self.UI_SPEED:
            l0 = "[ VITESSE GOTO ]" if lang == "fr" else "[ GOTO SPEED ]"
            l1 = f"> {self.temp_speed:.1f} deg/s"[:20]
            l2 = ""
            l3 = "[ENT] Valider" if lang == "fr" else "[ENT] Confirm"
            
        elif self.state == self.UI_BEEP:
            l0 = "[ BIP BUZZER ]" if lang == "fr" else "[ BEEP BUZZER ]"
            state_str = "ACTIVE" if self.temp_buzzer_on else "DESACTIVE"
            l1 = f"> {state_str}"[:20]
            l2 = ""
            l3 = "[ENT] Valider" if lang == "fr" else "[ENT] Confirm"
            
        elif self.state == self.UI_MOTOR_POWER:
            l0 = "[ ALIM MOTEURS ]" if lang == "fr" else "[ MOTOR POWER ]"
            status = ("ACTIVE" if self.temp_motor_power else "OFF") if lang == "fr" else ("ON" if self.temp_motor_power else "OFF")
            l1 = f"> {status}"[:20]
            l2 = "Coupe le courant" if lang == "fr" else "Cuts motor power"
            l3 = "[ENT] Valider" if lang == "fr" else "[ENT] Confirm"
                
        elif self.state == self.UI_LANGUAGE:
            l0 = "[ LANGUE / LANG ]"
            l1 = f"> {'FRANCAIS' if self.temp_lang == 'fr' else 'ENGLISH'}"[:20]
            l2 = ""
            l3 = "[ENT] Valider" if lang == "fr" else "[ENT] Confirm"
            
        elif self.state == self.UI_MOUNT:
            l0 = "[ TYPE MONTURE ]" if lang == "fr" else "[ MOUNT TYPE ]"
            mount_str = "Alt-Azimutale" if self.temp_mount_type == 0 else ("Fourche Equato" if self.temp_mount_type == 1 else "Equatoriale All.")
            l1 = f"> {mount_str}"[:20]
            l2 = ""
            l3 = "[ENT] Valider" if lang == "fr" else "[ENT] Confirm"
            
        elif self.state == self.UI_RATIO_AZ:
            is_altaz = (self.cfg.get("mount_type", "AltAz") == "AltAz")
            lbl = "RATIO AZ" if is_altaz else "RATIO RA"
            if lang == "en": lbl = "AZ RATIO" if is_altaz else "RA RATIO"
            l0 = f"[ {lbl} ]"[:20]
            l1 = f"> {self.temp_ratio_az:.1f}"[:20]
            l2 = "Micro-pas / deg" if lang == "fr" else "Microsteps / deg"
            l3 = "[ENT] Valider" if lang == "fr" else "[ENT] Confirm"
            
        elif self.state == self.UI_RATIO_ALT:
            is_altaz = (self.cfg.get("mount_type", "AltAz") == "AltAz")
            lbl = "RATIO ALT" if is_altaz else "RATIO DEC"
            if lang == "en": lbl = "ALT RATIO" if is_altaz else "DEC RATIO"
            l0 = f"[ {lbl} ]"[:20]
            l1 = f"> {self.temp_ratio_alt:.1f}"[:20]
            l2 = "Micro-pas / deg" if lang == "fr" else "Microsteps / deg"
            l3 = "[ENT] Valider" if lang == "fr" else "[ENT] Confirm"

        self.lcd_lines[0].config(text=f"{l0:<20}")
        self.lcd_lines[1].config(text=f"{l1:<20}")
        self.lcd_lines[2].config(text=f"{l2:<20}")
        self.lcd_lines[3].config(text=f"{l3:<20}")
"""

# Extract everything before def update_lcd
parts = code.split('    def update_lcd(self):')
head = parts[0]
tail = parts[1]

# Find the end of update_lcd (def finish_sim_slew is the next method, or wait, we can just split at the first method after update_lcd)
# Wait, look at the original code. What comes after update_lcd?
# Let's search for the next `    def `
next_method_idx = tail.find('\n    def ')
if next_method_idx != -1:
    tail_after = tail[next_method_idx:]
else:
    tail_after = ""

final_code = head + new_update_lcd + tail_after

with open("raquette_virtuelle.py", "w") as f:
    f.write(final_code)

print("Updated RV UI for 2004 LCD")
