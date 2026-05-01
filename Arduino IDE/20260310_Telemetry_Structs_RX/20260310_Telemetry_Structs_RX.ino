// ==========================================
// ESTRUTURA DE DADOS BINÁRIA (73 BYTES)
// ==========================================
// Esta struct DEVE ser idêntica à do Transmissor
typedef struct __attribute__((packed)) {
  uint8_t header[2]; // 0xAA, 0x55
  
  // Variáveis do Nano (8 variáveis)
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

// Definindo os pinos do barramento UART2 para comunicar com o Módulo LoRa
#define RXD2 16
#define TXD2 17
#define PIN_M0 32
#define PIN_M1 33

const int TAMANHO_PACOTE = sizeof(PacoteTelemetria); // 73 bytes
uint8_t buffer_rx[sizeof(PacoteTelemetria)];
int indice_buffer = 0;
bool sincronizado = false;

void setup() {
  Serial.begin(115200);                         // Inicia o barramento UART0 USB PC
  // IMPORTANTE: O Baud Rate do LoRa agora deve ser 115200 igual ao Transmissor
  pinMode(PIN_M0, OUTPUT);  digitalWrite(PIN_M0, LOW);
  pinMode(PIN_M1, OUTPUT);  digitalWrite(PIN_M1, LOW);
  Serial2.begin(115200, SERIAL_8N1, RXD2, TXD2); // Inicia o barramento UART2 LoRa
}

void loop() {
  // Lê os dados enquanto houver bytes disponíveis no buffer da porta Serial2 (LoRa)
  while (Serial2.available() > 0) {
    uint8_t byte_recebido = Serial2.read();

    // Passo 1: Caçar o cabeçalho (0xAA e depois 0x55)
    if (!sincronizado) {
      if (indice_buffer == 0 && byte_recebido == 0xAA) {
        buffer_rx[indice_buffer] = byte_recebido;
        indice_buffer++;
      } 
      else if (indice_buffer == 1 && byte_recebido == 0x55) {
        buffer_rx[indice_buffer] = byte_recebido;
        indice_buffer++;
        sincronizado = true; // Assinatura confirmada!
      } 
      else {
        // Falso alarme ou lixo no meio do caminho, reseta a busca
        indice_buffer = 0; 
      }
    } 
    // Passo 2: Cabeçalho encontrado, ler o resto do pacote
    else {
      buffer_rx[indice_buffer] = byte_recebido;
      indice_buffer++;

      // Verifica se já preencheu os 73 bytes
      if (indice_buffer >= TAMANHO_PACOTE) {
        
        // Passo 3: Envia o pacote binário completo e puro para o PC via USB
        // O Python vai receber exatamente esses bytes e desempacotar com a biblioteca 'struct'
        Serial.write(buffer_rx, TAMANHO_PACOTE);
        
        // Prepara para o próximo pacote
        indice_buffer = 0;
        sincronizado = false;
      }
    }
  }
}