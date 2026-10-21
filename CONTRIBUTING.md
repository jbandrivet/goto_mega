# Contribuer à GotoAndrivet

Merci de vouloir améliorer GotoAndrivet ! Cette page explique comment signaler un problème, comment proposer une modification, et les quelques règles du projet. Elle évite les allers-retours : une proposition qui les respecte peut être acceptée beaucoup plus vite.

Le site GitHub est en anglais : les noms des boutons sont donc donnés tels qu'ils apparaissent à l'écran, **en gras**.

---

## Signaler un problème ou proposer une idée

Ouvrez un signalement dans l'onglet **Issues** du dépôt, puis **New issue**. Pour qu'on puisse reproduire le problème, indiquez :

- la carte de la monture : Arduino Mega 2560 ou Teensy 4.1 ;
- le type de monture : AltAz, ForkEq (fourche équatoriale) ou GermanEq (équatoriale allemande) ;
- la date de votre dernière mise à jour, et si le firmware a été reflashé depuis ;
- votre système (par exemple Ubuntu 24.04) ;
- ce que vous avez fait, ce qui devait se passer et ce qui s'est passé ;
- si possible, le contenu de l'onglet **Log LX200** de la carte du ciel, une capture d'écran, ou une photo du câblage s'il s'agit de matériel.

Une idée de nouvelle fonction se propose de la même façon. Pour une modification importante, ouvrez d'abord un signalement pour en discuter : cela évite de travailler pour rien.

---

## Proposer une modification

1. Copiez le dépôt sur votre propre compte GitHub avec le bouton **Fork**.
2. Faites vos modifications sur cette copie, de préférence dans une branche à part.
3. Décrivez chaque enregistrement (commit) en français, en une phrase claire : ce qui change et pourquoi.
4. Proposez la modification avec le bouton **Contribute** puis **Open pull request** (« demande de fusion »). Dans la description, expliquez :
   - ce que la modification apporte ou corrige ;
   - ce que vous avez vérifié (voir plus bas), et sur quel matériel ;
   - ce que vous n'avez **pas** pu essayer.

Le mainteneur relit chaque proposition avant de l'accepter. Il peut demander des changements : c'est normal, et ce n'est pas un refus.

---

## Les règles du projet

**Le firmware reste générique.** GotoAndrivet doit fonctionner sur tous les télescopes. On n'adapte pas le code à un instrument particulier : les rapports d'engrenage, les micro-pas, le type de monture et le reste se règlent dans le configurateur, qui les enregistre dans la carte.

**Le plan de câblage ne change pas sans accord.** Les tableaux de câblage du `README.md`, la `fiche_technique.md` et les cartes électroniques du dossier `pcb/` décrivent du matériel déjà construit. Toute modification se discute d'abord dans un signalement.

**Le protocole reste compatible.** La monture parle le protocole LX200/OnStep. Une commande ou une réponse modifiée doit continuer à fonctionner avec le pilote INDI `lx200_OnStep` (Ekos, KStars), avec les applications Python et avec la raquette. Le code du pilote INDI est dans `scratch/lx200_OnStep_full.cpp` : consultez-le avant de toucher aux réponses de la monture, en particulier à `:GU#`.

**Les deux firmwares avancent ensemble.** Une fonction de la monture concerne en général `mega_monture` et `teensy_monture` : modifiez les deux, ou expliquez pourquoi une seule carte est concernée.

**Pas de nouvelle bibliothèque Python sans discussion.** Le bouton « Mise à jour » remplace les fichiers du programme, mais il ne réinstalle pas les bibliothèques. Une bibliothèque nouvelle ferait donc planter les installations existantes. Les bibliothèques actuelles sont celles de `install_linux.py` : pyserial, pillow, zwoasi, numpy, requests, ephem, opencv-python-headless.

**L'interface est en français et en anglais.** Un texte affiché s'ajoute dans les deux langues (dictionnaires `TRANSLATIONS` de la carte du ciel, `TEXTS` des modules caméra et guidage).

**`ciel_donnees.py` ne se modifie pas à la main.** Il est produit par `outils/generer_ciel_donnees.py` : corrigez le générateur, puis relancez-le.

**Pas de fichier exécutable dans une proposition.** L'installateur `Install_Goto_Universal` est reconstruit par le mainteneur et par GitHub, jamais repris d'une contribution.

---

## Vérifier avant de proposer

**Firmware** : il doit se compiler sans erreur avec [arduino-cli](https://arduino.github.io/arduino-cli/latest/), le paquet de cartes Teensy étant installé :

```sh
arduino-cli compile --fqbn arduino:avr:mega mega_monture
arduino-cli compile --fqbn teensy:avr:teensy41 teensy_monture
arduino-cli compile --fqbn teensy:avr:teensy41 teensy_raquette
```

**Applications** : elles doivent démarrer et fonctionner sans matériel, en simulation.

- Carte du ciel : `python3 goto_andrivet.py`, cochez « Simulation », puis « Connecter ». Essayez au moins un GoTo.
- Module caméra : choisissez « Caméra simulée ».
- Module de guidage : choisissez « Caméra de guidage simulée ».
- Si vous avez `pyflakes` : `python3 -m pyflakes *.py` ne doit signaler aucune nouvelle erreur.

**Matériel** : dites clairement ce qui a été essayé sur une vraie monture et ce qui ne l'a été qu'en simulation.

---

## Pourquoi chaque proposition est relue

Ce qui est accepté dans la branche principale du dépôt (`main`) part ensuite chez **tous les utilisateurs**, par le bouton « Mise à jour » des applications et par l'installateur. Ce code s'exécute sur leur ordinateur, et le firmware pilote des moteurs qui portent leur instrument. Chaque proposition est donc lue en entier avant d'être acceptée, même une petite.

---

## Licence

GotoAndrivet est sous licence **GNU GPL v3** (fichier `LICENSE`). En proposant une contribution, vous acceptez qu'elle soit distribuée sous cette même licence. Vous en restez l'auteur.
