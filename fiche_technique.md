# FICHE TECHNIQUE : SYSTÈME DE COMMANDE GOTOUNIVERSAL
*Version 5.2 (Alignée Mega v9.1 + Teensy v6.2) — Juin 2026*

Ce document regroupe les spécifications électriques, le schéma de câblage des drivers **M542**, les paramètres mécaniques et les protocoles de communication pour le télescope Dobson 800mm motorisé GoTo (Observatoire Saint-Jacques).

---

## 1. Caractéristiques de Communication

*   **Liaison USB (PC / ASIAir / INDI) :** **38 400 bauds** (Vitesse optimisée pour la télémétrie en temps réel).
*   **Liaison Raquette (Serial3 / RJ11) :** **38 400 bauds**.
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

### Prise RJ11 Raquette (Teensy 4.1 $\leftrightarrow$ Mega)
*   **TX (Teensy 4.1)** $\rightarrow$ Broche **Pin 15 (RX3)** (dans la zone **`COMMUNICATION`**)
*   **RX (Teensy 4.1)** $\rightarrow$ Broche **Pin 14 (TX3)** (dans la zone **`COMMUNICATION`**)
*   **GND** $\rightarrow$ **GND** (dans la zone **`POWER`**)
*   **5V** $\rightarrow$ **5V** (dans la zone **`POWER`**) *(Alimente la raquette)*

---

## 3. Paramètres Mécaniques et Résolutions

La résolution de déplacement (PPD - Pas par Degré) de la monture est calculée selon la formule :

$$PPD = \frac{\text{Pas Moteur} \times \text{Microstepping} \times \text{Rapport Réduction}}{360}$$

### Valeurs par Défaut (Dobson Serrurier) :
*   **Pas moteur par tour :** 200 pas.
*   **Microstepping :** 80 (configuré sur les drivers pour donner 16 000 pas/tour).
*   **Rapport de réduction (AZ/ALT) :** 750.0.
*   **Résolution calculée :** **33 333,33 pas/degré**.

---

## 4. Modes de Suivi (Tracking)

*   **Suivi Sidéral (Ciel profond) :** Calculé en temps réel par l'Arduino Mega toutes les 500 ms à partir du Temps Sidéral Local (LST) de l'horloge.
*   **Suivi Lunaire (`:TL#`) :** Vitesse de l'angle horaire (HA) ralentie de **~2,37%** (facteur d'échelle `0.976327`) pour compenser le déplacement orbital de la Lune.
*   **Suivi Solaire (`:TS#`) :** Vitesse ralentie de **~0,27%** (facteur d'échelle `0.997270`) pour compenser le mouvement orbital de la Terre.
