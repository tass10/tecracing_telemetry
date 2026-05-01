// Definindo os pinos do barramento UART2 para comunicar com o Módulo LoRa
#define RXD2 16
#define TXD2 17

void setup() {
  Serial.begin(115200);                         // Inicia o barramento UART0 USB PC
  Serial2.begin(9600, SERIAL_8N1, RXD2, TXD2);  // Inicia o barramento UART2 LoRa
}

void loop() { //Choose Serial1 or Serial2 as required
// Verifica se há dados disponíveis para leitura na Serial2 (LoRa)
  if (Serial2.available()) {
    // 1. Usa readStringUntil('\n') para ler a string inteira até a quebra de linha
    // (que é enviada automaticamente pelo Serial2.println() do Transmissor).
    //String receivedString = Serial2.readStringUntil('\n');

    // 2. Remove quaisquer retornos de carro ('\r') que possam ter sido incluídos.
    //receivedString.trim(); 

    // 3. Imprime a string completa recebida.
    //Serial.print("String Completa Recebida: ");
    //Serial.println(receivedString);

    // Opcional: Imprime o tamanho para verificação
    //Serial.print("Tamanho da String: ");
    //Serial.println(receivedString.length());
    String receivedString = Serial2.readStringUntil('\n');

    Serial.println(receivedString);
  }
}