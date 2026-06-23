# GotoUniversal — Contrôleur Multi-Montures OnStep

Ce projet supporte de manière universelle trois types de montures astronomiques :
1. **Alt-Azimutale (AltAz)** : Pour montures Dobson et Alt-Azimutales standards.
2. **Fourche Équatoriale (ForkEq)** : Pour montures équatoriales à fourche ou tables équatoriales (aucun retournement de méridien requis, suivi sidéral direct sur l'angle horaire).
3. **Monture Équatoriale Allemande (GermanEq / GEM)** : Pour montures équatoriales allemandes (gestion automatique du **retournement de méridien** et de la position de pilier *Pier Side* Est/Ouest).

---

## Structure du Projet

* **`goto_universal.py`** : L'application principale en Python (interface graphique Tkinter avec carte du ciel interactive, catalogues Messier/NGC/IC/Caldwell et dérotateur).
* **`goto_universal_config_tool.py`** : L'utilitaire de configuration en style Windows 95 permettant de régler les coordonnées, vitesses, rapports d'engrenage et de flasher le firmware.
* **`raquette_virtuelle.py`** : L'émulateur de la raquette Teensy pour piloter le télescope depuis l'ordinateur.
* **`goto_universal_mega/`** : Le firmware C++ pour la carte Arduino Mega 2560.
* **`goto_universal_raquette/`** : Le firmware C++ pour la raquette physique Teensy 4.1.

---

## Fonctionnalités Avancées

* **Ajout du type de monture `GermanEq`** : Le firmware de l'Arduino Mega calcule automatiquement les inversions d'axes (Ascension Droite et Déclinaison) lors du franchissement du méridien.
* **Commande standard `:Gm#` implémentée** : Renvoie le *Pier Side* (`E#` pour l'Est, `W#` pour l'Ouest, `N#` pour les autres modes) requis pour les logiciels de guidage comme Ekos/INDI.
* **Intégration complète dans les interfaces** : Le sélecteur de monture dans `goto_universal_config_tool.py`, `goto_universal.py` et la raquette physique Teensy supporte désormais les trois options distinctes (`AltAz`, `ForkEq`, `GermanEq`).

---

## Licence

Ce projet est sous licence **GNU GPL v3**. Consultez le fichier [LICENSE](LICENSE) pour plus de détails.
