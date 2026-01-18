import sys
import pyqtgraph as pg
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QTextEdit
from PyQt5.QtCore import Qt, QTimer, QPointF
from PyQt5.QtGui import QPainter, QColor, QPen, QPainterPath, QPolygonF

# Alan Łangowski s202407 PG Projekt 2
class Rura:
    def __init__(self, punkty, grubosc=12, kolor=Qt.gray):
        self.punkty = [QPointF(float(p[0]), float(p[1])) for p in punkty]
        self.grubosc = grubosc
        self.kolor_rury = kolor
        self.kolor_cieczy = QColor(0, 180, 255)
        self.czy_plynie = False

    def ustaw_przeplyw(self, plynie):
        self.czy_plynie = plynie

    def draw(self, painter):
        if len(self.punkty) < 2: return
        path = QPainterPath()
        path.moveTo(self.punkty[0])
        for p in self.punkty[1:]: path.lineTo(p)

        pen_rura = QPen(self.kolor_rury, self.grubosc, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen_rura)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)

        if self.czy_plynie:
            pen_ciecz = QPen(self.kolor_cieczy, self.grubosc - 4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen_ciecz)
            painter.drawPath(path)

# Zbiornik stany wody i poziomy
class Zbiornik:
    def __init__(self, x, y, width=100, height=140, nazwa="", przesuniecie_tekstu=0):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.nazwa = nazwa
        self.przesuniecie_tekstu = przesuniecie_tekstu
        self.pojemnosc = 100.0
        self.aktualna_ilosc = 0.0
        self.poziom = 0.0

    def dodaj_ciecz(self, ilosc):
        wolne = self.pojemnosc - self.aktualna_ilosc
        dodano = min(ilosc, wolne)
        self.aktualna_ilosc += dodano
        self.aktualizuj_poziom()
        return dodano

    def usun_ciecz(self, ilosc):
        usunieto = min(ilosc, self.aktualna_ilosc)
        self.aktualna_ilosc -= usunieto
        self.aktualizuj_poziom()
        return usunieto

    def aktualizuj_poziom(self):
        self.poziom = self.aktualna_ilosc / self.pojemnosc
    def czy_pusty(self): return self.aktualna_ilosc <= 0.1
    def czy_pelny(self): return self.aktualna_ilosc >= self.pojemnosc - 0.1
    def punkt_gora_srodek(self): return (self.x + self.width / 2, self.y)
    def punkt_dol_srodek(self): return (self.x + self.width / 2, self.y + self.height)
    def punkt_dol_prawo(self): return (self.x + self.width, self.y + self.height - 20)

    def draw(self, painter):
        if self.poziom > 0:
            h_cieczy = self.height * self.poziom
            y_start = self.y + self.height - h_cieczy
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 120, 255, 200))
            painter.drawRect(int(self.x + 3), int(y_start), int(self.width - 6), int(h_cieczy - 2))
        pen = QPen(Qt.white, 4)
        pen.setJoinStyle(Qt.MiterJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(int(self.x), int(self.y), int(self.width), int(self.height))
        
        painter.setPen(Qt.white)
        painter.drawText(int(self.x + self.przesuniecie_tekstu), int(self.y - 10), self.nazwa)

# XXX głowny
class SymulacjaKaskady(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Projekt s202407")
        self.setFixedSize(1350, 650)
        self.setStyleSheet("background-color: #222;")

        # Tworzenie zbiorników
        self.z1 = Zbiornik(400, 50, nazwa="Z1")
        self.z1.aktualna_ilosc = 100.0
        self.z1.aktualizuj_poziom()
        
        self.z2 = Zbiornik(400, 250, nazwa="Z2") 
        self.z3 = Zbiornik(150, 450, nazwa="Z3") 
        self.z4 = Zbiornik(650, 450, nazwa="Z4", przesuniecie_tekstu=80) 
        
        self.zbiorniki = [self.z1, self.z2, self.z3, self.z4]

        # Układanie rur
        p1s = self.z1.punkt_dol_srodek()
        p1k = self.z2.punkt_gora_srodek()
        self.rura_1_2 = Rura([p1s, p1k])

        p2s = self.z2.punkt_dol_srodek()
        mid_y = p2s[1] + 40 

        p3k = self.z3.punkt_gora_srodek()
        self.rura_2_3 = Rura([p2s, (p2s[0], mid_y), (p3k[0], mid_y), p3k])

        p4k = self.z4.punkt_gora_srodek()
        self.rura_2_4 = Rura([p2s, (p2s[0], mid_y), (p4k[0], mid_y), p4k])

        pps = self.z4.punkt_dol_prawo()
        ppk = (self.z1.punkt_gora_srodek()[0] + 40, self.z1.y + 10)
        self.rura_pompa = Rura([
            pps, (pps[0]+20, pps[1]), (pps[0]+20, ppk[1]-30), (ppk[0], ppk[1]-30), ppk
        ], grubosc=8, kolor=QColor(100, 100, 100))

        self.rury = [self.rura_1_2, self.rura_2_3, self.rura_2_4, self.rura_pompa]

        # Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.logika_przeplywu)
        self.running = False
        self.flow_speed = 0.8
        self.pompa_aktywna = False
        self.kierunek_zaworu = "LEWO" 

        # Prawy bok rzeczy
        self.lista_alarmow = QTextEdit(self)
        self.lista_alarmow.setGeometry(920, 50, 400, 250)
        self.lista_alarmow.setReadOnly(True)
        self.lista_alarmow.setStyleSheet("background-color: #111; color: #0f0; font-family: Consolas; font-size: 9pt; border: 1px solid #555;")
        self.lista_alarmow.append("=== DZIENNIK ZDARZEŃ I ALARMÓW ===")
        self.lista_alarmow.append(f"[{datetime.now().strftime('%H:%M:%S')}] System uruchomiony.")

        self.graphWidget = pg.PlotWidget(self)
        self.graphWidget.setGeometry(920, 320, 400, 250)
        self.graphWidget.setBackground('#222') 
        self.graphWidget.setTitle("Wykres Poziomu Z4", color="w", size="10pt")
        
        styles = {'color':'white', 'font-size':'10px'}
        self.graphWidget.setLabel('left', 'Poziom', **styles)
        self.graphWidget.setLabel('bottom', 'Czas', **styles)
        self.graphWidget.showGrid(x=True, y=True, alpha=0.3)
        self.graphWidget.setYRange(0, 1.1)

        self.data_limit = 200
        self.z4_data = [0.0] * self.data_limit
        
        pen = pg.mkPen(color=(0, 180, 255), width=2)
        self.data_line = self.graphWidget.plot(self.z4_data, pen=pen)
        self.limit_line = self.graphWidget.addLine(y=0.4, pen=pg.mkPen('r', width=1, style=Qt.DashLine))

        self.setup_buttons()

    # wrzucanie txt do logów
    def log_alarm(self, wiadomosc):
        czas = datetime.now().strftime("%H:%M:%S")
        wpis = f"[{czas}] {wiadomosc}"
        self.lista_alarmow.append(wpis)
        cursor = self.lista_alarmow.textCursor()
        cursor.movePosition(cursor.End)
        self.lista_alarmow.setTextCursor(cursor)

    # Ustawienie przyciskow na ekranie
    def setup_buttons(self):
        self.btn_start = QPushButton("Start / Stop", self)
        self.btn_start.setGeometry(400, 600, 100, 30)
        self.btn_start.setStyleSheet("background-color: #666; color: white; font-weight: bold;")
        self.btn_start.clicked.connect(self.przelacz_symulacje)

        self.btn_z1_plus = QPushButton("Napełnij Z1", self)
        self.btn_z1_plus.setGeometry(400, 565, 100, 30)
        self.btn_z1_plus.setStyleSheet("background-color: #444; color: white;")
        self.btn_z1_plus.clicked.connect(self.napelnij_z1)

        self.btn_z3_minus = QPushButton("Opróżnij Z3", self)
        self.btn_z3_minus.setGeometry(150, 600, 100, 25)
        self.btn_z3_minus.setStyleSheet("background-color: #444; color: white;")
        self.btn_z3_minus.clicked.connect(self.oproznij_z3)
        
        self.btn_z4_minus = QPushButton("Opróżnij Z4", self)
        self.btn_z4_minus.setGeometry(650, 600, 100, 25)
        self.btn_z4_minus.setStyleSheet("background-color: #444; color: white;")
        self.btn_z4_minus.clicked.connect(self.oproznij_z4)

        self.btn_zawor = QPushButton(f"Zawór: {self.kierunek_zaworu}", self)
        self.btn_zawor.setGeometry(350, 420, 200, 30)
        self.btn_zawor.setStyleSheet("background-color: #D35400; color: white; font-weight: bold;")
        self.btn_zawor.clicked.connect(self.zmien_zawor)

    # panele klikane opis
    def napelnij_z1(self):
        self.z1.aktualna_ilosc = 100.0
        self.z1.aktualizuj_poziom()
        self.log_alarm("OPERATOR: Napełniono ręcznie Z1")
        self.update()

    def oproznij_z3(self):
        self.z3.aktualna_ilosc = 0.0
        self.z3.aktualizuj_poziom()
        self.log_alarm("OPERATOR: Opróżniono ręcznie Z3")
        self.update()

    def oproznij_z4(self):
        self.z4.aktualna_ilosc = 0.0
        self.z4.aktualizuj_poziom()
        self.log_alarm("OPERATOR: Opróżniono ręcznie Z4")
        self.update()

    def przelacz_symulacje(self):
        if self.running: 
            self.timer.stop()
            self.log_alarm("SYSTEM: Symulacja ZATRZYMANA")
        else: 
            self.timer.start(20)
            self.log_alarm("SYSTEM: Symulacja URUCHOMIONA")
        self.running = not self.running

    def zmien_zawor(self):
        if self.kierunek_zaworu == "LEWO": self.kierunek_zaworu = "PRAWO"
        else: self.kierunek_zaworu = "LEWO"
        self.btn_zawor.setText(f"Zawór: {self.kierunek_zaworu}")
        self.log_alarm(f"STEROWANIE: Przestawiono zawór na {self.kierunek_zaworu}")
        self.update()

    # Fizyka przepływu
    def logika_przeplywu(self):
        #  Z1 do Z2
        plynie_1_2 = False
        if not self.z1.czy_pusty() and not self.z2.czy_pelny():
            ilosc = self.z1.usun_ciecz(self.flow_speed)
            self.z2.dodaj_ciecz(ilosc)
            plynie_1_2 = True
        self.rura_1_2.ustaw_przeplyw(plynie_1_2)

        # Z2 leci do Z3 albo Z4 (zależnie jak ustawiony zawór)
        plynie_2_3 = False
        plynie_2_4 = False
        if not self.z2.czy_pusty():
            if self.kierunek_zaworu == "LEWO":
                if not self.z3.czy_pelny():
                    wolne = self.z3.pojemnosc - self.z3.aktualna_ilosc
                    ilosc = min(self.flow_speed, self.z2.aktualna_ilosc, wolne)
                    if ilosc > 0:
                        self.z2.usun_ciecz(ilosc)
                        self.z3.dodaj_ciecz(ilosc)
                        plynie_2_3 = True
            elif self.kierunek_zaworu == "PRAWO":
                if not self.z4.czy_pelny():
                    wolne = self.z4.pojemnosc - self.z4.aktualna_ilosc
                    ilosc = min(self.flow_speed, self.z2.aktualna_ilosc, wolne)
                    if ilosc > 0:
                        self.z2.usun_ciecz(ilosc)
                        self.z4.dodaj_ciecz(ilosc)
                        plynie_2_4 = True
        self.rura_2_3.ustaw_przeplyw(plynie_2_3)
        self.rura_2_4.ustaw_przeplyw(plynie_2_4)

        # Pompa pilnujaca z4
        poprzedni_stan = self.pompa_aktywna
        if self.z4.poziom >= 0.4: self.pompa_aktywna = True
        if self.z4.aktualna_ilosc < 2.0: self.pompa_aktywna = False

        if self.pompa_aktywna and not poprzedni_stan:
            self.log_alarm("ALARM: Wysoki poziom w Z4 (>40%). START POMPY!")
        elif not self.pompa_aktywna and poprzedni_stan:
            self.log_alarm("INFO: Poziom Z4 w normie. STOP POMPY.")

        plynie_pompa = False
        if self.pompa_aktywna:
            speed_pompy = self.flow_speed * 2.0
            if not self.z4.czy_pusty() and not self.z1.czy_pelny():
                ilosc = self.z4.usun_ciecz(speed_pompy)
                self.z1.dodaj_ciecz(ilosc)
                plynie_pompa = True
        self.rura_pompa.ustaw_przeplyw(plynie_pompa)

        self.update()

        # Aktualizacja wykresu
        self.z4_data = self.z4_data[1:] 
        self.z4_data.append(self.z4.poziom)
        self.data_line.setData(self.z4_data)

    # Rysowanie wszystkiego na ekranie
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        for r in self.rury: r.draw(p)
        for z in self.zbiorniki: z.draw(p)

        p.setPen(Qt.white)
        status = "WŁĄCZONA" if self.pompa_aktywna else "WYŁĄCZONA"
        p.drawText(760, 480, f"POMPA: {status}")

        # zawór
        p.setBrush(QColor("#D35400"))
        p.setPen(Qt.NoPen)
        center_x = self.z2.x + self.z2.width / 2
        center_y = self.z2.y + self.z2.height + 40
        
        # ZMIANA: nazwa zmiennej
        przyciskzaw = QPolygonF()
        if self.kierunek_zaworu == "LEWO":
            przyciskzaw.append(QPointF(center_x + 10, center_y - 10))
            przyciskzaw.append(QPointF(center_x + 10, center_y + 10))
            przyciskzaw.append(QPointF(center_x - 15, center_y))
        else:
            przyciskzaw.append(QPointF(center_x - 10, center_y - 10))
            przyciskzaw.append(QPointF(center_x - 10, center_y + 10))
            przyciskzaw.append(QPointF(center_x + 15, center_y))
        p.drawPolygon(przyciskzaw)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    okno = SymulacjaKaskady()
    okno.show()
    sys.exit(app.exec_())