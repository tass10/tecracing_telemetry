#include <SPI.h>

const int pino_ss = 10;      
const int tamanho_buffer = 64; 
volatile char buffer_spi[tamanho_buffer];
volatile int indice_spi = 0;
bool ss_anterior = HIGH;

unsigned long tempoAnterior = 0;

void setup() {
  pinMode(MISO, OUTPUT);
  pinMode(pino_ss, INPUT_PULLUP);
  
  // Habilita o SPI em modo Slave e a interrupção de hardware
  SPCR |= _BV(SPE);
  SPCR |= _BV(SPIE);

  // Preenche o buffer inicial e engatilha o primeiro caractere
  snprintf((char*)buffer_spi, tamanho_buffer, "Aguardando...");
  SPDR = buffer_spi[0]; 
}

void loop() {
  bool ss_atual = digitalRead(pino_ss);
  
  // MUDANÇA CHAVE: Detecta a borda de SUBIDA (quando o ESP32 termina a leitura)
  if (ss_anterior == LOW && ss_atual == HIGH) {
    indice_spi = 0;
    SPDR = buffer_spi[0]; // Deixa a "bala na agulha" para a próxima transação
  }
  ss_anterior = ss_atual;

  // Atualiza as leituras analógicas a cada 100ms sem usar delay()
  if (ss_atual == HIGH && (millis() - tempoAnterior >= 100)) {
    tempoAnterior = millis();
    atualizarLeituras();
    
    // Se o índice está zerado (aguardando leitura), atualiza o registrador 
    // com o dado mais novo do buffer
    if (indice_spi == 0) {
        SPDR = buffer_spi[0]; 
    }
  }
}

void atualizarLeituras() {
  int a0 = analogRead(A0);
  int a1 = analogRead(A1);
  int a2 = analogRead(A2);
  int a3 = analogRead(A3);
  int a4 = analogRead(A4);
  int a5 = analogRead(A5);
  int a6 = analogRead(A6);
  int a7 = analogRead(A7);

  snprintf((char*)buffer_spi, tamanho_buffer, "%d,%d,%d,%d,%d,%d,%d,%d", a0, a1, a2, a3, a4, a5, a6, a7);
}

ISR(SPI_STC_vect) {
  byte lixo = SPDR; // Ler o SPDR é necessário para limpar a flag de interrupção no AVR
  indice_spi++;
  
  if (indice_spi < tamanho_buffer) {
    SPDR = buffer_spi[indice_spi]; // Carrega o próximo caractere
  } else {
    SPDR = '\0'; // Envia caractere nulo se a mensagem já acabou
  }
}