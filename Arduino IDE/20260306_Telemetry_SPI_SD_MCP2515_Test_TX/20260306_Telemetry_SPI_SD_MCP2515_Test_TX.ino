#include <SPI.h>
#include <FS.h>
#include <SD.h>
#include <mcp2515.h>

// ==========================================
// VARIÁVEIS DE CONTROLE DE TEMPO (Adicione no início do código, antes do setup)
// ==========================================
unsigned long tempo_ultima_leitura = 250;
const unsigned long intervalo_telemetria = 1; // Atualiza a cada 100 milissegundos (10Hz). Ajuste conforme a necessidade.

// ==========================================
// DEFINIÇÃO DE PINOS
// ==========================================
// Pinos do barramento VSPI
const int pino_sck = 18;
const int pino_miso = 19;
const int pino_mosi = 23;

// Pinos CS (Chip Select) individuais
const int pino_cs_sd = 5;    // Módulo Cartão SD
const int pino_cs_nano = 22;  // Arduino Nano
const int pino_cs_mcp = 21;   // Módulo MCP2515 CAN

// Pinos UART2 para o Módulo LoRa
#define RXD2 16
#define TXD2 17

// ==========================================
// INSTÂNCIAS E VARIÁVEIS CAN
// ==========================================
MCP2515 mcp2515(pino_cs_mcp);
struct can_frame canMsg;

// Variáveis da Mensagem Principal (0x1E0)
float engine_speed = 0;       // RPM
float map_press = 0;          // kPa
float iat = 0;                // °C
float clt = 0;                // °C
float tps = 0;                // %
float lambda1 = 0;            // Lambda
float oil_press = 0;          // bar
float fuel_press = 0;         // bar

// Variáveis da CAN Custom (IDs 59 a 63)
int16_t ecu_uptime = 0;      
float aux1_v = 0, aux2_v = 0, aux3_v = 0;
float aux4_v = 0, aux5_v = 0, aux6_v = 0, aux7_v = 0;
float aux8_v = 0, aux9_v = 0;
float aux_out3_perc = 0, aux_out6_perc = 0;
int16_t launch_control = 0;   
float battery_v = 0;          
uint16_t gps_date_utc = 0;    
int16_t gps_lat = 0, gps_lon = 0; 
float gps_speed = 0;          
uint16_t gps_time_utc = 0;    

// ==========================================
// FUNÇÕES DE DECODIFICAÇÃO (ENDIANNESS)
// ==========================================
int16_t getRaw16Motorola(uint8_t byteMSB, uint8_t byteLSB) {
  return (int16_t)((byteMSB << 8) | byteLSB);
}

int16_t getRaw16Intel(uint8_t byteLSB, uint8_t byteMSB) {
  return (int16_t)((byteMSB << 8) | byteLSB);
}

uint16_t getUnsignedRaw16Intel(uint8_t byteLSB, uint8_t byteMSB) {
  return (uint16_t)((byteMSB << 8) | byteLSB);
}

// ==========================================
// SETUP
// ==========================================
void setup() {
  Serial.begin(115200);
  Serial2.begin(9600, SERIAL_8N1, RXD2, TXD2);
  
  // 1. ISOLAMENTO DOS PINOS CS (MUITO IMPORTANTE)
  // Define todos os CS como saída e nível HIGH antes de ligar o SPI
  pinMode(pino_cs_sd, OUTPUT);   digitalWrite(pino_cs_sd, HIGH);
  pinMode(pino_cs_nano, OUTPUT); digitalWrite(pino_cs_nano, HIGH);
  pinMode(pino_cs_mcp, OUTPUT);  digitalWrite(pino_cs_mcp, HIGH);

  // 2. INICIALIZAÇÃO DO BARRAMENTO SPI
  SPI.begin(pino_sck, pino_miso, pino_mosi);

  // 3. INICIALIZAÇÃO DO CARTÃO SD
  Serial.print("Inicializando SD Card... ");
  if (!SD.begin(pino_cs_sd, SPI, 4000000)) {
    Serial.println("FALHA no SD Card!");
  } else {
    Serial.println("SD Card OK.");
  }

  // 4. INICIALIZAÇÃO DO MCP2515
  Serial.print("Inicializando MCP2515... ");
  mcp2515.reset();
  if (mcp2515.setBitrate(CAN_500KBPS, MCP_8MHZ) != MCP2515::ERROR_OK) {
    Serial.println("ERRO de Bitrate no CAN!");
  }
  if (mcp2515.setListenOnlyMode() == MCP2515::ERROR_OK) {
    Serial.println("MCP2515 OK.");
  } else {
    Serial.println("FALHA CRÍTICA no MCP2515!");
  }

  Serial.println("Sistema de Telemetria Iniciado.");
}

// ==========================================
// LOOP PRINCIPAL
// ==========================================
void loop() {
  
  // ========================================================
  // 2. LEITURA DO BARRAMENTO CAN (MCP2515)
  // ========================================================
  // Usamos 'while' para esvaziar o buffer e pegar os dados mais recentes
  while (mcp2515.readMessage(&canMsg) == MCP2515::ERROR_OK) {
    
    if (canMsg.can_id == 0x1E0 && canMsg.can_dlc == 8) {
      uint8_t index = canMsg.data[0]; 
      switch (index) {
        case 2:
          engine_speed = getRaw16Motorola(canMsg.data[2], canMsg.data[3]);
          break;
        case 5:
          map_press = getRaw16Motorola(canMsg.data[2], canMsg.data[3]) * 0.1;
          iat = getRaw16Motorola(canMsg.data[4], canMsg.data[5]) * 0.1;
          clt = getRaw16Motorola(canMsg.data[6], canMsg.data[7]) * 0.1;
          break;
        case 6:
          tps = getRaw16Motorola(canMsg.data[2], canMsg.data[3]) * 0.1;
          lambda1 = getRaw16Motorola(canMsg.data[6], canMsg.data[7]) * 0.001;
          break;
        case 15:
          oil_press = getRaw16Motorola(canMsg.data[2], canMsg.data[3]) * 0.01;
          fuel_press = getRaw16Motorola(canMsg.data[4], canMsg.data[5]) * 0.01;
          break;
      }
    }
    else if (canMsg.can_id == 59 && canMsg.can_dlc == 8) {
      ecu_uptime = getUnsignedRaw16Intel(canMsg.data[0], canMsg.data[1]);
      aux1_v = getRaw16Intel(canMsg.data[2], canMsg.data[3]) * 0.01;
      aux2_v = getRaw16Intel(canMsg.data[4], canMsg.data[5]) * 0.01;
      aux3_v = getRaw16Intel(canMsg.data[6], canMsg.data[7]) * 0.01;
    }
    else if (canMsg.can_id == 60 && canMsg.can_dlc == 8) {
      aux4_v = getRaw16Intel(canMsg.data[0], canMsg.data[1]) * 0.01;
      aux5_v = getRaw16Intel(canMsg.data[2], canMsg.data[3]) * 0.01;
      aux6_v = getRaw16Intel(canMsg.data[4], canMsg.data[5]) * 0.01;
      aux7_v = getRaw16Intel(canMsg.data[6], canMsg.data[7]) * 0.01;
    }
    else if (canMsg.can_id == 61 && canMsg.can_dlc == 8) {
      aux8_v = getRaw16Intel(canMsg.data[0], canMsg.data[1]) * 0.01;
      aux9_v = getRaw16Intel(canMsg.data[2], canMsg.data[3]) * 0.01;
      aux_out3_perc = getRaw16Intel(canMsg.data[4], canMsg.data[5]) * 0.1;
      aux_out6_perc = getRaw16Intel(canMsg.data[6], canMsg.data[7]) * 0.1;
    }
    else if (canMsg.can_id == 62 && canMsg.can_dlc == 8) {
      launch_control = getRaw16Intel(canMsg.data[0], canMsg.data[1]);
      battery_v = getRaw16Intel(canMsg.data[2], canMsg.data[3]) * 0.1; 
      gps_date_utc = getUnsignedRaw16Intel(canMsg.data[4], canMsg.data[5]);
    }
    else if (canMsg.can_id == 63 && canMsg.can_dlc == 8) {
      gps_lat = getRaw16Intel(canMsg.data[0], canMsg.data[1]);
      gps_lon = getRaw16Intel(canMsg.data[2], canMsg.data[3]);
      gps_speed = getRaw16Intel(canMsg.data[4], canMsg.data[5]) * 0.1;
      gps_time_utc = getUnsignedRaw16Intel(canMsg.data[6], canMsg.data[7]);
    }
  }

  // ========================================================
  // 2. GATILHO TEMPORIZADO PARA NANO, SD E LORA
  // ========================================================
  // Só entra neste bloco a cada 'intervalo_telemetria' (ex: 100ms)
  if (millis() - tempo_ultima_leitura >= intervalo_telemetria) {
    tempo_ultima_leitura = millis(); // Reseta o cronômetro

    // --- A. LEITURA DOS DADOS DO NANO VIA SPI ---
    int tamanho_mensagem = 64; 
    char buffer_recebido[tamanho_mensagem];
    
    SPI.beginTransaction(SPISettings(1000000, MSBFIRST, SPI_MODE0));
    digitalWrite(pino_cs_nano, LOW);
    delayMicroseconds(10); 

    for (int i = 0; i < tamanho_mensagem; i++) {
      buffer_recebido[i] = SPI.transfer(0x00); 
      delayMicroseconds(10); 
    }
    
    digitalWrite(pino_cs_nano, HIGH);
    SPI.endTransaction();
    buffer_recebido[tamanho_mensagem - 1] = '\0'; 

    // --- B. MONTAR A MENSAGEM FINAL ---
    String string_nano = String(buffer_recebido);
    string_nano.trim();

    String string_can = String(ecu_uptime) + "," +
                      String(engine_speed) + "," +
                      String(map_press, 1) + "," +
                      String(iat, 1) + "," +
                      String(clt, 1) + "," +
                      String(tps, 1) + "," +
                      String(lambda1, 3) + "," +
                      String(oil_press, 2) + "," +
                      String(fuel_press, 2) + "," +
                      String(aux1_v, 2) + "," +
                      String(aux2_v, 2) + "," +
                      String(aux3_v, 2) + "," +
                      String(aux4_v, 2) + "," +
                      String(aux5_v, 2) + "," +
                      String(aux6_v, 2) + "," +
                      String(aux7_v, 2) + "," +
                      String(aux8_v, 2) + "," +
                      String(aux9_v, 2) + "," +
                      String(aux_out3_perc, 1) + "," +
                      String(aux_out6_perc, 1) + "," +
                      String(launch_control) + "," +
                      String(battery_v, 1) + "," +
                      String(gps_date_utc) + "," +
                      String(gps_lat, 1) + "," +
                      String(gps_lon, 1) + "," +
                      String(gps_speed, 1) + "," +
                      String(gps_time_utc);

    String dado_final = string_nano + "," + string_can;

    // --- C. GRAVAÇÃO NO CARTÃO SD ---
    File arquivo = SD.open("/log_telemetry.txt", FILE_APPEND);
    if (arquivo) {
      arquivo.println(dado_final);
      arquivo.close();
    } else {
      Serial.println("Erro ao abrir log no SD.");
    }

    // --- D. ENVIO DOS DADOS VIA LORA E MONITOR SERIAL ---
    Serial.print("A,");
    Serial.print(dado_final);
    Serial.println(",A");

    Serial2.print("A,");
    Serial2.print(dado_final);
    Serial2.println(",A");
  } 
}