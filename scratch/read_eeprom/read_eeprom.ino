#include <Arduino.h>
#include <EEPROM.h>

template <typename T>
void eepromRead(int address, T& value) {
  byte* p = (byte*)(void*)&value;
  for (unsigned int i = 0; i < sizeof(value); i++) {
    p[i] = EEPROM.read(address + i);
  }
}

void setup() {
  Serial.begin(9600);
  while (!Serial);
  delay(1000);
  
  Serial.println("--- EEPROM READ ---");
  
  byte magic = EEPROM.read(0);
  byte parked = EEPROM.read(1);
  byte synced = EEPROM.read(2);
  byte tracking = EEPROM.read(19);
  
  double maxSlewRate = 0;
  uint32_t motorStepsPerRev = 0;
  uint16_t microstep = 0;
  double gearRatioAZ = 0;
  double gearRatioALT = 0;
  uint8_t mountType = 0;
  
  eepromRead(20, maxSlewRate);
  eepromRead(24, motorStepsPerRev);
  eepromRead(28, microstep);
  eepromRead(30, gearRatioAZ);
  eepromRead(34, gearRatioALT);
  mountType = EEPROM.read(38);
  
  Serial.print("Magic: 0x"); Serial.println(magic, HEX);
  Serial.print("Parked: "); Serial.println(parked);
  Serial.print("Synced: "); Serial.println(synced);
  Serial.print("Tracking: "); Serial.println(tracking);
  Serial.print("Slew Rate: "); Serial.println(maxSlewRate);
  Serial.print("Steps/Rev: "); Serial.println(motorStepsPerRev);
  Serial.print("Microstep: "); Serial.println(microstep);
  Serial.print("Gear AZ: "); Serial.println(gearRatioAZ);
  Serial.print("Gear ALT: "); Serial.println(gearRatioALT);
  Serial.print("Mount Type: "); Serial.println(mountType);
  Serial.println("--- END ---");
}

void loop() {}
