import sys
import serial
import serial.tools.list_ports  # <-- NOVO: Para buscar as portas COM disponíveis automaticamente
import time
import struct # <-- IMPORTANTE: Módulo para lidar com dados binários em C/C++
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QProgressBar, QComboBox, QToolBar # <-- NOVO: QComboBox e QToolBar
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot
from PyQt5 import uic 
import random

# =======================================================
# FORMATO DA STRUCT DE TELEMETRIA
# =======================================================
# '<'   = Little-endian (padrão do ESP32)
# '2B'  = 2 unsigned char (Header 0xAA, 0x55)
# '8h'  = 8 short int (Nano vars)
# 'H'   = 1 unsigned short (ecu_uptime)
# '21h' = 21 short int (CAN vars)
# 'H'   = 1 unsigned short (gps_date)
# '3h'  = 3 short int (gps lat, lon, speed)
# 'H'   = 1 unsigned short (gps_time)
# 'B'   = 1 unsigned char (checksum)
# 'B'   = 1 unsigned char (RSSI injetado pelo módulo LoRa) <--- NOVO
STRUCT_FORMAT = '< 2B 8h H 21h H 3h H B B'
PACKET_SIZE = struct.calcsize(STRUCT_FORMAT) # Deve resultar em exatos 73 bytes

# =======================================================
# 1. THREAD DE AQUISIÇÃO DE DADOS (Background)
# =======================================================
class SerialWorker(QThread):
    # Por enquanto mantendo 3 floats no signal, mas você pode expandir depois!
    data_received = pyqtSignal(int, int, int, int, int, int, int, int, int, int, 
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
                                        
                                        # -- VARIÁVEIS DO NANO --
                                        nano_a0 = dados[2]
                                        nano_a1 = dados[3]
                                        nano_a2 = dados[4]
                                        nano_a3 = dados[5]
                                        nano_a4 = dados[6]
                                        nano_a5 = dados[7]
                                        nano_a6 = dados[8]
                                        nano_a7 = dados[9]

                                        # -- VARIÁVEIS DO CAN --
                                        # Lembre-se: Aqui nós aplicamos a divisão que tiramos do ESP32!
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
                                        # -- MÉTRICAS LORA (NOVO) --
                                        # O índice 37 é o Checksum, o 38 é o RSSI
                                        rssi_raw = dados[38]
                                        # Fórmula padrão EByte para converter o byte cru em dBm
                                        rssi_dbm = rssi_raw - 256

                                        print(dados)
                                        #print(nano_a1*0.00028350)
                                        # Emite para a interface gráfica 
                                        # (Atualmente usando as variáveis do Nano, mas você pode alterar para emitir o engine_speed do CAN, por exemplo)
                                        self.data_received.emit(int(nano_a0), int(nano_a1), int(nano_a2), int(nano_a3), int(nano_a4), int(nano_a5), int(nano_a6), 
                                                                int(nano_a7), int(ecu_uptime), int(engine_speed), float(map_press), float(iat), float(clt),
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
        
        uic.loadUi("dashboard.ui", self)

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

        # --- NOVO: Configurando Gauge 7 para o RSSI ---
        self.gauge7.setRange(-150, 0) # Sinal varia tipicamente de -120 a -30
        self.gauge7.setUnits("dBm")
        self.gauge7.setScaleSteps(5)
        self.gauge7.setCriticalThreshold(-110) # Fica vermelho se o sinal estiver muito fraco

        self.gauge8.setRange(0, 120)
        self.gauge8.setUnits("°C")
        self.gauge8.setScaleSteps(6) 
        self.gauge8.setCriticalThreshold(100)

        self.gauge14.setRange(0, 120)
        self.gauge14.setUnits("°C")
        self.gauge14.setScaleSteps(6) 
        self.gauge14.setCriticalThreshold(100)

        # --- NOVO: Configura a barra de ferramentas com o Drop-down ---
        self.setup_com_toolbar()

        # Inicia o SerialWorker com a porta selecionada no drop-down
        porta_inicial = 'COM11'#self.combo_ports.currentText() if self.combo_ports.count() > 0 else 'COM11'
        self.serial_thread = SerialWorker(port=porta_inicial, baudrate=115200, simulation_mode=False)
        self.serial_thread.data_received.connect(self.update_gauges)
        self.serial_thread.start()

    # =======================================================
    # NOVO: Funções para lidar com o seletor de Porta COM
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
        """Busca as portas ativas no PC e adiciona ao ComboBox."""
        self.combo_ports.blockSignals(True) # Evita disparar a mudança enquanto preenchemos
        self.combo_ports.clear()
        
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.combo_ports.addItem(port.device)
            
        self.combo_ports.blockSignals(False)

    def on_com_port_changed(self, new_port):
        """Reinicia a thread serial com a nova porta."""
        if not new_port:
            return

        print(f"Mudança detectada! Trocando para {new_port}...")
        
        # 1. Para a thread atual com segurança
        if hasattr(self, 'serial_thread') and self.serial_thread.isRunning():
            self.serial_thread.stop()

        # 2. Cria e inicia uma nova thread com a porta atualizada
        self.serial_thread = SerialWorker(port=new_port, baudrate=115200, simulation_mode=False)
        self.serial_thread.data_received.connect(self.update_gauges)
        self.serial_thread.start()


    @pyqtSlot(int, int, int, int, int, int, int, int, int, int, 
                float, float, float, float, float, float, float, 
                float, float, float, float, float, float, float, 
                float, float, float, float, int, float, int, int, 
                int, float, int, int)
    def update_gauges(self, nano_a0, nano_a1, nano_a2, nano_a3, nano_a4, nano_a5, nano_a6, 
                            nano_a7, ecu_uptime, engine_speed, map_press, iat, clt,
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
        self.lbl_gauge_7.setText("RSSI (SINAL)") # NOVO
        self.lbl_gauge_8.setText("RADIATOR IN TEMP")
        self.lbl_gauge_14.setText("RADIATOR OUT TEMP")
        
        """ # Limpa as labels não utilizadas
        for i in range(9, 19):
            getattr(self, f"lbl_gauge_{i}").setText("") """

        self.gauge1.setValue(nano_a0) # TEMPORáRIO
        self.gauge2.setValue(clt)   # Corrigido para mostrar a velocidade real que chegou na função
        self.gauge3.setValue(tps)  # Corrigido para mostrar a temp real que chegou na função
        self.gauge4.setValue(lambda1)
        self.gauge4.setDecimals(3)
        self.gauge5.setValue(battery_v)
        self.gauge5.setDecimals(1)
        self.gauge7.setValue(rssi_dbm) # NOVO: Atualiza o gauge do sinal

    def closeEvent(self, event):
        self.serial_thread.stop()
        event.accept()

# =======================================================
# 3. EXECUÇÃO DO APLICATIVO
# =======================================================
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = Dashboard()
    window.show()
    sys.exit(app.exec_())