# Código principal para visualização em tempo real e datalogging

import sys
import serial
import serial.tools.list_ports  # <-- NOVO: Para buscar as portas COM disponíveis automaticamente
import time
from datetime import datetime
import os
import struct 
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QProgressBar, QComboBox, QToolBar # <-- NOVO: QComboBox e QToolBar
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot
from PyQt5 import uic 
import random
import numpy as np
from scipy import signal

# =======================================================
# CLASSE DO FILTRO IIR EM TEMPO REAL
# =======================================================
class RealTimeIIR:
    """
    Mantém o estado (memória) de um filtro digital IIR tipo SOS (Second Order Sections)
    para filtrar sinais amostra por amostra em tempo real.
    """
    def __init__(self, sos_matrix, gains):
        self.sos = np.array(sos_matrix)
        self.total_gain = np.prod(gains)
        
        # Calcula as condições iniciais ideais do filtro
        self.zi_base = signal.sosfilt_zi(self.sos)
        self.zi = np.copy(self.zi_base)
        self.first_run = True

    def update(self, val):
        if self.first_run:
            # Na primeira leitura, assume que o sinal sempre esteve nesse valor
            self.zi = self.zi_base * val
            self.first_run = False
        
        # Filtra a amostra atual e guarda o novo estado (zi) para a próxima iteração
        filtered, self.zi = signal.sosfilt(self.sos, [val], zi=self.zi)
        
        return filtered[0] * self.total_gain

# =======================================================
# FORMATO DA STRUCT DE TELEMETRIA
# =======================================================
# '<'   = Little-endian (padrão do ESP32)
# '2B'  = 2 unsigned char (Header 0xAA, 0x55)
# '8h'  = 8 short int (ADCs vars)
# 'H'   = 1 unsigned short (ecu_uptime)
# '21h' = 21 short int (CAN vars)
# 'H'   = 1 unsigned short (gps_date)
# '3h'  = 3 short int (gps lat, lon, speed)
# 'H'   = 1 unsigned short (gps_time)
# 'B'   = 1 unsigned char (checksum)
# 'B'   = 1 unsigned char (RSSI injetado pelo módulo LoRa)
STRUCT_FORMAT = '< 2B 8h H 21h H 3h H B B'
PACKET_SIZE = struct.calcsize(STRUCT_FORMAT) # Deve resultar em exatos 73 bytes

# =======================================================
# 1. THREAD DE AQUISIÇÃO DE DADOS (Background)
# =======================================================
class SerialWorker(QThread):
    data_received = pyqtSignal(float, float, int, float, int, int, int, int, int, int, 
                               float, float, float, float, float, float, float, 
                               float, float, float, float, float, float, float, 
                               float, float, float, float, int, float, int, int, 
                               int, float, int, int)

    def __init__(self, port='COM11', baudrate=115200, simulation_mode=False):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.is_running = True
        self.simulation_mode = simulation_mode 

        # Filtro de Água (IIR Ordem 5 - Fpass 0.5Hz)
        sos_agua = [
            [1.0, 2.0, 1.0, 1.0, -1.451709412909310, 0.716794312985863],
            [1.0, 2.0, 1.0, 1.0, -1.181098283900234, 0.396769077093499],
            [1.0, 1.0, 0.0, 1.0, -0.551295907484470, 0.0]
        ]
        g_agua = [0.066271225019138, 0.053917698298316, 0.224352046257765, 1.0]
        
        self.filtro_temp_in = RealTimeIIR(sos_agua, g_agua)
        self.filtro_temp_out = RealTimeIIR(sos_agua, g_agua)

        # Filtro de Freio (IIR Ordem 4 - Fpass 1.5Hz)
        sos_freio = [
            [1.0000, 2.0000, 1.0000, 1.0000, -0.039197619731677, 0.446609698036549],
            [1.0000, 2.0000, 1.0000, 1.0000, -0.028173255014404, 0.039749459484601]
        ]
        g_freio = [0.351853019576218, 0.252894051117549, 1.000000000000000]
        
        self.filtro_freio = RealTimeIIR(sos_freio, g_freio)

        # Parâmetros para conversão de dados brutos em valores físicos. Obtidos através de testes em laboratório
        self.paramRadiadorIn = 0.123456
        self.paramRadiadorOut = 0.123456
        self.paramPressaoFreio = 0.123456
    
    def run(self):
        ser = None
        
        while self.is_running:
            # ---------------------------------------------------
            # MODO SIMULAÇÃO (Gera valores aleatórios)
            # ---------------------------------------------------
            if self.simulation_mode:
                try:
                    rpm = random.uniform(0, 12000)
                    vel = random.uniform(0, 120)
                    temp = random.uniform(0, 100)
                    
                    self.data_received.emit(rpm, vel, temp)
                    time.sleep(0.1) 
                except Exception as e:
                    print(f"Erro na simulação: {e}")
                    time.sleep(1)
            
            # ---------------------------------------------------
            # MODO REAL (Lê os dados binários da porta COM)
            # ---------------------------------------------------
            else:
                try:
                    if ser is None or not ser.is_open:
                        print(f"Tentando conectar à porta {self.port}...")
                        
                        # 1. Cria a instância sem abrir a porta imediatamente
                        ser = serial.Serial()
                        ser.port = self.port
                        ser.baudrate = self.baudrate
                        ser.timeout = 1
                        
                        # 2. Desativa os sinais de controle de hardware ANTES de abrir
                        ser.dtr = False
                        ser.rts = False
                        
                        # 3. Agora sim, abre a porta com segurança
                        ser.open()
                        
                        print(f"CONECTADO COM SUCESSO à porta {self.port}!")
                    
                    while self.is_running and ser.is_open and not self.simulation_mode:
                        
                        # 1. Caça o primeiro byte do cabeçalho (0xAA)
                        byte_lido = ser.read(1)
                        if not byte_lido:
                            continue
                            
                        if byte_lido[0] == 0xAA:
                            # 2. Caça o segundo byte (0x55)
                            byte2 = ser.read(1)
                            if byte2 and byte2[0] == 0x55:
                                # Lê o resto exato do pacote (agora são 72 bytes restantes, pois o total é 74)
                                resto_do_pacote = ser.read(PACKET_SIZE - 2)
                                
                                if len(resto_do_pacote) == PACKET_SIZE - 2:
                                    pacote_completo = b'\xAA\x55' + resto_do_pacote
                                    
                                    # 4. Validação de Checksum (XOR de todos os bytes exceto o penúltimo)
                                    calc_ck = 0
                                    for b in pacote_completo[:-2]:
                                        calc_ck ^= b
                                        
                                    checksum_recebido = pacote_completo[-2]
                                    
                                    if calc_ck != checksum_recebido:
                                        print("Pacote corrompido descartado pelo Checksum!")
                                        continue # Ignora o pacote inteiro e volta a procurar o cabeçalho
                                    
                                    # 5. Desempacota e converte para variáveis utilizáveis
                                    try:
                                        dados = struct.unpack(STRUCT_FORMAT, pacote_completo)
                                        
                                        # -- VARIÁVEIS DOS ADCs --
                                        adc_a0_raw = dados[2]
                                        adc_a1_raw = dados[3]
                                        adc_a2 = dados[4]
                                        adc_a3_raw = dados[5]
                                        adc_a4 = dados[6]
                                        adc_a5 = dados[7]
                                        adc_a6 = dados[8]
                                        adc_a7 = dados[9]

                                        # Aplica os filtros nos sinais de interesse
                                        adc_a0_filtrado = self.filtro_temp_in.update(adc_a0_raw * self.paramRadiadorIn)
                                        adc_a1_filtrado = self.filtro_temp_out.update(adc_a1_raw * self.paramRadiadorOut)
                                        adc_a3_filtrado = self.filtro_freio.update(adc_a3_raw * self.paramPressaoFreio)

                                        # -- VARIÁVEIS DO CAN --
                                        ecu_uptime = dados[10]
                                        engine_speed = dados[11] # RPM real da injeção
                                        map_press = dados[12] / 10.0
                                        iat = dados[13] / 10.0
                                        clt = dados[14] / 10.0
                                        tps = dados[15] / 10.0
                                        lambda1 = dados[16] / 1000.0
                                        oil_press = dados[17] / 100.0
                                        fuel_press = dados[18] / 100.0
                                        aux1_v = dados[19] / 100.0
                                        aux2_v = dados[20] / 100.0
                                        aux3_v = dados[21] / 100.0
                                        aux4_v = dados[22] / 100.0
                                        aux5_v = dados[23] / 100.0
                                        aux6_v = dados[24] / 100.0
                                        aux7_v = dados[25] / 100.0
                                        aux8_v = dados[26] / 100.0
                                        aux9_v = dados[27] / 100.0
                                        aux_out3_perc = dados[28] / 10.0
                                        aux_out6_perc = dados[29] / 10.0
                                        launch_control = dados[30]
                                        battery_v = dados[31] / 10.0
                                        gps_date_utc = dados[32]
                                        gps_lat = dados[33]
                                        gps_lon = dados[34]
                                        gps_speed = dados[35] / 10.0
                                        gps_time_utc = dados[36]
                                        rssi_raw = dados[38]
                                        rssi_dbm = rssi_raw - 256   # Fórmula padrão EByte para converter o byte cru em dBm

                                        print(dados)

                                        # Emite para a interface gráfica 
                                        self.data_received.emit(float(adc_a0_filtrado), float(adc_a1_filtrado), int(adc_a2), float(adc_a3_filtrado), int(adc_a4), int(adc_a5), int(adc_a6), 
                                                                int(adc_a7), int(ecu_uptime), int(engine_speed), float(map_press), float(iat), float(clt),
                                                                float(tps), float(lambda1), float(oil_press), float(fuel_press), float(aux1_v), float(aux2_v),
                                                                float(aux3_v), float(aux4_v), float(aux5_v), float(aux6_v), float(aux7_v), float(aux8_v),
                                                                float(aux9_v), float(aux_out3_perc), float(aux_out6_perc), int(launch_control), float(battery_v),
                                                                int(gps_date_utc), int(gps_lat), int(gps_lon), float(gps_speed), int(gps_time_utc), int(rssi_dbm))
                                        
                                    except struct.error:
                                        print("Erro ao desempacotar a struct.")
                                        pass 
                                        
                except serial.SerialException as e:
                    print(f"Sinal perdido ou erro na porta COM: {e}")
                    if ser is not None:
                        ser.close()
                    print("Aguardando 2 segundos antes de tentar reconectar...")
                    time.sleep(2) 

                except Exception as e:
                    print(f"Erro inesperado: {e}")
                    time.sleep(1)

    def stop(self):
        self.is_running = False
        self.wait()

# =======================================================
# 2. INTERFACE GRÁFICA (Thread Principal)
# =======================================================
class Dashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        
        uic.loadUi("python/telemetry/dashboard.ui", self)

        self.logger = ProTuneLogger()
        self.logger.start_new_log()

        self.gauge1.setRange(0, 12000)
        self.gauge1.setUnits("RPM")
        self.gauge1.setScaleSteps(6) 
        self.gauge1.setCriticalThreshold(9000) 

        self.gauge2.setRange(0, 120)
        self.gauge2.setUnits("°C")
        self.gauge2.setScaleSteps(6) 
        self.gauge2.setCriticalThreshold(100) 

        self.gauge3.setRange(0, 100)
        self.gauge3.setUnits("%")
        self.gauge3.setScaleSteps(5) 

        self.gauge4.setRange(0.5, 1)
        self.gauge4.setUnits("")
        self.gauge4.setScaleSteps(1) 

        self.gauge5.setRange(8, 15)
        self.gauge5.setUnits("V")
        self.gauge5.setScaleSteps(6) 
        self.gauge5.setCriticalThreshold(100) 

        self.gauge6.setRange(0, 120)
        self.gauge6.setUnits("KM/H")
        self.gauge6.setScaleSteps(6) 
        self.gauge6.setCriticalThreshold(100)

        self.gauge7.setRange(-150, 0)
        self.gauge7.setUnits("dBm")
        self.gauge7.setScaleSteps(5)
        self.gauge7.setCriticalThreshold(-110)

        self.gauge8.setRange(0, 120)
        self.gauge8.setUnits("°C")
        self.gauge8.setScaleSteps(6) 
        self.gauge8.setCriticalThreshold(100)

        self.gauge14.setRange(0, 120)
        self.gauge14.setUnits("°C")
        self.gauge14.setScaleSteps(6) 
        self.gauge14.setCriticalThreshold(100)

        # Configura a barra de ferramentas com o Drop-down
        self.setup_com_toolbar()

        # Inicia o SerialWorker com a porta selecionada no drop-down
        porta_inicial = 'COM11'
        self.serial_thread = SerialWorker(port=porta_inicial, baudrate=115200, simulation_mode=False)
        self.serial_thread.data_received.connect(self.update_gauges)
        self.serial_thread.start()

    # =======================================================
    # Funções para lidar com o seletor de Porta COM
    # =======================================================
    def setup_com_toolbar(self):
        """Cria uma barra no topo da janela para selecionar a porta."""
        self.toolbar = QToolBar("Configurações de Conexão")
        self.addToolBar(self.toolbar)

        self.lbl_com = QLabel(" Porta COM: ")
        self.toolbar.addWidget(self.lbl_com)

        self.combo_ports = QComboBox()
        self.refresh_com_ports() # Preenche as portas disponíveis
        self.toolbar.addWidget(self.combo_ports)

        # Conecta a mudança de texto do drop-down à função de reiniciar a thread
        self.combo_ports.currentTextChanged.connect(self.on_com_port_changed)

    def refresh_com_ports(self):
        # Busca as portas ativas no PC e adiciona ao ComboBox
        self.combo_ports.blockSignals(True) # Evita disparar a mudança enquanto se preenche
        self.combo_ports.clear()
        
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.combo_ports.addItem(port.device)
            
        self.combo_ports.blockSignals(False)

    def on_com_port_changed(self, new_port):
        # Reinicia a thread serial com a nova porta
        if not new_port:
            return

        print(f"Mudança detectada! Trocando para {new_port}...")
        
        # Para a thread atual com segurança
        if hasattr(self, 'serial_thread') and self.serial_thread.isRunning():
            self.serial_thread.stop()

        # Cria e inicia uma nova thread com a porta atualizada
        self.serial_thread = SerialWorker(port=new_port, baudrate=115200, simulation_mode=False)
        self.serial_thread.data_received.connect(self.update_gauges)
        self.serial_thread.start()


    @pyqtSlot(float, float, int, float, int, int, int, int, int, int, 
                float, float, float, float, float, float, float, 
                float, float, float, float, float, float, float, 
                float, float, float, float, int, float, int, int, 
                int, float, int, int)
    def update_gauges(self, adc_a0, adc_a1, adc_a2, adc_a3, adc_a4, adc_a5, adc_a6, 
                            adc_a7, ecu_uptime, engine_speed, map_press, iat, clt,
                            tps, lambda1, oil_press, fuel_press, aux1_v, aux2_v,
                            aux3_v, aux4_v, aux5_v, aux6_v, aux7_v, aux8_v,
                            aux9_v, aux_out3_perc, aux_out6_perc, launch_control, battery_v,
                            gps_date_utc, gps_lat, gps_lon, gps_speed, gps_time_utc, rssi_dbm):
        self.lbl_gauge_1.setText("ENGINE SPEED")
        self.lbl_gauge_2.setText("ENGINE TEMP")
        self.lbl_gauge_3.setText("TPS")
        self.lbl_gauge_4.setText("LAMBDA")
        self.lbl_gauge_5.setText("BATTERY VOLTAGE")
        self.lbl_gauge_6.setText("GPS VELOCITY")
        self.lbl_gauge_7.setText("RSSI (SINAL)")
        self.lbl_gauge_8.setText("RADIATOR IN TEMP")
        self.lbl_gauge_14.setText("RADIATOR OUT TEMP")
        
        self.gauge1.setValue(engine_speed)
        self.gauge2.setValue(clt)
        self.gauge3.setValue(tps)
        self.gauge4.setValue(lambda1)
        self.gauge4.setDecimals(3)
        self.gauge5.setValue(battery_v)
        self.gauge5.setDecimals(1)
        self.gauge7.setValue(rssi_dbm) 

        # Dataloggig
        dados_atuais = {
            'ecu_uptime': ecu_uptime,
            'engine_speed': engine_speed,
            'map_press': map_press,
            'iat': iat,
            'clt': clt,
            'tps': tps,
            'battery_v': battery_v,
            'lambda1': lambda1,
            'oil_press': oil_press,
            'fuel_press': fuel_press,
            'gps_speed': gps_speed,
            'rssi_dbm': rssi_dbm,
            'adc_a0': adc_a0,
            'adc_a1': adc_a1,
            'adc_a3': adc_a3 
        }
        self.logger.log_data(dados_atuais)

    def closeEvent(self, event):
        self.logger.stop_log() # Fecha o arquivo com segurança
        self.serial_thread.stop()
        event.accept()

# =======================================================
# 3. ARMAZENAMENTO LOCAL DOS DADOS RECEBIDOS
# =======================================================

class ProTuneLogger:
    def __init__(self, folder_path="datalog_telemetria"):
        self.folder_path = folder_path
        if not os.path.exists(self.folder_path):
            os.makedirs(self.folder_path)
            
        self.file = None
        self.start_time = None
        
        self.channel_info = [
            ("Tempo_desde_que_a_ECU_foi_ligada", ".001", "0", "0", "3", "Seg"),
            ("Rotacao_do_Motor", "1", "0", "0", "3", "1/min"),
            ("Pressao_de_Admissao_(MAP)", ".1", "0", "1", "2", "kPa"),
            ("Temperatura_do_Ar_da_Admissao_(IAT)", ".1", "0", "1", "2", "°C"),
            ("Temperatura_do_Motor_(ET)", ".1", "0", "1", "2", "°C"),
            ("Posicao_da_Borboleta_(TP/TP1L)", ".1", "0", "1", "2", "%"),
            ("Tensao_da_Bateria", ".1", "0", "1", "2", "V"),
            ("Lambda_1_-_Valor", ".001", "0", "2", "2", "Lambda"),
            ("Pressao_de_Oleo_(OP)", ".01", "0", "2", "2", "bar"),
            ("Fuel_-_Pressao_de_Combustivel", ".01", "0", "2", "2", "bar"),
            ("GPS_Velocidade", ".1", "0", "1", "3", "km/h"),
            ("RSSI_Sinal_LoRa", "1", "0", "0", "1", "dBm"),
            ("ADC_A0", ".1", "0", "0", "2", "°C"),
            ("ADC_A1", ".1", "0", "0", "2", "°C"),
            ("ADC_A3", ".1", "0", "0", "2", "Psi")
        ]

    def start_new_log(self):
        # Cria o arquivo e grava o cabeçalho compatível com ProTune
        now = datetime.now()
        filename = f"TELEMETRIA_TR07_{now.strftime('%Y%m%d_%H%M%S')}.dlf"
        filepath = os.path.join(self.folder_path, filename)
        
        self.file = open(filepath, 'w', encoding='utf-8')
        self.start_time = time.time()
        
        # ESCRITA DO CABEÇALHO GLOBAL
        self.file.write("#V2\n")
        self.file.write("#DEVICE TELEMETRIA_PC\n")
        self.file.write(f"#MAPFILE PROTOTIPO_TR07_{now.strftime('%b_%y').upper()}\n")
        self.file.write("#ECUCODE TELEMETRIA.PYTHON.V1\n")
        self.file.write(f"#SERIALNUMBER LORA_{now.strftime('%Y%m%d%H%M')}\n")
        self.file.write(f"#LOADDATE {now.strftime('%d/%m/%Y (%H:%M:%S)')}\n")
        
        # ESCRITA DOS CANAIS (As variáveis)
        self.file.write("#STARTCHINFO\n")
        for ch in self.channel_info:
            nome, res, unk1, unk2, dec = ch[:5]
            self.file.write(f"{nome} {res} {unk1} {unk2} {dec}\n")
        self.file.write("#ENDCHINFO\n")
        
        self.file.write("#NUMBEROFSHOWS 0\n")
        self.file.write("#TRACKLABEL Desconhecido\n")
        self.file.write("#MAXSPEED 0\n")
        self.file.write("#BESTLAP 00:00.000 (0)\n")
        self.file.write("#NUMBEROFLAPS 0\n")
        
        # ESCRITA DOS TÍTULOS E UNIDADES DAS COLUNAS (Para leitura em Excel/CSV)
        self.file.write("#DATASTART\n")
        
        titulos = "Datalog Time ; " + ";".join([ch[0].replace("_-_", " - ").replace("_", " ") for ch in self.channel_info]) + ";\n"
        unidades = "s ; " + ";".join([ch[5] for ch in self.channel_info]) + ";\n"
        
        self.file.write(titulos)
        self.file.write(unidades)

    def log_data(self, data_dict):
        # Recebe um dicionário com os valores atuais e grava uma linha no log. Formato compatível: Força o caracter 'A' entre todos os valores.
        
        if self.file is None or self.file.closed:
            return
            
        current_time = time.time() - self.start_time
        
        # Inicia a linha com o Tempo exato (com 3 casas decimais)
        line = f" {current_time:.3f}".replace('.', ',')
        
        # Extrai os dados na ordem exata do cabeçalho
        valores = [
            f"{data_dict.get('ecu_uptime', 0):.0f}",
            f"{data_dict.get('engine_speed', 0):.0f}",
            f"{data_dict.get('map_press', 0):.1f}",
            f"{data_dict.get('iat', 0):.1f}",
            f"{data_dict.get('clt', 0):.1f}",
            f"{data_dict.get('tps', 0):.1f}",
            f"{data_dict.get('battery_v', 0):.1f}",
            f"{data_dict.get('lambda1', 0):.3f}",
            f"{data_dict.get('oil_press', 0):.2f}",
            f"{data_dict.get('fuel_press', 0):.2f}",
            f"{data_dict.get('gps_speed', 0):.1f}",
            f"{data_dict.get('rssi_dbm', 0):.0f}",
            f"{data_dict.get('adc_a0', 0):.1f}",
            f"{data_dict.get('adc_a1', 0):.1f}",
            f"{data_dict.get('adc_a3', 0):.1f}"
        ]
        
        # Constrói a linha usando 'A' como separador 
        for val in valores:
            line += "A" + str(val).replace('.', ',')
            
        line += "A\n" # A ProTune geralmente termina a linha com o último separador
        
        self.file.write(line)
        self.file.flush() # Força a gravação no HD imediatamente para não perder dados se o PC travar

    def stop_log(self):
        if self.file and not self.file.closed:
            self.file.close()

# =======================================================
# 4. EXECUÇÃO DO APLICATIVO
# =======================================================
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = Dashboard()
    window.show()
    sys.exit(app.exec_())