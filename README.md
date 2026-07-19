# GotoAndrivet — Contrôleur Multi-Montures OnStep

Ce projet supporte de manière universelle trois types de montures astronomiques :
1. **Alt-Azimutale (AltAz)** : Pour montures Dobson et Alt-Azimutales standards.
2. **Fourche Équatoriale (ForkEq)** : Pour montures équatoriales à fourche ou tables équatoriales (aucun retournement de méridien requis, suivi sidéral direct sur l'angle horaire).
3. **Monture Équatoriale Allemande (GermanEq / GEM)** : Pour montures équatoriales allemandes (gestion automatique du **retournement de méridien** et de la position de pilier *Pier Side* Est/Ouest).

---

## Structure du Projet

* **`goto_andrivet.py`** : L'application principale en Python (interface graphique Tkinter avec carte du ciel interactive, catalogues Messier/NGC/IC/Caldwell et dérotateur).
* **`goto_andrivet_config_tool.py`** : L'utilitaire de configuration en style Windows 95 permettant de régler les coordonnées, vitesses, rapports d'engrenage et de flasher le firmware.
* **`raquette_virtuelle.py`** : L'émulateur de la raquette Teensy pour piloter le télescope depuis l'ordinateur.
* **`mega_monture/`** : Le firmware classique (1 étoile) pour le contrôleur Arduino Mega 2560.
* **`teensy_monture/`** : Le nouveau firmware haute performance pour contrôleur Teensy 4.1 (Inclut le Modèle de Pointage N-Étoiles par interpolation IDW).
* **`teensy_raquette/`** : Le firmware C++ pour la raquette physique avec écran LCD (sur Teensy 4.1).

---

## Guide d'Installation & Mode d'Emploi

### 1. Prérequis
Pour exécuter les applications graphiques en Python sur votre ordinateur, vous devez disposer de **Python 3**, du module **Tkinter** et de la bibliothèque **pyserial**.

Sur Ubuntu / Debian / Raspberry Pi OS, installez-les via votre terminal :
```bash
sudo apt update
sudo apt install python3 python3-tk python3-pip
pip3 install pyserial
```

### 2. Démarrage des Applications
Exécutez les scripts Python correspondants depuis le dossier du projet :

* **Configuration & Flashage** :
  ```bash
  python3 goto_andrivet_config_tool.py
  ```
* **Cartographie du Ciel & Pilotage** :
  ```bash
  python3 goto_andrivet.py
  ```
* **Raquette Virtuelle (Émulateur)** :
  ```bash
  python3 raquette_virtuelle.py
  ```

### 3. Compiler & Flasher sans IDE Arduino
Vous pouvez programmer vos cartes directement depuis l'utilitaire de configuration (sans avoir besoin d'ouvrir l'IDE Arduino classique) :
1. Installez l'utilitaire [arduino-cli](https://arduino.github.io/arduino-cli/latest/) sur votre PC.
2. Ouvrez l'utilitaire de configuration (`python3 goto_andrivet_config_tool.py`).
3. Sélectionnez le **Port** série de votre carte dans les paramètres de connexion.
4. Dans l'encadré **« Téléversement du Firmware »**, cliquez sur le bouton correspondant à votre carte pour compiler et flasher automatiquement.

### 4. Schéma de Câblage Rapide (Monture : Mega ou Teensy)

Câblez votre contrôleur principal en suivant ce schéma (les broches sont identiques pour le Mega et le Teensy, à l'exception de la broche du Buzzer) :

| Composant / Axe | Broche Arduino Mega 2560 | Broche Teensy 4.1 | Signal Module / Driver |
| :--- | :--- | :--- | :--- |
| **Moteur Azimut (AZ/RA)** | **Pin 2** | **Pin 2** | `PUL+` (Pulse/Step) |
| | **Pin 3** | **Pin 3** | `DIR+` (Direction) |
| | **Pin 4** | **Pin 4** | `ENB+` (Enable - Optionnel) |
| **Moteur Altitude (ALT/DEC)** | **Pin 5** | **Pin 5** | `PUL+` (Pulse/Step) |
| | **Pin 6** | **Pin 6** | `DIR+` (Direction) |
| | **Pin 7** | **Pin 7** | `ENB+` (Enable - Optionnel) |
| **Moteur Dérotateur** | **Pin 8** | **Pin 8** | `PUL+` (Pulse/Step) |
| | **Pin 9** | **Pin 9** | `DIR+` (Direction) |
| | **Pin 10** | **Pin 10** | `ENB+` (Enable - Optionnel) |
| **Moteur Focuseur** | **Pin 11** | **Pin 11** | `PUL+` (Pulse/Step) |
| | **Pin 12** | **Pin 12** | `DIR+` (Direction) |
| | **Pin 13** | **Pin 13** | `ENB+` (Enable - Optionnel) |
| **Buzzer** | **Pin 49** | **Pin 20** | Borne `+` (via résistance 100 Ω) |
| **Raquette Teensy** | **Pin 15 (RX3)** | **Pin 15 (RX3)** | `TX` de la raquette Teensy |
| | **Pin 14 (TX3)** | **Pin 14 (TX3)** | `RX` de la raquette Teensy |
| **Module GPS** | **Pin 17 (RX2)** | **Pin 17 (RX4)** | `TX` du module GPS |
| | **Pin 16 (TX2)** | **Pin 16 (TX4)** | `RX` du module GPS |

*Note : Les signaux de masse négatifs (`PUL-`, `DIR-`, `ENB-` des drivers, GND du buzzer, du GPS et de la Teensy) doivent tous être connectés à une broche **GND** de votre carte.*
*(Consultez le fichier `fiche_technique.md` pour des explications approfondies).*

### 4.1 Schéma de Câblage de la Raquette (Teensy 4.1)

Si vous fabriquez la raquette physique avec un Teensy 4.1, voici le câblage à effectuer :

| Composant | Broche Teensy 4.1 | Connexion / Signal |
| :--- | :--- | :--- |
| **Écran LCD (I2C)** | **Pin 18 (SDA0)** | `SDA` de l'écran LCD |
| | **Pin 19 (SCL0)** | `SCL` de l'écran LCD |
| | **VIN** | `VCC` (5V) de l'écran LCD |
| | **GND** | `GND` de l'écran LCD |
| **Boutons Poussoirs** | **Pin 6** | Bouton **Haut (UP)** (vers GND) |
| | **Pin 7** | Bouton **Bas (DOWN)** (vers GND) |
| | **Pin 8** | Bouton **Gauche (LEFT)** (vers GND) |
| | **Pin 9** | Bouton **Droite (RIGHT)** (vers GND) |
| | **Pin 10** | Bouton **Validation (ENTER)** (vers GND) |
| **Câble RJ11 (vers Mega)**| **GND** | Pin 1 RJ11 (`GND` de la Monture) |
| | **VIN** | Pin 2 RJ11 (`VIN` / `5V` de la Monture) |
| | **Pin 1 (TX1)** | Pin 3 RJ11 (vers `RX3` Pin 15 Monture) |
| | **Pin 0 (RX1)** | Pin 4 RJ11 (vers `TX3` Pin 14 Monture) |

*ATTENTION : Le Teensy est alimenté par la pin 5V du Mega via VIN. Ne pas brancher l'USB du Teensy en même temps, sauf si le pad VUSB a été coupé au préalable.*

### 5. Matériel Compatible

Pour monter votre système GotoAndrivet, les composants matériels suivants sont compatibles et recommandés :

* **Cartes de Contrôle** :
  * **Arduino Mega 2560** ou **Teensy 4.1** (au choix pour la carte principale de la monture).
  * **Teensy 4.1** (pour la raquette de commande physique - *Optionnelle*).
* **Drivers de Moteurs** :
  * Drivers standard acceptant des entrées `PUL/DIR` (Impulsion/Direction) comme les modèles **M542**, **DM542**, **TB6600**, **TMC2209**, etc.
* **Moteurs** :
  * Moteurs pas à pas bipolaires (ex. **NEMA 17** ou **NEMA 23** en 200 pas/tour).
* **Module GPS (Optionnel)** :
  * Module **Adafruit Ultimate GPS** (MTK3339) ou tout autre récepteur GPS délivrant des trames NMEA standards à 9600 bauds sur port série.
* **Afficheur Raquette** :
  * Écran **LCD 20x4** caractères équipé d'un adaptateur **I2C** (généralement à l'adresse `0x27`).
* **Boutons Raquette** :
  * 5 boutons poussoirs momentanés (Haut, Bas, Gauche, Droite, Validation).
* **Alerte Sonore** :
  * Un **Buzzer actif 5V**.

*Note concernant la raquette physique : La construction de la raquette matérielle (carte Teensy, écran LCD et boutons) n'est **pas obligatoire**. Si vous utilisez la monture en mode "remote", ou que vous la pilotez exclusivement depuis un PC, un planétarium, ou un boîtier type ASIAIR, l'Arduino Mega suffit à lui seul pour tout gérer via la connexion USB.*

---

## Fonctionnalités Avancées

* **Modèle de Pointage N-Étoiles (Teensy Monture uniquement)** : Interpolation des erreurs de suivi et de pointage par IDW (Inverse Distance Weighting) jusqu'à 20 étoiles mémorisées. Support de la commande de remise à zéro `:CML#`.
* **Ajout du type de monture `GermanEq`** : Le firmware de l'Arduino Mega calcule automatiquement les inversions d'axes (Ascension Droite et Déclinaison) lors du franchissement du méridien.
* **Commande standard `:Gm#` implémentée** : Renvoie le *Pier Side* (`E#` pour l'Est, `W#` pour l'Ouest, `N#` pour les autres modes) requis pour les logiciels de guidage comme Ekos/INDI.
* **Intégration complète dans les interfaces** : Le sélecteur de monture dans `goto_andrivet_config_tool.py`, `goto_andrivet.py` et la raquette physique Teensy supporte désormais les trois options distinctes (`AltAz`, `ForkEq`, `GermanEq`).

---

## Licence

Ce projet est sous licence **GNU GPL v3**. Consultez le fichier [LICENSE](LICENSE) pour plus de détails.
