/*
 * GotoAndrivetMega - Controleur de monture Astro Mega 2560 (Protocole OnStep)
 * Auteur : Andrivet Jean-Baptiste
 * 
 * Cablage :
 * - Moteur AZ  : Step Pin 2, Dir Pin 3
 * - Moteur ALT : Step Pin 5, Dir Pin 6
 * - Buzzer     : Pin 11
 * - Raquette   : Serial3 (Pin 14 TX, Pin 15 RX) @ 38400 baud (Connecteur DIN 4 broches)
 * - Module GPS : Serial2 (Pin 16 TX, Pin 17 RX) @ 9600 baud
 */

#include <math.h>
#include <EEPROM.h>
#include <TinyGPS++.h> // [ADD] Bibliotheque GPS

// === MECANIQUE ===
static uint32_t motorStepsPerRev = 200;
static uint16_t microstep = 128; // Par defaut 128 pour faire 25600 ppr (comme configure sur les switches SW5-SW7=OFF, SW8=ON du M542)
static double   gearRatioAZ = 750.0;
static double   gearRatioALT = 750.0;

static double AZ_PPD  = (double)motorStepsPerRev * microstep * gearRatioAZ / 360.0;
static double ALT_PPD = (double)motorStepsPerRev * microstep * gearRatioALT / 360.0;

static void recalculatePPD() {
  AZ_PPD  = (double)motorStepsPerRev * microstep * gearRatioAZ / 360.0;
  ALT_PPD = (double)motorStepsPerRev * microstep * gearRatioALT / 360.0;
}

uint8_t mountType = 1; // 0=AltAz, 1=ForkEq, 2=GermanEq (configure par defaut en equatorial pour la monture)

// === VITESSES (microsecondes) ===
#define STEP_DELAY_FAST   35      // 28.5 kHz max - clamp to avoid loop jitter on Mega 2560
#define STEP_DELAY_SLOW  100      // 10 kHz  -> 0.3 deg/s manuel
#define MAX_DELAY        500      // 2 kHz   -> 0.06 deg/s depart rampe
#define DEFAULT_SLEW_RATE 3.0
#define ACCEL_STEPS      2000UL
#define ACCEL_MIN_SLEW   (2 * ACCEL_STEPS)

static unsigned long stepDelaySlew = STEP_DELAY_FAST;
static double         maxSlewRate   = DEFAULT_SLEW_RATE;

// === BROCHES ===
#define AZ_STEP   2
#define AZ_DIR    3
#define AZ_EN     4
#define BUZZER_PIN 49
#define BUZZ_FREQ  2000
#define ALT_STEP  5
#define ALT_DIR   6
#define ALT_EN    7

#define DEROT_STEP 8
#define DEROT_DIR  9
#define DEROT_EN   10

#define FOCUS_STEP 11
#define FOCUS_DIR  12
#define FOCUS_EN   13

// === LIMITES ===
#define ALT_MIN  -1.0
#define ALT_MAX  89.5

// === COORDONNEES PAR DEFAUT ===
static double siteLat = 0.0;
static double siteLon = 0.0;
static double utcOff  = 0.0;

// Date/Heure
static int dt_y=2026, dt_m=4, dt_d=26;
static int dt_h=12, dt_mi=0, dt_s=0;
static unsigned long lastClkMs=0;
static bool timeSet = false;           // [FIX 25] False par defaut jusqu'au fix GPS ou :SC/:SL

// === ETAT ===
static double currAz=0.0, currAlt=0.0;
static volatile long azPos=0, altPos=0; // Volatile because modified in ISR
static long currRA=0, currDEC=0;
static long inRA=0, inDEC=0;

static double inAlt=0.0, inAz=0.0;
static bool   haveAltAzTarget=false;

static double trkRA=0.0, trkDec=0.0;
static volatile bool tracking=false; // Volatile because read in ISR
static volatile bool slewing=false;  // Volatile because read in ISR
static bool synced=false;
static bool parked=false;
static bool atHome=false;
static bool guiding=false;
static volatile bool limitHit=false; // Volatile because modified in ISR
static bool alarmActive = false;
static bool buzzerEnabled = true;
static bool azReversed = false;
float parkAlt = 90.0;
float parkAz = 0.0;
static bool altReversed = false;
static uint8_t trackRate=0;
static bool force_tracking_rebase = false;
static bool gpsEnabled = true;
static bool derotEnabled = false;
static double derotPPD = 100.0;
static long derotPos = 0;
static double derotTarget = 0.0;

static bool focusEnabled = false;
static int focusSpeed = 1000;
static int8_t focusMove = 0;
static uint8_t slowSpeed=8;
static unsigned long lastTrkMs=0;
static double trkStartLST = 0.0;
static unsigned long azStepInterval = 0;
static unsigned long altStepInterval = 0;
static long azStepsLeft = 0;
static long altStepsLeft = 0;
static int8_t azDirSign = 0;
static int8_t altDirSign = 0;
static unsigned long lastAzStepUs = 0;
static unsigned long lastAltStepUs = 0;

static volatile int8_t azMove=0, altMove=0; // Volatile because read in ISR
static unsigned long lastSlowAz=0, lastSlowAlt=0;

// === PERSISTENCE EEPROM ===
const uint16_t EEPROM_ADDR_MAGIC    = 0;
const uint16_t EEPROM_ADDR_PARKED   = 1;
const uint16_t EEPROM_ADDR_SYNCED   = 2;
const uint16_t EEPROM_ADDR_AZ_POS   = 3;
const uint16_t EEPROM_ADDR_ALT_POS  = 7;
const uint16_t EEPROM_ADDR_CURR_RA  = 11;
const uint16_t EEPROM_ADDR_CURR_DEC = 15;
const uint16_t EEPROM_ADDR_TRACKING = 19;
const uint16_t EEPROM_ADDR_SLEW_RATE = 20; 
const uint16_t EEPROM_ADDR_STEPS     = 24; 
const uint16_t EEPROM_ADDR_MICROSTEP = 28; 
const uint16_t EEPROM_ADDR_GEAR_AZ   = 30; 
const uint16_t EEPROM_ADDR_GEAR_ALT  = 34; 
const uint16_t EEPROM_ADDR_MOUNT_TYPE = 38; 
const uint16_t EEPROM_ADDR_BUZZER     = 39; 
const uint16_t EEPROM_ADDR_LATITUDE   = 40; 
const uint16_t EEPROM_ADDR_LONGITUDE  = 44; 
const uint16_t EEPROM_ADDR_REV_AZ     = 48; 
const uint16_t EEPROM_ADDR_REV_ALT    = 49; 
const uint16_t EEPROM_ADDR_PARK_ALT   = 50;
const uint16_t EEPROM_ADDR_PARK_AZ    = 54;
const uint16_t EEPROM_ADDR_DEROT_EN   = 58;
const uint16_t EEPROM_ADDR_DEROT_PPD  = 59;
const uint16_t EEPROM_ADDR_FOCUS_EN   = 63;
const uint16_t EEPROM_ADDR_GPS_EN     = 64;
const byte     EEPROM_MAGIC         = 0x5E;

template <typename T>
void eepromWrite(int address, const T& value) {
  const byte* p = (const byte*)(const void*)&value;
  for (unsigned int i = 0; i < sizeof(value); i++) {
    EEPROM.update(address + i, p[i]);
  }
}

template <typename T>
void eepromRead(int address, T& value) {
  byte* p = (byte*)(void*)&value;
  for (unsigned int i = 0; i < sizeof(value); i++) {
    p[i] = EEPROM.read(address + i);
  }
}

static void saveStateToEEPROM() {
  EEPROM.update(EEPROM_ADDR_MAGIC, EEPROM_MAGIC);
  EEPROM.update(EEPROM_ADDR_PARKED, parked ? 1 : 0);
  EEPROM.update(EEPROM_ADDR_SYNCED, synced ? 1 : 0);
  EEPROM.update(EEPROM_ADDR_TRACKING, 0); 
  EEPROM.update(EEPROM_ADDR_MOUNT_TYPE, mountType);
  EEPROM.update(EEPROM_ADDR_BUZZER, buzzerEnabled ? 1 : 0);
  eepromWrite(EEPROM_ADDR_AZ_POS, azPos);
  eepromWrite(EEPROM_ADDR_ALT_POS, altPos);
  eepromWrite(EEPROM_ADDR_CURR_RA, currRA);
  eepromWrite(EEPROM_ADDR_CURR_DEC, currDEC);
  eepromWrite(EEPROM_ADDR_SLEW_RATE, maxSlewRate); 
  eepromWrite(EEPROM_ADDR_STEPS, motorStepsPerRev);
  eepromWrite(EEPROM_ADDR_MICROSTEP, microstep);
  eepromWrite(EEPROM_ADDR_GEAR_AZ, gearRatioAZ);
  eepromWrite(EEPROM_ADDR_GEAR_ALT, gearRatioALT);
  eepromWrite(EEPROM_ADDR_LATITUDE, siteLat);
  eepromWrite(EEPROM_ADDR_LONGITUDE, siteLon);
  EEPROM.update(EEPROM_ADDR_REV_AZ, azReversed ? 1 : 0);
  EEPROM.update(EEPROM_ADDR_REV_ALT, altReversed ? 1 : 0);
  eepromWrite(EEPROM_ADDR_PARK_ALT, parkAlt);
  eepromWrite(EEPROM_ADDR_PARK_AZ, parkAz);
  EEPROM.update(EEPROM_ADDR_DEROT_EN, derotEnabled ? 1 : 0);
  eepromWrite(EEPROM_ADDR_DEROT_PPD, derotPPD);
  EEPROM.update(EEPROM_ADDR_FOCUS_EN, focusEnabled ? 1 : 0);
  EEPROM.update(EEPROM_ADDR_GPS_EN, gpsEnabled ? 1 : 0);
}

static void loadStateFromEEPROM() {
  if (EEPROM.read(EEPROM_ADDR_MAGIC) == EEPROM_MAGIC) {
    mountType = EEPROM.read(EEPROM_ADDR_MOUNT_TYPE);
    buzzerEnabled = (EEPROM.read(EEPROM_ADDR_BUZZER) == 1);
    eepromRead(EEPROM_ADDR_SLEW_RATE, maxSlewRate); 
    eepromRead(EEPROM_ADDR_STEPS, motorStepsPerRev);
    eepromRead(EEPROM_ADDR_MICROSTEP, microstep);
    eepromRead(EEPROM_ADDR_GEAR_AZ, gearRatioAZ);
    eepromRead(EEPROM_ADDR_GEAR_ALT, gearRatioALT);
    eepromRead(EEPROM_ADDR_LATITUDE, siteLat);
    eepromRead(EEPROM_ADDR_LONGITUDE, siteLon);
    azReversed = (EEPROM.read(EEPROM_ADDR_REV_AZ) == 1);
    altReversed = (EEPROM.read(EEPROM_ADDR_REV_ALT) == 1);
    eepromRead(EEPROM_ADDR_PARK_ALT, parkAlt);
    eepromRead(EEPROM_ADDR_PARK_AZ, parkAz);
    derotEnabled = (EEPROM.read(EEPROM_ADDR_DEROT_EN) == 1);
    eepromRead(EEPROM_ADDR_DEROT_PPD, derotPPD);
    focusEnabled = (EEPROM.read(EEPROM_ADDR_FOCUS_EN) == 1);
    gpsEnabled = (EEPROM.read(EEPROM_ADDR_GPS_EN) == 1);
    recalculatePPD();
    if(isnan(derotPPD) || derotPPD < 1.0) derotPPD = 100.0;
    if (isnan(parkAlt) || parkAlt < -90.0 || parkAlt > 90.0) parkAlt = (mountType >= 1) ? 90.0 : 0.0;
    if (isnan(parkAz) || parkAz < 0.0 || parkAz > 360.0) parkAz = 0.0;
    
    if (isnan(siteLat) || siteLat < -90.0 || siteLat > 90.0 ||
        isnan(siteLon) || siteLon < -180.0 || siteLon > 180.0) {
      siteLat = 0.0;
      siteLon = 0.0;
    }
    
    if (motorStepsPerRev < 100 || motorStepsPerRev > 100000UL ||
        microstep < 1 || microstep > 512 ||
        isnan(gearRatioAZ) || gearRatioAZ < 1.0 || gearRatioAZ > 10000.0 ||
        isnan(gearRatioALT) || gearRatioALT < 1.0 || gearRatioALT > 10000.0 ||
        isnan(maxSlewRate) || maxSlewRate < 0.1 || maxSlewRate > 25.0 ||
        mountType > 2) 
    {
      motorStepsPerRev = 200;
      microstep = 125; 
      gearRatioAZ = 750.0;
      gearRatioALT = 750.0;
      maxSlewRate = DEFAULT_SLEW_RATE;
      mountType = 2; 
      buzzerEnabled = true;
    }
  } else {
    motorStepsPerRev = 200;
    microstep = 125; 
    gearRatioAZ = 750.0;
    gearRatioALT = 750.0;
    maxSlewRate = DEFAULT_SLEW_RATE;
    mountType = 2; 
    buzzerEnabled = true;
    azReversed = false;
    altReversed = false;
    parkAlt = (mountType >= 1) ? 90.0 : 0.0;
    parkAz = 0.0;
    derotEnabled = false;
    derotPPD = 100.0;
    focusEnabled = false;
    saveStateToEEPROM();
  }

  parked = true;
  synced = true;
  tracking = false;

  recalculatePPD();

  currAz = 0.0;
  currAlt = (mountType >= 1) ? 90.0 : 0.0;
  azPos = 0;
  altPos = (long)(currAlt * ALT_PPD);

  currDEC = (mountType >= 1) ? 90L * 3600L : 0L;
  currRA = (long)(lst() * 3600.0);

  trkRA = (double)currRA / 3600.0;
  trkDec = (double)currDEC / 3600.0;

  double d = 1.0e6 / (AZ_PPD * maxSlewRate);
  if(d < (double)STEP_DELAY_FAST) d = STEP_DELAY_FAST;
  if(d > (double)MAX_DELAY)       d = MAX_DELAY;
  stepDelaySlew = (unsigned long)d;
}

static char lxRA[12]="00:00:00#";
static char lxDEC[14]="+90*00:00#";

#define CMD_MAX 40
static char cmdUsb[CMD_MAX];   static uint8_t ciUsb=0;
static char cmdRj[CMD_MAX];    static uint8_t ciRj=0;

static Print* slewOut = nullptr;

static void processCmd(const char* cmd, uint8_t ci, Print& out);
static void sendGU(Print& out);
static void handleGX(const char* cmd, Print& out);
static void handleGBE(Print& out);
static int slewToAA(double tAlt, double tAz);
void updateBuzzer();
void triggerConnectBeep();
void triggerGpsFixBeep();

// ======================== HELPERS DATE =====================

static uint8_t daysInMonth(int m, int y) {
  static const uint8_t d[] = {31,28,31,30,31,30,31,31,30,31,30,31};
  if(m < 1 || m > 12) return 30;
  if(m == 2 && ((y%4==0 && y%100!=0) || y%400==0)) return 29;
  return d[m-1];
}

static void getUTC(int *uy, int *um, int *ud, int *uh, int *umi, int *us) {
  double utcH = dt_h + dt_mi/60.0 + dt_s/3600.0 - utcOff;
  int dayOff = 0;
  while(utcH < 0.0)   { utcH += 24.0; dayOff--; }
  while(utcH >= 24.0) { utcH -= 24.0; dayOff++; }
  *uh  = (int)utcH;
  double rem = (utcH - *uh) * 60.0;
  *umi = (int)rem;
  *us  = (int)((rem - *umi) * 60.0);
  *uy = dt_y; *um = dt_m; *ud = dt_d + dayOff;
  while(*ud < 1) {
    (*um)--;
    if(*um < 1) { *um = 12; (*uy)--; }
    *ud += daysInMonth(*um, *uy);
  }
  while(*ud > daysInMonth(*um, *uy)) {
    *ud -= daysInMonth(*um, *uy);
    (*um)++;
    if(*um > 12) { *um = 1; (*uy)++; }
  }
}

// ======================== GPS ADAFRUIT =====================
TinyGPSPlus gps;

static bool gpsHasFixedOnce = false;
static unsigned long gpsSearchStart = 0;

static void handleGPS() {
  if (gpsSearchStart == 0) gpsSearchStart = millis();

  // Desactivation auto apres 10 min (600 000 ms) sans fix
  if (gpsEnabled && !gpsHasFixedOnce) {
    if (millis() - gpsSearchStart > 600000UL) {
      gpsEnabled = false; 
    }
  }

  while (Serial2.available() > 0) {
    char c = Serial2.read();
    if (!gpsEnabled) continue;

    if (gps.encode(c)) {
      if (!gpsHasFixedOnce && gps.location.isValid() && gps.date.isValid()) {
        gpsHasFixedOnce = true;
        triggerGpsFixBeep();
      }
      // Mise a jour des coordonnees
      if (gps.location.isValid() && gps.location.isUpdated()) {
        siteLat = gps.location.lat();
        siteLon = gps.location.lng();
      }
      
      // Mise a jour de l'heure
      if (gps.time.isValid() && gps.date.isValid() && gps.time.isUpdated()) {
        int new_y = gps.date.year();
        int new_m = gps.date.month();
        int new_d = gps.date.day();
        int new_h = gps.time.hour();
        int new_mi = gps.time.minute();
        int new_s = gps.time.second();

        // Le GPS donne l'heure UTC. Application de l'utcOff pour l'heure locale
        int offsetH = (int)utcOff;
        new_h += offsetH;

        // Wrap-around simple pour ajustement du jour selon l'heure locale
        if (new_h >= 24) {
          new_h -= 24;
          new_d++;
          if (new_d > daysInMonth(new_m, new_y)) {
            new_d = 1;
            new_m++;
            if (new_m > 12) { new_m = 1; new_y++; }
          }
        } else if (new_h < 0) {
          new_h += 24;
          new_d--;
          if (new_d < 1) {
            new_m--;
            if (new_m < 1) { new_m = 12; new_y--; }
            new_d = daysInMonth(new_m, new_y);
          }
        }

        dt_y = new_y;
        dt_m = new_m;
        dt_d = new_d;
        dt_h = new_h;
        dt_mi = new_mi;
        dt_s = new_s;

        lastClkMs = millis(); // Resynchronisation de l'horloge interne
        timeSet = true;       // Deverrouillage des commandes GoTo !
      }
    }
  }
}

// ======================== ASTRO ============================

static void jday_split(long *days_whole, double *days_frac) {
  int uy, um, ud, uh, umi, us;
  getUTC(&uy, &um, &ud, &uh, &umi, &us);
  
  unsigned long ms = millis() - lastClkMs;
  if (ms > 2000) ms = 0;
  double sub_sec = (double)ms / 1000.0;
  
  double h = uh + umi/60.0 + (us + sub_sec)/3600.0;
  int y = uy, m = um;
  if(m <= 2) { y--; m += 12; }
  long A = y / 100;
  long B = A / 4;
  long C = 2 - A + B;
  long tempY = y + 4716;
  long E_val = (tempY * 365) + (tempY / 4);
  long tempM = m + 1;
  long F_val = (tempM * 306) / 10;
  
  long jd_whole = C + E_val + F_val + ud - 1524;
  
  *days_whole = jd_whole - 2451545;
  *days_frac = -0.5 + h/24.0;
}

static double jday() {
  long whole;
  double frac;
  jday_split(&whole, &frac);
  return (double)whole + frac + 2451545.0;
}

static double lst_offset(double offset_sec) {
  long whole;
  double frac;
  jday_split(&whole, &frac);
  frac += offset_sec / 86400.0;
  
  double jd_diff = (double)whole + frac;
  double T = jd_diff / 36525.0;
  
  double w_term = 0.98564736629 * (double)whole;
  double w_term_mod = fmod(w_term, 360.0);
  if (w_term_mod < 0) w_term_mod += 360.0;
  
  double frac_term = 360.98564736629 * frac;
  double T_term = 0.000387933 * T * T;
  
  double g = 280.46061837 + w_term_mod + frac_term + T_term;
  g = fmod(g, 360.0); if(g < 0) g += 360.0;
  g = fmod(g + siteLon, 360.0); if(g < 0) g += 360.0;
  return g / 15.0;
}

static double lst() {
  return lst_offset(0.0);
}

static double getHourAngle(double ra) {
  double current_lst = lst();
  double ha_hours;
  if (tracking && trkStartLST > 0.0) {
    double scale = 1.0;
    if (trackRate == 1)      scale = 0.976327; 
    else if (trackRate == 2) scale = 0.997270; 
    double elapsed = current_lst - trkStartLST;
    if (elapsed < -12.0) elapsed += 24.0;
    if (elapsed > 12.0)  elapsed -= 24.0;
    ha_hours = (trkStartLST - ra) + elapsed * scale;
  } else {
    ha_hours = current_lst - ra;
  }
  double ha = fmod(ha_hours * 15.0, 360.0);
  if (ha < 0.0) ha += 360.0;
  return ha;
}

static void rd2aa_at(double ra, double dec, double *alt, double *az, double offset_sec) {
  double scale = 1.0;
  if (trackRate == 1)      scale = 0.976327;
  else if (trackRate == 2) scale = 0.997270;
  
  double l = lst_offset(offset_sec * scale);
  double ha_hours = l - ra;
  double ha = fmod(ha_hours * 15.0, 360.0);
  if (ha < 0.0) ha += 360.0;
  
  if (mountType == 1) { 
    *alt = dec;
    *az = ha;
    return;
  }
  if (mountType == 2) { 
    if (ha >= 0.0 && ha < 180.0) { 
      *az = ha;
      *alt = dec;
    } else { 
      *az = fmod(ha + 180.0, 360.0);
      *alt = 180.0 - dec;
    }
    return;
  }
  double hr=ha*DEG_TO_RAD,dr=dec*DEG_TO_RAD,lr=siteLat*DEG_TO_RAD;
  double sa=sin(dr)*sin(lr)+cos(dr)*cos(lr)*cos(hr);
  *alt=asin(sa)*RAD_TO_DEG;
  double ca=(sin(dr)-sin(*alt*DEG_TO_RAD)*sin(lr))/(cos(*alt*DEG_TO_RAD)*cos(lr));
  ca=constrain(ca,-1.0,1.0);
  *az=acos(ca)*RAD_TO_DEG;
  if(sin(hr)>0)*az=360.0-*az;
}

static void rd2aa(double ra, double dec, double *alt, double *az) {
  rd2aa_at(ra, dec, alt, az, 0.0);
}

static void aa2rd(double alt, double az, long *rs, long *ds) {
  if (mountType == 1) { 
    *ds = alt * 3600.0;
    double ra = lst() - (az / 15.0);
    while (ra < 0) ra += 24.0;
    while (ra >= 24.0) ra -= 24.0;
    *rs = ra * 3600.0;
    return;
  }
  if (mountType == 2) { 
    double dec, ha;
    double az_norm = fmod(az, 360.0);
    if (az_norm < 0) az_norm += 360.0;
    if (alt >= -90.0 && alt <= 90.0) { 
      ha = az_norm;
      dec = alt;
    } else { 
      ha = fmod(az_norm + 180.0, 360.0);
      dec = 180.0 - alt;
    }
    *ds = dec * 3600.0;
    double ra = lst() - (ha / 15.0);
    while (ra < 0) ra += 24.0;
    while (ra >= 24.0) ra -= 24.0;
    *rs = ra * 3600.0;
    return;
  }
  double ar=alt*DEG_TO_RAD,zr=az*DEG_TO_RAD,lr=siteLat*DEG_TO_RAD;
  double sd=sin(ar)*sin(lr)+cos(ar)*cos(lr)*cos(zr);
  double dec=asin(sd)*RAD_TO_DEG;
  double ch=(sin(ar)-sd*sin(lr))/(cos(dec*DEG_TO_RAD)*cos(lr));
  ch=constrain(ch,-1.0,1.0);
  double ha=acos(ch)*RAD_TO_DEG;
  if(sin(zr)>0)ha=360.0-ha;
  double ra=lst()-ha/15.0;
  if(ra<0)ra+=24.0; if(ra>=24)ra-=24.0;
  *rs=(long)(ra*3600.0); *ds=(long)(dec*3600.0);
}

static double getAstronomicalAlt(double ra, double dec) {
  double current_lst = lst();
  double ha_hours = current_lst - ra;
  double ha = fmod(ha_hours * 15.0, 360.0);
  if (ha < 0.0) ha += 360.0;
  double hr = ha * DEG_TO_RAD;
  double dr = dec * DEG_TO_RAD;
  double lr = siteLat * DEG_TO_RAD;
  double sa = sin(dr) * sin(lr) + cos(dr) * cos(lr) * cos(hr);
  return asin(constrain(sa, -1.0, 1.0)) * RAD_TO_DEG;
}

static double getPhysicalAlt() {
  if (mountType == 0) {
    return currAlt;
  }
  double ha, dec;
  double az_norm = fmod(currAz, 360.0);
  if (az_norm < 0) az_norm += 360.0;
  if (currAlt >= -90.0 && currAlt <= 90.0) {
    ha = az_norm;
    dec = currAlt;
  } else { 
    ha = fmod(az_norm + 180.0, 360.0);
    dec = 180.0 - currAlt;
  }
  double hr = ha * DEG_TO_RAD;
  double dr = dec * DEG_TO_RAD;
  double lr = siteLat * DEG_TO_RAD;
  double sa = sin(dr) * sin(lr) + cos(dr) * cos(lr) * cos(hr);
  return asin(constrain(sa, -1.0, 1.0)) * RAD_TO_DEG;
}

static double getPhysicalAz() {
  if (mountType == 0) {
    return currAz;
  }
  double ha, dec;
  double az_norm = fmod(currAz, 360.0);
  if (az_norm < 0) az_norm += 360.0;
  if (currAlt >= -90.0 && currAlt <= 90.0) {
    ha = az_norm;
    dec = currAlt;
  } else { 
    ha = fmod(az_norm + 180.0, 360.0);
    dec = 180.0 - currAlt;
  }
  double hr = ha * DEG_TO_RAD;
  double dr = dec * DEG_TO_RAD;
  double lr = siteLat * DEG_TO_RAD;
  double sa = sin(dr) * sin(lr) + cos(dr) * cos(lr) * cos(hr);
  double alt = asin(constrain(sa, -1.0, 1.0)) * RAD_TO_DEG;
  
  double ca = (sin(dr) - sin(alt * DEG_TO_RAD) * sin(lr)) / (cos(alt * DEG_TO_RAD) * cos(lr));
  ca = constrain(ca, -1.0, 1.0);
  double az = acos(ca) * RAD_TO_DEG;
  if (sin(hr) > 0) az = 360.0 - az;
  return az;
}

static void astronomy_aa2rd(double alt, double az, long *rs, long *ds) {
  double ar=alt*DEG_TO_RAD,zr=az*DEG_TO_RAD,lr=siteLat*DEG_TO_RAD;
  double sd=sin(ar)*sin(lr)+cos(ar)*cos(lr)*cos(zr);
  double dec=asin(sd)*RAD_TO_DEG;
  double ch=(sin(ar)-sd*sin(lr))/(cos(dec*DEG_TO_RAD)*cos(lr));
  ch=constrain(ch,-1.0,1.0);
  double ha=acos(ch)*RAD_TO_DEG;
  if(sin(zr)>0)ha=360.0-ha;
  double ra=lst()-ha/15.0;
  while(ra<0)ra+=24.0; while(ra>=24.0)ra-=24.0;
  *rs=(long)(ra*3600.0); *ds=(long)(dec*3600.0);
}

static void rd2aa_same_pier(double ra, double dec, double *alt, double *az) {
  double l = lst_offset(0.0);
  double ha_hours = l - ra;
  double ha = fmod(ha_hours * 15.0, 360.0);
  if (ha < 0.0) ha += 360.0;
  
  if (mountType == 1) { 
    *alt = dec;
    *az = ha;
    return;
  }
  if (mountType == 2) { 
    bool currentIsNormal = (currAlt >= -90.0 && currAlt <= 90.0);
    if (currentIsNormal) { 
      *az = ha;
      *alt = dec;
    } else { 
      *az = fmod(ha + 180.0, 360.0);
      *alt = 180.0 - dec;
    }
    return;
  }
  
  double hr=ha*DEG_TO_RAD,dr=dec*DEG_TO_RAD,lr=siteLat*DEG_TO_RAD;
  double sa=sin(dr)*sin(lr)+cos(dr)*cos(lr)*cos(hr);
  *alt=asin(sa)*RAD_TO_DEG;
  double ca=(sin(dr)-sin(*alt*DEG_TO_RAD)*sin(lr))/(cos(*alt*DEG_TO_RAD)*cos(lr));
  ca=constrain(ca,-1.0,1.0);
  *az=acos(ca)*RAD_TO_DEG;
  if(sin(hr)>0)*az=360.0-*az;
}

// ======================== MOTEURS ==========================

static inline void stepPulse(uint8_t pin) {
  if (pin == 2) {
    PORTE |= (1 << 4);
    delayMicroseconds(10);
    PORTE &= ~(1 << 4);
  } else if (pin == 5) {
    PORTE |= (1 << 3);
    delayMicroseconds(10);
    PORTE &= ~(1 << 3);
  } else {
    digitalWrite(pin,HIGH); delayMicroseconds(10); digitalWrite(pin,LOW);
  }
}

static void enableMotors(bool en) {
  if (alarmActive && en) {
    digitalWrite(AZ_EN, HIGH);
    digitalWrite(ALT_EN, HIGH);
    return;
  }
  digitalWrite(AZ_EN,en?LOW:HIGH); digitalWrite(ALT_EN,en?LOW:HIGH);
}

static void formatRaDec(long ra_s, long dec_s) {
  long r = ra_s; if(r<0)r+=86400; if(r>=86400)r-=86400;
  sprintf(lxRA,"%02d:%02d:%02d#",(int)(r/3600),(int)((r%3600)/60),(int)(r%60));
  long ad = abs(dec_s);
  sprintf(lxDEC,"%c%02d*%02d:%02d#",dec_s>=0?'+':'-',
          (int)(ad/3600),(int)((ad%3600)/60),(int)(ad%60));
}

static void updatePos() {
  currAz=(double)azPos/AZ_PPD;
  while(currAz<0)currAz+=360.0; while(currAz>=360)currAz-=360.0;
  currAlt=(double)altPos/ALT_PPD;
  if (mountType == 0) {
    if(currAlt < -90.0) currAlt = -90.0;
    if(currAlt >  90.0) currAlt =  90.0;
  } else {
    while(currAlt < -180.0) currAlt += 360.0;
    while(currAlt >  180.0) currAlt -= 360.0;
  }
  aa2rd(currAlt,currAz,&currRA,&currDEC);
  formatRaDec(currRA, currDEC);

  double physAlt = getPhysicalAlt();
  if (physAlt < ALT_MIN || (mountType == 0 && physAlt > ALT_MAX)) {
    if (physAlt < ALT_MIN) {
      if (tracking) {
        tracking = false;
        alarmActive = false;
        slewToAA((mountType >= 1) ? 90.0 : 0.0, 0.0);
        alarmActive = true;
        parked = true;
        enableMotors(false);
        saveStateToEEPROM();
      }
    }
    if (tracking) {
      tracking = false;
    }
    limitHit = true;
  } else {
    limitHit = false;
  }
}

// ======================== PARSER OUT INLINE PENDANT SLEW ===

static void processCmd(const char* cmd, uint8_t ci, Print& out);

static void slewServeOne(Stream& in, Print& out, char* buf, uint8_t& bi) {
  if(!in.available()) return;
  char c = in.read();
  if(c==' '||c=='\r') return;
  if(c==6) {
    if (mountType == 2) out.write('G');
    else if (mountType == 1) out.write('P');
    else out.write('A');
    return;
  }
  if(c=='#'||c=='\n') {
    buf[bi]='\0';
    if(bi>0 && buf[0]==':') {
      if(buf[1]=='Q' || buf[1]=='K') {
        slewing = false;
      }
      processCmd(buf, bi, out);
    }
    bi=0;
    return;
  }
  if(bi<CMD_MAX-1) buf[bi++]=c; else bi=0;
}

// ======================== SLEW =============================

static int slewToAA(double tAlt, double tAz) {
  if (alarmActive) return 0;
  double startPhysAlt = getPhysicalAlt();
  double targetAlt = tAlt;
  if (mountType >= 1) {
    // tAz is RA in degrees, tAlt is DEC in degrees
    double lst_deg = lst() * 15.0; // LST in degrees
    double ha_deg = lst_deg - tAz;
    if (ha_deg < 0) ha_deg += 360.0;
    
    double hr = ha_deg * DEG_TO_RAD;
    double dr = tAlt * DEG_TO_RAD;
    double lr = siteLat * DEG_TO_RAD;
    double sa = sin(dr) * sin(lr) + cos(dr) * cos(lr) * cos(hr);
    targetAlt = asin(constrain(sa, -1.0, 1.0)) * RAD_TO_DEG;
  }
  double targetPhysAlt = targetAlt;
  if (targetAlt < ALT_MIN - 0.01 || (mountType == 0 && targetAlt > ALT_MAX + 0.01)) {
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

  digitalWrite(AZ_DIR, (azS>=0) ^ azReversed ? HIGH : LOW);
  digitalWrite(ALT_DIR, (altS>=0) ^ altReversed ? HIGH : LOW);

  long startRA=currRA, startDEC=currDEC;
  long endRA, endDEC;
  aa2rd(tAlt, tAz, &endRA, &endDEC);
  long deltaRA=endRA-startRA;
  if(deltaRA>43200) deltaRA-=86400;
  if(deltaRA<-43200) deltaRA+=86400;
  long deltaDEC=endDEC-startDEC;

  long azStart=azPos, altStart=altPos;
  enableMotors(true); slewing=true;
  digitalWrite(LED_BUILTIN,HIGH);

  unsigned long minDelay = stepDelaySlew;
  double f_start = 1.0e6 / MAX_DELAY;
  double f_target = 1.0e6 / minDelay;
  
  unsigned long accel = (unsigned long)(0.5 * (f_start + f_target) * 5.0);
  if (2 * accel > maxS) {
    accel = maxS / 2;
  }

  uint16_t ramp_table[100];
  if (accel > 0) {
    for (int j = 0; j < 100; j++) {
      double f = f_start + (f_target - f_start) * j / 99.0;
      ramp_table[j] = (uint16_t)(1.0e6 / f);
    }
  }

  unsigned long dl;
  unsigned long lastUpdTime=millis();
  unsigned long lastI=0;
  bool interrupted=false;
  bool interrupting=false;

  static char sbUsb[CMD_MAX]; static uint8_t sbiUsb=0;
  static char sbRj [CMD_MAX]; static uint8_t sbiRj=0;
  sbiUsb=0; sbiRj=0;

  unsigned long err = maxS / 2;
  bool azIsMajor = (aAS >= aLS);

  for(unsigned long i=0;i<maxS;i++){
    unsigned long loopStart = micros();
    lastI = i;

    if(accel == 0) {
      dl = minDelay;
    } else if(i < accel) {
      int idx = (int)((i * 99UL) / accel);
      dl = ramp_table[idx];
    } else if(i >= maxS - accel) {
      unsigned long remaining = maxS - 1 - i;
      int idx = (int)((remaining * 99UL) / accel);
      dl = ramp_table[idx];
    } else {
      dl = minDelay;
    }

    if (azIsMajor) {
      stepPulse(AZ_STEP);
      err += aLS;
      if (err >= maxS) {
        err -= maxS;
        stepPulse(ALT_STEP);
      }
    } else {
      stepPulse(ALT_STEP);
      err += aAS;
      if (err >= maxS) {
        err -= maxS;
        stepPulse(AZ_STEP);
      }
    }

    if ((i & 31) == 0) {
      updateBuzzer();
    }

    unsigned long nowMs = millis();
    if(i == 0 || i == maxS - 1 || nowMs - lastUpdTime >= 200){
      lastUpdTime = nowMs;
      long azLive  = azStart  + (long)((double)azS  * i / maxS);
      long altLive = altStart + (long)((double)altS * i / maxS);
      currAz = (double)azLive / AZ_PPD;
      while(currAz<0)currAz+=360.0; while(currAz>=360)currAz-=360.0;
      currAlt = (double)altLive / ALT_PPD;
      long iRA=startRA+(long)((double)deltaRA*i/maxS);
      long iDEC=startDEC+(long)((double)deltaDEC*i/maxS);
      formatRaDec(iRA, iDEC);

      double physAlt = getPhysicalAlt();
      if (physAlt < ALT_MIN || (mountType == 0 && physAlt > ALT_MAX)) {
        bool triggerLower = (physAlt < ALT_MIN && targetPhysAlt < startPhysAlt);
        bool triggerUpper = (mountType == 0 && physAlt > ALT_MAX && targetPhysAlt > startPhysAlt);
        if (triggerLower || triggerUpper) {
          limitHit = true;
          if (triggerLower) {
            alarmActive = true;
            if (!parked) {
              parked = true;
              enableMotors(false);
              saveStateToEEPROM();
            }
          }
          slewing = false;
          interrupted = true;
          break;
        }
      }
    }

    bool wasSlewing = slewing;
    if ((i & 31) == 0) {
      slewServeOne(Serial,  Serial,  sbUsb, sbiUsb);
      slewServeOne(Serial3, Serial3, sbRj,  sbiRj);
      if(!slewing && wasSlewing && !interrupting) { 
        interrupting = true;
        interrupted = true; 
        unsigned long remaining_slew = maxS - i;
        unsigned long decelSteps = (i < accel) ? i : accel;
        if (decelSteps > remaining_slew) decelSteps = remaining_slew;
        
        if (decelSteps > 0) {
          maxS = i + decelSteps;
          if (i < aAS) aAS = maxS;
          if (i < aLS) aLS = maxS;
        } else {
          break;
        }
      }
    }

    unsigned long elapsed = micros() - loopStart;
    if(dl > elapsed) delayMicroseconds(dl - elapsed);
  }

  unsigned long azDone  = (lastI + 1 < aAS) ? (lastI + 1) : aAS;
  unsigned long altDone = (lastI + 1 < aLS) ? (lastI + 1) : aLS;
  long azDelta  = (azS  >= 0) ?  (long)azDone  : -(long)azDone;
  long altDelta = (altS >= 0) ?  (long)altDone : -(long)altDone;
  azPos  = azStart  + azDelta;
  altPos = altStart + altDelta;

  digitalWrite(LED_BUILTIN,LOW);
  slewing=false; updatePos();
  saveStateToEEPROM();
  if(!interrupted && maxS > 0) playArrivalMelody();
  return interrupted ? 0 : 1;
}

// ======================== SUIVI (ISR TIMER 1 @ 10 kHz) ============================

static volatile unsigned long az_accum = 0;
static volatile unsigned long alt_accum = 0;
static volatile unsigned long az_add = 0;
static volatile unsigned long alt_add = 0;
static volatile int8_t isr_az_dir = 0;
static volatile int8_t isr_alt_dir = 0;

ISR(TIMER1_COMPA_vect) {
  if (tracking && !slewing) {
    if (azMove == 0 && az_add > 0) {
      az_accum += az_add;
      if (az_accum >= 1000000UL) {
        az_accum -= 1000000UL;
        digitalWrite(AZ_DIR, (isr_az_dir > 0) ^ azReversed ? HIGH : LOW);
        stepPulse(AZ_STEP);
        azPos += isr_az_dir;
      }
    }
    if (altMove == 0 && alt_add > 0) {
      alt_accum += alt_add;
      if (alt_accum >= 1000000UL) {
        alt_accum -= 1000000UL;
        
        long nextAlt = altPos + isr_alt_dir;
        double nA = (double)nextAlt / ALT_PPD;
        if (mountType == 0 && (nA < ALT_MIN || nA > ALT_MAX)) {
          limitHit = true;
          tracking = false;
        } else {
          digitalWrite(ALT_DIR, (isr_alt_dir > 0) ^ altReversed ? HIGH : LOW);
          stepPulse(ALT_STEP);
          altPos = nextAlt;
        }
      }
    }
  }
}

static void doTrack() {
  static double smooth_speed_az = 0.0;
  static double smooth_speed_alt = 0.0;

  if (alarmActive) {
    tracking = false;
    trkStartLST = 0.0;
    azStepInterval = 0; altStepInterval = 0;
    azStepsLeft = 0; altStepsLeft = 0;
    smooth_speed_az = 0.0;
    smooth_speed_alt = 0.0;
    return;
  }

  if(!tracking||slewing){ 
    trkStartLST = 0.0; 
    azStepInterval = 0; altStepInterval = 0;
    azStepsLeft = 0; altStepsLeft = 0;
    smooth_speed_az = 0.0;
    smooth_speed_alt = 0.0;
    return; 
  }
  
  static double trk_base_lst = 0.0;
  static double trk_base_az = 0.0;
  static double trk_base_alt = 0.0;
  static double trk_speed_az = 0.0; 
  static double trk_speed_alt = 0.0; 
  static unsigned long last_full_trig_ms = 0;

  if(trkStartLST == 0.0 || force_tracking_rebase) {
    if (force_tracking_rebase) {
      trkRA = (double)currRA / 3600.0;
      trkDec = (double)currDEC / 3600.0;
    }
    trkStartLST = lst();
    lastAzStepUs = micros();
    lastAltStepUs = micros();
    last_full_trig_ms = 0; 
    smooth_speed_az = 0.0;
    smooth_speed_alt = 0.0;
    force_tracking_rebase = false;
  }
  if(millis()-lastTrkMs<200)return;
  lastTrkMs=millis();

  double physAlt = getPhysicalAlt();
  if (physAlt < ALT_MIN || (mountType == 0 && physAlt > ALT_MAX)) {
    tracking=false; limitHit=true; trkStartLST=0.0;
    if (physAlt < ALT_MIN) {
      alarmActive = true;
      if (!parked) {
        parked = true;
        enableMotors(false);
        saveStateToEEPROM();
      }
    }
    azStepInterval = 0; altStepInterval = 0;
    azStepsLeft = 0; altStepsLeft = 0;
    smooth_speed_az = 0.0;
    smooth_speed_alt = 0.0;
    return;
  }
  
  if(last_full_trig_ms == 0 || millis() - last_full_trig_ms >= 5000) {
    double current_lst = lst();
    double tA, tZ;
    rd2aa_at(trkRA, trkDec, &tA, &tZ, 0.0);
    double targetAlt = (mountType == 0) ? tA : getAstronomicalAlt(trkRA, trkDec);
    if(targetAlt < ALT_MIN){
      tracking=false; limitHit=true; alarmActive=true; trkStartLST=0.0;
      if (!parked) {
        parked = true;
        enableMotors(false);
        saveStateToEEPROM();
      }
      azStepInterval = 0; altStepInterval = 0;
      azStepsLeft = 0; altStepsLeft = 0;
      smooth_speed_az = 0.0;
      smooth_speed_alt = 0.0;
      return;
    }
    
    double tA_next, tZ_next;
    rd2aa_at(trkRA, trkDec, &tA_next, &tZ_next, 10.0);
    
    double speed_az = tZ_next - tZ;
    if(speed_az > 180.0) speed_az -= 360.0;
    if(speed_az < -180.0) speed_az += 360.0;
    
    double speed_alt = tA_next - tA;
    if(speed_alt > 180.0) speed_alt -= 360.0;
    if(speed_alt < -180.0) speed_alt += 360.0;
    
    trk_speed_az = speed_az * 360.0;
    trk_speed_alt = speed_alt * 360.0;
    
    trk_base_lst = current_lst;
    trk_base_az = tZ;
    trk_base_alt = tA;
    last_full_trig_ms = millis();
  }

  double current_lst = lst();
  double elapsed_lst = current_lst - trk_base_lst;
  if (elapsed_lst < -12.0) elapsed_lst += 24.0;
  if (elapsed_lst > 12.0)  elapsed_lst -= 24.0;
  
  double tZ = trk_base_az + trk_speed_az * elapsed_lst;
  double tA = trk_base_alt + trk_speed_alt * elapsed_lst;
  
  double steps_per_sec_az = (trk_speed_az * AZ_PPD) / 3600.0;
  double steps_per_sec_alt = (trk_speed_alt * ALT_PPD) / 3600.0;
  
  double liveAz = (double)azPos / AZ_PPD;
  double liveAlt = (double)altPos / ALT_PPD;
  
  double azD = tZ - liveAz;
  if(azD>180.0)azD-=360.0; if(azD<-180.0)azD+=360.0;
  
  double altD = tA - liveAlt;
  if(altD>180.0)altD-=360.0; if(altD<-180.0)altD+=360.0;
  
  double error_az_steps = azD * AZ_PPD;
  double error_alt_steps = altD * ALT_PPD;
  
  double Kp = 0.3;
  double corr_speed_az = steps_per_sec_az + Kp * error_az_steps;
  double corr_speed_alt = steps_per_sec_alt + Kp * error_alt_steps;
  
  double max_tracking_speed = 1000.0;
  if (corr_speed_az > max_tracking_speed) corr_speed_az = max_tracking_speed;
  if (corr_speed_az < -max_tracking_speed) corr_speed_az = -max_tracking_speed;
  if (corr_speed_alt > max_tracking_speed) corr_speed_alt = max_tracking_speed;
  if (corr_speed_alt < -max_tracking_speed) corr_speed_alt = -max_tracking_speed;
  
  double alpha = 0.2;
  if (smooth_speed_az == 0.0) smooth_speed_az = corr_speed_az;
  else smooth_speed_az = alpha * corr_speed_az + (1.0 - alpha) * smooth_speed_az;
  
  if (smooth_speed_alt == 0.0) smooth_speed_alt = corr_speed_alt;
  else smooth_speed_alt = alpha * corr_speed_alt + (1.0 - alpha) * smooth_speed_alt;
  
  noInterrupts();
  if (smooth_speed_az > 0.05) {
    isr_az_dir = 1;
    az_add = (unsigned long)(smooth_speed_az * 100.0);
  } else if (smooth_speed_az < -0.05) {
    isr_az_dir = -1;
    az_add = (unsigned long)((-smooth_speed_az) * 100.0);
  } else {
    isr_az_dir = 0;
    az_add = 0;
    az_accum = 0;
  }
  
  if (smooth_speed_alt > 0.05) {
    isr_alt_dir = 1;
    alt_add = (unsigned long)(smooth_speed_alt * 100.0);
  } else if (smooth_speed_alt < -0.05) {
    isr_alt_dir = -1;
    alt_add = (unsigned long)((-smooth_speed_alt) * 100.0);
  } else {
    isr_alt_dir = 0;
    alt_add = 0;
    alt_accum = 0;
  }
  interrupts();
  
  updatePos();
}

// ======================== HORLOGE ==========================

static void clk() {
  unsigned long n=millis(),e=n-lastClkMs;
  if(e>=1000){
    dt_s += e/1000; lastClkMs = n - (e%1000);
    while(dt_s>=60){ dt_s-=60; dt_mi++; }
    while(dt_mi>=60){ dt_mi-=60; dt_h++; }
    while(dt_h>=24){
      dt_h -= 24; dt_d++;
      if(dt_d > daysInMonth(dt_m, dt_y)) {
        dt_d = 1; dt_m++;
        if(dt_m > 12) { dt_m = 1; dt_y++; }
      }
    }
  }
}

// ======================== :GU# ==============================

static void sendGU(Print& out) {
  if(!tracking) out.write('n');
  if(!slewing)  out.write('N');
  out.write(parked?'P':'p');
  if(atHome)    out.write('H');
  if(synced)    out.write('S');
  if(guiding)   out.write('G');
  
  if (mountType == 2) out.write('G');
  else if (mountType == 1) out.write('P');
  else out.write('A');
  
  if (mountType == 2) {
    if (currAlt >= -90.0 && currAlt <= 90.0) out.write('e');
    else out.write('w');
  } else {
    out.write('o'); 
  }
  out.write('0'); 
  out.write('0'); 
  out.write('0'); 

  if(!timeSet) out.write('F');           
  
  out.write('#');
}

// ======================== :GX## =============================

static void handleGX(const char* cmd, Print& out) {
  char g1=cmd[3], g2=cmd[4];
  if(g1=='4'&&g2=='0'){ out.print(currAz,1); out.write('#'); return; }
  if(g1=='4'&&g2=='1'){ out.print(currAlt,1); out.write('#'); return; }
  if(g1=='4'&&g2=='2'){ out.print(currAz,1); out.write('#'); return; }
  if(g1=='4'&&g2=='3'){ out.print(currAlt,1); out.write('#'); return; }
  if(g1=='8'&&g2=='0'){
    int uy,um,ud,uh,umi,us; getUTC(&uy,&um,&ud,&uh,&umi,&us);
    double utcH = uh + umi/60.0 + us/3600.0;
    out.print(utcH,2); out.write('#'); return;
  }
  if(g1=='8'&&g2=='1'){
    int uy,um,ud,uh,umi,us; getUTC(&uy,&um,&ud,&uh,&umi,&us);
    char b[12]; sprintf(b,"%02d/%02d/%02d#", um, ud, uy%100);
    out.print(b); return;
  }
  if(g1=='9'&&g2=='0'){ out.print(F("15.0#")); return; }
  if(g1=='9'&&g2=='1'){ out.print(F("0.5#")); return; }
  if(g1=='9'&&g2=='2'){ out.print((int)maxSlewRate); out.write('#'); return; }
  if(g1=='9'&&g2=='3'){ out.print((int)maxSlewRate); out.write('#'); return; }
  if(g1=='9'&&g2=='4'){ out.print(F("A#")); return; }
  if(g1=='9'&&(g2=='5'||g2=='6')){ out.print(F("0#")); return; }
  if(g1=='9'&&g2=='A'){ out.print(F("0#")); return; }
  if(g1=='9'&&g2=='B'){ out.print(F("89#")); return; }
  if(g1=='9'&&g2=='C'){ out.print(F("-360#")); return; }
  if(g1=='9'&&g2=='D'){ out.print(F("360#")); return; }
  if(g1=='9'&&g2=='F'){ out.print((int)maxSlewRate); out.write('#'); return; }
  if(g1=='E'){ out.print(F("0#")); return; }
  if(g1=='F'){ out.print(F("20.0#")); return; }
  out.print(F("0#"));
}

// ======================== :GBE# =============================

static void handleGBE(Print& out) {
  out.print(tracking?1:0);         out.write(',');
  out.print(slewing?1:0);          out.write(',');
  out.print(limitHit?1:0);         out.write(',');
  out.print((int)(maxSlewRate*10)); out.write(',');
  out.print(currAlt,3);            out.write(',');
  out.print(currAz,3);             out.write(',');
  out.print(parked?1:0);           out.write(',');
  out.print(synced?1:0);
  out.write('#');
}

// ======================== HELPERS PARSING ===================

static long parseSdec(const char* s, uint8_t len) {
  if(len < 4) return 0;
  uint8_t i = 0; int8_t sg = 1;
  if(s[i] == '+') { i++; }
  else if(s[i] == '-') { sg = -1; i++; }
  long d=0, m=0, sec=0;
  while(i < len && s[i] >= '0' && s[i] <= '9') { d = d*10 + (s[i]-'0'); i++; }
  if(i < len && (s[i]=='*' || s[i]==':' || s[i]=='\xDF')) i++;
  while(i < len && s[i] >= '0' && s[i] <= '9') { m = m*10 + (s[i]-'0'); i++; }
  if(i < len && (s[i]==':' || s[i]=='\'' || s[i]=='*')) {
    i++;
    while(i < len && s[i] >= '0' && s[i] <= '9') { sec = sec*10 + (s[i]-'0'); i++; }
  }
  return sg * (d*3600 + m*60 + sec);
}

static long parseSaz(const char* s, uint8_t len) {
  if(len < 4) return 0;
  uint8_t i = 0; long d=0, m=0, sec=0;
  while(i < len && s[i] >= '0' && s[i] <= '9') { d = d*10 + (s[i]-'0'); i++; }
  if(i < len && (s[i]=='*' || s[i]==':')) i++;
  while(i < len && s[i] >= '0' && s[i] <= '9') { m = m*10 + (s[i]-'0'); i++; }
  if(i < len && (s[i]==':' || s[i]=='\'' || s[i]=='*')) {
    i++;
    while(i < len && s[i] >= '0' && s[i] <= '9') { sec = sec*10 + (s[i]-'0'); i++; }
  }
  return d*3600 + m*60 + sec;
}

static long parseSrSeconds(const char* s, uint8_t len) {
  if(len < 5) return -1;
  long h=0, m=0, sec=0;
  if(!(s[0]>='0'&&s[0]<='9' && s[1]>='0'&&s[1]<='9')) return -1;
  h = (s[0]-'0')*10 + (s[1]-'0');
  if(len < 5 || (s[2]!=':' && s[2]!='*')) return -1;
  if(!(s[3]>='0'&&s[3]<='9' && s[4]>='0'&&s[4]<='9')) return -1;
  m = (s[3]-'0')*10 + (s[4]-'0');
  if(len >= 8 && s[5]==':') {
    if(s[6]>='0'&&s[6]<='9' && s[7]>='0'&&s[7]<='9')
      sec = (s[6]-'0')*10 + (s[7]-'0');
  } else if(len >= 7 && s[5]=='.') {
    if(s[6]>='0'&&s[6]<='9') sec = (s[6]-'0')*6;       
  }
  return h*3600 + m*60 + sec;
}

// ======================== PROCESSCMD =======================

static void processCmd(const char* cmd, uint8_t ci, Print& out) {
  if(ci < 2) { out.print(F("0#")); return; }
  char c1=cmd[1], c2=cmd[2], c3 = (ci>3) ? cmd[3] : '\0';
  char buf[16];

  // ============ GET COMMANDS ============
  if(c1=='G'&&c2=='R'){ out.print(lxRA); return; }
  if(c1=='G'&&c2=='D'){ out.print(lxDEC); return; }
  if(c1=='G'&&c2=='A'){
    int d=(int)abs(currAlt),m=(int)((abs(currAlt)-d)*60);
    int s=(int)((abs(currAlt)-d-m/60.0)*3600)%60;
    sprintf(buf,"%c%02d*%02d:%02d#",currAlt>=0?'+':'-',d,m,s);
    out.print(buf); return;
  }
  if(c1=='G'&&(c2=='Z'||c2=='z')){
    int d=(int)currAz,m=(int)((currAz-d)*60);
    int s=(int)((currAz-d-m/60.0)*3600)%60;
    sprintf(buf,"%03d*%02d:%02d#",d,m,s);
    out.print(buf); return;
  }
  if(c1=='G'&&c2=='U'){ sendGU(out); return; }
  if(c1=='G'&&c2=='B'&&c3=='E'){ handleGBE(out); return; }
  if(c1=='G'&&c2=='r'){
    long r=inRA; if(r<0)r+=86400; if(r>=86400)r-=86400;
    sprintf(buf,"%02d:%02d:%02d#",(int)(r/3600),(int)((r%3600)/60),(int)(r%60));
    out.print(buf); return;
  }
  if(c1=='G'&&c2=='d'){
    long ad=abs(inDEC);
    sprintf(buf,"%c%02d*%02d:%02d#",inDEC>=0?'+':'-',
            (int)(ad/3600),(int)((ad%3600)/60),(int)(ad%60));
    out.print(buf); return;
  }
  if(c1=='G'&&c2=='Q'&&c3=='a'){ out.print(parkAlt); out.print('#'); return; }
  if(c1=='G'&&c2=='Q'&&c3=='z'){ out.print(parkAz); out.print('#'); return; }
  if(c1=='G'&&c2=='G'&&c3=='a'){ out.print(gearRatioAZ); out.print('#'); return; }
  if(c1=='G'&&c2=='G'&&c3=='e'){ out.print(gearRatioALT); out.print('#'); return; }
  if(c1=='G'&&c2=='S'&&c3=='p'){ out.print(motorStepsPerRev); out.print('#'); return; }
  if(c1=='G'&&c2=='S'&&c3=='m'){ out.print(microstep); out.print('#'); return; }
  if(c1=='G'&&c2=='m'){
    if (mountType == 2) {
      if (currAlt >= -90.0 && currAlt <= 90.0) {
        out.print(F("E#"));
      } else {
        out.print(F("W#"));
      }
    } else {
      out.print(F("N#"));
    }
    return;
  }
  if(c1=='G'&&c2=='h'){ out.print(F("+89*#")); return; }
  if(c1=='G'&&c2=='o'){ out.print(F("+00*#")); return; }
  if(c1=='G'&&c2=='W'){
    if (mountType == 2) out.write('G');
    else if (mountType == 1) out.write('F');
    else out.write('A');
    out.write(tracking?'T':'N');
    out.write(synced?'1':'0'); out.write('#'); return;
  }
  if(c1=='G'&&c2=='X'){ handleGX(cmd, out); return; }
  if(c1=='G'&&c2=='c'){ out.print(F("24#")); return; }
  if(c1=='G'&&c2=='a'){ sprintf(buf,"%02d:%02d:%02d#", (dt_h%12==0)?12:(dt_h%12), dt_mi, dt_s); out.print(buf); return; }
  if(c1=='G'&&c2=='L'){ sprintf(buf,"%02d:%02d:%02d#", dt_h, dt_mi, dt_s); out.print(buf); return; }
  if(c1=='G'&&c2=='C'){ sprintf(buf,"%02d/%02d/%02d#", dt_m, dt_d, dt_y%100); out.print(buf); return; }
  if(c1=='G'&&c2=='S'&&strlen(cmd)<=4){ 
    double l = lst(); int h = (int)l;
    double mm = (l - h) * 60.0; int m = (int)mm;
    int s = (int)((mm - m) * 60.0 + 0.5);
    if(s >= 60) { s -= 60; m++; }
    if(m >= 60) { m -= 60; h++; }
    if(h >= 24) { h -= 24; }
    sprintf(buf,"%02d:%02d:%02d#", h, m, s);
    out.print(buf); return;
  }
  if(c1=='G'&&c2=='T'){ out.print(F("60.0000#")); return; }
  if(c1=='G'&&c2=='M'){
    if (mountType == 0) out.print(F("AltAz#"));
    else if (mountType == 1) out.print(F("ForkEq#"));
    else if (mountType == 2) out.print(F("GermanEq#"));
    return;
  }
  if(c1=='G'&&c2=='N'){ out.print(F("Observatory#")); return; }
  if(c1=='G'&&c2=='O'){ out.print(F("Site2#")); return; }
  if(c1=='G'&&c2=='P'){ out.print(F("Site3#")); return; }
  if(c1=='G'&&c2=='V'&&c3=='P'){ out.print(F("OnStep#")); return; }
  if(c1=='G'&&c2=='V'&&c3=='N'){ out.print(F("4.24#")); return; }
  if(c1=='G'&&c2=='V'&&(c3=='D'||c3=='F')){ out.print(F("May 26 2026#")); return; }
  if(c1=='G'&&c2=='V'&&c3=='T'){ out.print(F("00:00:00#")); return; }
  if(c1=='G'&&c2=='t'){
    double a = fabs(siteLat); int d = (int)a;
    double mm = (a - d) * 60.0; int m = (int)mm;
    int s = (int)((mm - m) * 60.0 + 0.5);
    if(s >= 60) { s -= 60; m++; }
    if(m >= 60) { m -= 60; d++; }
    sprintf(buf,"%c%02d*%02d:%02d#", siteLat>=0?'+':'-', d, m, s);
    out.print(buf); return;
  }
  if(c1=='G'&&c2=='g'){
    double a = fabs(siteLon); int d = (int)a;
    double mm = (a - d) * 60.0; int m = (int)mm;
    int s = (int)((mm - m) * 60.0 + 0.5);
    if(s >= 60) { s -= 60; m++; }
    if(m >= 60) { m -= 60; d++; }
    sprintf(buf,"%c%03d*%02d:%02d#", siteLon>=0?'-':'+', d, m, s);
    out.print(buf); return;
  }
  if(c1=='G'&&c2=='G'){
    double ho = utcOff;
    if(ho == (int)ho) sprintf(buf,"%+03d#",(int)ho);
    else {
      char sgn = ho>=0?'+':'-'; double a = fabs(ho);
      int h = (int)a; int t = (int)((a - h) * 10.0 + 0.5);
      sprintf(buf,"%c%02d.%d#", sgn, h, t);
    }
    out.print(buf); return;
  }
  if(c1=='G'&&c2=='L'){ sprintf(buf,"%02d:%02d:%02d#",dt_h,dt_mi,dt_s); out.print(buf); return; }
  if(c1=='G'&&c2=='C'){ sprintf(buf,"%02d/%02d/%02d#",dt_m,dt_d,dt_y%100); out.print(buf); return; }
  if(c1=='G'&&c2=='S'){
    double l=lst(); int h=(int)l,m=(int)((l-h)*60),s=(int)((l-h-m/60.0)*3600)%60;
    sprintf(buf,"%02d:%02d:%02d#",h,m,s); out.print(buf); return;
  }

  // ============ SET TARGET ============
  if(c1=='S'&&c2=='r'){
    long secs = parseSrSeconds(cmd+3, ci-3);
    if(secs < 0) { out.write('0'); return; }
    inRA = secs; haveAltAzTarget=false;
    out.write('1'); return;
  }
  if(c1=='S'&&c2=='d'){
    inDEC = parseSdec(cmd+3, ci-3);
    haveAltAzTarget=false;
    out.write('1'); return;
  }
  if(c1=='S'&&c2=='a'){
    inAlt = parseSdec(cmd+3, ci-3) / 3600.0;
    haveAltAzTarget=true;
    out.write('1'); return;
  }
  if(c1=='S'&&c2=='z'){
    inAz = parseSaz(cmd+3, ci-3) / 3600.0;
    while(inAz < 0)    inAz += 360.0;
    while(inAz >= 360) inAz -= 360.0;
    haveAltAzTarget=true;
    out.write('1'); return;
  }

  // ============ SLEW / MOVE ============
  if(c1=='M'&&c2=='S'){
    if (alarmActive) { out.write('1'); return; }
    if (slewing) { out.write('1'); return; }
    if(!timeSet) { out.print(F("5Time not set#")); return; }
    double ra_h=inRA/3600.0, dec_d=inDEC/3600.0, tA, tZ;
    rd2aa(ra_h,dec_d,&tA,&tZ);
    double targetAlt = (mountType == 0) ? tA : getAstronomicalAlt(ra_h, dec_d);
    if(targetAlt < ALT_MIN - 0.01){ limitHit=true; out.print(F("1Below horizon#")); return; }
    out.write('0');
    if(slewToAA(tA,tZ)){ trkRA=ra_h; trkDec=dec_d; tracking=true; parked=false; }
    return;
  }
  if(c1=='M'&&c2=='A'){
    if (alarmActive) { out.write('1'); return; }
    if (slewing) { out.write('1'); return; }
    if(!haveAltAzTarget){ out.write('2'); return; }
    double targetAlt = inAlt;
    if (mountType >= 1) {
      double hr = inAz * DEG_TO_RAD;
      double dr = inAlt * DEG_TO_RAD;
      double lr = siteLat * DEG_TO_RAD;
      double sa = sin(dr) * sin(lr) + cos(dr) * cos(lr) * cos(hr);
      targetAlt = asin(constrain(sa, -1.0, 1.0)) * RAD_TO_DEG;
    }
    if (targetAlt < ALT_MIN - 0.01 || (mountType == 0 && targetAlt > ALT_MAX + 0.01)) {
      limitHit=true; out.print(F("1Below horizon#")); return;
    }
    out.write('0');
    if(slewToAA(inAlt, inAz)){
      long rs, ds; aa2rd(inAlt, inAz, &rs, &ds);
      trkRA  = rs/3600.0; trkDec = ds/3600.0; parked = false;
    }
    return;
  }

  if(c1=='M'){
    if(c2=='D'){
      enableMotors(false);
      out.write('1'); return;
    }
    if(c2=='E'){
      enableMotors(true);
      out.write('1'); return;
    }
    if(c2=='g' && ci>=4){
      if (alarmActive) return;
      char dir=cmd[3]; unsigned long ms=0;
      for(uint8_t i=4;i<ci;i++) if(cmd[i]>='0'&&cmd[i]<='9') ms=ms*10+(cmd[i]-'0');
      if(ms>5000)ms=5000; if(ms==0)return;
      enableMotors(true); guiding=true;
      unsigned long gDelay=STEP_DELAY_SLOW/2;
      unsigned long steps=(ms*1000UL)/gDelay; if(steps==0)steps=1;
      switch(dir){
        case 'n': {
          long maxAltPos = (long)(ALT_MAX * ALT_PPD);
          if(altPos + (long)steps > maxAltPos) {
            long room = maxAltPos - altPos;
            steps = (room > 0) ? (unsigned long)room : 0;
          }
          if(steps == 0) { guiding=false; return; }
          digitalWrite(ALT_DIR, altReversed ? LOW : HIGH);
          for(unsigned long i=0;i<steps;i++){stepPulse(ALT_STEP);delayMicroseconds(gDelay);}
          altPos+=steps; break;
        }
        case 's': {
          long minAltPos = (long)(ALT_MIN * ALT_PPD);
          if(altPos - (long)steps < minAltPos) {
            long room = altPos - minAltPos;
            steps = (room > 0) ? (unsigned long)room : 0;
          }
          if(steps == 0) { guiding=false; return; }
          digitalWrite(ALT_DIR, altReversed ? HIGH : LOW);
          for(unsigned long i=0;i<steps;i++){stepPulse(ALT_STEP);delayMicroseconds(gDelay);}
          altPos-=steps; break;
        }
        case 'e': digitalWrite(AZ_DIR, azReversed ? HIGH : LOW);
          for(unsigned long i=0;i<steps;i++){stepPulse(AZ_STEP);delayMicroseconds(gDelay);}
          azPos-=steps; break;
        case 'w': digitalWrite(AZ_DIR, azReversed ? LOW : HIGH);
          for(unsigned long i=0;i<steps;i++){stepPulse(AZ_STEP);delayMicroseconds(gDelay);}
          azPos+=steps; break;
      }
      guiding=false; updatePos(); 
      if (tracking) force_tracking_rebase = true;
      return;
    }
    if (alarmActive) return;
    enableMotors(true); parked=false;
    switch(c2){
      case 'n':altMove= 1; break; case 's':altMove=-1; break;
      case 'e':azMove =-1; break; case 'w':azMove = 1; break;
    }
    return;
  }

  if(c1=='Q'){
    if(c2=='n'||c2=='s')altMove=0;
    else if(c2=='e'||c2=='w')azMove=0;
    else { azMove=0; altMove=0; }
    return;
  }

  if(c1=='C'&&c2=='M'){
    if(!timeSet) { out.print(F("Time not set#")); return; }
    double ra_h=inRA/3600.0, dec_d=inDEC/3600.0;
    rd2aa(ra_h,dec_d,&currAlt,&currAz);
    azPos=(long)(currAz*AZ_PPD); altPos=(long)(currAlt*ALT_PPD);
    currRA=inRA; currDEC=inDEC;
    trkRA=ra_h; trkDec=dec_d; 
    synced=true; updatePos();
    if (tracking) force_tracking_rebase = true;
    saveStateToEEPROM();
    out.print(F("Synced#")); return;
  }
  if(c1=='C'&&c2=='S'){
    if(!timeSet) { out.print(F("N/A#")); return; }
    double ra_h=inRA/3600.0, dec_d=inDEC/3600.0;
    rd2aa(ra_h,dec_d,&currAlt,&currAz);
    azPos=(long)(currAz*AZ_PPD); altPos=(long)(currAlt*ALT_PPD);
    currRA=inRA; currDEC=inDEC;
    trkRA=ra_h; trkDec=dec_d; 
    synced=true; updatePos();
    saveStateToEEPROM();
    out.print(F("N/A#")); return;
  }

  
  // Commands for Derotator and Focus
  if(c1=='X'&&c2=='D'){
    if(c3=='e') { derotEnabled=(cmd[4]=='1'); saveStateToEEPROM(); out.write('1'); return; }
    if(c3=='p') { derotPPD=atof(cmd+4); saveStateToEEPROM(); out.write('1'); return; }
    if(c3=='a') { derotTarget=atof(cmd+4); out.write('1'); return; }
  }
  if(c1=='X'&&c2=='F'){
    if(c3=='e') { focusEnabled=(cmd[4]=='1'); saveStateToEEPROM(); out.write('1'); return; }
    if(c3=='s') { focusSpeed=1000; out.write('1'); return; } // Slow
    if(c3=='f') { focusSpeed=200; out.write('1'); return; } // Fast
    if(c3=='+') { focusMove=1; digitalWrite(FOCUS_EN,LOW); out.write('1'); return; }
    if(c3=='-') { focusMove=-1; digitalWrite(FOCUS_EN,LOW); out.write('1'); return; }
    if(c3=='Q') { focusMove=0; digitalWrite(FOCUS_EN,HIGH); out.write('1'); return; }
  }
  
  if(c1=='D'){ if(slewing)out.write(127); out.write('#'); return; }

  if(c1=='T'&&c2=='e'){
    tracking=true; parked=false; enableMotors(true);
    if (trkRA == 0.0 && trkDec == 0.0) {
      trkRA = (double)currRA / 3600.0;
      trkDec = (double)currDEC / 3600.0;
    }
    out.write('1'); return;
  }
  if(c1=='T'&&c2=='d'){ tracking=false; out.write('1'); return; }
  if(c1=='T'&&c2=='Q'){ trackRate=0; out.write('1'); return; }
  if(c1=='T'&&c2=='L'){ trackRate=1; out.write('1'); return; }
  if(c1=='T'&&c2=='S'){ trackRate=2; out.write('1'); return; }
  if(c1=='T'&&(c2=='R'||c2=='K'||c2=='r'||c2=='n'||c2=='+'||c2=='-')){ out.write('1'); return; }
  if(c1=='A'&&c2=='P'){
    tracking=true; parked=false; enableMotors(true);
    if (trkRA == 0.0 && trkDec == 0.0) {
      trkRA = (double)currRA / 3600.0;
      trkDec = (double)currDEC / 3600.0;
    }
    saveStateToEEPROM(); return;
  }
  if(c1=='A'&&c2=='L'){ tracking=false; saveStateToEEPROM(); return; }

  if(c1=='R'){
    switch(c2){
      case 'G':slowSpeed=2;break; case 'C':slowSpeed=4;break;
      case 'M':slowSpeed=8;break; case 'S':slowSpeed=16;break;
      default:
        if(c2>='1'&&c2<='9') slowSpeed=2*(c2-'0');
        break;
    }
    return;
  }

  if(c1=='B' && (c2=='V'||c2=='v')){
    if(c2=='v'){
      out.print((int)(maxSlewRate*10)); out.write('#'); return;
    }
    uint8_t i = 3;
    while(i<ci && (cmd[i]==' '||cmd[i]=='\t')) i++;
    long n = 0; bool hasNum = false;
    while(i<ci && cmd[i]>='0' && cmd[i]<='9'){ n = n*10 + (cmd[i]-'0'); i++; hasNum=true; }
    if(!hasNum){ out.write('0'); return; }
    double rate = n / 10.0;
    if(rate < 0.5) rate = 0.5;
    if(rate > 25.0) rate = 25.0;
    maxSlewRate = rate;
    double d = 1.0e6 / (AZ_PPD * rate);
    if(d < (double)STEP_DELAY_FAST) d = STEP_DELAY_FAST;
    if(d > (double)MAX_DELAY)       d = MAX_DELAY;
    stepDelaySlew = (unsigned long)d;
    saveStateToEEPROM(); 
    out.print(F("1#")); return;
  }
  
  if(c1=='B' && c2=='b'){
    if(ci>=4) {
      if(cmd[3] == '0') { buzzerEnabled = false; saveStateToEEPROM(); }
      else if(cmd[3] == '1') { buzzerEnabled = true; saveStateToEEPROM(); }
      else if(cmd[3] == 'p') {
        if(buzzerEnabled) {
          tone(BUZZER_PIN, BUZZ_FREQ);
          delay(80);
          noTone(BUZZER_PIN);
          digitalWrite(BUZZER_PIN, LOW);
        }
      }
    }
    out.write(buzzerEnabled ? '1' : '0'); 
    out.write('#');
    return;
  }
  
  if(c1=='B' && c2=='M'){
    if(ci>=4) {
      if(c3=='a') mountType = 0;
      else if(c3=='e') mountType = 1;
      else if(c3=='g') mountType = 2; 
      saveStateToEEPROM();
      out.print(F("1#")); return;
    } else {
      out.print(mountType); out.write('#'); return;
    }
  }
  
  if(c1=='B' && c2=='G'){
    if(ci>=5) {
      double ratio = atof(cmd+4);
      if(ratio > 1.0) {
        if(c3=='a') gearRatioAZ = ratio;
        else if(c3=='e') gearRatioALT = ratio;
        recalculatePPD();
        saveStateToEEPROM();
      }
      out.print(F("1#")); return;
    } else if (ci==4) {
      if(c3=='a') out.print(gearRatioAZ);
      else if(c3=='e') out.print(gearRatioALT);
      out.write('#'); return;
    }
  }
  
  if(c1=='B' && c2=='R'){
    if(ci>=5) {
      bool rev = (cmd[4]=='1');
      if(c3=='a') azReversed = rev;
      else if(c3=='e') altReversed = rev;
      saveStateToEEPROM();
      out.print(F("1#")); return;
    } else {
      if(c3=='a') out.print(azReversed ? F("1#") : F("0#"));
      else if(c3=='e') out.print(altReversed ? F("1#") : F("0#"));
      return;
    }
  }
  
  if(c1=='b' && c2=='g') {
    if(ci >= 4) {
      if(cmd[3] == '0') { gpsEnabled = false; gpsSearchStart = 0; saveStateToEEPROM(); }
      else if(cmd[3] == '1') { gpsEnabled = true; gpsSearchStart = 0; gpsHasFixedOnce = false; saveStateToEEPROM(); }
    }
    out.write(gpsEnabled ? '1' : '0');
    out.write('#');
    return;
  }

  
  if(c1=='B' && c2=='S'){
    if(ci>=5) {
      long val = atol(cmd+4);
      if(val > 0) {
        if(c3=='p') motorStepsPerRev = val;
        else if(c3=='m') microstep = (uint16_t)val;
        recalculatePPD();
        saveStateToEEPROM();
      }
    }
    out.print(F("1#")); return;
  }

  if(c1=='B' && c2=='P'){
    double val = atof(cmd+4);
    if(c3=='a') parkAlt = val;
    if(c3=='z') parkAz = val;
    saveStateToEEPROM();
    out.print(F("1#")); return;
  }

  if(c1=='h'&&c2=='P'){
    if (slewing) { out.write('0'); return; }
    out.write('1'); 
    tracking=false;
    if (!alarmActive) {
      double pAlt = parkAlt;
      double pAz = parkAz;
      long pRA, pDEC;
      aa2rd(pAlt, pAz, &pRA, &pDEC);
      inRA = pRA;
      inDEC = pDEC;
      slewToAA(pAlt, pAz);
    }
    parked=true;
    saveStateToEEPROM();
    return;
  }
  if(c1=='h'&&c2=='R'){
    if (alarmActive) { out.write('0'); return; }
    parked=false; enableMotors(true); saveStateToEEPROM(); out.write('1'); return;
  }
  if(c1=='P'&&c2=='O'){
    if (alarmActive) { out.write('0'); return; }
    parked=false; enableMotors(true); saveStateToEEPROM(); out.write('1'); return;
  }
  if(c1=='h'&&c2=='Q'){ out.write(parked?'1':'0'); return; }
  if(c1=='h'&&c2=='C'){
    if (slewing) { out.write('0'); return; }
    out.write('1'); 
    double pAlt = (mountType >= 1) ? 90.0 : 0.0;
    double pAz = 0.0;
    long pRA, pDEC;
    aa2rd(pAlt, pAz, &pRA, &pDEC);
    inRA = pRA;
    inDEC = pDEC;
    slewToAA(pAlt, pAz); atHome=true;
    saveStateToEEPROM();
    return;
  }
  if(c1=='h'&&c2=='F'){ out.write('1'); return; }

  if(c1=='S' && (c2=='t' || c2=='g') && ci>=6){
    uint8_t i=3; int8_t sg=1;
    while(i<ci && cmd[i]==' ') i++;
    if(i<ci && cmd[i]=='+') { sg=1; i++; }
    else if(i<ci && cmd[i]=='-') { sg=-1; i++; }
    while(i<ci && cmd[i]==' ') i++;
    int d=0, m=0, s=0;
    while(i<ci && cmd[i]>='0' && cmd[i]<='9'){ d = d*10 + (cmd[i]-'0'); i++; }
    if(i<ci && (cmd[i]=='*' || cmd[i]==':' || (unsigned char)cmd[i]==0xDF || cmd[i]=='\xDF' || cmd[i]==' ')){
      i++;
      while(i<ci && cmd[i]>='0' && cmd[i]<='9'){ m = m*10 + (cmd[i]-'0'); i++; }
      if(i<ci && (cmd[i]==':'||cmd[i]=='\''||cmd[i]=='*')){
        i++;
        while(i<ci && cmd[i]>='0' && cmd[i]<='9'){ s = s*10 + (cmd[i]-'0'); i++; }
      }
    }
    double val = sg * (d + m/60.0 + s/3600.0);
    if(c2=='t') siteLat = val;
    else {
      siteLon = -val;
      while(siteLon <= -180.0) siteLon += 360.0;
      while(siteLon >   180.0) siteLon -= 360.0;
    }
    saveStateToEEPROM(); 
    out.write('1'); return;
  }
  if(c1=='S'&&c2=='G' && ci>=4){
    utcOff=atof(cmd+3); out.write('1'); return;
  }
  if(c1=='S'&&c2=='L' && ci>=11){
    dt_h =(cmd[3]-'0')*10+(cmd[4]-'0');
    dt_mi=(cmd[6]-'0')*10+(cmd[7]-'0');
    dt_s =(cmd[9]-'0')*10+(cmd[10]-'0');
    lastClkMs=millis();
    timeSet = true;
    out.write('1'); return;
  }
  if(c1=='S'&&c2=='C' && ci>=11){
    dt_m=(cmd[3]-'0')*10+(cmd[4]-'0');
    dt_d=(cmd[6]-'0')*10+(cmd[7]-'0');
    dt_y=2000+(cmd[9]-'0')*10+(cmd[10]-'0');
    timeSet = true;
    out.print(F("1Updating#                              #")); return;
  }
  if(c1=='S'&&c2=='X'){ out.write('1'); return; }
  if(c1=='S'&&(c2=='h'||c2=='o')){ out.write('1'); return; }
  if(c1=='S'&&(c2=='M'||c2=='N'||c2=='O'||c2=='P')){ out.write('1'); return; }
  if(c1=='S'&&c2=='B'){ out.write('0'); return; }

  if(c1=='A'&&c2=='?'){ out.print(F("300#")); return; }
  if(c1=='A'&&((c2>='0'&&c2<='9')||c2=='W'||c2=='+'||c2=='-')){
    out.write('1'); return;
  }

  if(c1=='F' || c1=='f'){ out.print(F("0#")); return; }
  if(c1=='$'||c1=='%'){
    if(c2=='B'){
      bool isSet=false;
      for(uint8_t i=3;i<ci;i++){ if(cmd[i]==','){isSet=true;break;} }
      if(isSet) out.write('1');
      else out.print(F("0#"));
      return;
    }
    out.print(F("0#")); return;
  }
  if(c1=='B'&&(c2=='+'||c2=='-')){ return; }
  if(c1=='U'&&ci==2){ return; }

  if(c1>='0'&&c1<='9'){ out.write('1'); return; }

  out.print(F("0#"));
}

// ======================== BUZZER ===========================

#define NOTE_C5  523
#define NOTE_E5  659
#define NOTE_G5  784
#define NOTE_C6  1047

void playStartupMelody() {
  if(!buzzerEnabled) return;
  tone(BUZZER_PIN, NOTE_C5); delay(150);
  tone(BUZZER_PIN, NOTE_E5); delay(150);
  tone(BUZZER_PIN, NOTE_G5); delay(150);
  tone(BUZZER_PIN, NOTE_C6); delay(300);
  noTone(BUZZER_PIN);
}

void playArrivalMelody() {
  if(!buzzerEnabled) return;
  tone(BUZZER_PIN, NOTE_G5); delay(150);
  tone(BUZZER_PIN, NOTE_C6); delay(300);
  noTone(BUZZER_PIN);
}

static bool firstCmdReceived  = false;
static bool connectBeepActive = false;
static uint8_t connectBeepStep = 0;
static unsigned long connectBeepNext = 0;

static bool slewBuzzActive = false;
static bool slewBuzzState  = false;
static unsigned long slewBuzzNext = 0;

void triggerConnectBeep(){
  if(!buzzerEnabled) return;
  connectBeepActive = true;
  connectBeepStep   = 0;
  connectBeepNext   = millis();
}

static bool gpsFixBeepActive = false;
static uint8_t gpsFixBeepStep = 0;
static unsigned long gpsFixBeepNext = 0;

void triggerGpsFixBeep(){
  if (!buzzerEnabled) return;
  gpsFixBeepActive = true;
  gpsFixBeepStep   = 0;
  gpsFixBeepNext   = millis();
}

void updateBuzzer(){
  unsigned long now = millis();

  static bool alarmBuzzActive = false;
  static bool alarmBuzzState = false;
  static unsigned long alarmBuzzNext = 0;

  if (alarmActive && buzzerEnabled) {
    if (!alarmBuzzActive) {
      alarmBuzzActive = true;
      alarmBuzzState = true;
      alarmBuzzNext = now + 150;
      tone(BUZZER_PIN, 1500);
    } else if (now >= alarmBuzzNext) {
      if (alarmBuzzState) {
        noTone(BUZZER_PIN);
        digitalWrite(BUZZER_PIN, LOW);
        alarmBuzzState = false;
        alarmBuzzNext = now + 150;
      } else {
        tone(BUZZER_PIN, 1500);
        alarmBuzzState = true;
        alarmBuzzNext = now + 150;
      }
    }
    return;
  } else if (alarmBuzzActive) {
    noTone(BUZZER_PIN);
    digitalWrite(BUZZER_PIN, LOW);
    alarmBuzzActive = false;
  }
  
  static bool limitBuzzActive = false;
  bool tryingForbiddenMove = false;
  if (mountType == 0 && altMove != 0) {
    double nA = (double)(altPos + altMove)/ALT_PPD;
    if (nA < ALT_MIN || nA > ALT_MAX) {
      tryingForbiddenMove = true;
    }
  }

  if (tryingForbiddenMove && buzzerEnabled) {
    if (!limitBuzzActive) {
      tone(BUZZER_PIN, BUZZ_FREQ);
      limitBuzzActive = true;
    }
    return;
  } else if (limitBuzzActive) {
    noTone(BUZZER_PIN);
    digitalWrite(BUZZER_PIN, LOW);
    limitBuzzActive = false;
  }

  if(connectBeepActive){
    if(now < connectBeepNext) return;
    switch(connectBeepStep){
      case 0: case 2: case 4:
        tone(BUZZER_PIN, BUZZ_FREQ);
        connectBeepNext = now + 80; break;
      case 1: case 3:
        noTone(BUZZER_PIN);
        connectBeepNext = now + 120; break;
      case 5:
        noTone(BUZZER_PIN);
        digitalWrite(BUZZER_PIN, LOW);
        connectBeepActive = false; return;
    }
    connectBeepStep++;
    return;
  }

  if(gpsFixBeepActive){
    if(now < gpsFixBeepNext) return;
    switch(gpsFixBeepStep){
      case 0:
        tone(BUZZER_PIN, 261); gpsFixBeepNext = now + 200; break; // C4
      case 1:
        tone(BUZZER_PIN, 329); gpsFixBeepNext = now + 200; break; // E4
      case 2:
        tone(BUZZER_PIN, 392); gpsFixBeepNext = now + 400; break; // G4
      case 3:
        noTone(BUZZER_PIN);
        digitalWrite(BUZZER_PIN, LOW);
        gpsFixBeepActive = false; return;
    }
    gpsFixBeepStep++;
    return;
  }

  static unsigned long slowMoveStartMs = 0;
  bool currentlyMovingSlow = (azMove != 0 || altMove != 0);
  if (currentlyMovingSlow) {
    if (slowMoveStartMs == 0) {
      slowMoveStartMs = now;
    }
  } else {
    slowMoveStartMs = 0;
  }

  bool shouldBuzz = (slewing && buzzerEnabled) || 
                    (currentlyMovingSlow && (now - slowMoveStartMs >= 2000) && buzzerEnabled);

  if(shouldBuzz && !slewBuzzActive){
    slewBuzzActive = true; slewBuzzState  = true;
    slewBuzzNext   = now + 80;
    tone(BUZZER_PIN, BUZZ_FREQ); return;
  }
  if(!shouldBuzz && slewBuzzActive){
    slewBuzzActive = false; slewBuzzState  = false;
    noTone(BUZZER_PIN);
    digitalWrite(BUZZER_PIN, LOW); return;
  }
  if(!slewBuzzActive) return;
  if(now < slewBuzzNext) return;
  if(slewBuzzState){
    noTone(BUZZER_PIN);
    slewBuzzState = false; slewBuzzNext  = now + 920;
  } else {
    tone(BUZZER_PIN, BUZZ_FREQ);
    slewBuzzState = true;  slewBuzzNext  = now + 80;
  }
}

// ======================== SETUP/LOOP =======================

void setup() {
  Serial.begin(38400);                    
  Serial3.begin(38400);                   
  Serial2.begin(9600);   // [ADD] Initialisation du port GPS

  pinMode(AZ_STEP,OUTPUT); pinMode(AZ_DIR,OUTPUT); pinMode(AZ_EN,OUTPUT);
  pinMode(ALT_STEP,OUTPUT);pinMode(ALT_DIR,OUTPUT);pinMode(ALT_EN,OUTPUT);
  pinMode(DEROT_STEP,OUTPUT); pinMode(DEROT_DIR,OUTPUT); pinMode(DEROT_EN,OUTPUT);
  pinMode(FOCUS_STEP,OUTPUT); pinMode(FOCUS_DIR,OUTPUT); pinMode(FOCUS_EN,OUTPUT);
  digitalWrite(DEROT_EN, HIGH);
  digitalWrite(FOCUS_EN, HIGH);
  digitalWrite(AZ_STEP,LOW); digitalWrite(ALT_STEP,LOW);
  enableMotors(false);
  pinMode(LED_BUILTIN,OUTPUT);
  digitalWrite(LED_BUILTIN,HIGH); delay(300); digitalWrite(LED_BUILTIN,LOW);
  pinMode(BUZZER_PIN,OUTPUT);
  digitalWrite(BUZZER_PIN,LOW);
  azPos=0; altPos=0;
  loadStateFromEEPROM();
  if (!parked) {
    enableMotors(true);
  }
  lastClkMs=millis(); lastTrkMs=millis();
  updatePos();
  Serial.println(F("GotoAndrivet v9.2 - OnStep ready"));
  Serial.println(F("Site: Default (0.0000N / 0.0000E)"));
  Serial.println(F("USB:38400 + DIN4(Serial3):38400"));
  Serial3.println(F("GotoAndrivet Mega v9.2 ready"));
  
  noInterrupts();
  TCCR1A = 0;
  TCCR1B = 0;
  TCNT1  = 0;
  OCR1A = 199; 
  TCCR1B |= (1 << WGM12); 
  TCCR1B |= (1 << CS11);  
  TIMSK1 |= (1 << OCIE1A); 
  interrupts();
  
  playStartupMelody();
  delay(100);
  while(Serial.available() > 0) Serial.read();
  while(Serial3.available() > 0) Serial3.read();
}

static void serveStream(Stream& in, Print& out, char* buf, uint8_t& bi) {
  while(in.available()){
    char c=in.read();
    if(c==' '||c=='\r') continue;
    if(c==6){
      if (mountType == 2) out.write('G');
      else if (mountType == 1) out.write('P');
      else out.write('A');
      if(!firstCmdReceived){ firstCmdReceived=true; triggerConnectBeep(); }
      continue;
    }
    if(c=='#'||c=='\n'){
      buf[bi]='\0';
      if(bi>0 && buf[0]==':'){
        if(!firstCmdReceived){ firstCmdReceived=true; triggerConnectBeep(); }
        processCmd(buf, bi, out);
      }
      bi=0;
    } else {
      if(bi<CMD_MAX-1) buf[bi++]=c; else bi=0;
    }
  }
}

void loop() {
  clk();
  handleGPS(); // [ADD] On ecoute le GPS et on met a l'heure

  // Mouvement lent (boutons E/W/N/S)
  if(!slewing && !parked){
    unsigned long now=micros();
    unsigned long nowMs=millis();
    static int8_t azActiveMove = 0;
    static float azFrequency = 0.0;
    float f_min = 1.0e6 / MAX_DELAY;
    
    if (azMove != 0) {
      azActiveMove = azMove;
      azFrequency = f_min;
    } else {
      azActiveMove = 0;
      azFrequency = 0.0;
    }
    
    static int8_t altActiveMove = 0;
    static float altFrequency = 0.0;
    
    if (altMove != 0) {
      altActiveMove = altMove;
      altFrequency = f_min;
    } else {
      altActiveMove = 0;
      altFrequency = 0.0;
    }
    
    
    if (azActiveMove != 0 || altActiveMove != 0) {
        unsigned long delayAz = azActiveMove ? (unsigned long)(1.0e6 / azFrequency) : 0xFFFFFFFF;
        unsigned long delayAlt = altActiveMove ? (unsigned long)(1.0e6 / altFrequency) : 0xFFFFFFFF;
        if (delayAz < 5) delayAz = 5;
        if (delayAlt < 5) delayAlt = 5;
        
        while (true) {
            unsigned long nowUs = micros();
            bool azReady = azActiveMove && (nowUs - lastSlowAz >= delayAz);
            bool altReady = altActiveMove && (nowUs - lastSlowAlt >= delayAlt);
            
            if (azReady || altReady) {
                if (azReady) {
                    lastSlowAz = nowUs;
                    digitalWrite(AZ_DIR, (azActiveMove>0) ^ azReversed ? HIGH : LOW);
                    stepPulse(AZ_STEP); azPos+=azActiveMove;
                }
                if (altReady) {
                    lastSlowAlt = nowUs;
                    double nA=(double)(altPos+altActiveMove)/ALT_PPD;
                    bool allowed = false;
                    if (nA >= ALT_MIN && nA <= ALT_MAX) allowed = true;
                    else if (nA < ALT_MIN && altActiveMove > 0) allowed = true;
                    else if (nA > ALT_MAX && altActiveMove < 0) allowed = true;
                    
                    if(mountType >= 1 || allowed){
                        digitalWrite(ALT_DIR, (altActiveMove>0) ^ altReversed ? HIGH : LOW);
                        stepPulse(ALT_STEP); altPos+=altActiveMove;
                    } else {
                        limitHit=true;
                        altActiveMove = 0;
                        altFrequency = 0.0;
                    }
                }
                break;
            }
            if (Serial3.available() > 0 || Serial.available() > 0) {
                break;
            }
        }
    }
    
    static bool wasMovingSlow = false;
    bool currentlyMovingSlow = (azMove != 0 || altMove != 0 || azActiveMove != 0 || altActiveMove != 0);
    if (currentlyMovingSlow) {
      static unsigned long lastManualUpdMs = 0;
      if (millis() - lastManualUpdMs >= 200) {
        lastManualUpdMs = millis();
        updatePos();
      }
      wasMovingSlow = true;
    } else if (wasMovingSlow) {
      updatePos();
      if (tracking) {
        force_tracking_rebase = true;
      }
      saveStateToEEPROM();
      wasMovingSlow = false;
    }
  }

  
  doTrack();
  updateBuzzer();

  // Handle Derotator
  if(derotEnabled && mountType == 0) { // Only in Alt-Az
    long targetPos = (long)(derotTarget * derotPPD);
    long diff = targetPos - derotPos;
    if(abs(diff) > 0) {
      digitalWrite(DEROT_EN, LOW);
      digitalWrite(DEROT_DIR, diff > 0 ? HIGH : LOW);
      digitalWrite(DEROT_STEP, HIGH);
      delayMicroseconds(10);
      digitalWrite(DEROT_STEP, LOW);
      derotPos += (diff > 0 ? 1 : -1);
      delayMicroseconds(200);
    } else {
      digitalWrite(DEROT_EN, HIGH);
    }
  }

  // Handle Focus
  if(focusEnabled && focusMove != 0) {
    digitalWrite(FOCUS_DIR, focusMove > 0 ? HIGH : LOW);
    digitalWrite(FOCUS_STEP, HIGH);
    delayMicroseconds(10);
    digitalWrite(FOCUS_STEP, LOW);
    delayMicroseconds(focusSpeed);
  }

  serveStream(Serial,  Serial,  cmdUsb, ciUsb);

  serveStream(Serial3, Serial3, cmdRj,  ciRj);
}
