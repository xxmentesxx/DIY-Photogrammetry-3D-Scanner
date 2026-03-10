#include <WiFi.h>
#include <WebServer.h>
#include <ESP32Servo.h>

// --- WIFI ---
const char* ssid = "";
const char* password = "";

// --- PINLER ---
const int servoPin = 3; 
const int tablePins[4] = {8, 9, 10, 11};

// SENİN ÇALIŞAN SIRALAMAN (Bunu Korumamız Şart)
const int elevatorPins[4] = {6, 5, 7, 4}; 

WebServer server(80);
Servo myServo;

void setup() {
  Serial.begin(115200);

  // Servo Ayarı
  myServo.setPeriodHertz(50);
  myServo.attach(servoPin, 500, 2400);
  myServo.write(0);

  for(int i=0; i<4; i++) {
    pinMode(tablePins[i], OUTPUT);
    pinMode(elevatorPins[i], OUTPUT);
  }

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) delay(500);
  Serial.println(WiFi.localIP()); 

  server.on("/action", handleAction);
  server.begin();
}

void loop() {
  server.handleClient();
}

void handleAction() {
  if (!server.hasArg("type")) { server.send(400, "text/plain", "Hata"); return; }
  String type = server.arg("type");

  if (type == "servo") {
    int val = server.arg("val").toInt();
    if(val < 0) val = 0; if(val > 180) val = 180;
    myServo.write(val);
    server.send(200, "text/plain", "Servo OK");
  } 
  else if (type == "step") {
    String motor = server.arg("motor");
    String dir = server.arg("dir");
    int steps = server.arg("steps").toInt();
    int delayTime = server.arg("delay").toInt();
    
    // Gecikme limiti
    if(delayTime < 2000) delayTime = 2000;

    const int* activePins = (motor == "table") ? tablePins : elevatorPins;

    for (int i = 0; i < steps; i++) {
      int stepIndex = i % 4;
      if (dir == "ccw") stepIndex = 3 - (i % 4);
      
      // Güçlü Sürüş Fonksiyonunu Çağır
      setStepHighTorque(activePins, stepIndex);
      delayMicroseconds(delayTime);
    }
    stopMotor(activePins);
    server.send(200, "text/plain", "Step OK");
  }
}

// --- YENİ GÜÇLÜ SÜRÜŞ MODU (FULL STEP) ---
// Aynı anda 2 bobini yakarak %40 daha fazla güç üretir.
void setStepHighTorque(const int pins[], int step) {
  switch(step) {
    case 0: digitalWrite(pins[0], HIGH); digitalWrite(pins[1], HIGH); digitalWrite(pins[2], LOW);  digitalWrite(pins[3], LOW); break;
    case 1: digitalWrite(pins[0], LOW);  digitalWrite(pins[1], HIGH); digitalWrite(pins[2], HIGH); digitalWrite(pins[3], LOW); break;
    case 2: digitalWrite(pins[0], LOW);  digitalWrite(pins[1], LOW);  digitalWrite(pins[2], HIGH); digitalWrite(pins[3], HIGH); break;
    case 3: digitalWrite(pins[0], HIGH); digitalWrite(pins[1], LOW);  digitalWrite(pins[2], LOW);  digitalWrite(pins[3], HIGH); break;
  }
}

void stopMotor(const int pins[]) {
  for(int i=0; i<4; i++) digitalWrite(pins[i], LOW);
}