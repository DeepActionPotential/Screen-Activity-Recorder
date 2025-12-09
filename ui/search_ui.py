from typing import List, Optional, Tuple, Callable
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QFont

from schemas.activity_schemas import Activity
from services.index_manager import FaissIndexManager
from ui.utils import pil_to_qpixmap


class SearchResultWidget(QWidget):
    """Widget representing a single search result item."""
    
    def __init__(self, 
                 activity: Activity, 
                 on_click: Callable[[Activity], None],
                 parent: Optional[QWidget] = None):
        """
        Initialize the search result widget.
        
        Args:
            activity: The activity to display
            on_click: Callback when the result is clicked
            parent: Parent widget
        """
        super().__init__(parent)
        self.activity = activity
        self.on_click = on_click
        self._setup_ui()
        
    def _setup_ui(self) -> None:
        """Initialize the UI components."""
        self.setStyleSheet("background-color: #141414; border: 1px solid #2A2A2A;")
        self.setCursor(Qt.PointingHandCursor)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)
        
        self.thumb_label = self._create_thumbnail()
        self.text_label = self._create_text_label()
        
        layout.addWidget(self.thumb_label)
        layout.addWidget(self.text_label, 1)
        
    def _create_thumbnail(self) -> QLabel:
        """Create and return the thumbnail label."""
        thumb = QLabel()
        thumb.setFixedSize(36, 36)
        thumb.setStyleSheet("background-color: #2A2A2A; border: 1px solid #3A3A3A;")
        
        if hasattr(self.activity, 'modified_screenshot_pil_image'):
            pix = pil_to_qpixmap(self.activity.modified_screenshot_pil_image)
            if not pix.isNull():
                thumb.setPixmap(
                    pix.scaled(36, 36, Qt.KeepAspectRatioByExpanding, 
                             Qt.SmoothTransformation)
                )
        return thumb
        
    def _create_text_label(self) -> QLabel:
        """Create and return the text label."""
        label = QLabel()
        label.setWordWrap(True)
        label.setStyleSheet("color: #EDEDED; border: 0px")
        label.setText("")
        return label
        
    def _get_activity_text(self) -> str:
        """Get the formatted text for the activity."""
        if hasattr(self.activity, 'app_name'):
            return (f"{self.activity.app_name}\n"
                   f"{self.activity.window_title}\n"
                   f"{self.activity.app_activity_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            return (f"{self.activity.screenshot_id}\n"
                   f"{self.activity.screenshot_timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
                   f"{getattr(self.activity, 'screenshot_ocr_text', '')}")
        
    def mousePressEvent(self, event) -> None:
        """Handle mouse press events on the result item."""
        self.on_click(self.activity)
        super().mousePressEvent(event)


class SearchPanel(QWidget):
    """Panel for searching and displaying activity results."""
    
    def __init__(self, 
                 main_window: QWidget, 
                 index_manager: FaissIndexManager,
                 parent: Optional[QWidget] = None):
        """
        Initialize the search panel.
        
        Args:
            main_window: Reference to the main window
            index_manager: FAISS index manager for search operations
            parent: Parent widget
        """
        super().__init__(parent)
        self.main_window = main_window
        self.index_manager = index_manager
        self._setup_ui()
        
    def _setup_ui(self) -> None:
        """Initialize the UI components."""
        self.setStyleSheet("background-color: #1A1A1A; color: #EDEDED;")
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        self._setup_search_controls(layout)
        self._setup_results_area(layout)
        
    def _setup_search_controls(self, parent_layout: QVBoxLayout) -> None:
        """Set up the search input and buttons."""
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(8)
        
        self.query_edit = QLineEdit()
        self.query_edit.setPlaceholderText("Search activities...")
        self.query_edit.setStyleSheet(
            "background-color: #262626; color: #EDEDED; padding:4px;"
        )
        
        self.search_btn = QPushButton("Search")
        self.search_btn.setFixedWidth(70)
        self.search_btn.clicked.connect(self.on_search_clicked)
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setFixedWidth(60)
        self.clear_btn.clicked.connect(self.on_clear_clicked)
        
        search_layout.addWidget(self.query_edit)
        search_layout.addWidget(self.search_btn)
        search_layout.addWidget(self.clear_btn)
        
        parent_layout.addLayout(search_layout)
        
    def _setup_results_area(self, parent_layout: QVBoxLayout) -> None:
        """Set up the scrollable results area."""
        self.results_area = QScrollArea()
        self.results_area.setWidgetResizable(True)
        self.results_area.setStyleSheet("""
            QScrollArea { background-color: transparent; border: none; }
            QScrollArea > QWidget > QWidget { background-color: transparent; }
        """)
        self.results_area.setMinimumHeight(540)
        
        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_layout.setSpacing(6)
        self.results_layout.addStretch()  # Keeps items at the top
        
        self.results_area.setWidget(self.results_container)
        parent_layout.addWidget(self.results_area)
        
    def on_search_clicked(self) -> None:
        """Handle search button click."""
        query = self.query_edit.text().strip()
        if not query:
            return
            
        try:
            results = self.index_manager.search_by_text(query).to_list()
            self.populate_results(results)
        except Exception as e:
            print(f"Search error: {str(e)}")
            
    def on_clear_clicked(self) -> None:
        """Handle clear button click."""
        self.clear_results()
        self.query_edit.clear()
        
    def clear_results(self) -> None:
        """Clear all search results."""
        while self.results_layout.count() > 1:  # Keep the stretch
            item = self.results_layout.takeAt(0)
            if widget := item.widget():
                widget.deleteLater()
                
    def populate_results(self, activities: List[Activity]) -> None:
        """
        Populate the results area with activity items.
        
        Args:
            activities: List of activities to display
        """
        self.clear_results()
        
        for activity in activities:
            result_widget = SearchResultWidget(
                activity=activity,
                on_click=self._on_result_clicked,
                parent=self
            )
            self.results_layout.insertWidget(0, result_widget)
            
    def _on_result_clicked(self, activity: Activity) -> None:
        """Handle click on a search result.
        
        Args:
            activity: The clicked activity
        """
        try:
            self.main_window.on_select_activity(activity)
        except Exception as e:
            print(f"Error selecting activity: {str(e)}")