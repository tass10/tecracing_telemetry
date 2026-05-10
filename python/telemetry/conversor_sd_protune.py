import struct
import os
import time
from datetime import datetime

# ==========================================
# CONFIGURAÇÕES DO CONVERSOR
# ==========================================
ARQUIVO_ENTRADA = "telemetry.log"
FORMATO_BINARIO = '< 2B 8h H 21h H 3h H B'
TAMANHO_PACOTE = struct.calcsize(FORMATO_BINARIO) # 73 bytes

# O ESP32 estava programado para 200ms (5Hz), usaremos isso para avançar o tempo do Datalog
INTERVALO_SEGUNDOS = 0.200 

# ==========================================
# MAPEAMENTO DO CABEÇALHO PROTUNE
# ==========================================
# Tupla: (Nome, Resolução, Fixo, Tipo, Casas_Decimais, Unidade)
CANAIS_PROTUNE = [
    ("Tempo_desde_que_a_ECU_foi_ligada", ".001", "0", "0", "3", "Seg"),
    ("Rotacao_do_Motor", "1", "0", "0", "0", "1/min"),
    ("Pressao_de_Admissao_(MAP)", ".1", "0", "1", "1", "kPa"),
    ("Temperatura_do_Ar_da_Admissao_(IAT)", ".1", "0", "1", "1", "°C"),
    ("Temperatura_do_Motor_(ET)", ".1", "0", "1", "1", "°C"),
    ("Posicao_da_Borboleta_(TP)", ".1", "0", "1", "1", "%"),
    ("Lambda_1_-_Valor", ".001", "0", "2", "3", "Lambda"),
    ("Pressao_de_Oleo_(OP)", ".01", "0", "2", "2", "bar"),
    ("Fuel_-_Pressao_de_Combustivel", ".01", "0", "2", "2", "bar"),
    ("Tensao_da_Bateria", ".1", "0", "1", "1", "V"),
    ("GPS_Velocidade", ".1", "0", "1", "1", "km/h"),
    ("adc_A0_RAW", "1", "0", "1", "0", "Raw"),
    ("adc_A1_RAW", "1", "0", "1", "0", "Raw"),
    ("adc_A2_RAW", "1", "0", "1", "0", "Raw"),
    ("adc_A3_RAW", "1", "0", "1", "0", "Raw"),
    ("adc_A4_RAW", "1", "0", "1", "0", "Raw"),
    ("adc_A5_RAW", "1", "0", "1", "0", "Raw"),
    ("adc_A6_RAW", "1", "0", "1", "0", "Raw"),
    ("adc_A7_RAW", "1", "0", "1", "0", "Raw"),
]

def converter_arquivo():
    if not os.path.exists(ARQUIVO_ENTRADA):
        print(f"ERRO: Arquivo '{ARQUIVO_ENTRADA}' não encontrado na pasta atual.")
        return

    now = datetime.now()
    arquivo_saida = f"SD_LOG_{now.strftime('%Y%m%d_%H%M%S')}.dl"
    
    print(f"Lendo '{ARQUIVO_ENTRADA}' (Tamanho do pacote: {TAMANHO_PACOTE} bytes)...")
    
    pacotes_validos = 0
    pacotes_corrompidos = 0
    tempo_atual_datalog = 0.0

    try:
        with open(ARQUIVO_ENTRADA, 'rb') as f_in, open(arquivo_saida, 'w', encoding='utf-8') as f_out:
            
            # 1. ESCREVE O CABEÇALHO PROTUNE
            f_out.write("#V2\n")
            f_out.write("#DEVICE DATALOGGER_SD_ESP32\n")
            f_out.write(f"#MAPFILE PROTOTIPO_TR07_OFFLINE\n")
            f_out.write("#ECUCODE LOGGER_SD.V1\n")
            f_out.write(f"#SERIALNUMBER SD_{now.strftime('%Y%m%d')}\n")
            f_out.write(f"#LOADDATE {now.strftime('%d/%m/%Y (%H:%M:%S)')}\n")
            
            f_out.write("#STARTCHINFO\n")
            for ch in CANAIS_PROTUNE:
                f_out.write(f"{ch[0]} {ch[1]} {ch[2]} {ch[3]} {ch[4]}\n")
            f_out.write("#ENDCHINFO\n")
            
            f_out.write("#NUMBEROFSHOWS 0\n")
            f_out.write("#TRACKLABEL Desconhecido\n")
            f_out.write("#MAXSPEED 0\n")
            f_out.write("#BESTLAP 00:00.000 (0)\n")
            f_out.write("#NUMBEROFLAPS 0\n")
            
            titulos = "Datalog Time ; " + ";".join([ch[0].replace("_-_", " - ").replace("_", " ") for ch in CANAIS_PROTUNE]) + ";\n"
            unidades = "s ; " + ";".join([ch[5] for ch in CANAIS_PROTUNE]) + ";\n"
            
            f_out.write("#DATASTART\n")
            f_out.write(titulos)
            f_out.write(unidades)

            # 2. LÊ O BINÁRIO E CONVERTE EM LINHAS
            while True:
                chunk = f_in.read(TAMANHO_PACOTE)
                if not chunk:
                    break # Fim do arquivo
                
                if len(chunk) < TAMANHO_PACOTE:
                    # Sobrou um pedaço quebrado no fim do arquivo, ignoramos.
                    break

                # Desempacota os 73 bytes
                dados = struct.unpack(FORMATO_BINARIO, chunk)
                
                # Valida o cabeçalho 0xAA 0x55 (Evita lixo de memória)
                if dados[0] != 0xAA or dados[1] != 0x55:
                    pacotes_corrompidos += 1
                    continue
                
                pacotes_validos += 1

                # Extrai e aplica os divisores iguais ao painel PyQt5
                adc_a0 = dados[2]
                adc_a1 = dados[3]
                adc_a2 = dados[4]
                adc_a3 = dados[5]
                adc_a4 = dados[6]
                adc_a5 = dados[7]
                adc_a6 = dados[8]
                adc_a7 = dados[9]
                
                ecu_uptime = dados[10]
                engine_speed = dados[11]
                map_press = dados[12] / 10.0
                iat = dados[13] / 10.0
                clt = clt = dados[14] / 10.0
                tps = dados[15] / 10.0
                lambda1 = dados[16] / 1000.0
                oil_press = dados[17] / 100.0
                fuel_press = dados[18] / 100.0
                # Pulando alguns aux para focar no mapeamento principal pedido
                battery_v = dados[31] / 10.0
                gps_speed = dados[35] / 10.0

                # Formata a string de saída seguindo a ordem do CANAIS_PROTUNE
                linha_dados = [
                    f"{ecu_uptime:.0f}",
                    f"{engine_speed:.0f}",
                    f"{map_press:.1f}",
                    f"{iat:.1f}",
                    f"{clt:.1f}",
                    f"{tps:.1f}",
                    f"{lambda1:.3f}",
                    f"{oil_press:.2f}",
                    f"{fuel_press:.2f}",
                    f"{battery_v:.1f}",
                    f"{gps_speed:.1f}",
                    f"{adc_a0:.0f}",
                    f"{adc_a1:.0f}",
                    f"{adc_a2:.0f}",
                    f"{adc_a3:.0f}",
                    f"{adc_a4:.0f}",
                    f"{adc_a5:.0f}",
                    f"{adc_a6:.0f}",
                    f"{adc_a7:.0f}",
                ]

                # Monta a linha com o Tempo atual e o separador "A"
                linha_protune = f" {tempo_atual_datalog:.3f}".replace('.', ',')
                for val in linha_dados:
                    linha_protune += "A" + str(val).replace('.', ',')
                linha_protune += "A\n"
                
                f_out.write(linha_protune)
                
                # Avança o tempo do Datalog (200ms por ciclo)
                tempo_atual_datalog += INTERVALO_SEGUNDOS

        print("\n--- CONVERSÃO CONCLUÍDA ---")
        print(f"Pacotes válidos extraídos: {pacotes_validos} ({pacotes_validos * INTERVALO_SEGUNDOS:.1f} segundos de log)")
        print(f"Pacotes corrompidos/ignorados: {pacotes_corrompidos}")
        print(f"Arquivo gerado: {arquivo_saida}")

    except Exception as e:
        print(f"Erro ao processar o arquivo: {e}")

if __name__ == "__main__":
    converter_arquivo()