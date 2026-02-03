"""
Author: Alexander Zahrebaiev
Callsign: UW5EMC
Email: lulzsecer@gmail.com
Website: https://devtech.dp.ua/
Date: 2026-02-01
Version: 1.1
"""
import socket
# python
import sys

from PySide6.QtCore import QThread, Signal, Slot
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem, QPlainTextEdit
)
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt

from config import UDP_IP, UDP_PORT, CTY_FILE, CONFIRMED_FILES, CONFIRMED_FILE_DEFAULT
from dxcc.callsign import extract_dx_call
from dxcc.cty_parser import load_cty, get_country
from notify.windows import notify_new_dxcc
from wsjtx.decoder import parse_decode, parse_status


def load_confirmed(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        return set()

def get_confirmed_for_band(band):
    if band and band in CONFIRMED_FILES:
        return load_confirmed(CONFIRMED_FILES[band])
    return load_confirmed(CONFIRMED_FILE_DEFAULT)

class UdpWorker(QThread):
    status_update = Signal(object)  # dict with frequency, band
    new_dxcc = Signal(str, str, str, int, object)  # country, call, mode, snr, dict(decoded)
    log = Signal(str)
    finished_clean = Signal()

    def __init__(self, prefixes, parent=None):
        super().__init__(parent)
        self._running = False
        self.prefixes = prefixes
        self.alerted = set()
        self.current_band = None
        self.current_mode = None
        self.current_frequency = None
        self.confirmed = set()

    def run(self):
        self._running = True
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind((UDP_IP, UDP_PORT))
        except Exception as error:
            self.log.emit(f"Failed to bind UDP {UDP_IP}:{UDP_PORT}: {error}")
            return

        self.log.emit(f"Listening UDP {UDP_IP}:{UDP_PORT}...")

        try:
            while self._running:
                try:
                    data, _ = sock.recvfrom(8192)
                except OSError:
                    break

                status = parse_status(data)
                if status:
                    new_frequency = status.get("frequency")
                    new_band = status.get("band")
                    if new_band != self.current_band:
                        self.current_band = new_band
                        self.current_mode = status.get("mode")
                        self.current_frequency = new_frequency
                        self.confirmed = get_confirmed_for_band(self.current_band)
                        self.alerted.clear()
                        self.log.emit(f"Band changed to: {self.current_band or 'unknown'} ({(self.current_frequency or 0)/1e6:.3f} MHz)")
                        self.log.emit(f"Mode: {self.current_mode or 'unknown'}")
                        self.log.emit(f"Loaded {len(self.confirmed)} confirmed countries for this band")
                    else:
                        self.current_frequency = new_frequency
                    self.status_update.emit({"frequency": self.current_frequency, "band": self.current_band, "mode": self.current_mode})
                    continue

                decoded = parse_decode(data, self.current_frequency)
                if not decoded:
                    continue

                call = extract_dx_call(decoded["message"])
                if not call:
                    continue

                country = get_country(call, self.prefixes)
                if not country or country in self.confirmed:
                    continue

                key = f"{self.current_band}:{call}:{country}"
                if key in self.alerted:
                    continue

                self.alerted.add(key)
                self.log.emit(f"NEW DXCC [{self.current_band}]: {country} ({call}) - {decoded.get('frequency_mhz', 0):.3f} MHz")
                # Emit signal with basic details and the whole decoded dict (useful for UI)
                self.new_dxcc.emit(country, call, decoded.get("mode", ""), int(decoded.get("snr", 0)), decoded)

                # Optionally trigger native notification
                try:
                    notify_new_dxcc(country, call, decoded.get("mode", ""), decoded.get("snr", 0))
                except (KeyError, ValueError, TypeError) as error:
                    # Log the error if needed
                    print(f"Failed to notify new DXCC: {error}")

        except Exception as error:
            self.log.emit(f"Worker error: {error}")
        finally:
            try:
                sock.close()
            except (KeyError, ValueError, TypeError) as error:
                print(f"Failed to close socket: {error}")
                self.log.emit(f"Failed to close socket: {error}")

            self.finished_clean.emit()

    def stop(self):
        self._running = False
        # closing the socket will unblock recvfrom; create a dummy socket to self to unblock if needed
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.sendto(b"", (UDP_IP, UDP_PORT))
            s.close()
        except (KeyError, ValueError, TypeError) as error:
            print(f"Failed to close socket: {error}")
            self.log.emit(f"Failed to close socket: {error}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DXCC Watcher - GUI")
        self.prefixes = load_cty(CTY_FILE)
        self.current_mode = None
        self.worker = None

        self.icon_path = "assets/images/logo_dxwatcher.png"
        try:
            self.setWindowIcon(QIcon(self.icon_path))
        except (KeyError, ValueError, TypeError) as error:
            print(f"Failed to set window icon: {error}")

        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        v = QVBoxLayout(central)

        h = QHBoxLayout()
        icon_label = QLabel()
        try:
            pix = QPixmap(self.icon_path)
            if not pix.isNull():
                icon_label.setPixmap(pix.scaled(128, 128, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        except (KeyError, ValueError, TypeError) as error:
            print(f"Failed to set icon pixmap: {error}")

        h.addWidget(icon_label)
        self.start_btn = QPushButton("Start")
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.band_label = QLabel("Band: -")
        self.freq_label = QLabel("Freq: -")
        self.mode_label = QLabel("Mode: -")

        h.addWidget(self.start_btn)
        h.addWidget(self.stop_btn)
        h.addStretch()
        h.addWidget(self.band_label)
        h.addWidget(self.freq_label)
        h.addWidget(self.mode_label)
        v.addLayout(h)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Time", "Band", "Country", "Call", "Mode", "SNR"])
        v.addWidget(self.table)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        v.addWidget(self.log)

        self.start_btn.clicked.connect(self.start_worker)
        self.stop_btn.clicked.connect(self.stop_worker)

    @Slot()
    def start_worker(self):
        if self.worker and self.worker.isRunning():
            return
        self.worker = UdpWorker(self.prefixes)
        self.worker.status_update.connect(self.on_status)
        self.worker.new_dxcc.connect(self.on_new_dxcc)
        self.worker.log.connect(self.append_log)
        self.worker.finished_clean.connect(self.on_worker_finished)
        self.worker.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.append_log("Worker started")

    @Slot()
    def stop_worker(self):
        if not self.worker:
            return
        self.append_log("Stopping worker...")
        self.worker.stop()
        self.stop_btn.setEnabled(False)

    @Slot(object)
    def on_status(self, status):
        freq = status.get("frequency") or 0
        band = status.get("band") or "-"
        mode = status.get("mode") or "-"
        self.band_label.setText(f"Band: {band}")
        self.mode_label.setText(f"Mode: {mode}")
        self.current_mode = mode
        try:
            self.freq_label.setText(f"Freq: {freq/1e6:.3f} MHz")
        except (KeyError, ValueError, TypeError) as error:
            print(f"Failed to set frequency label: {error}")
            self.freq_label.setText("Freq: -")

    @Slot(str, str, str, str,  int, object)
    def on_new_dxcc(self, country, call, mode, snr, decoded):
        import datetime
        row = self.table.rowCount()
        self.table.insertRow(row)
        mode = self.current_mode or "-"
        time_item = QTableWidgetItem(datetime.datetime.now().strftime("%H:%M:%S"))
        band_item = QTableWidgetItem(decoded.get("band") or "-")
        country_item = QTableWidgetItem(country)
        call_item = QTableWidgetItem(call)
        snr_item = QTableWidgetItem(str(snr))
        mode_item = QTableWidgetItem(str(mode))
        self.table.setItem(row, 0, time_item)
        self.table.setItem(row, 1, band_item)
        self.table.setItem(row, 2, country_item)
        self.table.setItem(row, 3, call_item)
        self.table.setItem(row, 4, mode_item)
        self.table.setItem(row, 5, snr_item)

    @Slot(str)
    def append_log(self, text):
        self.log.appendPlainText(text)

    @Slot()
    def on_worker_finished(self):
        self.append_log("Worker finished")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.worker = None

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.append_log("Stopping worker before exit...")
            self.worker.stop()
            self.worker.wait(2000)
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    try:
        app.setWindowIcon(QIcon("assets/images/logo_dxwatcher.png"))
    except (KeyError, ValueError, TypeError) as e:
        print(f"Failed to set app icon: {e}")
    w = MainWindow()
    w.resize(800, 600)
    w.show()
    sys.exit(app.exec())
