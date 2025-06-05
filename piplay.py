import os
import sys
import cv2
import threading
import time
import logging
import yaml
from queue import Queue, Full, Empty
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QGridLayout, QLabel
from PyQt6.QtGui import QPixmap, QImage, QTransform
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QMetaObject

# Configure logging
logging.basicConfig(filename='/var/log/piplay.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load configuration
try:
    with open('config.yaml', 'r') as file:
        config = yaml.safe_load(file)
except FileNotFoundError:
    logging.warning(f"Error: 'config.yaml' not found.")
    sys.exit(1)
except yaml.YAMLError as e:
    logging.warning(f"Error parsing 'config.yaml': {e}")
    sys.exit(1)

# Read settings from the config file
try:
    FPS = config['settings']['fps']
    ROTATION_ANGLE = config['settings']['rotation_angle']
    GRID_ROWS = config['settings']['grid_rows']
    GRID_COLS = config['settings']['grid_cols']

    # Read streams from the config file
    streams = config['streams']
except KeyError as e:
    logging.warning(f"Missing key in config.yaml: {e}")
    sys.exit(1)

class VideoPanel(QWidget):
    frame_update_signal = pyqtSignal(QImage)
    reconnect_signal = pyqtSignal()

    def __init__(self, stream_url, parent=None):
        super().__init__(parent)
        self.stream_url = stream_url
        self.static_label = QLabel(self)
        self.reconnecting_label = QLabel("Reconnecting...", self)
        self.reconnecting_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.reconnecting_label.hide()

        layout = QVBoxLayout(self)
        layout.addWidget(self.static_label, 1)
        layout.addWidget(self.reconnecting_label, 1)
        layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout)

        self.cap = None
        self.is_playing = False
        self.frame_update_signal.connect(self.update_frame)
        self.reconnect_signal.connect(self.connect)

        self.frame_queue = Queue(maxsize=20)  # Increase buffer size to handle higher frame rate
        self.thread = threading.Thread(target=self.update_panel)
        self.thread.daemon = True
        self.thread.start()

        self.timer = QTimer()
        self.timer.timeout.connect(self.display_frame)
        self.timer.start(1000 // FPS)

    @pyqtSlot()
    def connect(self):
        if self.cap:
            self.cap.release()

        backends = [cv2.CAP_FFMPEG, cv2.CAP_GSTREAMER, cv2.CAP_ANY]
        for backend in backends:
            if backend == cv2.CAP_FFMPEG:
                # Use FFMPEG as a fallback for VLC functionality
                self.cap = cv2.VideoCapture(self.stream_url, cv2.CAP_FFMPEG)
            else:
                # Default OpenCV backend or GStreamer
                self.cap = cv2.VideoCapture(self.stream_url, backend)
            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer size
                break  # Exit loop if we successfully opened the stream

        if not self.cap.isOpened():
            logging.warning(f"Failed to connect to {self.stream_url} using any backend.")
            self.reconnecting_label.show()
            self.schedule_reconnect()
        else:
            self.reconnecting_label.hide()
            self.is_playing = True
            if backend == 1900:
                backendN = "FFMpeg"
            elif backend == 1800:
                backendN = "GStreamer"
            elif backend == 0:
                backendN = "CV Any"
            else:
                backendN = "Undocumented"
            logging.info(f"Connected to {self.stream_url} using backend {backendN}.")
    
    def schedule_reconnect(self):

        logging.info(f"Scheduling reconnection for {self.stream_url}")

        QMetaObject.invokeMethod(self, "emit_reconnect_signal", Qt.ConnectionType.QueuedConnection)



    @pyqtSlot()

    def emit_reconnect_signal(self):

        QTimer.singleShot(10000, self.reconnect_signal.emit)

    def update_panel(self):
        self.connect()
        while True:
            if self.is_playing and self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = frame.shape
                    qimg = QImage(frame.data, w, h, ch * w, QImage.Format.Format_RGB888).copy()
                    try:
                        self.frame_queue.put_nowait(qimg)
                    except Full:
                        # Drop the oldest frame in the queue to make room for the new one
                        self.frame_queue.get()
                        self.frame_queue.put_nowait(qimg)
                else:
                    self.is_playing = False
                    self.reconnecting_label.show()
                    logging.warning(f"Lost connection to {self.stream_url}. Reconnecting...")
                    self.schedule_reconnect()
            else:
                time.sleep(1)

    def display_frame(self):
        try:
            qimg = self.frame_queue.get_nowait()
            rotated_qimg = self.rotate_image(qimg)
            self.frame_update_signal.emit(rotated_qimg)
        except Empty:
            pass  # No frame to display

    def rotate_image(self, qimg):
        pixmap = QPixmap.fromImage(qimg)
        transform = QTransform()
        if ROTATION_ANGLE == 90:
            transform.rotate(90)
        elif ROTATION_ANGLE == 180:
            transform.rotate(180)
        elif ROTATION_ANGLE == 270:
            transform.rotate(270)
        # Default is 0
        rotated_pixmap = pixmap.transformed(transform, Qt.TransformationMode.SmoothTransformation)
        return rotated_pixmap.toImage()

    def stop(self):
        self.is_playing = False
        if self.cap:
            self.cap.release()

    def update_frame(self, qimg):
        pixmap = QPixmap.fromImage(qimg.scaled(self.static_label.size(), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.static_label.setPixmap(pixmap)
        self.static_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

class RtspPlayerFrame(QWidget):
    def __init__(self):
        super().__init__()
        self.panels = []
        self.initUI()

    def initUI(self):
        self.setStyleSheet("background-color: black;")
        grid_layout = QGridLayout(self)

        # Get screen dimensions
        screen_resolution = QApplication.primaryScreen().availableSize()
        screen_width, screen_height = screen_resolution.width(), screen_resolution.height()
        panel_width = int(screen_width / GRID_COLS)
        panel_height = int(screen_height / GRID_ROWS)
        
        for i, stream_url in enumerate(streams):
            row = i // GRID_COLS
            col = i % GRID_COLS
            video_panel = VideoPanel(stream_url, self)
            video_panel.setFixedSize(panel_width, panel_height)
            video_panel.setStyleSheet("background-color: black;")
            grid_layout.addWidget(video_panel, row, col)
            self.panels.append(video_panel)

        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(0)

        self.setLayout(grid_layout)
        self.setWindowTitle('RTSP Player')
        self.showFullScreen()

    def closeEvent(self, event):
        for panel in self.panels:
            panel.stop()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    frame = RtspPlayerFrame()
    sys.exit(app.exec())
