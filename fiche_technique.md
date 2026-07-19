# FICHE TECHNIQUE : SYSTÈME DE COMMANDE GOTO-ANDRIVET
*Version 9.2 (Dual Architecture : Mega & Teensy) — Juin 2026*

Ce document regroupe les spécifications électriques, le schéma de câblage des drivers **M542**, les paramètres mécaniques et les protocoles de communication pour le système de commande motorisé GoTo universel (GotoAndrivet).

---

## 1. Choix de l'Architecture (Monture Mega vs Teensy)

Le projet **Goto-Andrivet** propose désormais deux versions différentes pour le "cerveau" de la monture (le contrôleur moteur principal). Le choix de la carte affecte directement la puissance de calcul pour le suivi et les modèles de pointage.

### Option A : Contrôleur Arduino Mega 2560 (Dossier `mega_monture`)
* **Processeur :** 8-bit AVR @ 16 MHz.
* **Avantage :** Matériel très standard, robuste et peu cher.
* **Inconvénient :** Puissance de calcul très limitée. Il effectue d'excellents suivis basiques (1 étoile), mais il est incapable de faire fonctionner des modèles de pointage complexes (multi-étoiles) sans perdre la fluidité des moteurs.

### Option B : Contrôleur Teensy 4.1 (Dossier `teensy_monture`)
* **Processeur :** 32-bit ARM Cortex-M7 @ 600 MHz avec coprocesseur mathématique (FPU).
* **Avantage :** Une puissance phénoménale. Il génère des pas moteurs d'une fluidité parfaite même à très haute vitesse et permet les calculs matriciels complexes requis pour l'alignement multi-étoiles sans aucune saccade.
* **Inconvénient :** Plus coûteux.

> [!NOTE]
> Quel que soit le contrôleur choisi pour la monture, la télécommande (**Raquette**) reste toujours propulsée par un Teensy 4.1 (Dossier `teensy_raquette`) en raison de l'affichage graphique LCD et des calculs d'éphémérides requis.

---

## 2. Caractéristiques de Communication

*   **Liaison USB (PC / ASIAir / INDI) :** **38 400 bauds** (Vitesse optimisée pour la télémétrie en temps réel).
*   **Liaison Raquette (Connecteur DIN 4 broches) :** **38 400 bauds**.
*   **Protocole :** Meade LX200 avec extensions OnStep (supporté par KStars/Ekos, Stellarium, SkySafari).

---

## 3. Schéma de Câblage Électrique (Côté Monture)

Le câblage des drivers moteurs vers le contrôleur reste quasiment identique quelle que soit la carte utilisée. Les drivers M542 sont raccordés en configuration **Cathode Commune (GND commun)**.

### Broches selon le contrôleur choisi :

| Composant | Broche Arduino Mega 2560 | Broche Teensy 4.1 |
|---|---|---|
| **Moteur AZ (Step)** | Pin 2 | Pin 2 |
| **Moteur AZ (Dir)** | Pin 3 | Pin 3 |
| **Moteur ALT (Step)** | Pin 5 | Pin 5 |
| **Moteur ALT (Dir)** | Pin 6 | Pin 6 |
| **Buzzer** | Pin 49 | Pin 20 |
| **GPS (RX / TX)** | Pin 17 / Pin 16 (Serial2) | Pin 16 / Pin 17 (Serial4) |
| **Raquette (RX / TX)** | Pin 15 / Pin 14 (Serial3) | Pin 15 / Pin 14 (Serial3) |

> [!IMPORTANT]
> Pour le Teensy 4.1, les broches physiques pour le GPS restent aux emplacements 16 et 17, mais elles correspondent au port matériel `Serial4` (au lieu du `Serial2` sur le Mega). Le câblage physique des fils volants est donc préservé !

---

## 4. Paramètres Mécaniques et Résolutions

La résolution de déplacement (PPD - Pas par Degré) de la monture est calculée selon la formule :

$$PPD = \frac{\text{Pas Moteur} \times \text{Microstepping} \times \text{Rapport Réduction}}{360}$$

### Valeurs de Référence (Configurables) :
*   **Pas moteur par tour :** 200 pas.
*   **Microstepping :** 80 (configuré sur les drivers pour donner 16 000 pas/tour).
*   **Rapport de réduction (AZ/ALT) :** 750.0.
*   **Résolution calculée :** **33 333,33 pas/degré**.

---

## 5. Modes de Suivi (Tracking)

*   **Suivi Sidéral (Ciel profond) :** Calculé en temps réel toutes les 500 ms à partir du Temps Sidéral Local (LST) de l'horloge.
*   **Suivi Lunaire (`:TL#`) :** Vitesse de l'angle horaire (HA) ralentie de **~2,37%** (facteur d'échelle `0.976327`) pour compenser le déplacement orbital de la Lune.
*   **Suivi Solaire (`:TS#`) :** Vitesse ralentie de **~0,27%** (facteur d'échelle `0.997270`) pour compenser le mouvement orbital de la Terre.

---

## 6. Câblage de la Raquette Physique (Teensy 4.1)

La raquette physique est articulée autour d'une carte **Teensy 4.1**.

### 1. Connecteur DIN 4 broches (Communication + Alimentation depuis la Monture)

| Pin DIN | Signal | Broche Teensy |
|---|---|---|
| **1** | GND | **GND** |
| **2** | 5V (alimentation) | **VIN** |
| **3** | TX (Teensy → Monture) | **Pin 1 (TX1)** |
| **4** | RX (Monture → Teensy) | **Pin 0 (RX1)** |

> [!WARNING]
> La monture doit fournir assez de courant au Teensy via la pin VIN. Ne pas alimenter le Teensy par son port USB si le câble DIN l'alimente déjà, sauf si le pad `VUSB` sous le Teensy a été physiquement sectionné.

### 2. Écran LCD Grove I2C
* **SDA** $\rightarrow$ Broche **Pin 18 (SDA0)** de la Teensy
* **SCL** $\rightarrow$ Broche **Pin 19 (SCL0)** de la Teensy
* **VCC** $\rightarrow$ Broche **5V** (ou **3.3V** selon le modèle Grove)
* **GND** $\rightarrow$ Broche **GND**

### 3. Boutons Poussoirs (Clavier directionnel)
Les boutons sont câblés en **INPUT_PULLUP** (reliés entre la broche et le GND). Aucun besoin de résistance externe !

* **Haut (UP)** $\rightarrow$ Broche **Pin 6**
* **Bas (DOWN)** $\rightarrow$ Broche **Pin 7**
* **Gauche (LEFT)** $\rightarrow$ Broche **Pin 8**
* **Droite (RIGHT)** $\rightarrow$ Broche **Pin 9**
* **Entrée/OK (ENTER)** $\rightarrow$ Broche **Pin 10**
