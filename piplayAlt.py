    #install python3-pyqt6.qtquick qt6-declarative-dev qml6-module-qtquick qml6-module-qtquick-controls qml6-module-qtquick-layouts
    # qml6-module-qtquick-window qml6-module-qtqml-workerscript qml6-module-qtmultimedia qml6-module-qtquick-templates
import sys
import cv2
import logging
import yaml
import time
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtGui import QGuiApplication, QImage
from PyQt6.QtCore import QSize, QTimer, pyqtSignal, QObject, QUrl, QThreadPool, QThread
from PyQt6.QtQuick import QQuickImageProvider
import signal
import cProfile

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
    ROTATION_ANGLE = config['settings']['rotation_angle']
    GRID_ROWS = config['settings']['grid_rows']
    GRID_COLS = config['settings']['grid_cols']

    # Read streams from the config file
    streams = config['streams']
    max_views = GRID_COLS * GRID_ROWS
    views = min(len(streams), max_views)
except KeyError as e:
    logging.warning(f"Missing key in config.yaml: {e}")
    sys.exit(1)
    
class OpencvImageProvider(QQuickImageProvider):
    imageChanged = pyqtSignal(int)  # Signal to notify QML about image updates
    ready = pyqtSignal()
    def __init__(self, index):
        super().__init__(QQuickImageProvider.ImageType.Image)
        self.image = QImage(200, 200, QImage.Format.Format_RGB32)  # Initialize with a default image
        self.index = index
        #self.ready = False
        logging.debug(f"Provider {index} initialized.")
        
    def requestImage(self, id, size: QSize, requestedSize: QSize = QSize()):
        #if not self.ready:
        #    return QImage(200, 200, QImage.Format.Format_RGB32), QSize(200, 200)
        logging.debug(f"requestImage with {id} by {self.index}")
        return self.image, self.image.size()

    def updateImage(self, qImg):
        logging.debug(f"updateImage called for {self.index}")
        self.image = qImg
        self.imageChanged.emit(self.index)

class ReconnectWorker(QThread):
    reconnected = pyqtSignal()

    def __init__(self, parent, video_path):
        super().__init__(parent)
        self.video_path = video_path
        self.running = True
        logging.debug("ReconnectWorker initialized.")

    def run(self):
        retry_interval = 5  # Initial retry interval

        while self.running: 
            time.sleep(retry_interval)
            try:
                cap = cv2.VideoCapture(self.video_path, cv2.CAP_FFMPEG)
                if cap.isOpened():
                    logging.info(f"Reconnected to stream: {self.video_path}")
                    self.parent().cap = cap
                    self.reconnected.emit()
                    break  # Exit the loop after successful reconnection
                else:
                    logging.warning(f"Reconnect failed to stream: {self.video_path}")
            except Exception as e:
                logging.error(f"Error during reconnect: {e}")

            retry_interval *= 2
            retry_interval = min(retry_interval, 60) # Cap in case it's out too long.

    def stop(self):
        self.running = False

class VideoProcessor(QThread):
    imageReady = pyqtSignal(QImage, int)

    def __init__(self, video_path, index, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.index = index
        self.running = True

    def run(self):
        try:
            self.cap = cv2.VideoCapture(self.video_path, cv2.CAP_FFMPEG)
            if not self.cap.isOpened():
                logging.error(f"Failed to open video stream: {self.video_path}")
                return

            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 10)
            self.cap.set(cv2.CAP_PROP_HW_ACCELERATION, cv2.CAP_FFMPEG)

            while self.running:
                ret, frame = self.cap.read()
                if ret:
                    if ROTATION_ANGLE != 0:
                        rows, cols = frame.shape[:2]
                        rotation_matrix = cv2.getRotationMatrix2D((cols / 2, rows / 2), ROTATION_ANGLE, 1)
                        frame = cv2.warpAffine(frame, rotation_matrix, (frame.shape[1], frame.shape[0]))

                    height, width, channel = frame.shape
                    bytesPerLine = 3 * width
                    qImg = QImage(frame.data, width, height, bytesPerLine, QImage.Format.Format_BGR888)
                    self.imageReady.emit(qImg, self.index)  # Emit the image
                else:
                    logging.warning("Failed to grab frame.")
                    break

        except Exception as e:
            logging.error(f"{e}")

    def stop(self):
        self.running = False
        if hasattr(self, 'cap'):
            self.cap.release()

class VideoStreamerWorker(QObject):
    finished = pyqtSignal()

    def __init__(self, video_path, index, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.index = index
        self.running = True
        self.rotation_matrix = None
        self.reconnect_worker = None
        self.image_provider = OpencvImageProvider(index)
        self.video_processor = VideoProcessor(video_path, index, self)
        self.video_processor.imageReady.connect(self.updateImage)
        logging.debug(f"VideoStreamerWorker {self.index} initialized.")

    def initialize_rotation_matrix(self, frame):
        """Initialize the rotation matrix using the first frame's dimensions."""
        if ROTATION_ANGLE != 0:
            rows, cols = frame.shape[:2]
            self.rotation_matrix = cv2.getRotationMatrix2D((cols / 2, rows / 2), ROTATION_ANGLE, 1)
            logging.info(f"Rotation matrix initialized for stream {self.video_path}")
        else:
            logging.warning(f"Failed to retrieve initial frame for rotation matrix from: {self.video_path}")
        
    def updateImage(self, qImg, index):
        self.image_provider.updateImage(qImg)
                
    def start_reconnect_thread(self):
        if self.reconnect_worker is None or not self.reconnect_worker.isRunning():
            self.reconnect_worker = ReconnectWorker(self, self.video_path)
            self.reconnect_worker.reconnected.connect(self.on_reconnect_success)
            self.reconnect_worker.start()

    def on_reconnect_success(self):
        logging.info(f"Reconnect worker successfully reconnected to {self.video_path}")

    def stop(self):
        self.running = False
        if self.reconnect_worker is not None:
            self.reconnect_worker.stop()
            self.reconnect_worker.wait()
        
        
if __name__ == '__main__':
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    pr = cProfile.Profile()
    pr.enable()

    context = engine.rootContext()

    video_workers = []
    image_providers = []
    for i in range(views):
        worker = VideoStreamerWorker(streams[i], i, app)
        video_workers.append(worker)
        image_providers.append(worker.image_provider)
        engine.addImageProvider(f"live_{i}", worker.image_provider)
        logging.info(f"view {i} configured in main")
    context.setContextProperty("videoWorkers", video_workers)
    context.setContextProperty("liveImageProviders", image_providers)
    context.setContextProperty("numberOfStreams", views)
    context.setContextProperty("gridRows", GRID_ROWS)
    context.setContextProperty("gridCols", GRID_COLS)

    engine.load(QUrl.fromLocalFile("main.qml"))

    def check_ready():
        if engine.rootObjects():
            logging.info("QML components are ready.")
            for i, worker in enumerate(video_workers):
                QTimer.singleShot(i * 500, worker.video_processor.start)
        else:
            logging.info("QML components not ready yet. Retrying...")
            QTimer.singleShot(100, check_ready)
            
    def signal_handler(sig, frame):
        logging.debug(f"Caught signal {sig}")
        for worker in video_workers:
            worker.stop()
        QThreadPool.globalInstance().waitForDone(5000)
        pr.disable()
        pr.dump_stats('profileOutput.txt')
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    QTimer.singleShot(100, check_ready)

    if not engine.rootObjects():
        sys.exit(-1)

    sys.exit(app.exec())
    pr.disable()
    pr.dump_stats('profileOutput.txt')
