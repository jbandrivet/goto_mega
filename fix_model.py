import re

with open('teensy_monture/teensy_monture.ino', 'r') as f:
    content = f.read()

# Fix updatePos() error in compile log which showed aa2rd
# Wait, it means it didn't get replaced.
content = content.replace("aa2rd(currAlt,currAz,&currRA,&currDEC);", "mach2rd(currAlt,currAz,&currRA,&currDEC);")

# Fix slewToAA error
content = content.replace("aa2rd(tAlt, tAz, &endRA, &endDEC);", "mach2rd(tAlt, tAz, &endRA, &endDEC);")

# Fix processCmd error for inAlt/inAz to rs/ds
content = content.replace("aa2rd(inAlt, inAz, &rs, &ds);", "ideal_aa2rd(inAlt, inAz, &rs, &ds);")

# Fix cmdBuffer -> cmd
content = content.replace("cmdBuffer[2]=='L'", "c3=='L'")

# Fix remaining rd2aa to ideal_rd2aa
content = content.replace("rd2aa(ra_h,dec_d,&currAlt,&currAz);", "ideal_rd2aa(ra_h,dec_d,&currAlt,&currAz);")

# Fix processCmd parking logic calls to aa2rd
content = content.replace("aa2rd(pAlt, pAz, &pRA, &pDEC);", "mach2rd(pAlt, pAz, &pRA, &pDEC);")

# Add c3 extraction to processCmd
content = content.replace("char c1=cmd[0], c2=cmd[1];", "char c1=cmd[0], c2=cmd[1], c3=len>2?cmd[2]:' ';")

# Add ideal_rd2aa wrapper
ideal_wrapper = """
static void ideal_rd2aa(double ra, double dec, double *alt, double *az) {
  ideal_rd2aa_at(ra, dec, alt, az, 0.0);
}
"""
if "ideal_rd2aa(" not in content:
    content = content.replace("static void rd2mach(", ideal_wrapper + "\nstatic void rd2mach(")

with open('teensy_monture/teensy_monture.ino', 'w') as f:
    f.write(content)

print("Fixes applied")
