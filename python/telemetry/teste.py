import sys
import serial
import serial.tools.list_ports
import time
import struct
import csv 
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QProgressBar, QComboBox, QToolBar, QMessageBox 
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot
from PyQt5 import uic 
import random

# =======================================================
# FORMATO DA STRUCT DE TELEMETRIA
# =======================================================
STRUCT_FORMAT = '< 2B 8h H 21h H 3h H B B'
PACKET_SIZE = struct.calcsize(STRUCT_FORMAT)

# =======================================================
# 1. THREAD DE AQUISIÇÃO DE DADOS (Background)
# =======================================================
class SerialWorker(QThread):
    data_received = pyqtSignal(int, int, int, int, int, int, int, int, int, int, 
                               float, float, float, float, float, float, float, 
                               float, float, float, float, float, float, float, 
                               float, float, float, float, int, float, int, int, 
                               int, float, int, int)
    
    # --- ATUALIZADO: Sinal emitido quando o teste acaba (agora com +3 floats para a frequência) ---
    test_completed = pyqtSignal(int, float, float, int, int, str, float, float, float)

    def __init__(self, port='COM11', baudrate=115200, simulation_mode=False):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.is_running = True
        self.simulation_mode = simulation_mode 
        
        # --- Variáveis de controle do teste ---
        self.rssi_history = []
        self.freq_history = [] # NOVO: Armazena as frequências calculadas
        self.last_packet_time = 0
        self.receiving_data = False
        self.log_filename = ""

    def run(self):
        ser = None
        
        while self.is_running:
            if self.simulation_mode:
                try:
                    rpm = random.uniform(0, 12000)
                    vel = random.uniform(0, 120)
                    temp = random.uniform(0, 100)
                    time.sleep(0.1) 
                except Exception as e:
                    print(f"Erro na simulação: {e}")
                    time.sleep(1)
            
            else:
                try:
                    if ser is None or not ser.is_open:
                        print(f"Tentando conectar à porta {self.port}...")
                        ser = serial.Serial()
                        ser.port = self.port
                        ser.baudrate = self.baudrate
                        ser.timeout = 1
                        ser.dtr = False
                        ser.rts = False
                        ser.open()
                        print(f"CONECTADO COM SUCESSO à porta {self.port}!")
                    
                    while self.is_running and ser.is_open and not self.simulation_mode:
                        
                        byte_lido = ser.read(1)
                        current_time = time.time()
                        
                        # ==========================================================
                        # VERIFICAÇÃO DE TIMEOUT DE 5 SEGUNDOS (FIM DO TESTE)
                        # ==========================================================
                        if self.receiving_data and (current_time - self.last_packet_time) > 5.0:
                            total_msgs = len(self.rssi_history)
                            esperadas = 1000
                            # Calcula a porcentagem de erro (PER)
                            erro_perc = ((esperadas - total_msgs) / esperadas) * 100.0 if total_msgs <= esperadas else 0.0
                            
                            # Estatísticas de RSSI
                            if total_msgs > 0:
                                avg_rssi = sum(self.rssi_history) / total_msgs
                                max_rssi = max(self.rssi_history)
                                min_rssi = min(self.rssi_history)
                            else:
                                avg_rssi = max_rssi = min_rssi = 0
                                
                            # NOVO: Estatísticas de Frequência (Hz)
                            if len(self.freq_history) > 0:
                                avg_freq = sum(self.freq_history) / len(self.freq_history)
                                max_freq = max(self.freq_history)
                                min_freq = min(self.freq_history)
                            else:
                                avg_freq = max_freq = min_freq = 0.0
                                
                            # Emite o sinal para a interface gráfica exibir o relatório
                            self.test_completed.emit(total_msgs, erro_perc, avg_rssi, max_rssi, min_rssi, self.log_filename, avg_freq, max_freq, min_freq)
                            
                            # Reseta as variáveis para aguardar um próximo teste
                            self.rssi_history = []
                            self.freq_history = []
                            self.receiving_data = False
                        # ==========================================================

                        if not byte_lido:
                            continue
                            
                        if byte_lido[0] == 0xAA:
                            byte2 = ser.read(1)
                            if byte2 and byte2[0] == 0x55:
                                resto_do_pacote = ser.read(PACKET_SIZE - 2)
                                
                                if len(resto_do_pacote) == PACKET_SIZE - 2:
                                    pacote_completo = b'\xAA\x55' + resto_do_pacote
                                    
                                    calc_ck = 0
                                    for b in pacote_completo[:-2]:
                                        calc_ck ^= b
                                        
                                    checksum_recebido = pacote_completo[-2]
                                    
                                    if calc_ck != checksum_recebido:
                                        print("Pacote corrompido descartado pelo Checksum!")
                                        continue 
                                    
                                    try:
                                        dados = struct.unpack(STRUCT_FORMAT, pacote_completo)
                                        
                                        nano_a0 = dados[2]; nano_a1 = dados[3]; nano_a2 = dados[4]
                                        nano_a3 = dados[5]; nano_a4 = dados[6]; nano_a5 = dados[7]
                                        nano_a6 = dados[8]; nano_a7 = dados[9]

                                        ecu_uptime = dados[10]
                                        engine_speed = dados[11]
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
                                        rssi_dbm = rssi_raw - 256

                                        # ==================================================
                                        # SALVA DADOS NO CSV E ATUALIZA CONTADORES/FREQUÊNCIA
                                        # ==================================================
                                        if not self.receiving_data:
                                            self.receiving_data = True
                                            self.log_filename = f"telemetria_{int(current_time)}.csv"
                                            print(f"Iniciando novo teste. Salvando em: {self.log_filename}")
                                        else:
                                            # NOVO: Calcula a frequência em Hz (mensagens por segundo)
                                            delta_t = current_time - self.last_packet_time
                                            # Previne divisão por zero caso cheguem muito rápido para o clock do Python
                                            if delta_t > 0.001: 
                                                freq_hz = 1.0 / delta_t
                                                self.freq_history.append(freq_hz)

                                        self.rssi_history.append(rssi_dbm)
                                        self.last_packet_time = current_time

                                        # Salva a tupla crua completa no arquivo CSV
                                        with open(self.log_filename, 'a', newline='') as f:
                                            writer = csv.writer(f)
                                            writer.writerow(dados)
                                        # ==================================================

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
        
        uic.loadUi("python/telemetry/dashboard.ui", self)

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

        self.setup_com_toolbar()

        porta_inicial = 'COM11'
        self.serial_thread = SerialWorker(port=porta_inicial, baudrate=115200, simulation_mode=False)
        self.serial_thread.data_received.connect(self.update_gauges)
        
        # Conecta o sinal de fim de teste à função que exibe o pop-up
        self.serial_thread.test_completed.connect(self.show_test_report)
        
        self.serial_thread.start()

    def setup_com_toolbar(self):
        self.toolbar = QToolBar("Configurações de Conexão")
        self.addToolBar(self.toolbar)

        self.lbl_com = QLabel(" Porta COM: ")
        self.toolbar.addWidget(self.lbl_com)

        self.combo_ports = QComboBox()
        self.refresh_com_ports() 
        self.toolbar.addWidget(self.combo_ports)

        self.combo_ports.currentTextChanged.connect(self.on_com_port_changed)

    def refresh_com_ports(self):
        self.combo_ports.blockSignals(True) 
        self.combo_ports.clear()
        
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.combo_ports.addItem(port.device)
            
        self.combo_ports.blockSignals(False)

    def on_com_port_changed(self, new_port):
        if not new_port:
            return

        print(f"Mudança detectada! Trocando para {new_port}...")
        
        if hasattr(self, 'serial_thread') and self.serial_thread.isRunning():
            self.serial_thread.stop()

        self.serial_thread = SerialWorker(port=new_port, baudrate=115200, simulation_mode=False)
        self.serial_thread.data_received.connect(self.update_gauges)
        self.serial_thread.test_completed.connect(self.show_test_report) 
        self.serial_thread.start()

    # --- ATUALIZADO: Função que exibe a caixa de diálogo com as novas métricas de frequência ---
    @pyqtSlot(int, float, float, int, int, str, float, float, float)
    def show_test_report(self, total, erro_perc, avg_rssi, max_rssi, min_rssi, filename, avg_freq, max_freq, min_freq):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Relatório de Telemetria LoRa")
        msg.setText("Teste Finalizado! (5 segundos sem receber dados)")
        
        # Monta o texto formatado com as métricas
        relatorio = (
            f"Mensagens Recebidas: {total} de 1000\n"
            f"Taxa de Erro (PER): {erro_perc:.2f}%\n\n"
            f"Métricas de Sinal (RSSI):\n"
            f"  • Média: {avg_rssi:.1f} dBm\n"
            f"  • Máximo: {max_rssi} dBm (Mais forte)\n"
            f"  • Mínimo: {min_rssi} dBm (Mais fraco)\n\n"
            f"Frequência de Atualização:\n"
            f"  • Média: {avg_freq:.1f} Hz (pacotes/seg)\n"
            f"  • Máxima: {max_freq:.1f} Hz\n"
            f"  • Mínima: {min_freq:.1f} Hz\n\n"
            f"Os dados brutos foram salvos na pasta do projeto:\n'{filename}'"
        )
        
        msg.setInformativeText(relatorio)
        msg.exec_()


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
        self.lbl_gauge_7.setText("RSSI (SINAL)") 
        self.lbl_gauge_8.setText("RADIATOR IN TEMP")
        self.lbl_gauge_14.setText("RADIATOR OUT TEMP")

        self.gauge1.setValue(nano_a0) 
        self.gauge2.setValue(clt)   
        self.gauge3.setValue(tps)  
        self.gauge4.setValue(lambda1)
        self.gauge4.setDecimals(3)
        self.gauge5.setValue(battery_v)
        self.gauge5.setDecimals(1)
        self.gauge7.setValue(rssi_dbm) 

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