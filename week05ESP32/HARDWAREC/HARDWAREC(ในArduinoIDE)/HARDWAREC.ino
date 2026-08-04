#include "thingProperties.h"
#include "PCF8574.h"      // Rob Tillaart
#include "Wire.h"
#include "ModbusMaster.h"

// ================= struct + prototype (ต้องอยู่บนสุด) =================
struct Button { uint8_t pin; bool stable; bool lastRead; unsigned long tChg; };
Button btnGreen, btnBlack, btnRed;
bool pressed(Button &b);

// ================= PCF8574 =================
#define I2C_ADDR 0x20
#define I2C_SDA  21
#define I2C_SCL  22
TwoWire I2Ctwo = TwoWire(1);
PCF8574 pcf(I2C_ADDR, &I2Ctwo);

// ---- PCF8574 pin map ----
#define PIN_WHITE  0   // P0
#define PIN_GREEN  1   // P1
#define PIN_YELLOW 2   // P2
#define PIN_RED    3   // P3
#define SW_GREEN   4   // P4
#define SW_BLACK   5   // P5
#define SW_RED     6   // P6

// ---- Relay บน GPIO ESP32 ----
#define PIN_RELAY1 32
#define PIN_RELAY2 33

// ---- polarity (ถ้า active-HIGH สลับ 2 บรรทัดนี้) ----
#define LAMP_ON  LOW
#define LAMP_OFF HIGH

// ================= Modbus RS485 =================
#define MAX485_DE_RE 5
#define RX_PIN 26
#define TX_PIN 27
#define SENSOR_SLAVE 1     // เซนเซอร์อุณหภูมิ/ความชื้น
#define METER_SLAVE  2     // *** เปลี่ยนเป็น address มิเตอร์ไฟจริง ***
ModbusMaster nodeSensor, nodeMeter;
void preTx()  { digitalWrite(MAX485_DE_RE, HIGH); }
void postTx() { digitalWrite(MAX485_DE_RE, LOW);  }

// ================= debounce config =================
const unsigned long DEBOUNCE = 40;
unsigned long lastRead = 0;

// เก็บสถานะการอ่านล่าสุด (ไว้ print)
uint8_t sensorResult = 0xFF;
uint8_t meterResult  = 0xFF;

// ================= helper =================
void applyLamp(uint8_t pin, bool on) { pcf.write(pin, on ? LAMP_ON : LAMP_OFF); }

// ---- callback : สั่งจากมือถือ (cloud -> device) ----
void onWhiteLampChange()  { applyLamp(PIN_WHITE,  whiteLamp); }
void onGreenLampChange()  { applyLamp(PIN_GREEN,  greenLamp); }
void onYellowLampChange() { applyLamp(PIN_YELLOW, yellowLamp); }
void onRedLampChange()    { applyLamp(PIN_RED,    redLamp); }
void onRelay1Change()     { digitalWrite(PIN_RELAY1, relay1 ? LAMP_ON : LAMP_OFF); }
void onRelay2Change()     { digitalWrite(PIN_RELAY2, relay2 ? LAMP_ON : LAMP_OFF); }

// ---- คืน true เฉพาะตอน "เพิ่งกด" (falling edge หลัง debounce) ----
bool pressed(Button &b) {
  bool r = pcf.read(b.pin);
  bool edge = false;
  if (r != b.lastRead) { b.tChg = millis(); b.lastRead = r; }
  if (millis() - b.tChg > DEBOUNCE && r != b.stable) {
    b.stable = r;
    if (b.stable == LOW) edge = true;   // กดลง GND = LOW
  }
  return edge;
}

// ---- แปลง Modbus error code เป็นข้อความ ----
String mbErr(uint8_t r) {
  switch (r) {
    case ModbusMaster::ku8MBSuccess:            return "OK";
    case ModbusMaster::ku8MBIllegalFunction:    return "IllegalFunction";
    case ModbusMaster::ku8MBIllegalDataAddress: return "IllegalDataAddress";
    case ModbusMaster::ku8MBIllegalDataValue:   return "IllegalDataValue";
    case ModbusMaster::ku8MBSlaveDeviceFailure: return "SlaveDeviceFailure";
    case ModbusMaster::ku8MBInvalidSlaveID:     return "InvalidSlaveID";
    case ModbusMaster::ku8MBInvalidFunction:    return "InvalidFunction";
    case ModbusMaster::ku8MBResponseTimedOut:   return "TIMEOUT (ไม่ตอบ)";
    case ModbusMaster::ku8MBInvalidCRC:         return "InvalidCRC";
    default:                                    return "Unknown(" + String(r) + ")";
  }
}

// ---- 10.1 อ่านอุณหภูมิ/ความชื้น ----
void readSensor() {
  sensorResult = nodeSensor.readInputRegisters(1, 2);
  if (sensorResult == nodeSensor.ku8MBSuccess) {
    temperature = nodeSensor.getResponseBuffer(0) / 10.0;
    humidity    = nodeSensor.getResponseBuffer(1) / 10.0;
  }
}

// ---- 10.2 อ่านกำลังไฟ/แรงดัน/กระแส (map นี้อิง PZEM-004T ปรับตามมิเตอร์จริง) ----
void readMeter() {
  meterResult = nodeMeter.readInputRegisters(0x0000, 5);
  if (meterResult == nodeMeter.ku8MBSuccess) {
    voltage = nodeMeter.getResponseBuffer(0) / 10.0;              // 0.1 V
    uint32_t i = (uint32_t)nodeMeter.getResponseBuffer(1)
               | ((uint32_t)nodeMeter.getResponseBuffer(2) << 16);
    current = i / 1000.0;                                         // 0.001 A
    uint32_t p = (uint32_t)nodeMeter.getResponseBuffer(3)
               | ((uint32_t)nodeMeter.getResponseBuffer(4) << 16);
    power = p / 10.0;                                             // 0.1 W
  }
}

// ---- print ค่าทั้งหมดแบบเรียลไทม์ ----
void printAll() {
  Serial.println("========================================");
  Serial.print("Cloud   : ");
  Serial.println(ArduinoCloud.connected() ? "CONNECTED" : "disconnected");

  Serial.print("[SENSOR s1] "); Serial.println(mbErr(sensorResult));
  Serial.print("   Temp = "); Serial.print(temperature); Serial.println(" C");
  Serial.print("   Humi = "); Serial.print(humidity);    Serial.println(" %");

  Serial.print("[METER  s2] "); Serial.println(mbErr(meterResult));
  Serial.print("   Voltage = "); Serial.print(voltage); Serial.println(" V");
  Serial.print("   Current = "); Serial.print(current); Serial.println(" A");
  Serial.print("   Power   = "); Serial.print(power);   Serial.println(" W");

  Serial.print("Lamps -> White:"); Serial.print(whiteLamp);
  Serial.print(" Green:");  Serial.print(greenLamp);
  Serial.print(" Yellow:"); Serial.print(yellowLamp);
  Serial.print(" Red:");    Serial.print(redLamp);
  Serial.print(" R1:");     Serial.print(relay1);
  Serial.print(" R2:");     Serial.println(relay2);
}

void setup() {
  Serial.begin(115200);
  delay(1500);
  Serial.println("\n=== ESP32 Booting ===");

  // ---- PCF8574 ----
  I2Ctwo.begin(I2C_SDA, I2C_SCL);
  pcf.begin();                       // begin() ตั้งทุกขาเป็น HIGH (input พร้อมอ่าน)
  applyLamp(PIN_WHITE, false);
  applyLamp(PIN_GREEN, false);
  applyLamp(PIN_YELLOW, false);
  applyLamp(PIN_RED, false);

  // ---- Relay ----
  pinMode(PIN_RELAY1, OUTPUT); digitalWrite(PIN_RELAY1, LAMP_OFF);
  pinMode(PIN_RELAY2, OUTPUT); digitalWrite(PIN_RELAY2, LAMP_OFF);

  // ---- Modbus ----
  pinMode(MAX485_DE_RE, OUTPUT); digitalWrite(MAX485_DE_RE, LOW);
  Serial2.begin(9600, SERIAL_8N1, RX_PIN, TX_PIN);
  nodeSensor.begin(SENSOR_SLAVE, Serial2);
  nodeSensor.preTransmission(preTx); nodeSensor.postTransmission(postTx);
  nodeMeter.begin(METER_SLAVE, Serial2);
  nodeMeter.preTransmission(preTx);  nodeMeter.postTransmission(postTx);

  // ---- ปุ่ม ----
  btnGreen = {SW_GREEN, HIGH, HIGH, 0};
  btnBlack = {SW_BLACK, HIGH, HIGH, 0};
  btnRed   = {SW_RED,   HIGH, HIGH, 0};

  // ---- Arduino IoT Cloud ----
  initProperties();
  ArduinoCloud.begin(ArduinoIoTPreferredConnection);
  setDebugMessageLevel(2);
  ArduinoCloud.printDebugInfo();

  Serial.println("=== Setup done ===");
}

void loop() {
  ArduinoCloud.update();

  // ---- 10.5 / 10.6 / 10.7 : กดสวิตช์ toggle หลอด แล้ว sync ขึ้นมือถือ ----
  if (pressed(btnGreen)) { greenLamp  = !greenLamp;  applyLamp(PIN_GREEN,  greenLamp); }
  if (pressed(btnBlack)) { yellowLamp = !yellowLamp; applyLamp(PIN_YELLOW, yellowLamp); }
  if (pressed(btnRed))   { redLamp    = !redLamp;    applyLamp(PIN_RED,    redLamp); }

  // ---- อ่านค่า + print ทุก 1 วิ ----
  if (millis() - lastRead > 1000) {
    lastRead = millis();
    readSensor();
    readMeter();
    printAll();
  }
}