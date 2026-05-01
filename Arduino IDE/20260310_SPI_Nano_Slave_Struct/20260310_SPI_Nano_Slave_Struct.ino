#include <SPI.h>

// ==========================================
// ESTRUTURA DE DADOS BINÁRIA (16 BYTES)
// ==========================================
typedef struct __attribute__((packed)) {
  int16_t a0;   // A0
  int16_t a1;   // A1
  int16_t a2;   // A2
  int16_t a3;   // A3
  int16_t a4;   // A4
  int16_t a5;   // A5
  int16_t a6;   // A6
  int16_t a7;   // A7
} DadosNano;

volatile DadosNano dados_atuais;
const int tamanho_pacote = sizeof(DadosNano); // 16 bytes

// Ponteiro para tratar a struct como um vetor de bytes durante o envio SPI
volatile uint8_t* ponteiro_spi = (uint8_t*)&dados_atuais; 
volatile int indice_spi = 0;

const int pino_ss = 10;      
bool ss_anterior = HIGH;
unsigned long tempoAnterior = 0;

void setup() {
  pinMode(MISO, OUTPUT);
  pinMode(pino_ss, INPUT_PULLUP);
  
  // Habilita o SPI em modo Slave e a interrupção de hardware
  SPCR |= _BV(SPE);
  SPCR |= _BV(SPIE);

  // Zera a struct inicialmente e engatilha o primeiro byte
  memset((void*)&dados_atuais, 0, tamanho_pacote);
  SPDR = ponteiro_spi[0]; 
}

void loop() {
  bool ss_atual = digitalRead(pino_ss);
  
  // Detecta a borda de SUBIDA (quando o ESP32 termina a leitura)
  if (ss_anterior == LOW && ss_atual == HIGH) {
    indice_spi = 0;
    SPDR = ponteiro_spi[0]; // Deixa a "bala na agulha" para a próxima transação
  }
  ss_anterior = ss_atual;

  // Atualiza as leituras analógicas a cada 100ms
  if (ss_atual == HIGH && (millis() - tempoAnterior >= 100)) {
    tempoAnterior = millis();
    atualizarLeituras();
    
    // Se o índice está zerado (aguardando leitura), atualiza o registrador 
    // com o byte mais novo do buffer
    if (indice_spi == 0) {
        SPDR = ponteiro_spi[0]; 
    }
  }
}

void atualizarLeituras() {
  // 1. Lê os dados para variáveis locais primeiro. 
  // Isso demora cerca de 800 microssegundos.
  int16_t t_a0 = analogRead(A0);
  int16_t t_a1 = analogRead(A1);
  int16_t t_a2 = analogRead(A2);
  int16_t t_a3 = analogRead(A3);
  int16_t t_a4 = analogRead(A4);
  int16_t t_a5 = analogRead(A5);
  int16_t t_a6 = analogRead(A6);
  int16_t t_a7 = analogRead(A7);

  // 2. Desativa as interrupções bem rapidinho (fração de microssegundo)
  // para copiar os dados para a struct volátil. Isso garante que o ESP32
  // nunca leia um pacote pela metade se solicitar a leitura neste exato momento.
  noInterrupts();
  dados_atuais.a0 = t_a0;
  dados_atuais.a1 = t_a1;
  dados_atuais.a2 = t_a2;
  dados_atuais.a3 = t_a3;
  dados_atuais.a4 = t_a4;
  dados_atuais.a5 = t_a5;
  dados_atuais.a6 = t_a6;
  dados_atuais.a7 = t_a7;
  interrupts();
}

ISR(SPI_STC_vect) {
  byte lixo = SPDR; // Ler o SPDR limpa a flag de interrupção no AVR
  indice_spi++;
  
  if (indice_spi < tamanho_pacote) {
    SPDR = ponteiro_spi[indice_spi]; // Carrega o próximo byte da struct
  } else {
    SPDR = 0x00; // Envia zeros se o ESP32 pedir dados a mais
  }
}