/* Lab 10 (แบบ B) ET-ESP32 RS485 V2 + Blynk IoT
 * ESP = Modbus TCP server (PC/Modbus Poll ต่อผ่าน WiFi:502)
 *       + RTU master อ่าน REG48(id2) + XY-MD02(id1) บนสาย RS485
 *       + Blynk IoT (คุม/ดูผ่านแอปมือถือ)
 *
 * === Register map ที่ PC อ่าน/เขียนผ่าน TCP ===
 * Input Register (FC04):  0=Temp(x10) 1=Humi(x10) 2=REG48 PV 3=REG48 SV
 * Coil (FC01/05):         0=White 1=Green 2=Yellow 3=Red
 * Discrete Input (FC02):  0=GreenSw 1=BlackSw 2=RedSw   (1=กำลังกด)
 *
 * === Virtual pin ฝั่ง Blynk (ต้องไปสร้าง Datastream ให้ตรงใน console) ===
 * V0=Temp  V1=Humi  V2=PV  V3=SV          (Datastream: Double, read only)
 * V4=Yellow V5=Green V6=White V7=Red      (Datastream: Integer 0/1, ผูกกับ Switch/Button)
 * V8=SwGreen V9=SwBlack V10=SwRed         (Datastream: Integer 0/1, read only -> LED widget)
 */

// ====== Blynk credentials ======
#define BLYNK_TEMPLATE_ID   "TMPL6D-KV4OyY"
#define BLYNK_TEMPLATE_NAME "Pk007"
#define BLYNK_AUTH_TOKEN    "YnL9cB2KYsDQrgklODdgF7evlcBNmPQe"
#define BLYNK_PRINT Serial   // ให้ Blynk พิมพ์ debug ออก Serial

#include <WiFi.h>
#include <Wire.h>
#include "ModbusMaster.h"          // RTU master  (4-20ma)
#include <ModbusIP_ESP8266.h>      // TCP server  (emelianov/modbus-esp8266)
#include <BlynkSimpleEsp32.h>      // Blynk IoT (Blynk by Volodymyr Shymanskyy)

char ssid[] = "Kaitod";
char pass[] = "12345678";

#define MAX485_RE_NEG 5
#define RX_PIN        26
#define TX_PIN        27
#define ID_XYMD02     1
#define ID_REG48      2

#define PCF_ADDR       0x20
#define OUT_ACTIVE_HIGH true
#define INPUT_MASK     0b01110000   // P4,P5,P6 = input

#define PIN_WHITE    0
#define PIN_GREEN    1
#define PIN_YELLOW   2
#define PIN_RED      3
#define PIN_SW_BLACK 4
#define PIN_SW_GREEN 5
#define PIN_SW_RED   6

// ---- TCP register/coil offsets ----
#define IREG_TEMP  0
#define IREG_HUMI  1
#define IREG_PV    2
#define IREG_SV    3
#define COIL_WHITE 0
#define COIL_GREEN 1
#define COIL_YELLOW 2
#define COIL_RED   3
#define ISTS_GREEN 0
#define ISTS_BLACK 1
#define ISTS_RED   2

ModbusMaster modbus;   // XY-MD02
ModbusMaster reg48;    // REG48
ModbusIP mb;           // TCP server
BlynkTimer timer;      // (สำรองไว้ใช้ถ้าต้องการ)

double g_temp = 0, g_humi = 0, g_pv = 0, g_sv = 0;
bool whiteState=false, greenState=false, yellowState=false, redState=false;
bool prevGreen=false, prevBlack=false, prevRed=false;
uint8_t pcfShadow = INPUT_MASK;
uint32_t tRTU=0, tSw=0;

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

// ============================================================
//  Blynk: ปุ่มในแอปสั่งมา -> อัปเดต state + หลอด + coil (ให้ PC เห็นด้วย)
//  V4=Yellow  V5=Green  V6=White  V7=Red
// ============================================================
BLYNK_WRITE(V4) { yellowState = param.asInt(); applyYellow(); mb.Coil(COIL_YELLOW, yellowState); }
BLYNK_WRITE(V5) { greenState  = param.asInt(); applyGreen();  mb.Coil(COIL_GREEN,  greenState);  }
BLYNK_WRITE(V6) { whiteState  = param.asInt(); applyWhite();  mb.Coil(COIL_WHITE,  whiteState);  }
BLYNK_WRITE(V7) { redState    = param.asInt(); applyRed();    mb.Coil(COIL_RED,    redState);    }

// เมื่อแอปเชื่อมต่อสำเร็จ -> ส่งสถานะปัจจุบันขึ้นไป sync ปุ่มให้ตรงของจริง
BLYNK_CONNECTED() {
  Blynk.virtualWrite(V4, yellowState);
  Blynk.virtualWrite(V5, greenState);
  Blynk.virtualWrite(V6, whiteState);
  Blynk.virtualWrite(V7, redState);
}

// ---- RTU master: อ่านเซนเซอร์ -> mirror เข้า TCP + ส่งขึ้น Blynk ----
void readXYMD02() {
  uint8_t r = modbus.readInputRegisters(1, 2);
  if (getResultMsg(&modbus, r)) {
    int16_t t = modbus.getResponseBuffer(0);
    uint16_t h = modbus.getResponseBuffer(1);
    g_temp = t/10.0; g_humi = h/10.0;
    mb.Ireg(IREG_TEMP, t);
    mb.Ireg(IREG_HUMI, h);
    Blynk.virtualWrite(V0, g_temp);   // ส่งค่าจริง (หาร10แล้ว) ขึ้นแอป
    Blynk.virtualWrite(V1, g_humi);
    Serial.printf("[XY-MD02] T=%.1f H=%.1f\n", g_temp, g_humi);
  }
}
void readREG48() {
  delay(20);
  uint8_t rp = reg48.readInputRegisters(1000, 1);
  if (rp != reg48.ku8MBSuccess) { delay(30); rp = reg48.readInputRegisters(1000, 1); }
  if (getResultMsg(&reg48, rp)) {
    g_pv = (int16_t)reg48.getResponseBuffer(0);
    mb.Ireg(IREG_PV, (int16_t)g_pv);
    Blynk.virtualWrite(V2, g_pv);
  }

  delay(50);
  uint8_t rs = reg48.readHoldingRegisters(1002, 1);
  if (rs != reg48.ku8MBSuccess) { delay(30); rs = reg48.readHoldingRegisters(1002, 1); }
  if (getResultMsg(&reg48, rs)) {
    g_sv = (int16_t)reg48.getResponseBuffer(0);
    mb.Ireg(IREG_SV, (int16_t)g_sv);
    Blynk.virtualWrite(V3, g_sv);
  }

  Serial.printf("[REG48] PV=%.0f SV=%.0f\n", g_pv, g_sv);
}

// ---- PC เขียน coil มา -> สั่งหลอด + push ขึ้น Blynk ----
void syncCoils() {
  if (mb.Coil(COIL_WHITE)  != whiteState)  { whiteState  = mb.Coil(COIL_WHITE);  applyWhite();  Blynk.virtualWrite(V6, whiteState);  }
  if (mb.Coil(COIL_GREEN)  != greenState)  { greenState  = mb.Coil(COIL_GREEN);  applyGreen();  Blynk.virtualWrite(V5, greenState);  }
  if (mb.Coil(COIL_YELLOW) != yellowState) { yellowState = mb.Coil(COIL_YELLOW); applyYellow(); Blynk.virtualWrite(V4, yellowState); }
  if (mb.Coil(COIL_RED)    != redState)    { redState    = mb.Coil(COIL_RED);    applyRed();    Blynk.virtualWrite(V7, redState);    }
}

// ---- สวิตช์จริง: toggle หลอด + อัปเดต coil/discrete + push ขึ้น Blynk ----
void readSwitches() {
  uint8_t port = pcfReadPort();
  bool g = !((port >> PIN_SW_GREEN) & 1);
  bool b = !((port >> PIN_SW_BLACK) & 1);
  bool r = !((port >> PIN_SW_RED)   & 1);
  mb.Ists(ISTS_GREEN, g); mb.Ists(ISTS_BLACK, b); mb.Ists(ISTS_RED, r);
  Blynk.virtualWrite(V8, g); Blynk.virtualWrite(V9, b); Blynk.virtualWrite(V10, r);

  if (g && !prevGreen) { greenState=!greenState; applyGreen();  mb.Coil(COIL_GREEN, greenState);  Blynk.virtualWrite(V5, greenState);  }
  prevGreen = g;
  if (b && !prevBlack) { yellowState=!yellowState; applyYellow(); mb.Coil(COIL_YELLOW, yellowState); Blynk.virtualWrite(V4, yellowState); }
  prevBlack = b;
  if (r && !prevRed)   { redState=!redState; applyRed();      mb.Coil(COIL_RED, redState);      Blynk.virtualWrite(V7, redState);    }
  prevRed = r;
}

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n=== ESP32 Lab10-B (Modbus TCP + Blynk) ===");

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
    Serial.print(">>> Modbus TCP ที่ IP: "); Serial.print(WiFi.localIP());
    Serial.println("  port 502");
    // ต่อ Blynk โดยใช้ WiFi ที่เชื่อมไว้แล้ว (ไม่ block WiFi ซ้ำ)
    Blynk.config(BLYNK_AUTH_TOKEN);
    Blynk.connect(5000);   // พยายามต่อ cloud 5 วิ ถ้าไม่ติด loop จะต่อให้เองภายหลัง
  } else {
    Serial.println("WiFi FAILED (ต้อง 2.4GHz)");
  }

  // เริ่ม TCP server + สร้าง register map
  mb.server();
  mb.addIreg(IREG_TEMP, 0, 4);     // input reg 0..3
  mb.addCoil(COIL_WHITE, false, 4);// coil 0..3
  mb.addIsts(ISTS_GREEN, false, 3);// discrete input 0..2

  Serial.println("=== Setup done ===");
}

void loop() {
  mb.task();                       // ประมวลผล TCP ทุกลูป
  Blynk.run();                     // ประมวลผล Blynk ทุกลูป
  uint32_t now = millis();
  if (now - tSw >= 30)   { tSw = now;  readSwitches(); syncCoils(); }
  if (now - tRTU >= 1000){ tRTU = now; readXYMD02();   readREG48(); }
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