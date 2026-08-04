/* Lab 10  ET-ESP32(WROVER) RS485 V2 + Blynk
 * 10.1 Temp/Humidity (XY-MD02)  -> V0,V1
 * 10.2 PV/SV (REG48)            -> V2,V3
 * 10.3 White Lamp               -> V5
 * 10.5 Green Lamp + Green Sw     -> V6
 * 10.6 Yellow Lamp + Black Sw    -> V7
 * 10.7 Red Lamp + Red Sw         -> V8
 * สวิตช์: ดำ=P4, เขียว=P5, แดง=P6 | หลอด=รีเลย์ P0-P3 (บน PCF8574/A)
 * REG48: STno=2, CoM=96no | PV=InputReg addr1000 (FC04), SV=HoldingReg addr1002 (FC03), ไม่หาร10
 */

#define BLYNK_TEMPLATE_ID   "TMPL6D-KV4OyY"
#define BLYNK_TEMPLATE_NAME "Pk007"
#define BLYNK_AUTH_TOKEN    "YnL9cB2KYsDQrgklODdgF7evlcBNmPQe"
#define BLYNK_PRINT Serial

#include <WiFi.h>
#include <WiFiClient.h>
#include <BlynkSimpleEsp32.h>
#include <Wire.h>
#include "ModbusMaster.h"   // https://github.com/4-20ma/ModbusMaster

char ssid[] = "Tay2548";
char pass[] = "2548254500";

#define MAX485_RE_NEG 5
#define RX_PIN        26
#define TX_PIN        27
#define ID_XYMD02     1
#define ID_REG48      2

#define PCF_ADDR       0x20        // << verify ด้วย I2C scanner
#define OUT_ACTIVE_HIGH true       // รีเลย์กลับด้านใส่ false
#define INPUT_MASK     0b01110000  // P4,P5,P6 = input

#define PIN_WHITE    0
#define PIN_GREEN    1
#define PIN_YELLOW   2
#define PIN_RED      3
#define PIN_SW_BLACK 4
#define PIN_SW_GREEN 5
#define PIN_SW_RED   6

#define VP_TEMP   V0
#define VP_HUMI   V1
#define VP_PV     V2
#define VP_SV     V3
#define VP_WHITE  V5
#define VP_GREEN  V6
#define VP_YELLOW V7
#define VP_RED    V8

ModbusMaster modbus;   // XY-MD02
ModbusMaster reg48;    // REG48
BlynkTimer timer;

double g_temp = 0, g_humi = 0;
double g_pv = 0, g_sv = 0;

bool whiteState = false, greenState = false, yellowState = false, redState = false;
bool prevGreen = false, prevBlack = false, prevRed = false;

uint8_t pcfShadow = INPUT_MASK;

void preTransmission()  { digitalWrite(MAX485_RE_NEG, HIGH); }
void postTransmission() { digitalWrite(MAX485_RE_NEG, LOW);  }

void pcfWrite() {
  Wire.beginTransmission(PCF_ADDR);
  Wire.write(pcfShadow | INPUT_MASK);
  Wire.endTransmission();
}
uint8_t pcfReadPort() {
  Wire.requestFrom(PCF_ADDR, (uint8_t)1);
  return Wire.available() ? Wire.read() : 0xFF;
}
void setOut(uint8_t bit, bool on) {
  bool level = OUT_ACTIVE_HIGH ? on : !on;
  if (level) pcfShadow |=  (1 << bit);
  else       pcfShadow &= ~(1 << bit);
  pcfWrite();
}

void applyWhite()  { setOut(PIN_WHITE,  whiteState);  }
void applyGreen()  { setOut(PIN_GREEN,  greenState);  }
void applyYellow() { setOut(PIN_YELLOW, yellowState); }
void applyRed()    { setOut(PIN_RED,    redState);    }

bool getResultMsg(ModbusMaster *node, uint8_t result);

void readXYMD02() {
  uint8_t r = modbus.readInputRegisters(1, 2);
  if (getResultMsg(&modbus, r)) {
    g_temp = (int16_t)modbus.getResponseBuffer(0) / 10.0;
    g_humi = modbus.getResponseBuffer(1) / 10.0;
    Serial.printf("[XY-MD02] T=%.1f C  H=%.1f %%\n", g_temp, g_humi);
  }
}

// REG48: PV=Input Register addr1000 (FC04), SV=Holding Register addr1002 (FC03)
//   ไม่หาร10 (Pvd=0) | เพิ่มหน่วง+retry กันคำสั่งแรกหลุด
void readREG48() {
  delay(20);   // เว้นก่อนเริ่มคุยกับ REG48
  uint8_t rp = reg48.readInputRegisters(1000, 1);
  if (rp != reg48.ku8MBSuccess) { delay(30); rp = reg48.readInputRegisters(1000, 1); }  // retry
  if (getResultMsg(&reg48, rp))
    g_pv = (int16_t)reg48.getResponseBuffer(0);

  delay(50);   // เว้นระหว่าง 2 คำสั่ง
  uint8_t rs = reg48.readHoldingRegisters(1002, 1);
  if (rs != reg48.ku8MBSuccess) { delay(30); rs = reg48.readHoldingRegisters(1002, 1); } // retry
  if (getResultMsg(&reg48, rs))
    g_sv = (int16_t)reg48.getResponseBuffer(0);

  Serial.printf("[REG48] PV=%.0f  SV=%.0f\n", g_pv, g_sv);
}

BLYNK_WRITE(VP_WHITE)  { whiteState  = param.asInt(); applyWhite();  }
BLYNK_WRITE(VP_GREEN)  { greenState  = param.asInt(); applyGreen();  }
BLYNK_WRITE(VP_YELLOW) { yellowState = param.asInt(); applyYellow(); }
BLYNK_WRITE(VP_RED)    { redState    = param.asInt(); applyRed();    }

BLYNK_CONNECTED() {
  Blynk.virtualWrite(VP_WHITE,  whiteState);
  Blynk.virtualWrite(VP_GREEN,  greenState);
  Blynk.virtualWrite(VP_YELLOW, yellowState);
  Blynk.virtualWrite(VP_RED,    redState);
}

void readSwitches() {
  uint8_t port = pcfReadPort();
  bool gPressed = !((port >> PIN_SW_GREEN) & 1);
  bool bPressed = !((port >> PIN_SW_BLACK) & 1);
  bool rPressed = !((port >> PIN_SW_RED)   & 1);

  if (gPressed && !prevGreen) {
    greenState = !greenState; applyGreen();
    Blynk.virtualWrite(VP_GREEN, greenState);
  }
  prevGreen = gPressed;

  if (bPressed && !prevBlack) {
    yellowState = !yellowState; applyYellow();
    Blynk.virtualWrite(VP_YELLOW, yellowState);
  }
  prevBlack = bPressed;

  if (rPressed && !prevRed) {
    redState = !redState; applyRed();
    Blynk.virtualWrite(VP_RED, redState);
  }
  prevRed = rPressed;
}

void sendToBlynk() {
  if (!Blynk.connected()) return;
  Blynk.virtualWrite(VP_TEMP, g_temp);
  Blynk.virtualWrite(VP_HUMI, g_humi);
  Blynk.virtualWrite(VP_PV,   g_pv);
  Blynk.virtualWrite(VP_SV,   g_sv);
}

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n=== ESP32 Lab10 Booting ===");

  pinMode(MAX485_RE_NEG, OUTPUT);
  digitalWrite(MAX485_RE_NEG, LOW);
  Serial2.begin(9600, SERIAL_8N1, RX_PIN, TX_PIN);
  modbus.begin(ID_XYMD02, Serial2);
  modbus.preTransmission(preTransmission);
  modbus.postTransmission(postTransmission);
  reg48.begin(ID_REG48, Serial2);
  reg48.preTransmission(preTransmission);
  reg48.postTransmission(postTransmission);

  Wire.begin(21, 22);
  pcfWrite();

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, pass);
  int retry = 0;
  while (WiFi.status() != WL_CONNECTED && retry < 20) { delay(500); Serial.print("."); retry++; }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("WiFi OK: "); Serial.println(WiFi.localIP());
    Blynk.config(BLYNK_AUTH_TOKEN, "blynk.cloud", 80);   // << ระบุ server แก้ 0.0.0.0
    Blynk.connect(5000);
  } else {
    Serial.println("WiFi FAILED (ต้องเป็น 2.4GHz) แต่โค้ดยังรันต่อ");
  }

  timer.setInterval(1000L, readXYMD02);
  timer.setInterval(1000L, readREG48);
  timer.setInterval(1000L, sendToBlynk);
  timer.setInterval(30L,   readSwitches);

  Serial.println("=== Setup done ===");
}

void loop() {
  Blynk.run();
  timer.run();
}

bool getResultMsg(ModbusMaster *node, uint8_t result) {
  if (result == node->ku8MBSuccess) return true;
  String m = "\r\n";
  switch (result) {
    case node->ku8MBIllegalFunction:     m += "Illegal Function"; break;
    case node->ku8MBIllegalDataAddress:  m += "Illegal Data Address"; break;
    case node->ku8MBIllegalDataValue:    m += "Illegal Data Value"; break;
    case node->ku8MBSlaveDeviceFailure:  m += "Slave Device Failure"; break;
    case node->ku8MBInvalidSlaveID:      m += "Invalid Slave ID"; break;
    case node->ku8MBInvalidFunction:     m += "Invalid Function"; break;
    case node->ku8MBResponseTimedOut:    m += "Response Timed Out"; break;
    case node->ku8MBInvalidCRC:          m += "Invalid CRC"; break;
    default:                             m += "Unknown error: " + String(result); break;
  }
  Serial.println(m);
  return false;
}