#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <ArduinoJson.h>

// --- PINES DE LOS MOTORES ---
const int pinStepA = 12; // GPIO 12 (D6)
const int pinDirA = 14;  // GPIO 14 (D5)
const int pinEnA = 13;   // GPIO 13 (D7)

const int pinStepB = 5;  // GPIO 5  (D1)
const int pinDirB = 4;   // GPIO 4  (D2)
const int pinEnB = 16;   // GPIO 16 (D0)

// --- CONFIGURACIÓN DEL HOTSPOT ---
const char* ssid = "ValeoProyecto"; 
const char* password = "valeoverga"; 

ESP8266WebServer server(80);

// --- VARIABLES DE POSICIÓN Y CALIBRACIÓN ---
float posicionActualX = 0.0;
float posicionActualY = 0.0;

// ¡Aquí está tu valor calibrado exacto!
float pasosPorMilimetro = 80.0; 

void setup() {
  Serial.begin(115200);

  pinMode(pinStepA, OUTPUT); pinMode(pinDirA, OUTPUT); pinMode(pinEnA, OUTPUT);
  pinMode(pinStepB, OUTPUT); pinMode(pinDirB, OUTPUT); pinMode(pinEnB, OUTPUT);
  digitalWrite(pinEnA, LOW); digitalWrite(pinEnB, LOW);

  Serial.println("\nIniciando Hotspot...");
  WiFi.softAP(ssid, password);
  Serial.print("IP del ESP8266: ");
  Serial.println(WiFi.softAPIP());

  server.on("/ping", HTTP_GET, []() {
    server.send(200, "text/plain", "pong");
  });

  server.on("/cmd", HTTP_POST, []() {
    digitalWrite(pinEnA, HIGH);
    digitalWrite(pinEnB, HIGH);
    server.send(200, "text/plain", "ESTOP: Motores apagados");
  });

  server.on("/move", HTTP_POST, manejarMovimiento);

  server.begin();
}

void loop() {
  server.handleClient();
}

void manejarMovimiento() {
  if (server.hasArg("plain") == false) {
    server.send(400, "text/plain", "Vacio");
    return;
  }

  String body = server.arg("plain");
  StaticJsonDocument<200> doc;
  DeserializationError error = deserializeJson(doc, body);

  if (error) {
    server.send(500, "text/plain", "Error JSON");
    return;
  }

  float destinoX = doc["x"];
  float destinoY = doc["y"];

  float deltaX_mm = destinoX - posicionActualX;
  float deltaY_mm = destinoY - posicionActualY;

  long pasosX = deltaX_mm * pasosPorMilimetro;
  long pasosY = deltaY_mm * pasosPorMilimetro;

  digitalWrite(pinEnA, LOW);
  digitalWrite(pinEnB, LOW);
  
  // 1500 es la velocidad entre pulsos (más bajo = más rápido)
  moverCoreXY(pasosX, pasosY, 1500); 

  posicionActualX = destinoX;
  posicionActualY = destinoY;

  server.send(200, "text/plain", "Posicion alcanzada");
}

void moverCoreXY(long deltaX, long deltaY, int velocidadRetraso) {
  long pasosA = deltaX + deltaY;
  long pasosB = deltaX - deltaY;

  if (pasosA >= 0) digitalWrite(pinDirA, HIGH); else digitalWrite(pinDirA, LOW);
  if (pasosB >= 0) digitalWrite(pinDirB, HIGH); else digitalWrite(pinDirB, LOW);

  pasosA = abs(pasosA); pasosB = abs(pasosB);
  long pasosMaximos = max(pasosA, pasosB);

for (long i = 0; i < pasosMaximos; i++) {
    if (i < pasosA) digitalWrite(pinStepA, HIGH);
    if (i < pasosB) digitalWrite(pinStepB, HIGH);
    delayMicroseconds(velocidadRetraso);
    digitalWrite(pinStepA, LOW);
    digitalWrite(pinStepB, LOW);
    delayMicroseconds(velocidadRetraso);
    
    yield();
  }
}
