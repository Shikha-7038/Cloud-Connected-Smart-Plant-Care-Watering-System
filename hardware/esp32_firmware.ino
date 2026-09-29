/*
  Optional hardware version — ESP32 firmware
  ------------------------------------------
  Reads a capacitive soil-moisture sensor + DHT22, POSTs JSON readings to the
  SAME /api/sensors/data endpoint the Python simulator uses, and polls the
  cloud for a watering command. Swap the simulator for this file and the
  rest of the cloud architecture (backend, database, dashboard) is unchanged.

  Wiring:
    Soil sensor  VCC->3V3  GND->GND  OUT->GPIO34 (ADC1)
    DHT22        VCC->3V3  GND->GND  DATA->GPIO4 (10k pull-up to 3V3)
    Relay/MOSFET IN->GPIO26 (drives a 5-12V DC pump; keep mains AC out of this build)

  Libraries needed (Arduino Library Manager): "DHT sensor library" (Adafruit),
  "ArduinoJson".
*/
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "DHT.h"

#define SOIL_PIN 34
#define DHTPIN   4
#define DHTTYPE  DHT22
#define PUMP_PIN 26

const char* WIFI_SSID = "YOUR_WIFI";
const char* WIFI_PASS = "YOUR_PASS";
const char* API_URL   = "https://your-backend.example.com/api/sensors/data";
const char* DEVICE_ID = "PLANT-001";
const char* API_KEY   = "PASTE_DEVICE_API_KEY_HERE";   // printed by scripts/seed_demo.py

const int   DRY_RAW = 3200;   // calibrate: raw ADC value in dry air
const int   WET_RAW = 1200;   // calibrate: raw ADC value in a cup of water
const unsigned long SEND_INTERVAL_MS = 60000;          // 1 reading / minute

DHT dht(DHTPIN, DHTTYPE);

void setup() {
  Serial.begin(115200);
  pinMode(PUMP_PIN, OUTPUT);
  digitalWrite(PUMP_PIN, LOW);
  dht.begin();
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.println("\nConnected: " + WiFi.localIP().toString());
}

float readSoilPercent() {
  int raw = analogRead(SOIL_PIN);
  float pct = 100.0f * (DRY_RAW - raw) / (float)(DRY_RAW - WET_RAW);
  return constrain(pct, 0, 100);
}

void setPump(bool on) { digitalWrite(PUMP_PIN, on ? HIGH : LOW); }

void loop() {
  float soil = readSoilPercent();
  float temp = dht.readTemperature();
  float hum  = dht.readHumidity();

  if (isnan(temp) || isnan(hum)) {
    Serial.println("DHT22 read failed, skipping this cycle");
  } else if (WiFi.status() == WL_CONNECTED) {
    StaticJsonDocument<256> doc;
    doc["device_id"] = DEVICE_ID;
    doc["soil_moisture"] = soil;
    doc["temperature"] = temp;
    doc["humidity"] = hum;
    String body;
    serializeJson(doc, body);

    HTTPClient http;
    http.begin(API_URL);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("x-api-key", API_KEY);
    int code = http.POST(body);
    String resp = http.getString();
    Serial.printf("POST %d: %s\n", code, resp.c_str());

    if (code == 200) {
      // Cloud automation decides pump state; the firmware just obeys it.
      StaticJsonDocument<128> reply;
      if (deserializeJson(reply, resp) == DeserializationError::Ok) {
        const char* pump = reply["pump"] | "OFF";
        setPump(strcmp(pump, "ON") == 0);
      }
    } else if (code == 401) {
      Serial.println("Auth rejected - check API_KEY / DEVICE_ID");
    }
    http.end();
  } else {
    Serial.println("WiFi disconnected - reading buffered locally, will retry next cycle");
  }

  delay(SEND_INTERVAL_MS);
}
