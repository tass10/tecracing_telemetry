#define RXD2 16
#define TXD2 17

char sensor1[] = "sensor1,";
char sensor2[] = "sensor2,";
char sensor3[] = "sensor3,";
char sensor4[] = "sensor4,";
char sensor5[] = "sensor5,";
char sensor6[] = "sensor6,";
char sensor7[] = "sensor7,";
char sensor8[] = "sensor8,";
char sensor9[] = "sensor9,";
char sensor10[] = "sensor10,";
char sensor11[] = "sensor11,";
char sensor12[] = "sensor12,";
char sensor13[] = "sensor13,";
char sensor14[] = "sensor14,";
char sensor15[] = "sensor15,";
char sensor16[] = "sensor16,";
char sensor17[] = "sensor17,";
char sensor18[] = "sensor18,";
char sensor19[] = "sensor19,";
char sensor20[] = "sensor20";

void setup() {
  // Note the format for setting a serial port is as follows: Serial2.begin(baud-rate, protocol, RX pin, TX pin);
  Serial.begin(115200);
  Serial2.begin(9600, SERIAL_8N1, RXD2, TXD2);
}

void loop() {
  // Concatena todas as strings em uma única String
  String fullString = "";
  fullString += sensor1;
  fullString += sensor2;
  fullString += sensor3;
  fullString += sensor4;
  fullString += sensor5;
  fullString += sensor6;
  fullString += sensor7;
  fullString += sensor8;
  fullString += sensor9;
  fullString += sensor10;
  fullString += sensor11;
  fullString += sensor12;
  fullString += sensor13;
  fullString += sensor14;
  fullString += sensor15;
  fullString += sensor16;
  fullString += sensor17;
  fullString += sensor18;
  fullString += sensor19;
  fullString += sensor20; // O último não precisa da vírgula

  // Envia a string completa seguida de '\n'
  Serial2.println(fullString);

  // O delay é importante para o LoRa, pois ele precisa de tempo para esvaziar seu buffer e transmitir.
  delay(200);
}