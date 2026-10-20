import tkinter as tk
from tkinter import messagebox, ttk
import os
import sys
import subprocess
from pathlib import Path

class InstallerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Installation de Goto Universal (Linux)")
        self.geometry("500x350")
        self.configure(bg="#f0f0f0")
        
        lbl_title = tk.Label(self, text="Installation de Goto Universal", font=("Arial", 16, "bold"), bg="#f0f0f0")
        lbl_title.pack(pady=20)
        
        lbl_desc = tk.Label(self, text="Cet assistant va créer un environnement isolé\net installer les dépendances nécessaires sans modifier votre système.\n\nIl créera également deux raccourcis sur votre bureau :\nle configurateur et la carte du ciel.", bg="#f0f0f0", justify="center")
        lbl_desc.pack(pady=10)
        
        self.progress = ttk.Progressbar(self, orient="horizontal", length=400, mode="determinate")
        self.progress.pack(pady=20)
        
        self.status_lbl = tk.Label(self, text="Prêt à installer.", bg="#f0f0f0")
        self.status_lbl.pack(pady=5)
        
        self.btn_install = tk.Button(self, text="Installer", command=self.start_install, font=("Arial", 12, "bold"))
        self.btn_install.pack(pady=20)

    def start_install(self):
        self.btn_install.config(state="disabled")
        import threading
        threading.Thread(target=self.run_install, daemon=True).start()

    def run_install(self):
        try:
            import shutil
            if getattr(sys, 'frozen', False):
                source_dir = Path(sys.executable).parent.resolve()
            else:
                source_dir = Path(__file__).parent.resolve()
            install_dir = Path.home() / ".goto_andrivet"
            install_dir.mkdir(parents=True, exist_ok=True)
            venv_dir = install_dir / "venv"
            
            # 0. Copier les fichiers
            self.update_status("Copie des fichiers dans le dossier personnel...", 5)
            for f in source_dir.glob("*.py"):
                shutil.copy2(f, install_dir)
            for d in ["mega_monture", "teensy_monture", "teensy_raquette", "icons"]:
                if (source_dir / d).exists():
                    shutil.copytree(source_dir / d, install_dir / d, dirs_exist_ok=True)

            
            # 1. Créer le venv
            self.update_status("Création de l'environnement virtuel...", 15)
            # Use --copies just in case, though home is usually ext4
            python_bin = shutil.which('python3') or 'python3'
            subprocess.run([python_bin, "-m", "venv", "--copies", str(venv_dir)], capture_output=True, text=True, check=True)
            
            # 2. Installer les dépendances
            self.update_status("Installation des dépendances (cela peut prendre un moment)...", 30)
            pip_exe = venv_dir / "bin" / "pip"
            subprocess.run([str(pip_exe), "install", "--upgrade", "pip"], capture_output=True, text=True, check=True)
            
            reqs = ["pyserial", "pillow", "zwoasi", "numpy", "requests", "ephem", "opencv-python-headless"]
            for i, req in enumerate(reqs):
                self.update_status(f"Installation de {req}...", 30 + (i * 10))
                subprocess.run([str(pip_exe), "install", req], capture_output=True, text=True, check=True)
                
            # 3. Créer les raccourcis Desktop : configurateur et carte du ciel
            self.update_status("Création des raccourcis...", 90)
            desktop_dir = Path.home() / "Bureau"
            if not desktop_dir.exists():
                desktop_dir = Path.home() / "Desktop"
                
            python_exe = venv_dir / "bin" / "python3"
            shortcuts = (
                ("GotoMega.desktop", "Goto Universal Config", "Outil de configuration pour Goto Universal",
                 "goto_andrivet_config_tool.py", "goto_andrivet_config.svg", "utilities-terminal"),
                ("GotoAndrivet.desktop", "GotoAndrivet - Carte du ciel", "Carte du ciel, GoTo et dérotateur pour monture GotoAndrivet",
                 "goto_andrivet.py", "goto_andrivet.svg", "applications-science"),
            )
            for file_name, name, comment, script, icon_file, fallback_icon in shortcuts:
                icon = install_dir / "icons" / icon_file
                content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name={name}
Comment={comment}
Exec={python_exe} {install_dir / script}
Icon={icon if icon.exists() else fallback_icon}
Path={install_dir}
Terminal=false
Categories=Utility;Science;Astronomy;
"""
                desktop_file = desktop_dir / file_name
                desktop_file.write_text(content)
                os.chmod(desktop_file, 0o755)
                # GNOME : sans ce drapeau, le bureau demande d'autoriser le lancement du raccourci
                try:
                    subprocess.run(["gio", "set", str(desktop_file), "metadata::trusted", "true"], capture_output=True)
                except OSError:
                    pass
            
            self.update_status("Installation terminée avec succès !", 100)
            def on_success():
                messagebox.showinfo("Succès", "L'installation est terminée.\nVous pouvez maintenant lancer l'application depuis votre Bureau !")
                self.destroy()
            self.after(0, on_success)
            
        except Exception as e:
            self.after(0, lambda err=e: messagebox.showerror("Erreur", f"Une erreur est survenue:\n{err}"))
            self.after(0, lambda: self.btn_install.config(state="normal"))
            self.update_status("Erreur d'installation.", 0)

    def update_status(self, text, val):
        self.after(0, lambda: self.status_lbl.config(text=text))
        self.after(0, lambda: self.progress.config(value=val))

if __name__ == "__main__":
    app = InstallerApp()
    app.mainloop()
