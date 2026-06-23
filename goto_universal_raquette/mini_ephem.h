#ifndef MINI_EPHEM_H
#define MINI_EPHEM_H

#include <math.h>

#define PI 3.14159265358979323846
#define RADEG (180.0/PI)
#define DEGRAD (PI/180.0)

struct PlanetObj {
    const char* name;
    double ra;  // Hours
    double dec; // Degrees
};

// Objets: 0=Soleil, 1=Lune, 2=Mercure, 3=Venus, 4=Mars, 5=Jupiter, 6=Saturne, 7=Uranus
#define SYSSOL_COUNT 8
PlanetObj sysSolObjs[SYSSOL_COUNT] = {
    {"Soleil", 0, 0}, {"Lune", 0, 0}, {"Mercure", 0, 0}, {"Venus", 0, 0},
    {"Mars", 0, 0}, {"Jupiter", 0, 0}, {"Saturne", 0, 0}, {"Uranus", 0, 0}
};

double rev(double x) { return x - floor(x/360.0)*360.0; }

double julian_date(int y, int m, int d, double ut) {
    if (m <= 2) { y -= 1; m += 12; }
    int A = y / 100;
    int B = 2 - A + (A / 4);
    return floor(365.25 * (y + 4716)) + floor(30.6001 * (m + 1)) + d + ut/24.0 + B - 1524.5;
}

// Paramètres orbitaux (simplifiés) Kepler
struct KeplerElements {
    double N_0, N_d;
    double i_0, i_d;
    double w_0, w_d;
    double a;
    double e_0, e_d;
    double M_0, M_d;
};

const KeplerElements kepler[8] = {
    // Soleil (Terre)
    {0.0, 0.0, 0.0, 0.0, 282.9404, 4.70935e-5, 1.0, 0.016709, -1.151e-9, 356.0470, 0.9856002585},
    // Lune (non utilisé ici car algorithme spécifique plus bas)
    {0,0,0,0,0,0,0,0,0,0,0},
    // Mercure
    {48.3313, 3.24587E-5, 7.0047, 5.00E-8, 29.1241, 1.01444E-5, 0.387098, 0.205635, 5.59E-9, 168.6562, 4.0923344368},
    // Vénus
    {76.6799, 2.46590E-5, 3.3946, 2.75E-8, 54.8910, 1.38374E-5, 0.723330, 0.006773, -1.302E-9, 48.0052, 1.6021302244},
    // Mars
    {49.5574, 2.11081E-5, 1.8497, -1.78E-8, 286.5016, 2.92961E-5, 1.523688, 0.093405, 2.516E-9, 18.6021, 0.5240207766},
    // Jupiter
    {100.4542, 2.76854E-5, 1.3030, -1.557E-7, 273.8777, 1.64505E-5, 5.20256, 0.048498, 4.469E-9, 19.8950, 0.0830853001},
    // Saturne
    {113.6634, 2.38980E-5, 2.4886, -1.081E-7, 339.3939, 2.97661E-5, 9.55475, 0.055546, -9.499E-9, 316.9670, 0.0334442282},
    // Uranus
    {74.0005, 1.3978E-5, 0.7733, 1.9E-8, 96.6612, 3.0565E-5, 19.18171, 0.047318, 7.45E-9, 142.5905, 0.011725806}
};

void computeSysSol(int y, int m, int d, int hr, int min, int sec) {
    double ut = hr + min/60.0 + sec/3600.0;
    double d_jd = julian_date(y, m, d, ut) - 2451543.5;
    double oblecl = 23.4393 - 3.563e-7 * d_jd;
    double sinO = sin(oblecl * DEGRAD);
    double cosO = cos(oblecl * DEGRAD);

    // 0. Terre / Soleil
    double w_s = kepler[0].w_0 + kepler[0].w_d * d_jd;
    double e_s = kepler[0].e_0 + kepler[0].e_d * d_jd;
    double M_s = rev(kepler[0].M_0 + kepler[0].M_d * d_jd);
    double E_s = M_s + e_s * RADEG * sin(M_s * DEGRAD) * (1.0 + e_s * cos(M_s * DEGRAD));
    double x_s = cos(E_s * DEGRAD) - e_s;
    double y_sun = sin(E_s * DEGRAD) * sqrt(1.0 - e_s*e_s);
    double v_s = atan2(y_sun, x_s) * RADEG;
    double lon_s = rev(v_s + w_s);
    double x_eq_s = cos(lon_s * DEGRAD);
    double y_eq_s = sin(lon_s * DEGRAD) * cosO;
    double z_eq_s = sin(lon_s * DEGRAD) * sinO;
    sysSolObjs[0].ra = rev(atan2(y_eq_s, x_eq_s) * RADEG) / 15.0;
    sysSolObjs[0].dec = atan2(z_eq_s, sqrt(x_eq_s*x_eq_s + y_eq_s*y_eq_s)) * RADEG;
    double r_sun = sqrt(x_s*x_s + y_sun*y_sun);

    // 1. Lune (formule Schlyter)
    double N = rev(125.1228 - 0.0529538083 * d_jd);
    double i = 5.1454;
    double w_m = rev(318.0634 + 0.1643573223 * d_jd);
    double a_m = 60.2666;
    double e_m = 0.054900;
    double M_m = rev(115.3654 + 13.0649929509 * d_jd);
    double E_m = M_m + e_m * RADEG * sin(M_m * DEGRAD) * (1.0 + e_m * cos(M_m * DEGRAD));
    double x_m = a_m * (cos(E_m * DEGRAD) - e_m);
    double ym_m = a_m * sqrt(1.0 - e_m*e_m) * sin(E_m * DEGRAD);
    double v_m = atan2(ym_m, x_m) * RADEG;
    double r_m = sqrt(x_m*x_m + ym_m*ym_m);
    double lon_m = rev(v_m + w_m);
    double x_ecl_m = r_m * (cos(N*DEGRAD)*cos(lon_m*DEGRAD) - sin(N*DEGRAD)*sin(lon_m*DEGRAD)*cos(i*DEGRAD));
    double y_ecl_m = r_m * (sin(N*DEGRAD)*cos(lon_m*DEGRAD) + cos(N*DEGRAD)*sin(lon_m*DEGRAD)*cos(i*DEGRAD));
    double z_ecl_m = r_m * (sin(lon_m*DEGRAD)*sin(i*DEGRAD));
    double x_eq_m = x_ecl_m;
    double y_eq_m = y_ecl_m * cosO - z_ecl_m * sinO;
    double z_eq_m = y_ecl_m * sinO + z_ecl_m * cosO;
    sysSolObjs[1].ra = rev(atan2(y_eq_m, x_eq_m) * RADEG) / 15.0;
    sysSolObjs[1].dec = atan2(z_eq_m, sqrt(x_eq_m*x_eq_m + y_eq_m*y_eq_m)) * RADEG;

    // 2 a 7. Planetes
    for(int p=2; p<8; p++) {
        double N_p = rev(kepler[p].N_0 + kepler[p].N_d * d_jd);
        double i_p = kepler[p].i_0 + kepler[p].i_d * d_jd;
        double w_p = rev(kepler[p].w_0 + kepler[p].w_d * d_jd);
        double a_p = kepler[p].a;
        double e_p = kepler[p].e_0 + kepler[p].e_d * d_jd;
        double M_p = rev(kepler[p].M_0 + kepler[p].M_d * d_jd);
        double E_p = M_p + e_p * RADEG * sin(M_p * DEGRAD) * (1.0 + e_p * cos(M_p * DEGRAD));
        double x_p = a_p * (cos(E_p * DEGRAD) - e_p);
        double y_p = a_p * sqrt(1.0 - e_p*e_p) * sin(E_p * DEGRAD);
        double r_p = sqrt(x_p*x_p + y_p*y_p);
        double v_p = atan2(y_p, x_p) * RADEG;
        double lon_p = rev(v_p + w_p);
        double x_h = r_p * (cos(N_p*DEGRAD)*cos(lon_p*DEGRAD) - sin(N_p*DEGRAD)*sin(lon_p*DEGRAD)*cos(i_p*DEGRAD));
        double y_h = r_p * (sin(N_p*DEGRAD)*cos(lon_p*DEGRAD) + cos(N_p*DEGRAD)*sin(lon_p*DEGRAD)*cos(i_p*DEGRAD));
        double z_h = r_p * (sin(lon_p*DEGRAD)*sin(i_p*DEGRAD));
        
        // Coordonnées géocentriques
        double x_g = x_h + r_sun * cos(lon_s * DEGRAD);
        double y_g = y_h + r_sun * sin(lon_s * DEGRAD);
        double z_g = z_h;
        
        // Equatoriales
        double x_eq = x_g;
        double y_eq = y_g * cosO - z_g * sinO;
        double z_eq = y_g * sinO + z_g * cosO;
        sysSolObjs[p].ra = rev(atan2(y_eq, x_eq) * RADEG) / 15.0;
        sysSolObjs[p].dec = atan2(z_eq, sqrt(x_eq*x_eq + y_eq*y_eq)) * RADEG;
    }
}

#endif
