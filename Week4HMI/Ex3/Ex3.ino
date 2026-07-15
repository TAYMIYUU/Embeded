#include <WiFi.h> 
#include <ModbusIP_ESP8266.h>  
 // modbus-esp8266 by Andre and emelianov, V4.1.0 
#include <TM1638plus.h>        
 // TM1638plus by Gavin Lyons, V2.2.0 
 
const char* ssid = "wifi_2BEEB8"; 
const char* password = ""; 
 
ModbusIP mb; 
TM1638plus tm(25, 33, 32, false);  // STB, CLK, DIO 
 
const int NUM_COILS = 8; 
uint8_t lastButtons = 0; 
 
unsigned long lastWifiCheck = 0; 
const unsigned long WIFI_CHECK_INTERVAL = 5000; 
 
void connectWiFi() { 
  Serial.print("Connecting to WiFi"); 
  tm.displayText("WIFI"); 
  WiFi.begin(ssid, password); 
  unsigned long start = millis(); 
  while (WiFi.status() != WL_CONNECTED) { 
    Serial.print("."); 
    delay(500); 
    if (millis() - start > 15000) { 
      WiFi.disconnect(); 
      WiFi.begin(ssid, password); 
      start = millis(); 
    } 
  } 
  Serial.println(); 
  Serial.print("IP Address : "); 
  Serial.println(WiFi.localIP()); 
  tm.displayText("READY"); 
} 
 
void setup() { 
  Serial.begin(115200); 
  tm.displayBegin(); 
  tm.reset(); 
  tm.displayText("BOOT"); 
 
  connectWiFi(); 
 
  mb.server(); 
  for (int i = 0; i < NUM_COILS; i++) { 
    mb.addCoil(i, LOW); 
  } 
} 
 
 
 
 
 
void loop() { 
  if (millis() - lastWifiCheck > WIFI_CHECK_INTERVAL) { 
    lastWifiCheck = millis(); 
    if (WiFi.status() != WL_CONNECTED) { 
      connectWiFi(); 
      mb.server(); 
    } 
  } 
 
  mb.task(); 
 
  //--------- 1) Read local buttons ---------- 
  uint8_t buttons = tm.readButtons(); 
 
  // DEBUG: uncomment to see raw button bitmask when 
  // if (buttons != lastButtons) { 
  //   Serial.print("Buttons raw = 0b"); 
  //   for (int b = 7; b >= 0; b--) Serial.print((buttons >> b) & 1); 
  //   Serial.println(); 
  // } 
 
  uint8_t newPress = buttons & ~lastButtons; 
  for (int i = 0; i < NUM_COILS; i++) { 
    if (newPress & (1 << i)) { 
      // toggle THIS coil directly — coil is single source of truth 
      bool current = mb.Coil(i); 
      mb.Coil(i, !current); 
      Serial.print("Switch "); 
      Serial.print(i); 
      Serial.print(" toggled coil to "); 
      Serial.println(!current); 
    } 
  } 
  lastButtons = buttons; 
 
  //--------- 2) Reflect coil states -> LEDs ---------- 
  for (int i = 0; i < NUM_COILS; i++) { 
    tm.setLED(i, mb.Coil(i));  //    (ต ำแหน่ง, ค่ำ) 
  } 
 
  delay(10); 
} 