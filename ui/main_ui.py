import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QFrame, QStackedWidget)
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint
from PyQt5.QtGui import QFont, QColor, QPalette
import os
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QLabel

# Import your existing UI components
from .recording_ui import SimpleRecorderWindow
from .history_ui import DualStreamlineWindow


class CollapsibleMenu(QFrame):
    def __init__(self, parent=None, activity_manager=None, recording_ui=None):
        super().__init__(parent)
        self.recording_ui = recording_ui
        self.activity_manager = activity_manager
        self.current_session = None
        self.setFixedWidth(200)
        self.setStyleSheet("""
            QFrame {
                background-color: #2b2b2b;
                border-right: 1px solid #3e3e3e;
            }
            QPushButton {
                background-color: #3a3a3a;
                color: white;
                border: none;
                padding: 10px;
                text-align: left;
                font-size: 14px;
                margin: 5px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QLabel {
                color: #ffffff;
                padding: 10px;
                margin: 5px;
                border-bottom: 1px solid #3e3e3e;
                word-wrap: break-word;
            }
        """)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 10, 5, 10)
        layout.setSpacing(10)

        # Session Info Label
        self.session_label = QLabel("No active session")
        layout.addWidget(self.session_label)

        # Menu Buttons
        self.load_btn = QPushButton("📂 Load Session")
        self.create_btn = QPushButton("🆕 Create New Session")
        self.history_btn = QPushButton("📜 History")
        self.recording_btn = QPushButton("⏺ Recording")
        self.app_exit_button = QPushButton("❌ Exit")
        
        # Connect buttons
        self.load_btn.clicked.connect(self.on_load_session)
        self.create_btn.clicked.connect(self.on_create_session)
        
        # Add widgets to layout
        layout.addWidget(self.load_btn)
        layout.addWidget(self.create_btn)
        layout.addWidget(self.history_btn)
        layout.addWidget(self.recording_btn)
        layout.addWidget(self.app_exit_button)
        layout.addStretch()

    def on_load_session(self):
        """Handle loading a session file"""
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Session",
            "",
            "Joblib Files (*.joblib);;All Files (*)",
            options=QFileDialog.Options()
        )
        
        if file_path:
            try:
                if self.recording_ui.is_recording:
                    self.recording_ui.toggle_recording(continue_timer=False, force_restart=True)

                self.activity_manager.load_session(file_path)
                self.current_session = file_path
                self.update_session_label(os.path.basename(file_path))
                print(f"Session loaded: {file_path}")
                
                
                self.recording_ui.toggle_recording(continue_timer=False, force_restart=True)

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load session: {str(e)}")

    def on_create_session(self):
        """Handle creating a new session"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Create New Session",
            "",
            "Joblib Files (*.joblib);;All Files (*)",
            options=QFileDialog.Options()
        )
        
        if file_path:
            try:
                if self.recording_ui.is_recording:
                    self.recording_ui.toggle_recording(continue_timer=False, force_restart=True)
                

                if not file_path.endswith('.joblib'):
                    file_path += '.joblib'
                
  
                self.activity_manager.create_session(file_path)
                self.current_session = file_path
                self.update_session_label(os.path.basename(file_path))
                print(f"Session created: {file_path}")

                
                self.recording_ui.toggle_recording(continue_timer=False, force_restart=True)

            except Exception as e:
                import traceback
                traceback.print_exc()
                QMessageBox.critical(self, "Error", f"Failed to create session: {str(e)}")

    def update_session_label(self, session_name):
        """Update the session label with the current session name"""
        self.session_label.setText(f"Session:\n{session_name}")

    @property
    def is_current_session(self):
        """Check if there is an active session"""
        return self.current_session is not None and os.path.exists(self.current_session)


from core.activity_manager import ActivityManager

class MainWindow(QMainWindow):
    def __init__(self, activity_manager:ActivityManager, faiss_index_manager):
        super().__init__()
        self.activity_manager = activity_manager
        self.faiss_index_manager = faiss_index_manager
        self.setWindowTitle("Activity Recorder")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setGeometry(int((1920-1300)/2), 20, 1300, 600)  # 1280 + 20 for menu
        self.init_ui()
        print(self.geometry())

    def init_ui(self):
        # Main widget and layout

        # Create and add pages
        self.recording_page = SimpleRecorderWindow(self.activity_manager)
        self.history_page = DualStreamlineWindow(self.activity_manager.get_session_activities(), self.faiss_index_manager)   # Pass empty data for now


        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create menu and content area
        self.menu = CollapsibleMenu(activity_manager=self.activity_manager, recording_ui=self.recording_page)
        self.content_area = QFrame()
        self.content_area.setStyleSheet("background-color: #0F0F0F;")

        

        # Menu toggle button
        self.toggle_btn = QPushButton("☰", self)
        self.toggle_btn.setFixedSize(30, 30)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #0F0F0F;
                color: white;
                border: none;
                border-radius: 3px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
        """)
        self.toggle_btn.clicked.connect(self.toggle_menu)

        # Stacked widget for pages
        self.stacked_widget = QStackedWidget()
        
        
        self.stacked_widget.addWidget(self.recording_page)
        self.stacked_widget.addWidget(self.history_page)

        # Content layout
        content_layout = QVBoxLayout(self.content_area)
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.addWidget(self.toggle_btn)
        content_layout.addWidget(self.stacked_widget)

        # Add widgets to main layout
        main_layout.addWidget(self.menu)
        main_layout.addWidget(self.content_area)

        # Connect menu buttons
        self.menu.history_btn.clicked.connect(self.show_history_page)
        self.menu.recording_btn.clicked.connect(self.show_recording_page)
        self.menu.app_exit_button.clicked.connect(self.close)

        # Menu animation
        self.animation = QPropertyAnimation(self.menu, b"pos")
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        
        # Initially hide menu
        self.menu.hide()
        self.is_menu_visible = False

    
        self.animation.finished.connect(self.on_animation_finished)

    def on_animation_finished(self):
        if not self.is_menu_visible:
            self.menu.hide()
    
    def show_history_page(self):
        "Shows histroy page"
        self.stacked_widget.setCurrentIndex(1)
        self.history_page.update_history_ui(self.activity_manager.get_session_activities())
    

    def show_recording_page(self):
        "Shows recording page"
        self.stacked_widget.setCurrentIndex(0)

    def toggle_menu(self):

        if self.is_menu_visible:
            self.hide_menu()
            self.is_menu_visible = False

        else:
            self.show_menu()
            self.is_menu_visible = True


    def hide_menu(self):
        self.animation.setStartValue(QPoint(0, 0))
        self.animation.setEndValue(QPoint(-self.menu.width(), 0))
        self.animation.start()

    def show_menu(self):
        self.menu.show()
        self.animation.setStartValue(QPoint(-self.menu.width(), 0))
        self.animation.setEndValue(QPoint(0, 0))
        self.animation.start()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())