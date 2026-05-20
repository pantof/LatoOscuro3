from PySide6.QtWidgets import (
    QMainWindow, QMessageBox, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget
)
from PySide6.QtSql import QSqlDatabase

from widget.porta_widget import PortaDetailWidget
from widget.location_manager import LocationManagerWidget


class MainWindow(QMainWindow):
    def __init__(self, db: QSqlDatabase):
        super().__init__()
        self.setWindowTitle("Gestione Inventario Impianti")
        self.setGeometry(100, 100, 1200, 700)
        self.db = db
        if not db or not db.isOpen():
            QMessageBox.critical(self, "Errore", "Connessione DB non valida.")
            return
        self._setup_ui()

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # Pannello sinistro — albero navigazione
        nav_panel = QWidget()
        nav_layout = QVBoxLayout(nav_panel)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_panel.setMaximumWidth(300)

        self.asset_tree = LocationManagerWidget(self.db)
        nav_layout.addWidget(self.asset_tree)

        # Pannello destro — stack di pagine
        self.main_stack = QStackedWidget()
        self.placeholder_page = QWidget()
        self.detail_widget = PortaDetailWidget(self.db)

        self.main_stack.addWidget(self.placeholder_page)  # indice 0
        self.main_stack.addWidget(self.detail_widget)     # indice 1

        main_layout.addWidget(nav_panel)
        main_layout.addWidget(self.main_stack, stretch=1)

        self.asset_tree.item_selected.connect(self._on_asset_selected)
        self.main_stack.setCurrentIndex(0)

    def _on_asset_selected(self, item_type: str, item_id: int):
        if item_type == "porta":
            self.main_stack.setCurrentWidget(self.detail_widget)
            self.detail_widget.load_porta_data(item_id)
        else:
            self.main_stack.setCurrentIndex(0)
            self.detail_widget.clear_form()
