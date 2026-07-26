import sys
with open('mega_monture.ino', 'r') as f:
    c = f.read()

start_idx = c.find('static int slewToAA(double tAlt, double tAz) {')
end_idx = c.find('  digitalWrite(AZ_DIR, (azS>=0) ^ azReversed ? HIGH : LOW);', start_idx)

old_block = c[start_idx:end_idx]

new_block = """static int slewToAA(double tAlt, double tAz) {
  if (alarmActive) return 0;
  double startPhysAlt = getPhysicalAlt();
  double targetAlt = tAlt;
  if (mountType >= 1) {
    // tAz is HA (motor Az), tAlt is DEC (motor Alt)
    double ha, dec;
    double az_norm = fmod(tAz, 360.0);
    if (az_norm < 0) az_norm += 360.0;
    if (tAlt >= -90.0 && tAlt <= 90.0) {
      ha = az_norm; dec = tAlt;
    } else {
      ha = fmod(az_norm + 180.0, 360.0);
      dec = 180.0 - tAlt;
    }
    double hr = ha * DEG_TO_RAD;
    double dr = dec * DEG_TO_RAD;
    double lr = siteLat * DEG_TO_RAD;
    double sa = sin(dr) * sin(lr) + cos(dr) * cos(lr) * cos(hr);
    targetAlt = asin(constrain(sa, -1.0, 1.0)) * RAD_TO_DEG;
  }
  double targetPhysAlt = targetAlt;
  if (targetPhysAlt < ALT_MIN - 0.01 || (mountType == 0 && targetPhysAlt > ALT_MAX + 0.01)) {
    limitHit = true;
    return 0;
  }
  limitHit=false;
  double azD=tAz-currAz;
  if(azD>180.0)azD-=360.0; if(azD<-180.0)azD+=360.0;
  
  long azS=(long)(azD*AZ_PPD);
  long altS=(long)((tAlt-currAlt)*ALT_PPD);
  unsigned long aAS=abs(azS),aLS=abs(altS);
  unsigned long maxS=max(aAS,aLS);
  if(maxS==0)return 1;

"""

c = c.replace(old_block, new_block)

with open('mega_monture.ino', 'w') as f:
    f.write(c)
