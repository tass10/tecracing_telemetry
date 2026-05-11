// Código utilizado no  ESP32 do Sistema Transmissor durante o teste de comunicação enviando 1.000 mensagens

#include <SPI.h>
#include <FS.h>
#include <SD.h>
#include <mcp2515.h>
#include <Wire.h>
#include <Adafruit_ADS1X15.h> // Inclua a biblioteca do ADS1115

// ==========================================
// ESTRUTURA DE DADOS BINÁRIA (73 BYTES)
// ==========================================
typedef struct __attribute__((packed)) {
  uint8_t header[2]; // 0xAA, 0x55
  
  // Variáveis dos ADS1115 (8 variáveis de 16-bits)
  int16_t a0;
  int16_t a1;
  int16_t a2;
  int16_t a3;
  int16_t a4;
  int16_t a5;
  int16_t a6;
  int16_t a7;

  // Variáveis do CAN (27 variáveis)
  uint16_t ecu_uptime;
  int16_t engine_speed;
  int16_t map_press;      
  int16_t iat;            
  int16_t clt;            
  int16_t tps;            
  int16_t lambda1;        
  int16_t oil_press;      
  int16_t fuel_press;     
  int16_t aux1_v;         
  int16_t aux2_v;         
  int16_t aux3_v;         
  int16_t aux4_v;         
  int16_t aux5_v;         
  int16_t aux6_v;         
  int16_t aux7_v;         
  int16_t aux8_v;         
  int16_t aux9_v;         
  int16_t aux_out3_perc;  
  int16_t aux_out6_perc;  
  int16_t launch_control; 
  int16_t battery_v;      
  uint16_t gps_date_utc;
  int16_t gps_lat;
  int16_t gps_lon;
  int16_t gps_speed;      
  uint16_t gps_time_utc;

  uint8_t checksum;
} PacoteTelemetria;

PacoteTelemetria pacote_tx; 

// ==========================================
// DEFINIÇÃO DE PINOS - BARRAMENTO VSPI (NÚCLEO 1)
// ==========================================
const int pino_sck_vspi = 18;
const int pino_miso_vspi = 19;
const int pino_mosi_vspi = 23;
const int pino_cs_sd = 5;    

// ==========================================
// DEFINIÇÃO DE PINOS - BARRAMENTO HSPI (NÚCLEO 0)
// ==========================================
const int pino_sck_hspi = 25;
const int pino_miso_hspi = 26;
const int pino_mosi_hspi = 27;
const int pino_cs_mcp = 21;   

// ==========================================
// DEFINIÇÃO DE PINOS - BARRAMENTO I2C (ADS1115)
// ==========================================
const int PIN_SDA = 22;
const int PIN_SCL = 4;

// Pinos UART2 para o Módulo LoRa
#define RXD2 16
#define TXD2 17
#define PIN_M0 32
#define PIN_M1 33

const int amostras = 1000;
int i=0;

// ==========================================
// INSTÂNCIAS SPI, CAN E I2C
// ==========================================
SPIClass hspi(HSPI); 
MCP2515 mcp2515(pino_cs_mcp, 10000000, &hspi); 
struct can_frame canMsg;

Adafruit_ADS1115 ads1; // Instância do ADS 1
Adafruit_ADS1115 ads2; // Instância do ADS 2

// ==========================================
// VARIÁVEIS CAN (VOLATILE)
// ==========================================
volatile int16_t engine_speed = 0;       
volatile int16_t map_press = 0;          
volatile int16_t iat = 0;                
volatile int16_t clt = 0;                
volatile int16_t tps = 0;                
volatile int16_t lambda1 = 0;            
volatile int16_t oil_press = 0;          
volatile int16_t fuel_press = 0;         

volatile uint16_t ecu_uptime = 0;      
volatile int16_t aux1_v = 0, aux2_v = 0, aux3_v = 0;
volatile int16_t aux4_v = 0, aux5_v = 0, aux6_v = 0, aux7_v = 0;
volatile int16_t aux8_v = 0, aux9_v = 0;
volatile int16_t aux_out3_perc = 0, aux_out6_perc = 0;
volatile int16_t launch_control = 0;   
volatile int16_t battery_v = 0;          
volatile uint16_t gps_date_utc = 0;    
volatile int16_t gps_lat = 0, gps_lon = 0; 
volatile int16_t gps_speed = 0;          
volatile uint16_t gps_time_utc = 0;    

// ==========================================
// CONTROLE DE TEMPO DA TELEMETRIA
// ==========================================
unsigned long tempo_ultima_leitura = 0;
const unsigned long intervalo_telemetria = 100; 

TaskHandle_t TaskCAN_Handle;

// ==========================================
// FUNÇÕES DE DECODIFICAÇÃO (ENDIANNESS) E CHECKSUM
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

uint8_t calcularChecksum(uint8_t* dados, size_t tamanho_sem_checksum) {
  uint8_t ck = 0;
  for (size_t i = 0; i < tamanho_sem_checksum; i++) {
    ck ^= dados[i];
  }
  return ck;
}

// ==========================================
// TASK DO FREERTOS (RODA NO NÚCLEO 0) - INTACTA
// ==========================================
void TaskLeituraCAN(void *pvParameters) {
  for (;;) { 
    while (mcp2515.readMessage(&canMsg) == MCP2515::ERROR_OK) {
      if (canMsg.can_id == 0x1E0 && canMsg.can_dlc == 8) {
        uint8_t index = canMsg.data[0]; 
        switch (index) {
          case 2: engine_speed = getRaw16Motorola(canMsg.data[2], canMsg.data[3]); break;
          case 5:
            map_press = getRaw16Motorola(canMsg.data[2], canMsg.data[3]);
            iat = getRaw16Motorola(canMsg.data[4], canMsg.data[5]);
            clt = getRaw16Motorola(canMsg.data[6], canMsg.data[7]);
            break;
          case 6:
            tps = getRaw16Motorola(canMsg.data[2], canMsg.data[3]);
            lambda1 = getRaw16Motorola(canMsg.data[6], canMsg.data[7]);
            break;
          case 15:
            oil_press = getRaw16Motorola(canMsg.data[2], canMsg.data[3]);
            fuel_press = getRaw16Motorola(canMsg.data[4], canMsg.data[5]);
            break;
        }
      }
      else if (canMsg.can_id == 59 && canMsg.can_dlc == 8) {
        ecu_uptime = getUnsignedRaw16Intel(canMsg.data[0], canMsg.data[1]);
        aux1_v = getRaw16Intel(canMsg.data[2], canMsg.data[3]);
        aux2_v = getRaw16Intel(canMsg.data[4], canMsg.data[5]);
        aux3_v = getRaw16Intel(canMsg.data[6], canMsg.data[7]);
      }
      else if (canMsg.can_id == 60 && canMsg.can_dlc == 8) {
        aux4_v = getRaw16Intel(canMsg.data[0], canMsg.data[1]);
        aux5_v = getRaw16Intel(canMsg.data[2], canMsg.data[3]);
        aux6_v = getRaw16Intel(canMsg.data[4], canMsg.data[5]);
        aux7_v = getRaw16Intel(canMsg.data[6], canMsg.data[7]);
      }
      else if (canMsg.can_id == 61 && canMsg.can_dlc == 8) {
        aux8_v = getRaw16Intel(canMsg.data[0], canMsg.data[1]);
        aux9_v = getRaw16Intel(canMsg.data[2], canMsg.data[3]);
        aux_out3_perc = getRaw16Intel(canMsg.data[4], canMsg.data[5]);
        aux_out6_perc = getRaw16Intel(canMsg.data[6], canMsg.data[7]);
      }
      else if (canMsg.can_id == 62 && canMsg.can_dlc == 8) {
        launch_control = getRaw16Intel(canMsg.data[0], canMsg.data[1]);
        battery_v = getRaw16Intel(canMsg.data[2], canMsg.data[3]); 
        gps_date_utc = getUnsignedRaw16Intel(canMsg.data[4], canMsg.data[5]);
      }
      else if (canMsg.can_id == 63 && canMsg.can_dlc == 8) {
        gps_lat = getRaw16Intel(canMsg.data[0], canMsg.data[1]);
        gps_lon = getRaw16Intel(canMsg.data[2], canMsg.data[3]);
        gps_speed = getRaw16Intel(canMsg.data[4], canMsg.data[5]);
        gps_time_utc = getUnsignedRaw16Intel(canMsg.data[6], canMsg.data[7]);
      }
    }
    vTaskDelay(pdMS_TO_TICKS(1)); 
  }
}

// ==========================================
// SETUP
// ==========================================
void setup() {
  Serial.begin(115200);

  pinMode(PIN_M0, OUTPUT);  digitalWrite(PIN_M0, LOW);
  pinMode(PIN_M1, OUTPUT);  digitalWrite(PIN_M1, LOW);
  Serial2.begin(115200, SERIAL_8N1, RXD2, TXD2); 
  
  pinMode(pino_cs_sd, OUTPUT);   digitalWrite(pino_cs_sd, HIGH);
  pinMode(pino_cs_mcp, OUTPUT);  digitalWrite(pino_cs_mcp, HIGH);

  SPI.begin(pino_sck_vspi, pino_miso_vspi, pino_mosi_vspi);
  hspi.begin(pino_sck_hspi, pino_miso_hspi, pino_mosi_hspi, pino_cs_mcp);

  // ========================================================
  // INICIALIZAÇÃO I2C E ADS1115
  // ========================================================
  Wire.begin(PIN_SDA, PIN_SCL); 
  Wire.setClock(100000); // Barramento em 100 kHz (Estabilidade máxima)
  Wire.setTimeOut(20000); // Tempo limite do I2C
  
  ads1.setDataRate(RATE_ADS1115_860SPS);
  ads2.setDataRate(RATE_ADS1115_860SPS);

  // Passa o &Wire para garantir que a biblioteca use os pinos 22 e 4
  if (!ads1.begin(0x48, &Wire)) { 
    Serial.println("Falha no ADS 1 (0x48)!");
  }
  if (!ads2.begin(0x49, &Wire)) {
    Serial.println("Falha no ADS 2 (0x49)!");
  } else {
    Serial.println("ADS1115 OK.");
  }

  // ========================================================
  // INICIALIZAÇÃO CAN E SD
  // ========================================================
  mcp2515.reset();
  if (mcp2515.setBitrate(CAN_500KBPS, MCP_8MHZ) != MCP2515::ERROR_OK) {
    Serial.println("ERRO de Bitrate no CAN!");
  }
  if (mcp2515.setListenOnlyMode() == MCP2515::ERROR_OK) {
    Serial.println("MCP2515 OK.");
  } else {
    Serial.println("FALHA no MCP2515!");
  }

  if (!SD.begin(pino_cs_sd, SPI, 4000000)) {
    Serial.println("FALHA no SD Card!");
  } else {
    Serial.println("SD Card OK.");
  }

  xTaskCreatePinnedToCore(
    TaskLeituraCAN, "Task_CAN", 4096, NULL, 1, &TaskCAN_Handle, 0
  );

  pacote_tx.header[0] = 0xAA;
  pacote_tx.header[1] = 0x55;
}

// ==========================================
// LOOP PRINCIPAL (RODA NO NÚCLEO 1)
// ==========================================
void loop() {
  if (i < amostras) {
    
    if (millis() - tempo_ultima_leitura >= intervalo_telemetria) {
      tempo_ultima_leitura = millis(); 

      // 1. LEITURA ADS1115
      pacote_tx.a0 = ads1.readADC_SingleEnded(0);
      pacote_tx.a1 = ads1.readADC_SingleEnded(1);
      pacote_tx.a2 = ads1.readADC_SingleEnded(2);
      pacote_tx.a3 = ads1.readADC_SingleEnded(3);
      pacote_tx.a4 = ads2.readADC_SingleEnded(0);
      pacote_tx.a5 = ads2.readADC_SingleEnded(1);
      pacote_tx.a6 = ads2.readADC_SingleEnded(2);
      pacote_tx.a7 = ads2.readADC_SingleEnded(3);

      // 2. POPULAR VARIÁVEIS CAN
      pacote_tx.ecu_uptime = ecu_uptime;
      pacote_tx.engine_speed = engine_speed;
      pacote_tx.map_press = map_press;
      pacote_tx.iat = iat;
      pacote_tx.clt = clt;
      pacote_tx.tps = tps;
      pacote_tx.lambda1 = lambda1;
      pacote_tx.oil_press = oil_press;
      pacote_tx.fuel_press = fuel_press;
      pacote_tx.aux1_v = aux1_v;
      pacote_tx.aux2_v = aux2_v;
      pacote_tx.aux3_v = aux3_v;
      pacote_tx.aux4_v = aux4_v;
      pacote_tx.aux5_v = aux5_v;
      pacote_tx.aux6_v = aux6_v;
      pacote_tx.aux7_v = aux7_v;
      pacote_tx.aux8_v = aux8_v;
      pacote_tx.aux9_v = aux9_v;
      pacote_tx.aux_out3_perc = aux_out3_perc;
      pacote_tx.aux_out6_perc = aux_out6_perc;
      pacote_tx.launch_control = launch_control;
      pacote_tx.battery_v = battery_v;
      pacote_tx.gps_date_utc = gps_date_utc;
      pacote_tx.gps_lat = gps_lat;
      pacote_tx.gps_lon = gps_lon;
      pacote_tx.gps_speed = gps_speed;
      pacote_tx.gps_time_utc = gps_time_utc;

      // Calcula o checksum
      pacote_tx.checksum = calcularChecksum((uint8_t*)&pacote_tx, sizeof(PacoteTelemetria) - 1);

      // 3. ENVIO VIA LORA
      Serial2.write((uint8_t*)&pacote_tx, sizeof(PacoteTelemetria));
      
      // 4. GRAVAÇÃO NO SD
      File arquivo = SD.open("/telemetry.log", FILE_APPEND);
      if (arquivo) {
        arquivo.write((const uint8_t *)&pacote_tx, sizeof(PacoteTelemetria));
        arquivo.close();
      }
      
      i++; // Incrementa o contador apenas quando envia
    }
  } 
}