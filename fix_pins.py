import re

# 1. Update teensy_monture.ino
with open("teensy_monture/teensy_monture.ino", "r") as f:
    content = f.read()
content = content.replace("#define BUZZER_PIN 49", "#define BUZZER_PIN 20")
content = content.replace("* - Buzzer     : Pin 11", "* - Buzzer     : Pin 20")
with open("teensy_monture/teensy_monture.ino", "w") as f:
    f.write(content)

# 2. Update README.md
with open("README.md", "r") as f:
    content = f.read()

old_table = """| **Moteur Dérotateur** | **Pin 8** | N/A | `PUL+` (Pulse/Step) |
| | **Pin 9** | N/A | `DIR+` (Direction) |
| **Moteur Focuseur** | **Pin 11** | N/A | `PUL+` (Pulse/Step) |
| | **Pin 12** | N/A | `DIR+` (Direction) |
| **Buzzer** | **Pin 49** | **Pin 11** | Borne `+` (via résistance 100 Ω) |"""

new_table = """| **Moteur Dérotateur** | **Pin 8** | **Pin 8** | `PUL+` (Pulse/Step) |
| | **Pin 9** | **Pin 9** | `DIR+` (Direction) |
| | **Pin 10** | **Pin 10** | `ENB+` (Enable - Optionnel) |
| **Moteur Focuseur** | **Pin 11** | **Pin 11** | `PUL+` (Pulse/Step) |
| | **Pin 12** | **Pin 12** | `DIR+` (Direction) |
| | **Pin 13** | **Pin 13** | `ENB+` (Enable - Optionnel) |
| **Buzzer** | **Pin 49** | **Pin 20** | Borne `+` (via résistance 100 Ω) |"""

content = content.replace(old_table, new_table)
with open("README.md", "w") as f:
    f.write(content)

# 3. Update fiche_technique.md
with open("fiche_technique.md", "r") as f:
    content = f.read()

# Wait, fiche_technique doesn't have the ENB pins in the table. Let's do a regex or just replace specifically.
content = content.replace("| **Buzzer** | Pin 49 | Pin 11 |", "| **Buzzer** | Pin 49 | Pin 20 |")
content = content.replace("N/A", "Pin 8", 1)  # Derot 8
content = content.replace("N/A", "Pin 9", 1)  # Derot 9
content = content.replace("N/A", "Pin 11", 1) # Focus 11
content = content.replace("N/A", "Pin 12", 1) # Focus 12

with open("fiche_technique.md", "w") as f:
    f.write(content)

print("Pins Patched")
