#include <SPI.h>
#include <FS.h>
#include <SD.h>
#include <mcp2515.h>

// ==========================================
// DEFINIÇÃO DE PINOS - BARRAMENTO VSPI (NÚCLEO 1)
// ==========================================
// Usado para o Cartão SD e o Arduino Nano
const int pino_sck_vspi = 18;
const int pino_miso_vspi = 19;
const int pino_mosi_vspi = 23;
const int pino_cs_sd = 5;    
const int pino_cs_nano = 22;  

// ==========================================
// DEFINIÇÃO DE PINOS - BARRAMENTO HSPI (NÚCLEO 0)
// ==========================================
// Usado EXCLUSIVAMENTE para o MCP2515
const int pino_sck_hspi = 25;
const int pino_miso_hspi = 26;
const int pino_mosi_hspi = 27;
const int pino_cs_mcp = 21;   

// Pinos UART2 para o Módulo LoRa
#define RXD2 16
#define TXD2 17
#define PIN_M0 32
#define PIN_M1 33

// ==========================================
// INSTÂNCIAS SPI E CAN
// ==========================================
SPIClass hspi(HSPI); // Instanciando o barramento HSPI globalmente
MCP2515 mcp2515(pino_cs_mcp, 10000000, &hspi); // Pino CS, Clock SPI (10MHz), Ponteiro do Barramento
struct can_frame canMsg;

// ==========================================
// VARIÁVEIS CAN (VOLATILE)
// ==========================================
// O termo 'volatile' avisa ao ESP32 que essas variáveis podem ser 
// modificadas a qualquer microssegundo pela Task do Core 0.
volatile float engine_speed = 0;       
volatile float map_press = 0;          
volatile float iat = 0;                
volatile float clt = 0;                
volatile float tps = 0;                
volatile float lambda1 = 0;            
volatile float oil_press = 0;          
volatile float fuel_press = 0;         

volatile uint16_t ecu_uptime = 0;      
volatile float aux1_v = 0, aux2_v = 0, aux3_v = 0;
volatile float aux4_v = 0, aux5_v = 0, aux6_v = 0, aux7_v = 0;
volatile float aux8_v = 0, aux9_v = 0;
volatile float aux_out3_perc = 0, aux_out6_perc = 0;
volatile int16_t launch_control = 0;   
volatile float battery_v = 0;          
volatile uint16_t gps_date_utc = 0;    
volatile int16_t gps_lat = 0, gps_lon = 0; 
volatile float gps_speed = 0;          
volatile uint16_t gps_time_utc = 0;    

// ==========================================
// CONTROLE DE TEMPO DA TELEMETRIA
// ==========================================
unsigned long tempo_ultima_leitura = 0;
// 62 ms equivale a aproximadamente 16 mensagens por segundo (16Hz)
const unsigned long intervalo_telemetria = 62; 

// Declaração da Task do FreeRTOS
TaskHandle_t TaskCAN_Handle;

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
// TASK DO FREERTOS (RODA NO NÚCLEO 0)
// ==========================================
void TaskLeituraCAN(void *pvParameters) {
  Serial.print("Task CAN rodando no núcleo: ");
  Serial.println(xPortGetCoreID());

  for (;;) { // Loop infinito da Task
    
    // Esvazia o buffer do MCP2515 o mais rápido possível
    while (mcp2515.readMessage(&canMsg) == MCP2515::ERROR_OK) {
      if (canMsg.can_id == 0x1E0 && canMsg.can_dlc == 8) {
        uint8_t index = canMsg.data[0]; 
        switch (index) {
          case 2: engine_speed = getRaw16Motorola(canMsg.data[2], canMsg.data[3]) * 1.0; break;
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
    
    // DELAY OBRIGATÓRIO (Alimenta o Watchdog Timer do ESP32 para não travar o núcleo)
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
  
  // 1. ISOLAMENTO DOS PINOS CS
  pinMode(pino_cs_sd, OUTPUT);   digitalWrite(pino_cs_sd, HIGH);
  pinMode(pino_cs_nano, OUTPUT); digitalWrite(pino_cs_nano, HIGH);
  pinMode(pino_cs_mcp, OUTPUT);  digitalWrite(pino_cs_mcp, HIGH);

  // 2. INICIALIZAÇÃO DO VSPI (Padrão) - NÚCLEO 1
  SPI.begin(pino_sck_vspi, pino_miso_vspi, pino_mosi_vspi);

  // 3. INICIALIZAÇÃO DO HSPI - NÚCLEO 0
  // Usando a instância direta em vez do ponteiro
  hspi.begin(pino_sck_hspi, pino_miso_hspi, pino_mosi_hspi, pino_cs_mcp);

  // 4. INICIALIZAÇÃO DO MCP2515
  Serial.print("Inicializando MCP2515 no HSPI... ");
  // A linha 'setSPI' foi removida, o objeto já foi linkado nas variáveis globais!
  mcp2515.reset();

  if (mcp2515.setBitrate(CAN_500KBPS, MCP_8MHZ) != MCP2515::ERROR_OK) {
    Serial.println("ERRO de Bitrate no CAN!");
  }
  if (mcp2515.setListenOnlyMode() == MCP2515::ERROR_OK) {
    Serial.println("MCP2515 OK.");
  } else {
    Serial.println("FALHA no MCP2515!");
  }

  // 5. INICIALIZAÇÃO DO CARTÃO SD (No VSPI)
  Serial.print("Inicializando SD Card no VSPI... ");
  if (!SD.begin(pino_cs_sd, SPI, 4000000)) {
    Serial.println("FALHA no SD Card!");
  } else {
    Serial.println("SD Card OK.");
  }

  // 6. CRIANDO A TASK DO FREERTOS (NÚCLEO 0)
  xTaskCreatePinnedToCore(
    TaskLeituraCAN,     // Função que a Task vai executar
    "Task_CAN",         // Nome da Task
    4096,               // Tamanho da pilha (Stack) em bytes
    NULL,               // Parâmetros passados para a Task
    1,                  // Prioridade da Task (1 é uma prioridade padrão)
    &TaskCAN_Handle,    // Handle da Task
    0                   // Núcleo onde ela vai rodar (Core 0)
  );

  Serial.print("Setup finalizado no núcleo: ");
  Serial.println(xPortGetCoreID()); // Deve imprimir 1
}

// ==========================================
// LOOP PRINCIPAL (RODA NO NÚCLEO 1)
// ==========================================
void loop() {
  
  // Gatilho de tempo para respeitar o intervalo de ~16Hz (62ms)
  if (millis() - tempo_ultima_leitura >= intervalo_telemetria) {
    tempo_ultima_leitura = millis(); 

    // ========================================================
    // 1. LEITURA DOS DADOS DO NANO VIA VSPI
    // ========================================================
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

    // ========================================================
    // 2. MONTAR A MENSAGEM FINAL
    // ========================================================
    String string_nano = String(buffer_recebido);
    string_nano.trim(); 

    // Lendo as variáveis 'volatile' que estão sendo atualizadas pelo Core 0
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

    // ========================================================
    // 3. GRAVAÇÃO NO CARTÃO SD (VSPI)
    // ========================================================
    File arquivo = SD.open("/log_telemetry.txt", FILE_APPEND);
    if (arquivo) {
      arquivo.println(dado_final);
      arquivo.close();
    } else {
      Serial.println("Erro SD");
    }

    // ========================================================
    // 4. ENVIO VIA LORA (UART2)
    // ========================================================
    Serial.print("A,");
    Serial.print(dado_final);
    Serial.println(",A");

    Serial2.print("A,");
    Serial2.print(dado_final);
    Serial2.println(",A");
  }
}