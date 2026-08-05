// ==== Blynk 2.0 config (วางไว้บนสุดก่อน include เสมอ) ====
#define BLYNK_TEMPLATE_ID   "TMPL6D-KV4OyY"
#define BLYNK_TEMPLATE_NAME "Pk007"
#define BLYNK_AUTH_TOKEN    "YnL9cB2KYsDQrgklODdgF7evlcBNmPQe"

#define BLYNK_PRINT Serial

#include <WiFi.h>
#include <WiFiClient.h>
#include <BlynkSimpleEsp32.h>
#include "ModbusMaster.h" //https://github.com/4-20ma/ModbusMaster

// ==== WiFi ====
char ssid[] = "Tay2548";
char pass[] = "2548254500";

#define Slave_ID      1
#define MAX485_RE_NEG 5
#define RX_PIN        26
#define TX_PIN        27

ModbusMaster modbus;
BlynkTimer timer;

double g_temp = 0.0;
double g_humi = 0.0;

void preTransmission() {
  digitalWrite(MAX485_RE_NEG, HIGH);
}

void postTransmission() {
  digitalWrite(MAX485_RE_NEG, LOW);
}

bool getResultMsg(ModbusMaster *node, uint8_t result);

void readModbus() {
  uint8_t result = modbus.readInputRegisters(1, 2);
  if (getResultMsg(&modbus, result)) {
    g_temp = modbus.getResponseBuffer(0) / 10.0;
    g_humi = modbus.getResponseBuffer(1) / 10.0;

    Serial.println("========================");
    Serial.print("Temperature: ");
    Serial.print(g_temp);
    Serial.println(" C");
    Serial.print("Humidity   : ");
    Serial.print(g_humi);
    Serial.println(" %");
  }
}

void sendToBlynk() {
  if (Blynk.connected()) {
    Blynk.virtualWrite(V0, g_temp);
    Blynk.virtualWrite(V1, g_humi);
    Serial.println(">> ส่งขึ้น Blynk แล้ว (V0, V1)");
  } else {
    Serial.println(">> Blynk ยังไม่ connect ข้ามการส่ง");
  }
}

void setup() {
  // USB debug = 115200, Modbus = 9600 (คนละตัวกัน)
  Serial.begin(115200);
  delay(500);
  Serial.println("\n\n=== ESP32 Booting ===");

  pinMode(MAX485_RE_NEG, OUTPUT);
  digitalWrite(MAX485_RE_NEG, LOW);

  Serial2.begin(9600, SERIAL_8N1, RX_PIN, TX_PIN);
  modbus.begin(Slave_ID, Serial2);
  modbus.preTransmission(preTransmission);
  modbus.postTransmission(postTransmission);

  // ---- ต่อ WiFi เอง แบบมี timeout ----
  Serial.print("Connecting WiFi: ");
  Serial.println(ssid);
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, pass);

  int retry = 0;
  while (WiFi.status() != WL_CONNECTED && retry < 20) {
    delay(500);
    Serial.print(".");
    retry++;
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("WiFi connected! IP: ");
    Serial.println(WiFi.localIP());

    // config + connect Blynk แบบไม่ block ค้าง
    Blynk.config(BLYNK_AUTH_TOKEN);
    if (Blynk.connect(5000)) {
      Serial.println("Blynk connected!");
    } else {
      Serial.println("Blynk connect FAILED (แต่โค้ดยังรันต่อ)");
    }
  } else {
    Serial.println("WiFi FAILED! เช็ค SSID/pass และต้องเป็น 2.4GHz");
  }

  // ตั้ง timer
  timer.setInterval(1000L, readModbus);
  timer.setInterval(1000L, sendToBlynk);

  Serial.println("=== Setup done, entering loop ===");
}

void loop() {
  Blynk.run();
  timer.run();
}

bool getResultMsg(ModbusMaster *node, uint8_t result) {
  String tmpstr2 = "\r\n";
  switch (result) {
    case node->ku8MBSuccess:
      return true;
      break;
    case node->ku8MBIllegalFunction:
      tmpstr2 += "Illegal Function";
      break;
    case node->ku8MBIllegalDataAddress:
      tmpstr2 += "Illegal Data Address";
      break;
    case node->ku8MBIllegalDataValue:
      tmpstr2 += "Illegal Data Value";
      break;
    case node->ku8MBSlaveDeviceFailure:
      tmpstr2 += "Slave Device Failure";
      break;
    case node->ku8MBInvalidSlaveID:
      tmpstr2 += "Invalid Slave ID";
      break;
    case node->ku8MBInvalidFunction:
      tmpstr2 += "Invalid Function";
      break;
    case node->ku8MBResponseTimedOut:
      tmpstr2 += "Response Timed Out";
      break;
    case node->ku8MBInvalidCRC:
      tmpstr2 += "Invalid CRC";
      break;
    default:
      tmpstr2 += "Unknown error: " + String(result);
      break;
  }
  Serial.println(tmpstr2);
  return false;
}