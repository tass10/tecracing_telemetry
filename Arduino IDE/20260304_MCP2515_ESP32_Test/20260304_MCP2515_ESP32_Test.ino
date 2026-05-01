#include <SPI.h>
#include <mcp2515.h>

const int CS_PIN = 21;
MCP2515 mcp2515(CS_PIN);
struct can_frame canMsg;

// ==========================================
// VARIÁVEIS DA MENSAGEM PRINCIPAL (0x1E0)
// ==========================================
float engine_speed = 0;       // RPM
float map_press = 0;          // kPa
float iat = 0;                // °C
float clt = 0;                // °C
float tps = 0;                // %
float lambda1 = 0;            // Lambda
float oil_press = 0;          // bar
float fuel_press = 0;         // bar

// ==========================================
// VARIÁVEIS DA CAN CUSTOM (IDs 59 a 63)
// ==========================================
// ID 59
uint16_t ecu_uptime = 0;      // Tempo ligado (provavelmente em segundos ou milisegundos)
float aux1_v = 0;             // Volts
float aux2_v = 0;             // Volts
float aux3_v = 0;             // Volts
// ID 60
float aux4_v = 0;             // Volts
float aux5_v = 0;             // Volts
float aux6_v = 0;             // Volts
float aux7_v = 0;             // Volts
// ID 61
float aux8_v = 0;             // Volts
float aux9_v = 0;             // Volts
float aux_out3_perc = 0;      // %
float aux_out6_perc = 0;      // %
// ID 62
int16_t launch_control = 0;   // Sinal de ativação (0 ou 1)
float battery_v = 0;          // Volts
uint16_t gps_date_utc = 0;    // Data GPS Bruta
// ID 63
int16_t gps_lat = 0;          // Latitude Bruta
int16_t gps_lon = 0;          // Longitude Bruta
float gps_speed = 0;          // Velocidade GPS
uint16_t gps_time_utc = 0;    // Tempo GPS Bruto

// ==========================================
// FUNÇÕES DE DECODIFICAÇÃO (ENDIANNESS)
// ==========================================
// Usado na mensagem 0x1E0 (Padrão PRO_TUNE) - O Byte Maior (MSB) vem primeiro
int16_t getRaw16Motorola(uint8_t byteMSB, uint8_t byteLSB) {
  return (int16_t)((byteMSB << 8) | byteLSB);
}

// Usado na CAN Custom - O Byte Menor (LSB) vem primeiro, conforme as imagens
int16_t getRaw16Intel(uint8_t byteLSB, uint8_t byteMSB) {
  return (int16_t)((byteMSB << 8) | byteLSB);
}

// Mesma função Intel, mas para variáveis sem sinal (Tempo, Data) para não dar número negativo
uint16_t getUnsignedRaw16Intel(uint8_t byteLSB, uint8_t byteMSB) {
  return (uint16_t)((byteMSB << 8) | byteLSB);
}


void setup() {
  Serial.begin(115200);
  while (!Serial);
  Serial.println("Iniciando Leitor CAN Principal e Custom...");

  SPI.begin();
  mcp2515.reset();
  
  if (mcp2515.setBitrate(CAN_500KBPS, MCP_8MHZ) != MCP2515::ERROR_OK) {
    Serial.println("Erro ao configurar bitrate!");
  }
  
  // Voltamos para Listen Only pois vamos apenas escutar
  if (mcp2515.setListenOnlyMode() == MCP2515::ERROR_OK) {
    Serial.println("Comunicacao SPI OK! Aguardando mensagens...");
  } else {
    Serial.println("FALHA SPI!");
    while(1);
  }
}

void loop() {
  if (mcp2515.readMessage(&canMsg) == MCP2515::ERROR_OK) {
    
    // ==========================================
    // MENSAGEM PRINCIPAL (ID: 480 / 0x1E0)
    // ==========================================
    if (canMsg.can_id == 0x1E0 && canMsg.can_dlc == 8) {
      uint8_t index = canMsg.data[0]; 
      
      switch (index) {
        case 2:
          engine_speed = getRaw16Motorola(canMsg.data[2], canMsg.data[3]) * 1.0;
          Serial.print("ID 480 | m2"); 
          Serial.print(" | RPM: "); Serial.println(engine_speed, 0);
          break;
        case 5:
          map_press = getRaw16Motorola(canMsg.data[2], canMsg.data[3]) * 0.1;
          iat = getRaw16Motorola(canMsg.data[4], canMsg.data[5]) * 0.1;
          clt = getRaw16Motorola(canMsg.data[6], canMsg.data[7]) * 0.1;
          Serial.print("ID 480 | m5");
          Serial.print(" | MAP: "); Serial.print(map_press, 1); Serial.print(" kPa | ");
          Serial.print(" | Temp Ar: "); Serial.print(iat, 1); Serial.print(" C | ");
          Serial.print(" | Temp Motor: "); Serial.println(clt, 1);
          break;
        case 6:
          tps = getRaw16Motorola(canMsg.data[2], canMsg.data[3]) * 0.1;
          lambda1 = getRaw16Motorola(canMsg.data[6], canMsg.data[7]) * 0.001;
          Serial.print("ID 480 | m6");
          Serial.print(" | TPS: "); Serial.print(tps, 1); Serial.print(" % | ");
          Serial.print(" | Lambda 1: "); Serial.println(lambda1, 3);
          break;
        case 15:
          oil_press = getRaw16Motorola(canMsg.data[2], canMsg.data[3]) * 0.01;
          fuel_press = getRaw16Motorola(canMsg.data[4], canMsg.data[5]) * 0.01;
          Serial.print("ID 480 | m15");
          Serial.print(" | Pressao Oleo: "); Serial.print(oil_press, 2); Serial.print(" bar | ");
          Serial.print(" | Pressao Combustivel: "); Serial.println(fuel_press, 2);
          break;
      }
    }
    
    // ==========================================
    // CAN CUSTOM 1 (ID: 59)
    // ==========================================
    else if (canMsg.can_id == 59 && canMsg.can_dlc == 8) {
      ecu_uptime = getUnsignedRaw16Intel(canMsg.data[0], canMsg.data[1]);
      aux1_v = getRaw16Intel(canMsg.data[2], canMsg.data[3]) * 0.01;
      aux2_v = getRaw16Intel(canMsg.data[4], canMsg.data[5]) * 0.01;
      aux3_v = getRaw16Intel(canMsg.data[6], canMsg.data[7]) * 0.01;
      
      Serial.print("ID 59 | Uptime: "); Serial.print(ecu_uptime);
      Serial.print(" | Aux1: "); Serial.print(aux1_v, 2); Serial.print("V");
      Serial.print(" | Aux2: "); Serial.print(aux2_v, 2); Serial.print("V");
      Serial.print(" | Aux3: "); Serial.print(aux3_v, 2); Serial.println("V");
    }

    // ==========================================
    // CAN CUSTOM 2 (ID: 60)
    // ==========================================
    else if (canMsg.can_id == 60 && canMsg.can_dlc == 8) {
      aux4_v = getRaw16Intel(canMsg.data[0], canMsg.data[1]) * 0.01;
      aux5_v = getRaw16Intel(canMsg.data[2], canMsg.data[3]) * 0.01;
      aux6_v = getRaw16Intel(canMsg.data[4], canMsg.data[5]) * 0.01;
      aux7_v = getRaw16Intel(canMsg.data[6], canMsg.data[7]) * 0.01;
      
      Serial.print("ID 60 | Aux4: "); Serial.print(aux4_v, 2); Serial.print("V");
      Serial.print(" | Aux5: "); Serial.print(aux5_v, 2); Serial.print("V");
      Serial.print(" | Aux6: "); Serial.print(aux6_v, 2); Serial.print("V");
      Serial.print(" | Aux7: "); Serial.print(aux7_v, 2); Serial.println("V");
    }

    // ==========================================
    // CAN CUSTOM 3 (ID: 61)
    // ==========================================
    else if (canMsg.can_id == 61 && canMsg.can_dlc == 8) {
      aux8_v = getRaw16Intel(canMsg.data[0], canMsg.data[1]) * 0.01;
      aux9_v = getRaw16Intel(canMsg.data[2], canMsg.data[3]) * 0.01;
      aux_out3_perc = getRaw16Intel(canMsg.data[4], canMsg.data[5]) * 0.1;
      aux_out6_perc = getRaw16Intel(canMsg.data[6], canMsg.data[7]) * 0.1;
      
      Serial.print("ID 61 | Aux8: "); Serial.print(aux8_v, 2); Serial.print("V");
      Serial.print(" | Aux9: "); Serial.print(aux9_v, 2); Serial.print("V");
      Serial.print(" | Out3 Uso: "); Serial.print(aux_out3_perc, 1); Serial.print("%");
      Serial.print(" | Out6 Uso: "); Serial.print(aux_out6_perc, 1); Serial.println("%");
    }

    // ==========================================
    // CAN CUSTOM 4 (ID: 62)
    // ==========================================
    else if (canMsg.can_id == 62 && canMsg.can_dlc == 8) {
      launch_control = getRaw16Intel(canMsg.data[0], canMsg.data[1]);
      battery_v = getRaw16Intel(canMsg.data[2], canMsg.data[3]) * 0.1; // Bateria geralmente usa fator 0.01
      gps_date_utc = getUnsignedRaw16Intel(canMsg.data[4], canMsg.data[5]);
      
      Serial.print("ID 62 | Launch Ctrl: "); Serial.print(launch_control);
      Serial.print(" | Bateria: "); Serial.print(battery_v, 2); Serial.println("V");
    }

    // ==========================================
    // CAN CUSTOM 5 (ID: 63)
    // ==========================================
    else if (canMsg.can_id == 63 && canMsg.can_dlc == 8) {
      gps_lat = getRaw16Intel(canMsg.data[0], canMsg.data[1]);
      gps_lon = getRaw16Intel(canMsg.data[2], canMsg.data[3]);
      gps_speed = getRaw16Intel(canMsg.data[4], canMsg.data[5]) * 0.1;
      gps_time_utc = getUnsignedRaw16Intel(canMsg.data[6], canMsg.data[7]);
      
      
      Serial.print("ID 63 | GPS Vel: "); Serial.print(gps_speed, 1);
      Serial.print(" km/h | GPS Time: "); Serial.print(gps_time_utc);
      Serial.print(" | Latitude: "); Serial.print(gps_lat);
      Serial.print(" | Longitude: "); Serial.println(gps_lon);
    }
  }
}