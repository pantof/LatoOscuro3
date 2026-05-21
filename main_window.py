from PySide6.QtWidgets import (
    QMainWindow, QMessageBox, QWidget, QHBoxLayout, QVBoxLayout,
    QStackedWidget, QToolBar, QLabel
)
from PySide6.QtSql import QSqlDatabase
from PySide6.QtCore import Qt

from widget.porta_widget          import PortaDetailWidget
from widget.locale_detail_widget  import LocaleDetailWidget
from widget.piano_detail_widget   import PianoDetailWidget
from widget.edificio_detail_widget import EdificioDetailWidget
from widget.garanzie_widget       import GaranzieWidget
from widget.location_manager      import LocationManagerWidget


class MainWindow(QMainWindow):
    def __init__(self, db: QSqlDatabase):
        super().__init__()
        self.setWindowTitle("Gestione Inventario Impianti")
        self.setGeometry(100, 100, 1280, 750)
        self.db = db
        if not db or not db.isOpen():
            QMessageBox.critical(self, "Errore", "Connessione DB non valida.")
            return
        self._setup_ui()

    def _setup_ui(self):
        # --- Toolbar principale ---
        toolbar = QToolBar("Principale")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self.act_garanzie = toolbar.addAction("Scadenzario Garanzie")
        self.act_garanzie.setCheckable(True)
        self.act_garanzie.triggered.connect(self._toggle_garanzie)

        # --- Layout centrale ---
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

        # indice 0 — placeholder
        placeholder = QWidget()
        ph_layout = QVBoxLayout(placeholder)
        ph_label = QLabel("Seleziona un elemento dall'albero\no usa il tasto destro per aggiungere.")
        ph_label.setAlignment(Qt.AlignCenter)
        ph_label.setStyleSheet("color: #888; font-size: 13px;")
        ph_layout.addWidget(ph_label)
        self.main_stack.addWidget(placeholder)               # 0

        # indice 1 — dettaglio porta
        self.porta_widget = PortaDetailWidget(self.db)
        self.main_stack.addWidget(self.porta_widget)         # 1

        # indice 2 — dettaglio locale
        self.locale_widget = LocaleDetailWidget(self.db)
        self.main_stack.addWidget(self.locale_widget)        # 2

        # indice 3 — dettaglio piano
        self.piano_widget = PianoDetailWidget(self.db)
        self.main_stack.addWidget(self.piano_widget)         # 3

        # indice 4 — dettaglio edificio
        self.edificio_widget = EdificioDetailWidget(self.db)
        self.main_stack.addWidget(self.edificio_widget)      # 4

        # indice 5 — scadenzario garanzie
        self.garanzie_widget = GaranzieWidget(self.db)
        self.main_stack.addWidget(self.garanzie_widget)      # 5

        main_layout.addWidget(nav_panel)
        main_layout.addWidget(self.main_stack, stretch=1)

        # Connessioni albero
        self.asset_tree.item_selected.connect(self._on_asset_selected)
        self.asset_tree.tree_changed.connect(self._on_tree_changed)

        # Connessioni content_changed dai widget di dettaglio → aggiorna albero
        self.locale_widget.content_changed.connect(self.asset_tree.load_location_tree)
        self.piano_widget.content_changed.connect(self.asset_tree.load_location_tree)
        self.edificio_widget.content_changed.connect(self.asset_tree.load_location_tree)

        self.main_stack.setCurrentIndex(0)

    # ------------------------------------------------------------------
    # Navigazione
    # ------------------------------------------------------------------

    def _on_asset_selected(self, item_type: str, item_id: int):
        self.act_garanzie.setChecked(False)
        if item_type == "porta":
            self.main_stack.setCurrentWidget(self.porta_widget)
            self.porta_widget.load_porta_data(item_id)
        elif item_type == "locale":
            self.main_stack.setCurrentWidget(self.locale_widget)
            self.locale_widget.load_locale_data(item_id)
        elif item_type == "piano":
            self.main_stack.setCurrentWidget(self.piano_widget)
            self.piano_widget.load_piano_data(item_id)
        elif item_type == "edificio":
            self.main_stack.setCurrentWidget(self.edificio_widget)
            self.edificio_widget.load_edificio_data(item_id)
        else:
            self.main_stack.setCurrentIndex(0)

    def _toggle_garanzie(self, checked: bool):
        if checked:
            self.main_stack.setCurrentWidget(self.garanzie_widget)
            self.garanzie_widget.load_data()
        else:
            self.main_stack.setCurrentIndex(0)

    # ------------------------------------------------------------------
    # Aggiornamento dopo modifiche all'albero
    # ------------------------------------------------------------------

    def _on_tree_changed(self):
        self.porta_widget._populate_combos()
        self.main_stack.setCurrentIndex(0)
