"""Mise à jour en ligne des applications GotoAndrivet, partagée par la carte du ciel et le configurateur.

Version installée : commit git du dossier si c'est un dépôt, sinon ~/.config/goto_andrivet/version.txt.
Version disponible : dernier commit de la branche main du dépôt GitHub.
Mise à jour : « git pull » pour un dépôt, sinon téléchargement de l'archive de main, recopiée sur
l'installation (le venv et les données d'astrométrie sont conservés).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

REPO = "jbandrivet/goto_mega"
VERSION_FILE = Path.home() / ".config" / "goto_andrivet" / "version.txt"
KEEP = {"venv", ".git", "__pycache__", "astrometry_data"}
_UA = {"User-Agent": "GotoAndrivet-Updater/1.0"}


def is_git(app_dir):
    return (Path(app_dir) / ".git").exists()


def local_version(app_dir):
    """Commit installé, ou "" s'il est inconnu."""
    if is_git(app_dir):
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(app_dir), capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else ""
    return VERSION_FILE.read_text().strip() if VERSION_FILE.exists() else ""


def remote_version(timeout=5):
    """Dernier commit de main sur GitHub (lève une exception si le réseau ne répond pas)."""
    req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/commits/main", headers=_UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())["sha"]


def check(app_dir):
    """(mise à jour disponible, commit distant, commit local). Une installation sans version connue
    est considérée comme à jour : la version distante est alors enregistrée comme version installée."""
    remote = remote_version()
    local = local_version(app_dir)
    if not local:
        save_version(remote)
        return False, remote, remote
    return local != remote, remote, local


def save_version(sha):
    VERSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    VERSION_FILE.write_text(sha)


def apply(app_dir, remote_sha=None):
    """Installe la dernière version dans app_dir. Lève une exception en cas d'échec."""
    app_dir = Path(app_dir)
    if is_git(app_dir):
        r = subprocess.run(["git", "pull"], cwd=str(app_dir), capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(r.stderr.strip() or "git pull a échoué")
        return
    req = urllib.request.Request(f"https://github.com/{REPO}/archive/refs/heads/main.zip", headers=_UA)
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = Path(tmp) / "main.zip"
        with urllib.request.urlopen(req, timeout=120) as r, open(zip_path, "wb") as f:
            shutil.copyfileobj(r, f)
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(tmp)
        src = next(p for p in Path(tmp).iterdir() if p.is_dir())       # « goto_mega-main »
        for item in src.iterdir():
            if item.name in KEEP:
                continue
            dest = app_dir / item.name
            if item.is_file():
                shutil.copy2(item, dest)
            else:
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
    if remote_sha:
        save_version(remote_sha)


def restart():
    """Relance le programme courant (même interpréteur, mêmes arguments)."""
    os.execv(sys.executable, [sys.executable] + sys.argv)
