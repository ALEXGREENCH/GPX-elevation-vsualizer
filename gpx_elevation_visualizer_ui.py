import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout, 
                             QWidget, QFileDialog, QPushButton, QMessageBox, 
                             QProgressBar, QFrame)
from PyQt5.QtCore import Qt, QMimeData
from PyQt5.QtGui import QDragEnterEvent, QDropEvent
import threading
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import gpx_elevation_visualizer

class DragDropWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.setAcceptDrops(True)
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        self.label = QLabel("Drag and drop your GPX or KML file here")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                padding: 20px;
                border: 2px dashed #ccc;
                border-radius: 10px;
                background-color: #f5f5f5;
            }
        """)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        layout.addWidget(self.label)
        layout.addWidget(self.progress_bar)
        
        self.setLayout(layout)
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            urls = mime_data.urls()
            if urls:
                file_path = urls[0].toLocalFile()
                if file_path.lower().endswith(('.gpx', '.kml')):
                    event.acceptProposedAction()
                    return
        event.ignore()
        
    def dropEvent(self, event: QDropEvent):
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            urls = mime_data.urls()
            if urls:
                file_path = urls[0].toLocalFile()
                if file_path.lower().endswith(('.gpx', '.kml')):
                    self.process_file(file_path)
                    
    def process_file(self, file_path):
        thread = threading.Thread(target=self.process_file_thread, args=(file_path,))
        thread.daemon = True
        thread.start()
        
    def process_file_thread(self, file_path):
        try:
            self.label.setText("Processing file...")
            self.progress_bar.setVisible(True)
            
            coords = gpx_elevation_visualizer.read_points(file_path)
            pts = gpx_elevation_visualizer.load_elevations(coords)
            out = file_path.replace(".kml","_elev.kml").replace(".gpx","_elev.kml")
            
            self.progress_bar.setRange(0, len(pts))
            for i in range(len(pts)):
                time.sleep(0.01)
                self.progress_bar.setValue(i + 1)
                
            gpx_elevation_visualizer.write_kml(pts, out)
            
            self.label.setText(f"File processed successfully!\nResult:{os.path.basename(out)}")
            self.progress_bar.setVisible(False)
            
        except Exception as e:
            self.label.setText("Error processing file")
            self.progress_bar.setVisible(False)
            QMessageBox.critical(self, "Error", f"An error occurred:\n{str(e)}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GPX/KML Elevation Visualizer")
        self.setGeometry(300, 300, 500, 300)
        
        central_widget = DragDropWidget()
        self.setCentralWidget(central_widget)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())