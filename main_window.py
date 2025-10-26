from PySide6.QtWidgets import (
    QMainWindow, QMessageBox, QWidget, QHBoxLayout, QVBoxLayout, 
    QStackedWidget # Aggiunti QHBoxLayout, QVBoxLayout, QStackedWidget
)
from PySide6.QtSql import QSqlDatabase, QSqlQuery
from PySide6.QtCore import Qt

from widget.porta_widget import PortaDetailWidget
# Importiamo la nuova classe rinominata
from widget.location_manager import LocationManagerWidget

class MainWindow(QMainWindow):
    def __init__(self, db: QSqlDatabase):
        super().__init__()
        self.setWindowTitle("Gestione Inventario Impianti (Vista Unificata)")
        self.setGeometry(100, 100, 1200, 700) # Un po' più largo per i 3 pannelli
        self.db = db
        if not db or not db.isOpen():
             QMessageBox.critical(self, "Errore", "Connessione DB non valida.")
             return

        self.setup_ui()
        # Carica inizialmente tutte le porte
        self.load_door_list(locale_id=-1)

    def setup_ui(self):
        # Widget centrale e layout principale orizzontale
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5) # Margini piccoli
        main_layout.setSpacing(5)

        # --- Pannello Navigazione Sinistro ---
        navigation_panel = QWidget()
        nav_layout = QVBoxLayout(navigation_panel)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        navigation_panel.setMaximumWidth(300) # O la larghezza che preferisci

        # L'albero va nel pannello di navigazione
        self.asset_tree = LocationManagerWidget(self.db)
        nav_layout.addWidget(self.asset_tree)

        # --- Area Contenuti Destra (Stacked Widget) ---
        self.main_stack = QStackedWidget()

        # Aggiungi le pagine allo stack
        self.placeholder_page = QWidget() # Pagina vuota iniziale
        self.detail_widget = PortaDetailWidget(self.db) # Il tuo widget dettaglio porta

        self.main_stack.addWidget(self.placeholder_page) # Indice 0
        self.main_stack.addWidget(self.detail_widget)    # Indice 1

        # (Aggiungi qui futuri widget dettaglio per Locali, Edifici, etc.)
        # self.locale_detail_widget = LocaleDetailWidget(self.db)
        # self.main_stack.addWidget(self.locale_detail_widget) # Indice 2 ...

        # Aggiungi i due pannelli principali al layout orizzontale
        main_layout.addWidget(navigation_panel)
        main_layout.addWidget(self.main_stack, stretch=1) # Dà più spazio allo stack

        # Connessione del segnale dall'albero allo slot
        self.asset_tree.item_selected.connect(self.on_asset_selected)

        # Inizia mostrando la pagina placeholder
        self.main_stack.setCurrentIndex(0)

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
        
    def on_asset_selected(self, item_type: str, item_id: int):
        """
        Chiamato quando un item nell'albero viene cliccato.
        Cambia la pagina nello StackedWidget e carica i dati.
        """
        if item_type == "porta":
            # Cambia alla pagina del dettaglio porta
            self.main_stack.setCurrentWidget(self.detail_widget)
            # Carica i dati della porta selezionata
            self.detail_widget.load_porta_data(item_id)
        # --- Esempi per il futuro ---
        # elif item_type == "locale":
        #     # Cambia alla pagina del dettaglio locale (da creare)
        #     # self.main_stack.setCurrentWidget(self.locale_detail_widget)
        #     # self.locale_detail_widget.load_locale_data(item_id)
        #     # Per ora, torna alla pagina vuota se non c'è dettaglio
        #     self.main_stack.setCurrentIndex(0)
        #     self.detail_widget.clear_form() # Pulisce anche il form porta
        # elif item_type == "edificio":
        #      # Cambia alla pagina del dettaglio edificio (da creare)
        #     # self.main_stack.setCurrentWidget(self.edificio_detail_widget)
        #     # self.edificio_detail_widget.load_edificio_data(item_id)
        #     # Per ora, torna alla pagina vuota
        #     self.main_stack.setCurrentIndex(0)
        #     self.detail_widget.clear_form()
        else:
            # Per tutti gli altri tipi (Piani, Edifici al momento) o se non valido
            # mostra la pagina placeholder iniziale
            self.main_stack.setCurrentIndex(0)
            # Assicurati che il form dettaglio porta sia pulito
            self.detail_widget.clear_form()

    # (closeEvent rimane uguale)
