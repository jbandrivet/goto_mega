#include <iostream>
#include <cmath>

using namespace std;

#define MAX_SYNC_POINTS 20
struct SyncPoint {
  double ideal_az;
  double ideal_alt;
  double mach_az;
  double mach_alt;
};
SyncPoint syncPoints[MAX_SYNC_POINTS];
int numSyncPoints = 0;
int syncIndex = 0;

void rd2mach(double ideal_alt, double ideal_az, double *mach_alt, double *mach_az) {
  if (numSyncPoints == 0) {
    *mach_alt = ideal_alt;
    *mach_az = ideal_az;
    return;
  }
  
  if (numSyncPoints == 1) {
    double dAlt = syncPoints[0].mach_alt - syncPoints[0].ideal_alt;
    double dAz  = syncPoints[0].mach_az - syncPoints[0].ideal_az;
    *mach_alt = ideal_alt + dAlt;
    *mach_az = ideal_az + dAz;
    *mach_az = fmod(*mach_az, 360.0);
    if (*mach_az < 0) *mach_az += 360.0;
    return;
  }
  
  double sumWeight = 0.0;
  double sumDAlt = 0.0;
  double sumDAz = 0.0;
  
  for (int i=0; i<numSyncPoints; i++) {
    double d_alt = ideal_alt - syncPoints[i].ideal_alt;
    double d_az = ideal_az - syncPoints[i].ideal_az;
    if (d_az > 180.0) d_az -= 360.0;
    if (d_az < -180.0) d_az += 360.0;
    
    double distSq = d_alt*d_alt + d_az*d_az;
    
    if (distSq < 0.0001) {
      sumDAlt = syncPoints[i].mach_alt - syncPoints[i].ideal_alt;
      sumDAz  = syncPoints[i].mach_az - syncPoints[i].ideal_az;
      sumWeight = 1.0;
      break;
    }
    
    double weight = 1.0 / distSq;
    double errAlt = syncPoints[i].mach_alt - syncPoints[i].ideal_alt;
    double errAz = syncPoints[i].mach_az - syncPoints[i].ideal_az;
    if (errAz > 180.0) errAz -= 360.0;
    if (errAz < -180.0) errAz += 360.0;
    
    sumDAlt += errAlt * weight;
    sumDAz += errAz * weight;
    sumWeight += weight;
  }
  
  double avgDAlt = sumDAlt / sumWeight;
  double avgDAz = sumDAz / sumWeight;
  
  *mach_alt = ideal_alt + avgDAlt;
  *mach_az = fmod(ideal_az + avgDAz, 360.0);
  if (*mach_az < 0) *mach_az += 360.0;
}

int main() {
  // Sync 1
  syncPoints[0] = {10.0, 20.0, 15.0, 25.0};
  numSyncPoints++;
  // Sync 2
  syncPoints[1] = {50.0, 60.0, 50.0, 60.0};
  numSyncPoints++;
  
  double m_alt, m_az;
  rd2mach(20.0, 10.0, &m_alt, &m_az);
  cout << "Mach: " << m_alt << ", " << m_az << endl;
  return 0;
}
