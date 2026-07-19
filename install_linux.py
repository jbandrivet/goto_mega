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
        
        lbl_desc = tk.Label(self, text="Cet assistant va créer un environnement isolé\net installer les dépendances nécessaires sans modifier votre système.\n\nIl créera également un raccourci sur votre bureau.", bg="#f0f0f0", justify="center")
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
            source_dir = Path(__file__).parent.resolve()
            install_dir = Path.home() / ".goto_andrivet"
            install_dir.mkdir(parents=True, exist_ok=True)
            venv_dir = install_dir / "venv"
            
            # 0. Copier les fichiers
            self.update_status("Copie des fichiers dans le dossier personnel...", 5)
            for f in source_dir.glob("*.py"):
                shutil.copy2(f, install_dir)
            if (source_dir / "astrometry_data").exists():
                shutil.copytree(source_dir / "astrometry_data", install_dir / "astrometry_data", dirs_exist_ok=True)
            
            # 1. Créer le venv
            self.update_status("Création de l'environnement virtuel...", 15)
            # Use --copies just in case, though home is usually ext4
            subprocess.run([sys.executable, "-m", "venv", "--copies", str(venv_dir)], check=True)
            
            # 2. Installer les dépendances
            self.update_status("Installation des dépendances (cela peut prendre un moment)...", 30)
            pip_exe = venv_dir / "bin" / "pip"
            subprocess.run([str(pip_exe), "install", "--upgrade", "pip"], check=True)
            
            reqs = ["pyserial", "pillow", "zwoasi", "numpy", "requests", "ephem", "opencv-python-headless"]
            for i, req in enumerate(reqs):
                self.update_status(f"Installation de {req}...", 30 + (i * 10))
                subprocess.run([str(pip_exe), "install", req], check=True)
                
            # 3. Créer le raccourci Desktop
            self.update_status("Création du raccourci...", 90)
            desktop_dir = Path.home() / "Bureau"
            if not desktop_dir.exists():
                desktop_dir = Path.home() / "Desktop"
                
            python_exe = venv_dir / "bin" / "python3"
            main_script = install_dir / "goto_andrivet_config_tool.py"
            
            desktop_file = desktop_dir / "GotoMega.desktop"
            content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=Goto Universal Config
Comment=Outil de configuration pour Goto Universal
Exec={python_exe} {main_script}
Icon=utilities-terminal
Path={install_dir}
Terminal=false
Categories=Utility;Science;Astronomy;
"""
            desktop_file.write_text(content)
            os.chmod(desktop_file, 0o755)
            
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
