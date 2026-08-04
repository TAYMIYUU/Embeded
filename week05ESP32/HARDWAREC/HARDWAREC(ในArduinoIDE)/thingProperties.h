#include <ArduinoIoTCloud.h>
#include <Arduino_ConnectionHandler.h>

// ---- WiFi ----
const char SSID[] = "Tay2548";              // แก้เป็น WiFi ของคุณ (2.4GHz)
const char PASS[] = "2548254500";

// ---- จาก Arduino Cloud (หน้า Device) ----
const char DEVICE_LOGIN_NAME[] = "26ebd7b0-ef1b-4e99-bd13-b8a835702101";  // Device ID
const char DEVICE_KEY[]        = "IxmwNNJ8wm7SMTf#!2sB5P!QW";                // Secret Key

// ---- callback prototype ----
void onWhiteLampChange();
void onRelay1Change();
void onRelay2Change();
void onGreenLampChange();
void onYellowLampChange();
void onRedLampChange();

// ---- monitor (READ) : 10.1, 10.2 ----
float temperature;
float humidity;
float voltage;
float current;
float power;

// ---- control (READWRITE) : 10.3–10.7 ----
bool whiteLamp;
bool relay1;
bool relay2;
bool greenLamp;
bool yellowLamp;
bool redLamp;

void initProperties() {
  ArduinoCloud.setBoardId(DEVICE_LOGIN_NAME);
  ArduinoCloud.setSecretDeviceKey(DEVICE_KEY);

  ArduinoCloud.addProperty(temperature, READ, ON_CHANGE, NULL);
  ArduinoCloud.addProperty(humidity,    READ, ON_CHANGE, NULL);
  ArduinoCloud.addProperty(voltage,     READ, ON_CHANGE, NULL);
  ArduinoCloud.addProperty(current,     READ, ON_CHANGE, NULL);
  ArduinoCloud.addProperty(power,       READ, ON_CHANGE, NULL);

  ArduinoCloud.addProperty(whiteLamp,  READWRITE, ON_CHANGE, onWhiteLampChange);
  ArduinoCloud.addProperty(relay1,     READWRITE, ON_CHANGE, onRelay1Change);
  ArduinoCloud.addProperty(relay2,     READWRITE, ON_CHANGE, onRelay2Change);
  ArduinoCloud.addProperty(greenLamp,  READWRITE, ON_CHANGE, onGreenLampChange);
  ArduinoCloud.addProperty(yellowLamp, READWRITE, ON_CHANGE, onYellowLampChange);
  ArduinoCloud.addProperty(redLamp,    READWRITE, ON_CHANGE, onRedLampChange);
}

WiFiConnectionHandler ArduinoIoTPreferredConnection(SSID, PASS);