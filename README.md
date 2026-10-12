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

Câblez votre contrôleur principal en suivant ce schéma (les broches sont identiques pour le Mega et le Teensy, à l'exception du Buzzer, de l'`ENB` du focuseur et du GPS, dont les fils TX/RX sont croisés d'une carte à l'autre) :

| Composant / Axe | Broche Arduino Mega 2560 | Broche Teensy 4.1 | Signal Module / Driver |
| :--- | :--- | :--- | :--- |
| **Moteur Azimut (AZ/RA)** | **Pin 2** | **Pin 2** | `PUL+` (Pulse/Step) |
| | **Pin 3** | **Pin 3** | `DIR+` (Direction) |
| | **Pin 4** | **Pin 4** | `ENB+` (Enable) |
| **Moteur Altitude (ALT/DEC)** | **Pin 5** | **Pin 5** | `PUL+` (Pulse/Step) |
| | **Pin 6** | **Pin 6** | `DIR+` (Direction) |
| | **Pin 7** | **Pin 7** | `ENB+` (Enable) |
| **Moteur Dérotateur** | **Pin 8** | **Pin 8** | `PUL+` (Pulse/Step) |
| | **Pin 9** | **Pin 9** | `DIR+` (Direction) |
| | **Pin 10** | **Pin 10** | `ENB+` (Enable) |
| **Moteur Focuseur** | **Pin 11** | **Pin 11** | `PUL+` (Pulse/Step) |
| | **Pin 12** | **Pin 12** | `DIR+` (Direction) |
| | **Pin 13** | **Pin 21** | `ENB+` (Enable) |
| **Buzzer** | **Pin 49** | **Pin 20** | Borne `+` (actif : direct / passif : via résistance 100 Ω) |
| **Port Série PC** | **Non dispo** | **Pin 25 (RX6)** | `TX` de l'adaptateur USB/Série TTL (Câble long) |
| | **Non dispo** | **Pin 24 (TX6)** | `RX` de l'adaptateur USB/Série TTL |
| **Raquette Teensy** | **Pin 15 (RX3)** | **Pin 15 (RX3)** | `TX` de la raquette Teensy |
| | **Pin 14 (TX3)** | **Pin 14 (TX3)** | `RX` de la raquette Teensy |
| **Module GPS** | **Pin 17 (RX2)** | **Pin 16 (RX4)** | `TX` du module GPS |
| | **Pin 16 (TX2)** | **Pin 17 (TX4)** | `RX` du module GPS |
| **Drivers TMC5160 (SPI1, PCB)** | **Non dispo** | **Pin 26 (MOSI1)** | `SDI` des modules (ponts SPI fermés) |
| | **Non dispo** | **Pin 27 (SCK1)** | `SCK` des modules |
| | **Non dispo** | **Pin 39 (MISO1)** | `SDO` des modules |
| | **Non dispo** | **Pins 41 / 40 / 38 / 37** | `CSN` AZ / ALT / Dérotateur / Focuseur |

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

### 5. Arduino Mega 2560 vs Teensy 4.1 (Contrôleur de Monture)

Le projet vous permet de choisir le cerveau principal de la monture. Bien que le câblage soit quasiment identique, voici les différences pour vous aider à choisir :

| Caractéristique | Arduino Mega 2560 | Teensy 4.1 |
| :--- | :--- | :--- |
| **Vitesse de calcul** | 16 MHz (8-bit) | **600 MHz** (32-bit ARM) |
| **Précision (Maths)** | Flottants 32-bit lents | **Flottants 64-bit (double)** natifs ultra-rapides |
| **Microstepping & Vitesse max**| Limité (saturera à très haut microstepping) | **Parfait** (génère des impulsions à plus de 200kHz sans sourciller) |
| **Modèle de pointage** | Basique | **N-Étoiles** (50 points mémorisés avec calculs IDW) |
| **Evolutivité (Futur)** | Faible | **Très haute** (Port USB Host pour Manette/Gamepad) |
| **Coût** | ~15-20€ (Clones pas chers) | ~35-40€ |

**Recommandation** : Si vous utilisez de petits drivers (1/16 ou 1/32 de pas) et voulez un système économique, le **Mega 2560** fait parfaitement le travail. Si vous utilisez des drivers modernes (TMC2209, M542) à fort microstepping (1/128, 1/256), que vous voulez des déplacements GoTo ultra-rapides et silencieux, et le modèle de pointage multi-étoiles intégré, optez sans hésiter pour le **Teensy 4.1**.

### 6. Matériel Compatible

Pour monter votre système GotoAndrivet, les composants matériels suivants sont compatibles et recommandés :

* **Cartes de Contrôle** :
  * **Arduino Mega 2560** ou **Teensy 4.1** (au choix pour la carte principale de la monture).
  * **Teensy 4.1** (pour la raquette de commande physique - *Optionnelle*).
* **Drivers de Moteurs** :
  * Drivers standard acceptant des entrées `PUL/DIR` (Impulsion/Direction) comme les modèles **M542**, **DM542**, **TB6600**, **TMC2209**, etc.
  * Sur le PCB monture (Teensy) : modules au format StepStick, dont le **BTT TMC5160 Pro** configuré en SPI (voir plus bas).
* **Moteurs** :
  * Moteurs pas à pas bipolaires (ex. **NEMA 17** ou **NEMA 23** en 200 pas/tour).
* **Module GPS (Optionnel)** :
  * Module **Adafruit Ultimate GPS** (MTK3339) ou tout autre récepteur GPS délivrant des trames NMEA standards à 9600 bauds sur port série.
* **Afficheur Raquette** :
  * Écran **LCD 20x4** caractères équipé d'un adaptateur **I2C** (généralement à l'adresse `0x27`).
* **Boutons Raquette** :
  * 5 boutons poussoirs momentanés (Haut, Bas, Gauche, Droite, Validation).
* **Alerte Sonore** :
  * Un **Buzzer actif 5V** ou un **Buzzer passif**. (Si vous utilisez un buzzer actif, câblez-le directement ; si vous utilisez un buzzer passif, ajoutez une résistance de 100 Ω en série avec le signal).

*Note concernant la raquette physique : La construction de la raquette matérielle (carte Teensy, écran LCD et boutons) n'est **pas obligatoire**. Si vous utilisez la monture en mode "remote", ou que vous la pilotez exclusivement depuis un PC, un planétarium, ou un boîtier type ASIAIR, l'Arduino Mega suffit à lui seul pour tout gérer via la connexion USB.*

---

## Fonctionnalités Avancées

* **Modèle de Pointage N-Étoiles (Teensy Monture uniquement)** : Interpolation des erreurs de suivi et de pointage par IDW (Inverse Distance Weighting) jusqu'à 50 étoiles mémorisées. Support de la commande de remise à zéro `:CML#`.
* **Ajout du type de monture `GermanEq`** : Le firmware de l'Arduino Mega calcule automatiquement les inversions d'axes (Ascension Droite et Déclinaison) lors du franchissement du méridien.
* **Commande standard `:Gm#` implémentée** : Renvoie le *Pier Side* (`E#` pour l'Est, `W#` pour l'Ouest, `N#` pour les autres modes) requis pour les logiciels de guidage comme Ekos/INDI.
* **Commande standard `:D#` implémentée** : Permet l'interrogation dynamique du statut de pointage (Slewing), accélérant drastiquement le modèle de pointage automatique ZWO en évitant les pauses fixes.
* **Intégration complète dans les interfaces** : Le sélecteur de monture dans `goto_andrivet_config_tool.py`, `goto_andrivet.py` et la raquette physique Teensy supporte désormais les trois options distinctes (`AltAz`, `ForkEq`, `GermanEq`).

---

## Licence

Ce projet est sous licence **GNU GPL v3**. Consultez le fichier [LICENSE](LICENSE) pour plus de détails.

## Mise à jour Matérielle (PCB 36V / 12V + Drivers Externes)
- Chaque axe dispose de deux sorties sur la carte mère :
  - un support au format **StepStick / Pololu** (2 × 8 broches espacées de 12,7 mm) ;
  - des pastilles à souder **DRIVER EXT. 5V** (EN, STEP, DIR, GND) pour des drivers externes plus puissants, par exemple M542, DM542 ou DM556.
- **Sélecteur de drivers** : l'interrupteur DIP `SW_SEL` a 4 positions, une par axe (AZ, ALT, DER, FOC).
  - Sur **OFF** (réglage par défaut), l'axe est piloté par le module StepStick ; les sorties externes sont coupées.
  - Sur **ON**, l'axe est piloté par le driver externe. Les signaux sont convertis en 5 V par des 74HCT125, ce qui suffit pour les optocoupleurs. Le support StepStick est coupé et son module désactivé.
  - On peut donc, par exemple, mettre de gros drivers sur AZ/ALT et garder des StepSticks pour le dérotateur et le focuseur. Le firmware n'a rien à savoir de ce réglage.
- Orientation d'un module StepStick : sa broche **EN** va sur la pastille marquée `EN` (en haut à gauche). **VMOT** se trouve donc en face, sur la pastille marquée `VM`. La logique des modules (VIO) est alimentée en **3,3 V**.
- **Ponts SPI (TMC5160)** : sous chaque support, entre les deux rangées, se trouvent 5 ponts à souder marqués `SPI`. Ils sont en face des broches 2 à 6 du module. De haut en bas : `SDI` vers MOSI1 (broche 26), `SCK` vers SCK1 (27), `CSN` vers le CS de l'axe (41 AZ, 40 ALT, 38 dérotateur, 37 focuseur), `SDO` vers MISO1 (39), et `CLK` vers GND (horloge interne du TMC5160).
  - **Ponts ouverts** (réglage par défaut) : le support accepte les modules STEP/DIR sans SPI, c'est-à-dire TMC2208/TMC2209 en mode autonome, A4988 (reliez RESET à SLEEP sur le module) ou DRV8825.
  - **Les 5 ponts fermés** (une goutte d'étain chacun) : pour un **BTT TMC5160 Pro**, ou un autre TMC5160 au format StepStick avec le même brochage (EN, SDI, SCK, CSN, SDO, CLK, STEP, DIR).
  - Ne fermez jamais les ponts avec un A4988, un DRV8825 ou un TMC2209 : leurs broches MSx, RESET et SLEEP se retrouveraient sur le bus SPI.
- **Configuration des TMC5160 (firmware Teensy)** : au démarrage, puis chaque seconde, le firmware cherche un TMC5160 sur chaque axe et le configure (courant, micro-pas, stealthChop). Un TMC5160 en SPI garde son étage de puissance coupé tant qu'il n'est pas configuré. Si le 36V n'est pas encore là, le module ne répond pas : il est configuré dès que le 36V arrive, et reconfiguré après une coupure.
  - Micro-pas : AZ/ALT utilisent le réglage *Microstepping*, qui doit être une puissance de 2 (16, 32, 64, 128 ou 256). Une valeur comme 125 est refusée et l'axe reste coupé (état `M`). Le dérotateur et le focuseur sont à 16 micro-pas par défaut : ajustez les *Pas/Deg* du dérotateur en conséquence.
  - Courant : il se règle dans l'outil de configuration, de 100 à 3000 mA RMS par axe (Rsense 0,075 Ω du BTT TMC5160 Pro), avec un courant de maintien en %. Valeurs par défaut : 800 mA pour AZ/ALT, 400 mA pour le dérotateur et le focuseur, maintien à 50 %.
  - Commandes : `:XFS0#` / `:XFS1#` (désactiver / activer, activé par défaut), `:XTS#` (état par axe : `-` SPI désactivé, `0` absent, `1` configuré, `M` micro-pas refusé, `E` défaut driver), `:XTI<a|e|d|f>[mA]#` (courant), `:XTH[%]#` (maintien), `:XTP[0|1]#` (stealthChop), `:XTMd[n]#` / `:XTMf[n]#` (micro-pas dérotateur / focuseur), `:XTC#` (tout reconfigurer). Sans valeur, ces commandes renvoient le réglage en cours.
  - Le firmware Mega n'a pas de SPI : le PCB est prévu pour le Teensy.
  - Hauteur : un TMC5160 avec radiateur est plus haut qu'un StepStick ordinaire. Le boîtier fait donc 45 mm de haut (`box_h` dans `boitier_monture.scad`), ce qui laisse 25,8 mm entre la carte du module et le couvercle. Un BTT TMC5160 Pro (23,2 mm hors tout) passe avec au moins 4 mm de marge, et les grilles du couvercle se trouvent au-dessus des radiateurs.
- Le Teensy 4.1 de la monture n'a pas de port USB Host câblé.
- Une prise **jack 12V** est ajoutée en plus du bornier 36V. Elle passe par la diode `D_JACK` (SB560), ce qui évite que le 36V du bornier remonte dans le bloc 12V.
- Sur le Teensy de la monture, **coupez le pont VUSB-VIN** sous la carte : le Teensy est alimenté par le 5V du PCB (VIN) et reste branché en USB au PC.
- Port **PC SERIAL** (Serial6, broches 24/25) : les repères RX/TX sont donnés côté Teensy (`3 TX6`, `4 RX6`). Il faut donc les croiser vers l'adaptateur, et ne pas brancher son 5V sur la broche `2 +5V`.
