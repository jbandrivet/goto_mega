# FICHE TECHNIQUE : SYSTÈME DE COMMANDE GOTOUNIVERSAL
*Version 5.2 (Alignée Mega v9.1 + Teensy v6.2) — Juin 2026*

Ce document regroupe les spécifications électriques, le schéma de câblage des drivers **M542**, les paramètres mécaniques et les protocoles de communication pour le système de commande motorisé GoTo universel (GotoUniversal).

---

## 1. Caractéristiques de Communication

*   **Liaison USB (PC / ASIAir / INDI) :** **38 400 bauds** (Vitesse optimisée pour la télémétrie en temps réel).
*   **Liaison Raquette (Serial3 / DIN 4 broches) :** **38 400 bauds**.
*   **Protocole :** Meade LX200 avec extensions OnStep (supporté par KStars/Ekos, Stellarium, SkySafari).

---

## 2. Schéma de Câblage Électrique (Arduino Mega 2560)

> [!IMPORTANT]
> **Repérage physique des broches sur votre carte Arduino Mega :**
> - Les pins **2 à 7** (moteurs) se situent dans la rangée étiquetée **`PWM`** (qui contient les broches `0` à `13`).
> - Les pins **14 et 15** (raquette Teensy) se situent dans la rangée étiquetée **`COMMUNICATION`**.
> - La pin **49** (buzzer) se situe dans le grand bloc double-rangée étiqueté **`DIGITAL`** qui commence à `22` (situé à l'extrémité de la carte).
> - Les pins **GND** (masses) et **5V** (alimentation) se situent dans la section étiquetée **`POWER`**.

### Axe Azimut / RA (Moteur AZ)
Le driver de l'axe Azimut (AZ) est raccordé en configuration **Cathode Commune (GND commun)** :
*   **`PUL+` (Pulse / Step)** $\rightarrow$ Broche **Pin 2** (dans la zone **`PWM`**)
*   **`DIR+` (Direction)** $\rightarrow$ Broche **Pin 3** (dans la zone **`PWM`**)
*   **`ENB+` (Enable)** $\rightarrow$ Broche **Pin 4** (dans la zone **`PWM`**) *(Optionnel - Voir note)*
*   **`PUL-` / `DIR-` / `ENB-`** $\rightarrow$ Reliés ensemble $\rightarrow$ **GND** (dans la zone **`POWER`**)

### Axe Altitude / DEC (Moteur ALT)
Le driver de l'axe Altitude (ALT) est raccordé de la même manière :
*   **`PUL+` (Pulse / Step)** $\rightarrow$ Broche **Pin 5** (dans la zone **`PWM`**)
*   **`DIR+` (Direction)** $\rightarrow$ Broche **Pin 6** (dans la zone **`PWM`**)
*   **`ENB+` (Enable)** $\rightarrow$ Broche **Pin 7** (dans la zone **`PWM`**) *(Optionnel - Voir note)*
*   **`PUL-` / `DIR-` / `ENB-`** $\rightarrow$ Reliés ensemble $\rightarrow$ **GND** (dans la zone **`POWER`**)

> [!NOTE]
> **Activation des drivers (ENB) :** Les drivers M542 sont activés par défaut lorsque aucun courant ne traverse le signal `ENB`. Les raccordements à la **Pin 4** et **Pin 7** sont donc optionnels si vous souhaitez laisser les moteurs constamment sous tension (recommandé pour éviter le glissement de la monture).

### Le Buzzer (Alerte sonore)
*   **Borne positive (+)** $\rightarrow$ Résistance de 100 $\Omega$ $\rightarrow$ Broche **Pin 49** (dans la zone **`DIGITAL`** commençant à 22)
*   **Borne négative (-)** $\rightarrow$ **GND** (dans la zone **`POWER`**)

### Connecteur DIN 4 broches Raquette (Teensy 4.1 $\leftrightarrow$ Mega)

Connecteur DIN 4 broches avec détrompeur intégré (mâle côté câble, femelle châssis côté boîtier raquette).

| Pin DIN | Signal | Broche Mega | Zone sur la carte |
|---|---|---|---|
| **1** | GND | **GND** | **`POWER`** |
| **2** | 5V (alim Teensy → VIN) | **5V** | **`POWER`** |
| **3** | TX (Teensy → Mega) | **Pin 15 (RX3)** | **`COMMUNICATION`** |
| **4** | RX (Mega → Teensy) | **Pin 14 (TX3)** | **`COMMUNICATION`** |

> [!WARNING]
> Le Mega doit être alimenté par **barrel jack (7-12V DC)** pour fournir assez de courant au Teensy via la pin 5V. Ne pas alimenter le Mega uniquement par USB si la raquette est branchée.
> **Ne pas brancher l'USB du Teensy** quand le VIN est alimenté, sauf si le pad VUSB est coupé.

### Module GPS (Adafruit Ultimate GPS Breakout v3)
Le module GPS (pour l'heure et la position exactes) communique via le port série matériel 2 (`Serial2`) à 9600 bauds. Le module Adafruit v3 est 100% compatible avec la logique 5V de l'Arduino Mega.

*   **VIN (Alimentation)** $\rightarrow$ **5V** (dans la zone **`POWER`** du Mega)
*   **GND (Masse)** $\rightarrow$ **GND** (dans la zone **`POWER`** du Mega)
*   **TX (Transmission GPS)** $\rightarrow$ Broche **Pin 17 (RX2)** (dans la zone **`COMMUNICATION`** du Mega)
*   **RX (Réception GPS)** $\rightarrow$ Broche **Pin 16 (TX2)** (dans la zone **`COMMUNICATION`** du Mega)

---

## 3. Paramètres Mécaniques et Résolutions

La résolution de déplacement (PPD - Pas par Degré) de la monture est calculée selon la formule :

$$PPD = \frac{\text{Pas Moteur} \times \text{Microstepping} \times \text{Rapport Réduction}}{360}$$

### Valeurs de Référence (Configurables) :
*   **Pas moteur par tour :** 200 pas.
*   **Microstepping :** 80 (configuré sur les drivers pour donner 16 000 pas/tour).
*   **Rapport de réduction (AZ/ALT) :** 750.0.
*   **Résolution calculée :** **33 333,33 pas/degré**.

---

## 4. Modes de Suivi (Tracking)

*   **Suivi Sidéral (Ciel profond) :** Calculé en temps réel par l'Arduino Mega toutes les 500 ms à partir du Temps Sidéral Local (LST) de l'horloge.
*   **Suivi Lunaire (`:TL#`) :** Vitesse de l'angle horaire (HA) ralentie de **~2,37%** (facteur d'échelle `0.976327`) pour compenser le déplacement orbital de la Lune.
*   **Suivi Solaire (`:TS#`) :** Vitesse ralentie de **~0,27%** (facteur d'échelle `0.997270`) pour compenser le mouvement orbital de la Terre.

## Câblage de la Raquette Physique (Teensy 4.1)

La raquette physique est articulée autour d'une carte **Teensy 4.1**, alimentée par le **5V du Mega** via sa broche **VIN** (plage acceptée : 3.6V – 5.5V).

### 1. Connecteur DIN 4 broches (Communication + Alimentation depuis le Mega)

| Pin DIN | Signal | Broche Teensy |
|---|---|---|
| **1** | GND | **GND** |
| **2** | 5V (alimentation) | **VIN** |
| **3** | TX (Teensy → Mega) | **Pin 1 (TX1)** |
| **4** | RX (Mega → Teensy) | **Pin 0 (RX1)** |

*(Rappel : TX1/RX1 du Teensy sont reliées aux pins RX3/TX3 de l'Arduino Mega via le câble DIN.)*

> [!NOTE]
> **Consommation :** Teensy 4.1 (~100-150 mA) + LCD I2C (~30 mA) = ~200 mA. Le régulateur du Mega (barrel jack) supporte ~800 mA, marge largement suffisante.

### 2. Écran LCD Grove I2C
* **SDA** $\rightarrow$ Broche **Pin 18 (SDA0)** de la Teensy
* **SCL** $\rightarrow$ Broche **Pin 19 (SCL0)** de la Teensy
* **VCC** $\rightarrow$ Broche **5V** (ou **3.3V** selon le modèle Grove)
* **GND** $\rightarrow$ Broche **GND**

### 3. Boutons Poussoirs (Clavier directionnel)
Les boutons sont câblés en **INPUT_PULLUP**, ce qui signifie qu'ils doivent être reliés d'un côté à la broche correspondante de la Teensy, et de l'autre côté à la masse (**GND**). Aucun besoin de résistance externe !

* **Haut (UP)** $\rightarrow$ Broche **Pin 6**
* **Bas (DOWN)** $\rightarrow$ Broche **Pin 7**
* **Gauche (LEFT)** $\rightarrow$ Broche **Pin 8**
* **Droite (RIGHT)** $\rightarrow$ Broche **Pin 9**
* **Entrée/OK (ENTER)** $\rightarrow$ Broche **Pin 10**
