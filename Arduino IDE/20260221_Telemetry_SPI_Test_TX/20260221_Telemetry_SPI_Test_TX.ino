#include <SPI.h>

// Definindo os pinos do barramento VSPI
const int pino_sck = 18;
const int pino_miso = 19;
const int pino_mosi = 23;
const int pino_cs = 5;

// Definindo os pinos do barramento UART2 para comunicar com o Módulo LoRa
#define RXD2 16
#define TXD2 17

void setup() {
  Serial.begin(115200);                         // Inicia o barramento UART0 USB PC
  Serial2.begin(9600, SERIAL_8N1, RXD2, TXD2);  // Inicia o barramento UART2 LoRa
  
  // Inicializa o barramento SPI nos pinos definidos
  SPI.begin(pino_sck, pino_miso, pino_mosi, pino_cs);
  
  // Configura o pino CS como saída e garante que ele comece desligado (HIGH)
  pinMode(pino_cs, OUTPUT);
  digitalWrite(pino_cs, HIGH);
  
  Serial.println("ESP32 Mestre iniciado. Aguardando dados...");
}

void loop() {
  // Sabemos que a mensagem do Nano tem 23 caracteres (incluindo o terminador nulo \0)
  int tamanho_mensagem = 64; 
  char buffer_recebido[tamanho_mensagem];
  
  // Inicia a transação a 1MHz (1000000 Hz), MSB primeiro, Modo 0
  SPI.beginTransaction(SPISettings(1000000, MSBFIRST, SPI_MODE0));
  
  // Baixa o pino CS para iniciar a comunicação (chama a atenção do Nano)
  digitalWrite(pino_cs, LOW);
  
  delayMicroseconds(10); // ADICIONE ESTA LINHA: Dá 10 microssegundos para o Nano se preparar

  // Faz um laço para "puxar" byte a byte
  for (int i = 0; i < tamanho_mensagem; i++) {
    // SPI.transfer(0x00) envia um byte vazio apenas para gerar o clock
    // e retorna o byte que estava engatilhado no Nano
    buffer_recebido[i] = SPI.transfer(0x00); 
    
    // Dá tempo ao ATmega328P para processar a interrupção e carregar o próximo byte
    delayMicroseconds(10); 
  }
  
  // Sobe o pino CS para encerrar a comunicação
  digitalWrite(pino_cs, HIGH);
  
  // Encerra a transação SPI
  SPI.endTransaction();
  
  // Garante que a string recebida termina com um caractere nulo
  buffer_recebido[tamanho_mensagem - 1] = '\0';
  
  // Imprime o que recebeu
  Serial.print("A,");
  Serial2.print("A,");
  Serial.print(buffer_recebido);
  Serial2.print(buffer_recebido);
  Serial.println(",A");
  Serial2.println(",A");
  
  //delay(500); // Aguarda 2 segundos antes do próximo pedido
}