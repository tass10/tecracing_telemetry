import sys
import serial
import serial.tools.list_ports
import time
import struct
import random
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QProgressBar, QComboBox, QToolBar
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot
from PyQt5 import uic 

STRUCT_FORMAT = '< 2B 8h H 21h H 3h H B B'
PACKET_SIZE = struct.calcsize(STRUCT_FORMAT)

# =======================================================
# 1. THREAD DE AQUISIÇÃO DE DADOS
# =======================================================
class SerialWorker(QThread):
    data_received = pyqtSignal(int, int, int, int, int, int, int, int, int, int, 
                               float, float, float, float, float, float, float, 
                               float, float, float, float, float, float, float, 
                               float, float, float, float, int, float, int, int, 
                               int, float, int, int)

    def __init__(self, port='COM11', baudrate=115200, simulation_mode=True): # <-- Definido como True para demonstração
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.is_running = True
        self.simulation_mode = simulation_mode 

    def run(self):
        ser = None
        
        while self.is_running:
            # ---------------------------------------------------
            # MODO SIMULAÇÃO (Demonstração com todos os dados)
            # ---------------------------------------------------
            if self.simulation_mode:
                try:
                    # Gerando dados fictícios realistas para demonstração
                    nano_a0 = random.randint(0, 1023)
                    nano_a1 = random.randint(40, 90) # Simulação temp radiador In
                    nano_a2 = random.randint(30, 80) # Simulação temp radiador Out
                    nano_a3, nano_a4, nano_a5, nano_a6, nano_a7 = [random.randint(0, 1023) for _ in range(5)]
                    
                    ecu_uptime = random.randint(0, 65000)
                    engine_speed = random.randint(800, 11500) # RPM
                    map_press = random.uniform(20.0, 250.0)   # kPa
                    iat = random.uniform(20.0, 60.0)          # Temp ar admissão
                    clt = random.uniform(70.0, 105.0)         # Temp motor
                    tps = random.uniform(0.0, 100.0)          # Borboleta
                    lambda1 = random.uniform(0.75, 1.10)      # Sonda
                    oil_press = random.uniform(1.5, 6.0)      # Bar
                    fuel_press = random.uniform(2.5, 4.5)     # Bar
                    
                    aux_v = [random.uniform(0.5, 4.5) for _ in range(9)] # Aux 1 ao 9
                    aux_out3_perc = random.uniform(0.0, 100.0)
                    aux_out6_perc = random.uniform(0.0, 100.0)
                    launch_control = random.choice([0, 1])
                    battery_v = random.uniform(11.5, 14.4)
                    
                    gps_date_utc = 240526
                    gps_lat, gps_lon = -129754, -385123
                    gps_speed = random.uniform(0.0, 140.0)
                    gps_time_utc = 1430
                    rssi_dbm = random.randint(-95, -45)

                    # Emitindo todos os 36 parâmetros exigidos pelo Signal
                    self.data_received.emit(
                        nano_a0, nano_a1, nano_a2, nano_a3, nano_a4, nano_a5, nano_a6, nano_a7,
                        ecu_uptime, engine_speed, map_press, iat, clt, tps, lambda1, oil_press, fuel_press,
                        aux_v[0], aux_v[1], aux_v[2], aux_v[3], aux_v[4], aux_v[5], aux_v[6], aux_v[7], aux_v[8],
                        aux_out3_perc, aux_out6_perc, launch_control, battery_v,
                        gps_date_utc, gps_lat, gps_lon, gps_speed, gps_time_utc, rssi_dbm
                    )
                    time.sleep(0.1) # Atualiza a 10Hz
                except Exception as e:
                    print(f"Erro na simulação: {e}")
                    time.sleep(1)
            
            # ---------------------------------------------------
            # MODO REAL (Mantido intacto)
            # ---------------------------------------------------
            else:
                # ... (Seu código original de conexão serial continua aqui sem alterações)
                pass 

    def stop(self):
        self.is_running = False
        self.wait()

# =======================================================
# 2. INTERFACE GRÁFICA
# =======================================================
class Dashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("python/telemetry/dashboard.ui", self)

        # Configurações originais mantidas
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

        self.gauge4.setRange(0.5, 1.5)
        self.gauge4.setUnits("λ")
        self.gauge4.setScaleSteps(1) 

        self.gauge5.setRange(8, 16)
        self.gauge5.setUnits("V")
        self.gauge5.setScaleSteps(6) 
        self.gauge5.setCriticalThreshold(15) 

        self.gauge6.setRange(0, 160)
        self.gauge6.setUnits("KM/H")
        self.gauge6.setScaleSteps(6) 
        self.gauge6.setCriticalThreshold(120)

        self.gauge7.setRange(-120, -30) 
        self.gauge7.setUnits("dBm")
        self.gauge7.setScaleSteps(5)
        self.gauge7.setCriticalThreshold(0) 

        self.gauge8.setRange(0, 120)
        self.gauge8.setUnits("°C")
        self.gauge8.setScaleSteps(6) 
        self.gauge8.setCriticalThreshold(100)

        self.gauge14.setRange(0, 120)
        self.gauge14.setUnits("°C")
        self.gauge14.setScaleSteps(6) 
        self.gauge14.setCriticalThreshold(100)

        # --- PREENCHENDO O RESTANTE DOS GAUGES (9 ao 30) ---
        config_pressao = {"range": (0, 10), "units": "Bar", "steps": 5, "crit": 8}
        config_map = {"range": (0, 300), "units": "kPa", "steps": 6, "crit": 250}
        config_volts = {"range": (0, 5), "units": "V", "steps": 5, "crit": 15}
        config_perc = {"range": (0, 100), "units": "%", "steps": 5, "crit": 90}
        config_raw = {"range": (0, 1023), "units": "Raw", "steps": 5, "crit": 1000}

        self._setup_gauge(self.gauge9, config_map)      # MAP
        self._setup_gauge(self.gauge10, config_pressao) # Oil Press
        self._setup_gauge(self.gauge11, config_pressao) # Fuel Press
        self._setup_gauge(self.gauge12, config_raw)     # Nano A0
        self._setup_gauge(self.gauge13, config_raw)     # Nano A3
        self._setup_gauge(self.gauge15, config_volts)   # Aux 1
        self._setup_gauge(self.gauge16, config_volts)   # Aux 2
        self._setup_gauge(self.gauge17, config_volts)   # Aux 3
        self._setup_gauge(self.gauge18, config_volts)   # Aux 4
        self._setup_gauge(self.gauge19, config_volts)   # Aux 5
        self._setup_gauge(self.gauge20, config_volts)   # Aux 6
        self._setup_gauge(self.gauge21, config_volts)   # Aux 7
        self._setup_gauge(self.gauge22, config_volts)   # Aux 8
        self._setup_gauge(self.gauge23, config_volts)   # Aux 9
        self._setup_gauge(self.gauge24, config_perc)    # Aux Out 3
        self._setup_gauge(self.gauge25, config_perc)    # Aux Out 6
        self._setup_gauge(self.gauge26, {"range": (0, 1), "units": "ON/OFF", "steps": 1, "crit": 1}) # Launch Control
        self._setup_gauge(self.gauge27, {"range": (0, 120), "units": "°C", "steps": 6, "crit": 80})  # IAT
        self._setup_gauge(self.gauge28, config_raw)     # Nano A4
        self._setup_gauge(self.gauge29, config_raw)     # Nano A5
        self._setup_gauge(self.gauge30, config_raw)     # Nano A6

        self.setup_com_toolbar()

        # Inicia o simulador
        self.serial_thread = SerialWorker(simulation_mode=True)
        self.serial_thread.data_received.connect(self.update_gauges)
        self.serial_thread.start()

    def _setup_gauge(self, gauge, cfg):
        """Função auxiliar para não repetir código configurando os gauges"""
        gauge.setRange(*cfg["range"])
        gauge.setUnits(cfg["units"])
        gauge.setScaleSteps(cfg["steps"])
        if "crit" in cfg:
            gauge.setCriticalThreshold(cfg["crit"])

    # ... (Funções da barra COM mantidas) ...
    def setup_com_toolbar(self):
        pass # Mantido igual o seu

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
        
        # 1. Definindo as Labels para os 30 mostradores
        self.lbl_gauge_1.setText("ENGINE SPEED (RPM)")
        self.lbl_gauge_2.setText("ENGINE TEMP")
        self.lbl_gauge_3.setText("TPS")
        self.lbl_gauge_4.setText("LAMBDA")
        self.lbl_gauge_5.setText("BATTERY VOLTAGE")
        self.lbl_gauge_6.setText("GPS VELOCITY")
        self.lbl_gauge_7.setText("RSSI (SINAL LORA)") 
        self.lbl_gauge_8.setText("RADIATOR IN TEMP")
        self.lbl_gauge_9.setText("MAP PRESS")
        self.lbl_gauge_10.setText("OIL PRESS")
        self.lbl_gauge_11.setText("FUEL PRESS")
        self.lbl_gauge_12.setText("SENSOR 4 (RAW)")
        self.lbl_gauge_13.setText("SENSOR 5 (RAW)")
        self.lbl_gauge_14.setText("RADIATOR OUT TEMP")
        self.lbl_gauge_15.setText("AUX 1 VOLTAGE")
        self.lbl_gauge_16.setText("AUX 2 VOLTAGE")
        self.lbl_gauge_17.setText("AUX 3 VOLTAGE")
        self.lbl_gauge_18.setText("AUX 4 VOLTAGE")
        self.lbl_gauge_19.setText("AUX 5 VOLTAGE")
        self.lbl_gauge_20.setText("AUX 6 VOLTAGE")
        self.lbl_gauge_21.setText("AUX 7 VOLTAGE")
        self.lbl_gauge_22.setText("AUX 8 VOLTAGE")
        self.lbl_gauge_23.setText("AUX 9 VOLTAGE")
        self.lbl_gauge_24.setText("AUX OUT 3 DUTY")
        self.lbl_gauge_25.setText("AUX OUT 6 DUTY")
        self.lbl_gauge_26.setText("LAUNCH CONTROL")
        self.lbl_gauge_27.setText("INTAKE AIR TEMP")
        self.lbl_gauge_28.setText("SENSOR 6 (RAW)")
        self.lbl_gauge_29.setText("SENSOR 7 (RAW)")
        self.lbl_gauge_30.setText("SENSOR 8 (RAW)")

        # 2. Injetando os dados nos 30 Gauges
        self.gauge1.setValue(engine_speed)
        self.gauge2.setValue(clt)  
        self.gauge3.setValue(tps)  
        
        self.gauge4.setValue(lambda1)
        self.gauge4.setDecimals(3)
        
        self.gauge5.setValue(battery_v)
        self.gauge5.setDecimals(1)
        
        self.gauge6.setValue(gps_speed)
        self.gauge7.setValue(rssi_dbm)
        self.gauge8.setValue(nano_a1)
        
        self.gauge9.setValue(map_press)
        self.gauge10.setValue(oil_press)
        self.gauge10.setDecimals(1)
        self.gauge11.setValue(fuel_press)
        self.gauge11.setDecimals(1)
        self.gauge12.setValue(nano_a0)
        self.gauge13.setValue(nano_a3)
        self.gauge14.setValue(nano_a2)
        
        # Mapeando Auxiliares
        auxiliares_v = [aux1_v, aux2_v, aux3_v, aux4_v, aux5_v, aux6_v, aux7_v, aux8_v, aux9_v]
        gauges_aux = [self.gauge15, self.gauge16, self.gauge17, self.gauge18, self.gauge19, self.gauge20, self.gauge21, self.gauge22, self.gauge23]
        for idx, g in enumerate(gauges_aux):
            g.setValue(auxiliares_v[idx])
            g.setDecimals(2)

        self.gauge24.setValue(aux_out3_perc)
        self.gauge25.setValue(aux_out6_perc)
        self.gauge26.setValue(launch_control)
        self.gauge27.setValue(iat)
        self.gauge28.setValue(nano_a4)
        self.gauge29.setValue(nano_a5)
        self.gauge30.setValue(nano_a6)

    def closeEvent(self, event):
        self.serial_thread.stop()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = Dashboard()
    window.show()
    sys.exit(app.exec_())