/* 

TABELA DE PARÂMETROS

Air Data Rate (Taxa de dados pelo ar)
Quanto menor a taxa, maior a distância de alcance, mas menor a velocidade.

AIR_DATA_RATE_000_03 (0.3 kbps - Alcance Máximo)

AIR_DATA_RATE_001_12 (1.2 kbps)

AIR_DATA_RATE_010_24 (2.4 kbps)

AIR_DATA_RATE_011_48 (4.8 kbps)

AIR_DATA_RATE_100_96 (9.6 kbps)

AIR_DATA_RATE_101_192 (19.2 kbps)

AIR_DATA_RATE_110_384 (38.4 kbps)

AIR_DATA_RATE_111_625 (62.5 kbps - Menor alcance, maior velocidade de dados)

Potência de Transmissão (Transmission Power)
Como você declarou #define E22_30 no topo, o módulo usa a escala de 30dBm.

POWER_30 (30dBm / 1 Watt - Alcance Máximo, alto consumo)

POWER_27 (27dBm)

POWER_24 (24dBm)

POWER_21 (21dBm / ~125mW - Menor alcance, baixo consumo)

Tamanho do Sub-Pacote (Sub Packet Setting)

SPS_240_00 (240 bytes por pacote - Padrão)

SPS_128_01 (128 bytes)

SPS_064_10 (64 bytes)

SPS_032_11 (32 bytes - Útil para pacotes menores e menos latência em redes)

Habilitações de Status (Bits - 0 ou 1)
Para enableRepeater, enableLBT, enableRSSI e RSSIAmbientNoise:

0 = Disable (Desativado)

1 = Enable (Ativado) */



#include <Arduino.h>

// 1. OBRIGATÓRIO: Definir a versão de 30dBm ANTES de incluir a biblioteca
#define E22_30 
#include "LoRa_E22.h"

// Definição dos pinos do UART2 no ESP32
#define RX2_PIN 16 
#define TX2_PIN 17 

// Definição dos pinos de controle do E22
#define PIN_M0 32
#define PIN_M1 33
#define PIN_AUX 35 // O pino AUX é essencial. Altere conforme a sua montagem.

HardwareSerial mySerial(2);

// Instancia o objeto LoRa
LoRa_E22 e22(&mySerial, PIN_AUX, PIN_M0, PIN_M1);

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("Iniciando configuracao do E22-400T30D...");

  // Inicia a comunicação com o LoRa no Baud Rate atual dele (padrão de fábrica é 9600)
  mySerial.begin(9600, SERIAL_8N1, RX2_PIN, TX2_PIN);

  e22.begin();

  // Lê a configuração atual do módulo
  ResponseStructContainer c;
  c = e22.getConfiguration();

  if (c.status.code != 1) {
    Serial.println("Erro ao ler as configuracoes! Verifique a fiacao e o Baud Rate atual.");
    return;
  }

  Configuration configuration = *(Configuration*) c.data;

  // ---------------------------------------------------------
  // AJUSTANDO OS PARÂMETROS DO LORA
  // ---------------------------------------------------------
// 1. Endereço e Network ID
  configuration.ADDH = 0;           // Byte alto do endereço (0)
  configuration.ADDL = 88;          // Byte baixo do endereço (88)
  configuration.NETID = 0;          // ID da rede (0)

  // 2. Chave de Criptografia (Key = 0)
  configuration.CRYPT.CRYPT_H = 0; 
  configuration.CRYPT.CRYPT_L = 0;

  // 3. Frequência / Canal (Canal 59)
  // Como a base é 410MHz, Canal 59 = 469 MHz
  configuration.CHAN = 59;          

  // 4. Velocidades (Baud Rate 115200 e Air Rate 62.5 kbps)
  configuration.SPED.uartBaudRate = UART_BPS_115200; 
  configuration.SPED.uartParity   = MODE_00_8N1; 
  configuration.SPED.airDataRate  = AIR_DATA_RATE_111_625; 

  // 5. Modo de Transmissão e Funcionalidades
  configuration.TRANSMISSION_MODE.fixedTransmission = 0; // 0 = Modo Transparente (Normal), 1 = Fixo
  configuration.TRANSMISSION_MODE.enableRepeater    = 0; // 0 = Disable Relay
  configuration.TRANSMISSION_MODE.enableLBT         = 0; // 0 = Disable LBT (Listen Before Talk)
  configuration.TRANSMISSION_MODE.enableRSSI        = 1; // 0 = Disable Packet RSSI

  // 6. Opções (Potência 21dBm, Pacote 240 bytes e Channel RSSI)
  configuration.OPTION.transmissionPower = POWER_21;  // Potência = 21dBm
  configuration.OPTION.subPacketSetting  = SPS_240_00; // Tamanho do pacote = 240 bytes
  configuration.OPTION.RSSIAmbientNoise  = 0;          // 0 = Disable Channel RSSI
  
  // Salva a configuração de forma permanente
  ResponseStatus rs = e22.setConfiguration(configuration, WRITE_CFG_PWR_DWN_SAVE);

  Serial.print("Status da gravacao: ");
  Serial.println(rs.getResponseDescription());

  c.close(); 

  if(rs.code == 1) {
      Serial.println("Configuracao concluida!");
  }
}

void loop() {
  // Nada no loop para o script de configuração
}