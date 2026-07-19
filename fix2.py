import re
with open('teensy_monture/teensy_monture.ino', 'r') as f:
    content = f.read()

content = content.replace("ideal_rd2aa(ra_h,dec_d,&currAlt,&currAz);", "ideal_rd2aa_at(ra_h,dec_d,&currAlt,&currAz,0.0);")

with open('teensy_monture/teensy_monture.ino', 'w') as f:
    f.write(content)
