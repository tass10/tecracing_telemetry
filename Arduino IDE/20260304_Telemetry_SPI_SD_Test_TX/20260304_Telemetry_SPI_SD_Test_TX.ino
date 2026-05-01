#include <SPI.h>
#include <FS.h>
#include <SD.h>

// Definindo os pinos do barramento VSPI
const int pino_sck = 18;
const int pino_miso = 19;
const int pino_mosi = 23;

// ATENÇÃO: Pinos CS (Chip Select) separados para cada dispositivo!
const int pino_cs_sd = 5;    // Fio CS do Módulo Cartão SD
const int pino_cs_nano = 22;  // Fio CS do Arduino Nano (MUDAR PARA ESTE PINO)

// Definindo os pinos do barramento UART2 para comunicar com o Módulo LoRa
#define RXD2 16
#define TXD2 17

void setup() {
  Serial.begin(115200);                         // Inicia o barramento UART0 USB PC
  Serial2.begin(9600, SERIAL_8N1, RXD2, TXD2);  // Inicia o barramento UART2 LoRa
  
  // Inicializa o barramento SPI
  // O último parâmetro aqui não importa muito agora pois controlaremos os CS manualmente/pela biblioteca
  SPI.begin(pino_sck, pino_miso, pino_mosi, pino_cs_nano);
  
  // Configura o pino CS do NANO como saída e garante que ele comece desligado (HIGH)
  pinMode(pino_cs_nano, OUTPUT);
  digitalWrite(pino_cs_nano, HIGH);
  
  // Inicializa o Cartão SD
  Serial.print("Inicializando SD Card... ");
  // Utiliza a velocidade de 4MHz que sabemos que é estável para o módulo
  if (!SD.begin(pino_cs_sd, SPI, 4000000)) {
    Serial.println("Falha ao montar o SD Card!");
  } else {
    Serial.println("SD Card inicializado com sucesso.");
  }
  
  Serial.println("ESP32 Mestre iniciado. Aguardando dados...");
}

void loop() {
  // Sabemos que a mensagem do Nano tem 23 caracteres (incluindo o terminador nulo \0)
  int tamanho_mensagem = 64; 
  char buffer_recebido[tamanho_mensagem];
  
  // ========================================================
  // 1. LEITURA DOS DADOS DO NANO VIA SPI
  // ========================================================

  // Inicia a transação a 1MHz (1000000 Hz), MSB primeiro, Modo 0
  SPI.beginTransaction(SPISettings(1000000, MSBFIRST, SPI_MODE0));
  
  // Baixa o pino CS para iniciar a comunicação (chama a atenção do Nano)
  digitalWrite(pino_cs_nano, LOW);
  
  delayMicroseconds(10); // ADICIONE ESTA LINHA: Dá 10 microssegundos para o Nano se preparar

  // Faz um laço para "puxar" byte a byte
  for (int i = 0; i < tamanho_mensagem; i++) {
    // SPI.transfer(0x00) envia um byte vazio apenas para gerar o clock
    // e retorna o byte que estava engatilhado no Nano
    buffer_recebido[i] = SPI.transfer(0x00); 
    
    // Dá tempo ao ATmega328P para processar a interrupção e carregar o próximo byte
    delayMicroseconds(10); 
  }
  
  // Sobe o pino CS para encerrar a comunicação EXCLUSIVA com o Nano
  digitalWrite(pino_cs_nano, HIGH);
  
  // Encerra a transação SPI
  SPI.endTransaction();
  
  // Garante que a string recebida termina com um caractere nulo
  buffer_recebido[tamanho_mensagem - 1] = '\0';
  
  // ========================================================
  // 2. GRAVAÇÃO NO CARTÃO SD
  // ========================================================
  
  // Abre o arquivo em modo FILE_APPEND (Adiciona ao final, não apaga o que já existe)
  File arquivo = SD.open("/log_telemetry.txt", FILE_APPEND);
  
  if (arquivo) {
    // O método println já adiciona o "pulo de linha" (\r\n) no final
    arquivo.println(buffer_recebido);
    arquivo.close(); // Fecha o arquivo para salvar as alterações no disco
    // Serial.println("Dado gravado no SD."); // Descomente se quiser monitorar o sucesso
  } else {
    Serial.println("Erro ao abrir log_telemetry.txt para gravacao.");
  }
  
  // ========================================================
  // 3. ENVIO DOS DADOS VIA SERIAL / LORA
  // ========================================================

  // Imprime o que recebeu
  Serial.print("A,");
  Serial2.print("A,");
  Serial.print(buffer_recebido);
  Serial2.print(buffer_recebido);
  Serial.println(",A");
  Serial2.println(",A");
  
  //delay(500); // Aguarda 2 segundos antes do próximo pedido
}