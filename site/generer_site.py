#!/usr/bin/env python3
"""Génère le site de GotoAndrivet à partir du dépôt : pages HTML statiques, style rétro, ciel étoilé.

    python3 site/generer_site.py --depot . --sortie /var/www/gotoandrivet [--miroir] [--force]

Les pages reprennent les documents du dépôt (README, manuel de la raquette, fiche technique, guide pour
contribuer) et l'historique git. Avec --miroir, les fichiers d'installation publiés sur GitHub sont copiés
dans <sortie>/telechargements, pour que le site reste utilisable même si GitHub ne répond pas ; ils ne sont
retéléchargés que s'ils ont changé. Sans --force, rien n'est réécrit si le dépôt n'a pas bougé.
Dépendance : python3-markdown.
"""
import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

import markdown

REPO = "jbandrivet/goto_mega"
GITHUB = f"https://github.com/{REPO}"
RELEASE = f"{GITHUB}/releases/latest/download"
FICHIERS = ("GotoAndrivet.deb", "Install_Goto_Universal")
COMMANDE = "wget -qO- https://raw.githubusercontent.com/jbandrivet/goto_mega/main/installer.sh | sh"
ICI = Path(__file__).resolve().parent

# Documents publiés : fichier du dépôt -> (page, titre du menu)
DOCS = {
    "README.md": ("documentation.html", "Documentation"),
    "MANUEL_RAQUETTE.md": ("raquette.html", "Raquette"),
    "fiche_technique.md": ("fiche-technique.html", "Fiche technique"),
    "CONTRIBUTING.md": ("contribuer.html", "Contribuer"),
}
MENU = (("index.html", "Accueil"), ("telecharger.html", "Télécharger"), ("documentation.html", "Documentation"),
        ("raquette.html", "Raquette"), ("fiche-technique.html", "Fiche technique"),
        ("nouveautes.html", "Nouveautés"), ("contribuer.html", "Contribuer"))

FONCTIONS = (
    ("✦", "Carte du ciel et GoTo", "Étoiles, constellations, planètes, Messier, NGC, IC et Caldwell, précessés à la date. "
     "Un clic sur un objet, et la monture y va."),
    ("◉", "Caméra et astrométrie", "Caméra ZWO, photos FITS, résolution locale du champ : la monture se recale toute seule "
     "après chaque GoTo et construit son modèle de pointage."),
    ("◎", "Guidage", "Deuxième caméra, calibration automatique, corrections envoyées par le PC à la monture, "
     "courbe des erreurs et dithering entre les poses."),
    ("↻", "Dérotateur et focuseur", "Compensation de la rotation de champ en AltAz, angle de cadrage en équatoriale, "
     "focuseur intégré ou ZWO EAF."),
    ("▣", "Deux firmwares", "Arduino Mega 2560 ou Teensy 4.1, protocole LX200/OnStep compatible avec KStars, Ekos et INDI."),
    ("☰", "Raquette physique", "Teensy 4.1 et écran 20 × 4 : catalogues, GoTo, parking, suivi, sans ordinateur."),
    ("⚙", "Configurateur", "Rapports d'engrenage, micro-pas, vitesses, type de monture, et flashage des cartes "
     "sans l'IDE Arduino."),
    ("⌁", "Cartes électroniques", "Deux circuits KiCad : modules StepStick ou drivers externes, TMC5160 en SPI, "
     "alimentation 36 V."),
)


# ── Dépôt ─────────────────────────────────────────────────────
def git(depot, *args):
    r = subprocess.run(["git", "-C", str(depot), *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def historique(depot, n=40):
    """[(sha, date jj/mm/aaaa, titre, corps)] des n derniers commits."""
    out = git(depot, "log", f"-n{n}", "--format=%H%x1f%ad%x1f%s%x1f%b%x1e", "--date=format:%d/%m/%Y")
    commits = []
    for bloc in out.split("\x1e"):
        champs = bloc.strip("\n").split("\x1f")
        if len(champs) == 4:
            corps = re.sub(r"\n*Co-Authored-By:.*", "", champs[3], flags=re.S).strip()
            commits.append((champs[0], champs[1], champs[2], corps))
    return commits


# ── Miroir des fichiers d'installation ────────────────────────
def miroir(sortie):
    """Copie locale des fichiers publiés sur GitHub, retéléchargés seulement s'ils ont changé
    (taille et date annoncées par le serveur). Renvoie les fichiers mis à jour."""
    dossier = sortie / "telechargements"
    dossier.mkdir(parents=True, exist_ok=True)
    etat_path = dossier / ".etat.json"
    try:
        etat = json.loads(etat_path.read_text())
    except (OSError, ValueError):
        etat = {}
    changes = []
    for nom in FICHIERS:
        req = urllib.request.Request(f"{RELEASE}/{nom}", headers={"User-Agent": "GotoAndrivet-Site/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                signe = [r.headers.get("Content-Length"), r.headers.get("Last-Modified")]
                if signe == etat.get(nom) and (dossier / nom).exists():
                    continue                       # inchangé : on ferme sans lire le contenu
                tmp = dossier / f".{nom}.part"
                with open(tmp, "wb") as f:
                    shutil.copyfileobj(r, f)
            os.replace(tmp, dossier / nom)
            etat[nom] = signe
            changes.append(nom)
        except Exception as e:
            print(f"miroir : {nom} non mis à jour ({e})", file=sys.stderr)
    etat_path.write_text(json.dumps(etat))
    return changes


# ── Mise en page ──────────────────────────────────────────────
def page(titre, actif, contenu, version):
    actif_cls = ' class="actif"'
    nav = "\n".join(f'<a href="{href}"{actif_cls if href == actif else ""}>{html.escape(nom)}</a>'
                    for href, nom in MENU)
    sha, date = version
    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(titre)} · GotoAndrivet</title>
<meta name="description" content="GotoAndrivet : contrôleur GoTo libre pour télescopes, carte du ciel, caméra, astrométrie et guidage.">
<link rel="icon" href="statique/icone.svg" type="image/svg+xml">
<link rel="stylesheet" href="statique/style.css">
</head>
<body>
<canvas id="ciel" aria-hidden="true"></canvas>
<header class="bandeau">
  <a class="logo" href="index.html"><img src="statique/icone.svg" alt="" width="36" height="36"><span>GOTO<em>ANDRIVET</em></span></a>
  <nav>{nav}<a class="github" href="{GITHUB}">GitHub ↗</a></nav>
</header>
<main>
{contenu}
</main>
<footer>
  <p>GotoAndrivet est un logiciel libre sous licence <a href="{GITHUB}/blob/main/LICENSE">GNU GPL v3</a>
  · code source sur <a href="{GITHUB}">GitHub</a></p>
  <p class="petit">Site mis à jour automatiquement depuis GitHub · version <a href="{GITHUB}/commit/{sha}">{sha[:7]}</a> du {date}</p>
</footer>
<script src="statique/etoiles.js"></script>
</body>
</html>
"""


def lien_local(m):
    """Liens relatifs des documents : vers la page du site si elle existe, sinon vers GitHub."""
    texte, cible = m.group(1), m.group(2)
    if re.match(r"^[a-z]+:|^#", cible):
        return m.group(0)
    chemin, _, ancre = cible.partition("#")
    if chemin in DOCS:
        return f"[{texte}]({DOCS[chemin][0]}{'#' + ancre if ancre else ''})"
    return f"[{texte}]({GITHUB}/blob/main/{chemin}{'#' + ancre if ancre else ''})"


CITATION = re.compile(r"^((?:>\s?)*)")
PUCE = re.compile(r"^\s*(\d+\.|[-*+])\s")
ALERTES = {"NOTE": "Note", "TIP": "Conseil", "IMPORTANT": "Important", "WARNING": "Attention", "CAUTION": "Prudence"}


def listes_comme_github(texte):
    """GitHub accepte une liste collée à la ligne qui la précède, y compris dans une citation ;
    python-markdown veut une ligne vide avant."""
    lignes, dans_code = [], False
    for ligne in texte.split("\n"):
        q = CITATION.match(ligne).group(1)
        corps = ligne[len(q):]
        if corps.lstrip().startswith("```"):
            dans_code = not dans_code
        prec = lignes[-1] if lignes else ""
        pq = CITATION.match(prec).group(1)
        pcorps = prec[len(pq):]
        if (not dans_code and PUCE.match(corps) and pcorps.strip() and q.strip() == pq.strip()
                and not PUCE.match(pcorps) and not pcorps.startswith((" ", "\t"))):
            lignes.append(q.rstrip())
        lignes.append(ligne)
    return "\n".join(lignes)


def alertes_github(texte):
    """Encadrés de GitHub (« > [!NOTE] », « > [!IMPORTANT] »…) changés en blocs du site. Sans cela,
    python-markdown affiche la balise telle quelle et fusionne deux encadrés qui se suivent."""
    lignes, out, i = texte.split("\n"), [], 0
    while i < len(lignes):
        m = re.match(r"^>\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*$", lignes[i])
        if not m:
            out.append(lignes[i]); i += 1
            continue
        bloc, i = [], i + 1
        while i < len(lignes) and lignes[i].startswith(">"):
            bloc.append(re.sub(r"^> ?", "", lignes[i])); i += 1
        genre = m.group(1)
        out += ["", f'<div class="alerte {genre.lower()}" markdown="1">', "",
                f'<p class="titre-alerte">{ALERTES[genre]}</p>', ""] + bloc + ["", "</div>", ""]
    return "\n".join(out)


def rendre_md(texte):
    texte = listes_comme_github(alertes_github(texte))
    texte = re.sub(r"\[([^\]]*)\]\(([^)\s]+)\)", lien_local, texte)
    md = markdown.Markdown(extensions=["tables", "fenced_code", "toc", "sane_lists", "md_in_html"],
                           extension_configs={"toc": {"permalink": False}})
    corps = md.convert(texte)
    corps = corps.replace("<table>", '<div class="tableau"><table>').replace("</table>", "</table></div>")
    return corps, md.toc


def page_doc(depot, fichier, version):
    href, nom = DOCS[fichier]
    corps, toc = rendre_md((depot / fichier).read_text(encoding="utf-8"))
    sommaire = f'<details class="sommaire panneau"><summary>Sommaire</summary>{toc}</details>' if toc.count("<li>") > 3 else ""
    contenu = f"""<article class="document panneau">
{sommaire}
{corps}
<p class="source">Source : <a href="{GITHUB}/blob/main/{fichier}">{fichier}</a> sur GitHub</p>
</article>"""
    return href, page(nom, href, contenu, version)


def taille(p):
    n = p.stat().st_size
    return f"{n / 1e6:.1f} Mo" if n >= 1e6 else f"{n / 1e3:.0f} ko"


def page_telecharger(sortie, version):
    local = sortie / "telechargements"
    def bouton(nom, texte):
        f = local / nom
        if f.exists():
            date = datetime.fromtimestamp(f.stat().st_mtime).strftime("%d/%m/%Y")
            return (f'<a class="bouton" href="telechargements/{nom}" download>▶ {texte}</a>'
                    f'<p class="petit">{taille(f)}, publié le {date} · '
                    f'<a href="{RELEASE}/{nom}">ou depuis GitHub</a></p>')
        return f'<a class="bouton" href="{RELEASE}/{nom}">▶ {texte}</a><p class="petit">depuis GitHub</p>'
    contenu = f"""<section class="panneau">
<h1>Télécharger</h1>
<p>La carte du ciel avec le GoTo, la caméra et le guidage, et le configurateur de la monture s'installent
ensemble, dans votre dossier personnel, sans toucher au système. Ensuite, le bouton « Mise à jour » des
applications suffit.</p>
</section>
<section class="panneau choix">
<h2><span class="pastille">1</span> Ubuntu et Debian : le paquet .deb</h2>
<p>Le plus simple.</p>
{bouton("GotoAndrivet.deb", "GotoAndrivet.deb")}
<ol>
<li>Double-cliquez sur le fichier téléchargé : le Centre d'applications s'ouvre. Cliquez sur
<strong>Installer</strong> (votre mot de passe est demandé).</li>
<li>Ouvrez <strong>GotoAndrivet - Carte du ciel</strong> depuis le menu des applications. La première fois,
GotoAndrivet s'installe dans votre dossier personnel (quelques minutes), puis s'ouvre.</li>
</ol>
</section>
<section class="panneau choix">
<h2><span class="pastille">2</span> Autres distributions : l'installateur</h2>
{bouton("Install_Goto_Universal", "Install_Goto_Universal")}
<ol>
<li>Clic droit sur le fichier → <strong>Propriétés</strong> → activez <strong>Exécutable comme programme</strong>.</li>
<li>Clic droit → <strong>Exécuter comme un programme</strong>, puis « Installer ».</li>
</ol>
<p class="petit">Le double-clic ne lance pas un programme téléchargé : passez par le clic droit.</p>
</section>
<section class="panneau choix">
<h2><span class="pastille">3</span> En une commande</h2>
<p>Dans un terminal :</p>
<pre><code>{html.escape(COMMANDE)}</code></pre>
</section>
<section class="panneau">
<h2>Prérequis</h2>
<ul>
<li>Installateur et commande : <code>sudo apt install python3-venv python3-tk</code> (le paquet .deb s'en charge).</li>
<li>Module caméra : <code>sudo apt install astrometry.net astrometry-data-tycho2</code> et le SDK caméra de ZWO.</li>
<li>Flashage des cartes : <a href="https://arduino.github.io/arduino-cli/latest/">arduino-cli</a>.</li>
</ul>
</section>"""
    return page("Télécharger", "telecharger.html", contenu, version)


def page_accueil(commits, version):
    cartes = "\n".join(f'<div class="carte"><div class="symbole">{s}</div><h3>{html.escape(t)}</h3><p>{html.escape(d)}</p></div>'
                       for s, t, d in FONCTIONS)
    recents = "\n".join(f'<li><span class="date">{d}</span> {html.escape(t)}</li>' for _, d, t, _ in commits[:5])
    contenu = f"""<section class="hero">
  <p class="surtitre">Contrôleur GoTo libre pour télescopes</p>
  <h1 class="titre">GOTO<br><em>ANDRIVET</em></h1>
  <p class="accroche">Carte du ciel · GoTo · caméra · astrométrie · guidage<span class="curseur">_</span></p>
  <div class="actions">
    <a class="bouton" href="telecharger.html">▶ Télécharger</a>
    <a class="bouton secondaire" href="{GITHUB}">Code sur GitHub</a>
  </div>
  <p class="montures">AltAz · fourche équatoriale · équatoriale allemande</p>
</section>
<section class="grille">
{cartes}
</section>
<section class="panneau">
  <h2>Dernières nouveautés</h2>
  <ul class="journal court">
{recents}
  </ul>
  <p><a href="nouveautes.html">Tout l'historique →</a></p>
</section>"""
    return page("Accueil", "index.html", contenu, version)


def page_nouveautes(commits, version):
    items = []
    for sha, d, titre, corps in commits:
        detail = ""
        if corps:
            detail = f"<details><summary>Détails</summary><pre class=\"corps\">{html.escape(corps)}</pre></details>"
        items.append(f'<li><span class="date">{d}</span> <a class="sha" href="{GITHUB}/commit/{sha}">{sha[:7]}</a> '
                     f'<strong>{html.escape(titre)}</strong>{detail}</li>')
    contenu = f"""<section class="panneau">
<h1>Nouveautés</h1>
<p>Les dernières modifications du projet, les plus récentes en premier. Elles arrivent chez les utilisateurs
par le bouton « Mise à jour » des applications.</p>
<ul class="journal">
{chr(10).join(items)}
</ul>
</section>"""
    return page("Nouveautés", "nouveautes.html", contenu, version)


def page_404(version):
    contenu = """<section class="panneau hero-petit">
<h1>404</h1>
<p>Cette page s'est perdue dans l'espace.</p>
<p><a class="bouton" href="index.html">▶ Retour à l'accueil</a></p>
</section>"""
    return page("Page introuvable", "", contenu, version)


# ── Écriture ──────────────────────────────────────────────────
def ecrire(chemin, texte):
    tmp = chemin.with_name(f".{chemin.name}.tmp")
    tmp.write_text(texte, encoding="utf-8")
    os.replace(tmp, chemin)


def generer(depot, sortie, avec_miroir=False, force=False):
    depot, sortie = Path(depot).resolve(), Path(sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    changes = miroir(sortie) if avec_miroir else []
    sha = git(depot, "rev-parse", "HEAD") or "inconnu"
    tampon = sortie / ".version"
    marque = f"{sha} {sorted(changes)}" if changes else sha
    if not force and not changes and tampon.exists() and tampon.read_text().split()[0] == sha:
        return False
    date = git(depot, "log", "-1", "--format=%ad", "--date=format:%d/%m/%Y") or "?"
    version = (sha, date)
    commits = historique(depot)

    statique = sortie / "statique"
    if statique.exists():
        shutil.rmtree(statique)
    shutil.copytree(ICI / "statique", statique)
    shutil.copy2(depot / "icons" / "goto_andrivet.svg", statique / "icone.svg")

    ecrire(sortie / "index.html", page_accueil(commits, version))
    ecrire(sortie / "telecharger.html", page_telecharger(sortie, version))
    ecrire(sortie / "nouveautes.html", page_nouveautes(commits, version))
    ecrire(sortie / "404.html", page_404(version))
    for fichier in DOCS:
        if (depot / fichier).exists():
            href, texte = page_doc(depot, fichier, version)
            ecrire(sortie / href, texte)
    ecrire(tampon, marque)
    return True


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--depot", default=str(ICI.parent), help="dossier du dépôt git (par défaut : celui de ce script)")
    ap.add_argument("--sortie", required=True, help="dossier du site généré")
    ap.add_argument("--miroir", action="store_true", help="copier aussi les fichiers d'installation publiés")
    ap.add_argument("--force", action="store_true", help="tout régénérer même si rien n'a changé")
    a = ap.parse_args()
    if generer(a.depot, a.sortie, a.miroir, a.force):
        print(f"{datetime.now():%d/%m/%Y %H:%M} site régénéré ({git(a.depot, 'rev-parse', '--short', 'HEAD')})")
