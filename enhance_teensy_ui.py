import re

with open("goto_mega_raquette/teensy_raquette_v62/teensy_raquette_v62.ino", "r") as f:
    code = f.read()

# Replace printMain
old_printMain = """void printMain(){
    char buf[21];
    int rah=(int)m_currentRA, ram=(int)((m_currentRA-rah)*60);
    bool dneg=(m_currentDEC<0); double da=fabs(m_currentDEC);
    int dd=(int)da, dm=(int)((da-dd)*60);
    snprintf(buf,21,"R%02dh%02d D%c%02d%c%02d", rah,ram, dneg?'-':'+', dd, 0xDF, dm);
    lcdLine(0,buf);

    if(!m_online){
        lcdLine(1, "OFFLINE");
    } else if(m_isPaused){
        lcdLine(1, "* EN PAUSE *");
    } else if(m_limitHit){
        lcdLine(1, "!! LIMITE !!");
    } else {
        snprintf(buf,21,"%cMNT OK %c%s", 
                 m_isTracking?(char)CHAR_CHECK:'-',
                 (char)CHAR_UP,
                 m_isSlewing?" GOTO":"");
        lcdLine(1,buf);
    }
}"""

new_printMain = """void printMain(){
    char buf[21];
    int rah=(int)m_currentRA, ram=(int)((m_currentRA-rah)*60);
    bool dneg=(m_currentDEC<0); double da=fabs(m_currentDEC);
    int dd=(int)da, dm=(int)((da-dd)*60);
    
    snprintf(buf,21,"RA: %02dh%02dm", rah,ram);
    lcdLine(0,buf);
    snprintf(buf,21,"DE: %c%02d%c%02d'", dneg?'-':'+', dd, 0xDF, dm);
    lcdLine(1,buf);

    if(!m_online){
        lcdLine(2, isEnglish ? "STATE: OFFLINE" : "ETAT: HORS LIGNE");
        lcdLine(3, "");
    } else if(m_isPaused){
        lcdLine(2, "* EN PAUSE *");
        lcdLine(3, "");
    } else if(m_limitHit){
        lcdLine(2, "!! LIMITE !!");
        lcdLine(3, "");
    } else {
        snprintf(buf,21,"ETAT: %cMNT OK %s", 
                 m_isTracking?(char)CHAR_CHECK:'-',
                 m_isSlewing?"GOTO":"");
        lcdLine(2,buf);
        
        if (m_isSlewing) {
             double d_ra_rad = (m_currentRA - targetRA) * 15.0 * DEGRAD;
             double cos_dist = sin(m_currentDEC * DEGRAD) * sin(targetDEC * DEGRAD) + cos(m_currentDEC * DEGRAD) * cos(targetDEC * DEGRAD) * cos(d_ra_rad);
             if (cos_dist < -1.0) cos_dist = -1.0;
             if (cos_dist > 1.0) cos_dist = 1.0;
             double dist = acos(cos_dist) * RADEG;
             if (dist > 0.05) {
                 snprintf(buf,21,"Cible dist: %.1f%c", dist, 0xDF);
                 lcdLine(3,buf);
             } else {
                 lcdLine(3, "[ENT]=Menu");
             }
        } else {
             lcdLine(3, "[ENT]=Menu");
        }
    }
}"""
if old_printMain in code:
    code = code.replace(old_printMain, new_printMain)
else:
    print("Could not find printMain")

# Replace printCatSelect
old_printCatSelect = """void printCatSelect(){
    lcdLine(0, isEnglish ? "[ SELECT CATAL.]" : "[ CHOIX CATALOG]");
    char buf[21];
    snprintf(buf,21,">%s %4lu", getCatName((int)currentCat), getCatalogCount((CatID)currentCat));
    lcdLine(1,buf);
}"""
new_printCatSelect = """void printCatSelect(){
    lcdLine(0, isEnglish ? "[ SELECT CATALOG ]" : "[ CHOIX CATALOGUE ]");
    char buf[21];
    snprintf(buf,21,"> %-15s", getCatName((int)currentCat));
    lcdLine(1,buf);
    snprintf(buf,21,"  (%lu obj)", getCatalogCount((CatID)currentCat));
    lcdLine(2,buf);
    lcdLine(3, isEnglish ? "  [UP/DWN] Select" : "  [HAUT/BAS] Choisir");
}"""
if old_printCatSelect in code:
    code = code.replace(old_printCatSelect, new_printCatSelect)
else:
    print("Could not find printCatSelect")

# Replace printObjectList
old_printObjectList = """void printObjectList(){
    char buf[21];
    snprintf(buf,21,"[%s] %4luobj", getCatName((int)currentCat), getCatalogCount((CatID)currentCat));
    lcdLine(0,buf);

    uint32_t total=getCatalogCount(currentCat);
    if(total==0){ lcdLine(1," Aucun objet"); return; }

    char line[21];
    if(currentCat==CAT_BSC){
        StarObject s=getStarFromCatalog((uint32_t)objectIndex);
        char ast = isVisible(s.ra, s.dec) ? '*' : ' ';
        snprintf(line,21,">%s%c m%.1f", s.name, ast, s.mag/10.0f);
    } else if(currentCat==CAT_SYSSOL){
        char ast = isVisible(sysSolObjs[objectIndex].ra, sysSolObjs[objectIndex].dec) ? '*' : ' ';
        snprintf(line,21,">%s%c", sysSolObjs[objectIndex].name, ast);
    } else {
        DeepSkyObject o; getObj(currentCat,(uint32_t)objectIndex,o);
        char ast = isVisible(o.ra, o.dec) ? '*' : ' ';
        snprintf(line,21,">%s%d%c m%.1f", getCatPrefix(currentCat), o.id, ast, o.mag/10.0f);
    }
    lcdLine(1,line);
}"""

new_printObjectList = """void printObjectList(){
    char buf[21];
    snprintf(buf,21,"[%s] %lu obj", getCatName((int)currentCat), getCatalogCount((CatID)currentCat));
    lcdLine(0,buf);

    uint32_t total=getCatalogCount(currentCat);
    if(total==0){ 
        lcdLine(1," Aucun objet"); 
        lcdLine(2,"");
        lcdLine(3,"");
        return; 
    }

    char line[21];
    float mag = 0;
    double ra = 0, dec = 0;
    
    if(currentCat==CAT_BSC){
        StarObject s=getStarFromCatalog((uint32_t)objectIndex);
        char ast = isVisible(s.ra, s.dec) ? '*' : ' ';
        snprintf(line,21,"> %s%c", s.name, ast);
        mag = s.mag/10.0f;
        ra = s.ra; dec = s.dec;
    } else if(currentCat==CAT_SYSSOL){
        char ast = isVisible(sysSolObjs[objectIndex].ra, sysSolObjs[objectIndex].dec) ? '*' : ' ';
        snprintf(line,21,"> %s%c", sysSolObjs[objectIndex].name, ast);
        mag = 0; // Not available
        ra = sysSolObjs[objectIndex].ra; dec = sysSolObjs[objectIndex].dec;
    } else {
        DeepSkyObject o; getObj(currentCat,(uint32_t)objectIndex,o);
        char ast = isVisible(o.ra, o.dec) ? '*' : ' ';
        snprintf(line,21,"> %s%d%c", getCatPrefix(currentCat), o.id, ast);
        mag = o.mag/10.0f;
        ra = o.ra; dec = o.dec;
    }
    lcdLine(1,line);
    
    if (currentCat!=CAT_SYSSOL) {
        snprintf(buf,21,"  Mag: %.1f", mag);
        lcdLine(2,buf);
    } else {
        lcdLine(2,"");
    }
    
    int rah=(int)ra;
    int ram=(int)((ra-rah)*60);
    int dd=(int)fabs(dec);
    snprintf(buf,21,"  %02dh%02d %c%02d%c", rah,ram, dec<0?'-':'+', dd, 0xDF);
    lcdLine(3,buf);
}"""
if old_printObjectList in code:
    code = code.replace(old_printObjectList, new_printObjectList)
else:
    print("Could not find printObjectList")

# Replace printObjectInfo
old_printObjectInfo = """void printObjectInfo(){
    char buf[21];
    if (currentCat == CAT_SYSSOL) {
        char ast = isVisible(sysSolObjs[objectIndex].ra, sysSolObjs[objectIndex].dec) ? '*' : ' ';
        snprintf(buf,21,">%s%c",sysSolObjs[objectIndex].name, ast);
    } else if(selectedIsStar){
        char ast = isVisible(selectedStar.ra, selectedStar.dec) ? '*' : ' ';
        snprintf(buf,21,">%s%c",selectedStar.name, ast);
    } else {
        char ast = isVisible(selectedObj.ra, selectedObj.dec) ? '*' : ' ';
        snprintf(buf,21,">%s%d%c %s", getCatPrefix(currentCat), selectedObj.id, ast, getTypeName(selectedObj.type));
    }
    lcdLine(0,buf);
    lcdLine(1, "E=GOTO  >=SYNC");
}"""
new_printObjectInfo = """void printObjectInfo(){
    char buf[21];
    double ra = 0, dec = 0;
    
    if (currentCat == CAT_SYSSOL) {
        char ast = isVisible(sysSolObjs[objectIndex].ra, sysSolObjs[objectIndex].dec) ? '*' : ' ';
        snprintf(buf,21,"OBJET: %s%c",sysSolObjs[objectIndex].name, ast);
        ra = sysSolObjs[objectIndex].ra; dec = sysSolObjs[objectIndex].dec;
    } else if(selectedIsStar){
        char ast = isVisible(selectedStar.ra, selectedStar.dec) ? '*' : ' ';
        snprintf(buf,21,"OBJET: %s%c",selectedStar.name, ast);
        ra = selectedStar.ra; dec = selectedStar.dec;
    } else {
        char ast = isVisible(selectedObj.ra, selectedObj.dec) ? '*' : ' ';
        snprintf(buf,21,"OBJET: %s%d%c", getCatPrefix(currentCat), selectedObj.id, ast);
        ra = selectedObj.ra; dec = selectedObj.dec;
    }
    lcdLine(0,buf);
    
    int rah=(int)ra, ram=(int)((ra-rah)*60);
    snprintf(buf,21,"RA: %02dh%02dm", rah,ram);
    lcdLine(1,buf);
    
    int dd=(int)fabs(dec), dm=(int)((fabs(dec)-dd)*60);
    snprintf(buf,21,"DE: %c%02d%c%02d'", dec<0?'-':'+', dd, 0xDF, dm);
    lcdLine(2,buf);
    
    lcdLine(3, "[ENT]=GOTO [>]=SYNC");
}"""
if old_printObjectInfo in code:
    code = code.replace(old_printObjectInfo, new_printObjectInfo)
else:
    print("Could not find printObjectInfo")
    
# Replace printSlewing
old_printSlewing = """void printSlewing(){
    char anim_chars[] = {'*', '+', 'x', '+'};
    char anim = anim_chars[(millis() / 250) % 4];
    char b0[21];
    
    if (isParkingWorkflow) {
        snprintf(b0, 21, "PARKING %c", anim);
        lcdLine(0, b0);
        lcdLine(1, isEnglish ? " Please wait... " : " Patientez...   ");
    } else {
        snprintf(b0, 21, isEnglish ? "SLEWING %c" : "GOTO %c", anim);
        lcdLine(0, b0);
        
        double ra  = selectedIsStar?selectedStar.ra  :selectedObj.ra;
        double dec = selectedIsStar?selectedStar.dec :selectedObj.dec;
        double c_dec_rad = m_currentDEC * DEGRAD;
        double t_dec_rad = dec * DEGRAD;
        double d_ra_rad = (m_currentRA - ra) * 15.0 * DEGRAD;
        double cos_dist = sin(c_dec_rad) * sin(t_dec_rad) + cos(c_dec_rad) * cos(t_dec_rad) * cos(d_ra_rad);
        if (cos_dist < -1.0) cos_dist = -1.0;
        if (cos_dist > 1.0) cos_dist = 1.0;
        double dist = acos(cos_dist) * RADEG;
        double speed = m_slewSpeed;
        if (speed < 0.05) speed = 3.0;
        int eta = (int)(dist / speed);

        char buf[21];
        snprintf(buf, 21, "E:%ds D:%.1f%c", eta, dist, 0xDF);
        lcdLine(1, buf);
    }
}"""
new_printSlewing = """void printSlewing(){
    char anim_chars[] = {'*', '+', 'x', '+'};
    char anim = anim_chars[(millis() / 250) % 4];
    char b0[21];
    
    if (isParkingWorkflow) {
        snprintf(b0, 21, isEnglish ? "PARKING IN PROG %c" : "PARKING EN COURS %c", anim);
        lcdLine(0, b0);
        lcdLine(1, isEnglish ? "Motors running..." : "Moteurs en route...");
        lcdLine(2, isEnglish ? "Please wait" : "Veuillez patienter");
        lcdLine(3, isEnglish ? "[<] Cancel" : "[<] Annuler");
    } else {
        snprintf(b0, 21, isEnglish ? "SLEWING TO TGT %c" : "GOTO EN COURS... %c", anim);
        lcdLine(0, b0);
        
        double ra  = selectedIsStar?selectedStar.ra  :selectedObj.ra;
        double dec = selectedIsStar?selectedStar.dec :selectedObj.dec;
        double c_dec_rad = m_currentDEC * DEGRAD;
        double t_dec_rad = dec * DEGRAD;
        double d_ra_rad = (m_currentRA - ra) * 15.0 * DEGRAD;
        double cos_dist = sin(c_dec_rad) * sin(t_dec_rad) + cos(c_dec_rad) * cos(t_dec_rad) * cos(d_ra_rad);
        if (cos_dist < -1.0) cos_dist = -1.0;
        if (cos_dist > 1.0) cos_dist = 1.0;
        double dist = acos(cos_dist) * RADEG;
        double speed = m_slewSpeed;
        if (speed < 0.05) speed = 3.0;
        int eta = (int)(dist / speed);

        char buf[21];
        snprintf(buf, 21, "Dist restante: %.1f%c", dist, 0xDF);
        lcdLine(1, buf);
        snprintf(buf, 21, "Temps estime:  %ds", eta);
        lcdLine(2, buf);
        lcdLine(3, isEnglish ? "[<] Cancel GOTO" : "[<] Annuler GOTO");
    }
}"""
if old_printSlewing in code:
    code = code.replace(old_printSlewing, new_printSlewing)
else:
    print("Could not find printSlewing")

with open("goto_mega_raquette/teensy_raquette_v62/teensy_raquette_v62.ino", "w") as f:
    f.write(code)

print("Updated Teensy UI for 2004 LCD")
