from PySide6.QtWidgets import (
    QMainWindow, QListWidget, QSplitter, QListWidgetItem,
    QMessageBox, QVBoxLayout, QWidget, QLabel
)
from PySide6.QtSql import QSqlDatabase, QSqlQuery
from PySide6.QtCore import Qt

from widget.porta_widget import PortaDetailWidget
# Importiamo la nuova classe rinominata
from widget.location_manager import LocationTreeWidget

class MainWindow(QMainWindow):
    def __init__(self, db: QSqlDatabase):
        super().__init__()
        self.setWindowTitle("Gestione Inventario Impianti (Vista Unificata)")
        self.setGeometry(100, 100, 1200, 700) # Un po' più largo per i 3 pannelli
        self.db = db
        if not db or not db.isOpen(): return

        self.setup_ui()
        # Carica inizialmente tutte le porte
        self.load_door_list(locale_id=-1)

    def setup_ui(self):
        # SPLITTER PRINCIPALE (Orizzontale)
        main_splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(main_splitter)

        # --- PANNELLO 1 (Sinistra): Albero Posizioni ---
        self.tree_panel = LocationTreeWidget(self.db)

        # --- PANNELLO 2 (Centro): Lista Porte ---
        # Usiamo un widget contenitore per potergli dare un titolo
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0,0,0,0)
        self.center_label = QLabel("Elenco Porte")
        self.center_label.setStyleSheet("font-weight: bold; padding: 5px;")
        self.door_list_widget = QListWidget()
        center_layout.addWidget(self.center_label)
        center_layout.addWidget(self.door_list_widget)

        # --- PANNELLO 3 (Destra): Dettaglio Porta ---
        self.detail_panel = PortaDetailWidget(self.db)

        # Aggiungiamo tutto allo splitter principale
        main_splitter.addWidget(self.tree_panel)
        main_splitter.addWidget(center_widget)
        main_splitter.addWidget(self.detail_panel)

        # Impostiamo le dimensioni iniziali dei 3 pannelli
        main_splitter.setSizes([250, 300, 650])
        # Rende i pannelli laterali "collassabili" se si restringe troppo la finestra
        main_splitter.setCollapsible(0, False)
        main_splitter.setCollapsible(1, False)

        # --- CONNESSIONI SEGNALI ---
        # 1. Se seleziono un locale nell'albero -> Filtra la lista centrale
        self.tree_panel.locale_selected_signal.connect(self.load_door_list)

        # 2. Se seleziono una porta nella lista centrale -> Mostra dettagli a destra
        self.door_list_widget.currentItemChanged.connect(self.on_door_selected)

    def load_door_list(self, locale_id=-1):
        """
        Carica le porte. Se locale_id è -1 mostra tutto,
        altrimenti filtra per quel locale.
        """
        self.door_list_widget.clear()
        # Deseleziona il dettaglio a destra quando cambia la lista
        self.detail_panel.clear_form()

        query = QSqlQuery(self.db)
        if locale_id == -1:
            self.center_label.setText("Elenco Porte (Tutte)")
            query.prepare("SELECT porta_id, nome_porta FROM Porte ORDER BY nome_porta")
        else:
            self.center_label.setText("Elenco Porte (Filtrato per Locale)")
            query.prepare("SELECT porta_id, nome_porta FROM Porte WHERE locale_id = ? ORDER BY nome_porta")
            query.addBindValue(locale_id)

        if query.exec():
            while query.next():
                item = QListWidgetItem(query.value(1))
                item.setData(Qt.UserRole, query.value(0)) # ID porta
                self.door_list_widget.addItem(item)

    def on_door_selected(self, current_item, previous):
        if current_item is None:
            self.detail_panel.clear_form()
            return
        porta_id = current_item.data(Qt.UserRole)
        self.detail_panel.load_porta_data(porta_id)

    # (closeEvent rimane uguale)
