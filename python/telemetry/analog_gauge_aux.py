from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QPen, QColor, QFont
from PyQt5.QtCore import Qt, QRectF
import math # <-- OBRIGATÓRIO PARA A TRIGONOMETRIA

class AnalogGaugeAux(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = 0
        self.vmin = 0
        self.vmax = 100
        self.units = "Unidade"
        self.decimals = 0
        
        self.critical_value = 80 
        self.normal_color = QColor(0, 150, 255) 
        self.critical_color = QColor(255, 50, 50) 
        
        # --- NOVA VARIÁVEL: Quantidade de intervalos na escala ---
        self.scale_steps = 5 
        
        self.setMinimumSize(150, 150)

    def setRange(self, vmin, vmax):
        self.vmin = vmin
        self.vmax = vmax
        self.update()

    def setValue(self, value):
        self.value = max(self.vmin, min(value, self.vmax))
        self.update()

    def setDecimals(self, decimals):
        self.decimals = decimals
        self.update()

    def setUnits(self, units):
        self.units = units
        self.update()

    def setCriticalThreshold(self, value):
        self.critical_value = value
        self.update()

    def setCustomColors(self, normal_hex, critical_hex):
        self.normal_color = QColor(normal_hex)
        self.critical_color = QColor(critical_hex)
        self.update()

    # --- NOVO MÉTODO: Define quantos números intermediários desenhar ---
    def setScaleSteps(self, steps):
        """Ex: 5 passos cria 6 números (0, 20, 40, 60, 80, 100)"""
        self.scale_steps = steps
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()
        width = rect.width()
        height = rect.height()
        size = min(width, height) - 20
        
        painter.translate(width / 2, height / 2)
        
        start_angle = 225 
        span_angle = -270 

        # 1. Fundo do arco
        pen_bg = QPen(QColor(50, 50, 50), 10, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(pen_bg)
        arc_rect = QRectF(-size/2, -size/2, size, size)
        painter.drawArc(arc_rect, start_angle * 16, span_angle * 16)

        # 2. Arco de Valor
        if self.vmax - self.vmin != 0:
            proporcao = (self.value - self.vmin) / (self.vmax - self.vmin)
        else:
            proporcao = 0
            
        current_span = span_angle * proporcao

        if self.value >= self.critical_value:
            pen_fill = QPen(self.critical_color, 15, Qt.SolidLine, Qt.RoundCap)
        else:
            pen_fill = QPen(self.normal_color, 15, Qt.SolidLine, Qt.RoundCap)
            
        painter.setPen(pen_fill)
        painter.drawArc(arc_rect, start_angle * 16, int(current_span * 16))

        # --- 3. NOVA LÓGICA: DESENHA OS NÚMEROS DA ESCALA ---
        font_scale = QFont("Arial", 8, QFont.Bold)
        painter.setFont(font_scale)
        painter.setPen(QColor(200, 200, 200)) # Cinza claro

        # Define o raio onde os números vão ficar (um pouco para dentro da barra)
        radius = (size / 2) - 20 

        for i in range(self.scale_steps + 1):
            # Calcula o valor deste ponto específico
            current_val = self.vmin + (self.vmax - self.vmin) * (i / self.scale_steps)
            
            # Calcula o ângulo em graus (começa em 225 e vai subtraindo até chegar em -45)
            angle_deg = start_angle + (span_angle * (i / self.scale_steps))
            angle_rad = math.radians(angle_deg)
            
            # Converte polar para cartesiano (eixo Y invertido no Qt)
            x = radius * math.cos(angle_rad)
            y = -radius * math.sin(angle_rad)
            
            # Abrevia valores altos (ex: 12000 -> 12k) para não amontoar os textos
            if self.vmax >= 1000:
                text = f"{int(current_val/1000)}k" if current_val > 0 else "0"
            else:
                text = f"{int(current_val)}"
            
            # Desenha o texto centralizado nas coordenadas x e y calculadas
            text_rect = QRectF(x - 20, y - 10, 40, 20)
            painter.drawText(text_rect, Qt.AlignCenter, text)

        # 4. Texto do Valor Central
        painter.setPen(QColor(0, 0, 0))
        font = QFont("Arial", 20, QFont.Bold)
        painter.setFont(font)
        if self.decimals <= 0:
            painter.drawText(QRectF(-size/2, -size/5, size, size/3), Qt.AlignCenter, f"{int(self.value)}")
        else:
            painter.drawText(QRectF(-size/2, -size/5, size, size/3), Qt.AlignCenter, f"{self.value:.{self.decimals}f}")
        
        # 5. Texto da Unidade
        font_unit = QFont("Arial", 13, QFont.Bold)
        painter.setFont(font_unit)
        painter.drawText(QRectF(-size/2, size/5, size, size/3), Qt.AlignCenter, self.units)

        

        painter.end()