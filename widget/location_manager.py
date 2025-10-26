from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeView, QToolBar
)
# AGGIUNTA: Importiamo Signal
from PySide6.QtCore import Qt, Signal
from PySide6.QtSql import QSqlDatabase, QSqlQuery
from PySide6.QtGui import QStandardItemModel, QStandardItem

class LocationManagerWidget(QWidget): # Rinominiamo per chiarezza
    # Segnale personalizzato: emette l'ID del locale quando viene selezionato
    locale_selected_signal = Signal(int)

    def __init__(self, db: QSqlDatabase, parent=None):
        super().__init__(parent)
        self.db = db
        self.setup_ui()
        self.load_location_tree()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.toolbar = QToolBar()
        style = self.style()
        self.refresh_action = self.toolbar.addAction(
            style.standardIcon(style.StandardPixmap.SP_BrowserReload), "Aggiorna"
        )
        self.refresh_action.triggered.connect(self.load_location_tree)
        layout.addWidget(self.toolbar)

        self.tree_view = QTreeView()
        self.tree_view.setHeaderHidden(True)
        self.model = QStandardItemModel()
        self.tree_view.setModel(self.model)
        # Disabilita l'editing col doppio click
        self.tree_view.setEditTriggers(QTreeView.NoEditTriggers)

        layout.addWidget(self.tree_view)

        # CONNETTIAMO LA SELEZIONE
        self.tree_view.selectionModel().currentChanged.connect(self.on_selection_changed)

    def load_location_tree(self):
        """
        Carica (o ricarica) l'intera gerarchia dal DB e popola il modello.
        """
        self.model.clear()

                # Icone (opzionali)
        style = self.style()
        icon_building = style.standardIcon(style.StandardPixmap.SP_DirHomeIcon)
        icon_floor = style.standardIcon(style.StandardPixmap.SP_DirOpenIcon)
        # --- QUESTA È LA RIGA CORRETTA ---
        icon_room = style.standardIcon(style.StandardPixmap.SP_DirIcon)

        # Livello 1: Edifici
        query_edifici = QSqlQuery(self.db)
        if query_edifici.exec("SELECT edificio_id, nome_edificio FROM Edifici ORDER BY nome_edificio"):
            while query_edifici.next():
                edificio_id = query_edifici.value(0)
                nome_edificio = query_edifici.value(1)

                item_edificio = QStandardItem(nome_edificio)
                item_edificio.setIcon(icon_building)
                item_edificio.setData(edificio_id, Qt.UserRole) # Salviamo l'ID
                item_edificio.setData("edificio", Qt.UserRole + 1) # Salviamo il tipo
                item_edificio.setEditable(False)

                self.model.appendRow(item_edificio)

                # Livello 2: Piani (per questo edificio)
                query_piani = QSqlQuery(self.db)
                query_piani.prepare("SELECT piano_id, nome_piano FROM Piani WHERE edificio_id = ? ORDER BY nome_piano")
                query_piani.addBindValue(edificio_id)
                if query_piani.exec():
                    while query_piani.next():
                        piano_id = query_piani.value(0)
                        nome_piano = query_piani.value(1)

                        item_piano = QStandardItem(nome_piano)
                        item_piano.setIcon(icon_floor)
                        item_piano.setData(piano_id, Qt.UserRole)
                        item_piano.setData("piano", Qt.UserRole + 1)
                        item_piano.setEditable(False)

                        item_edificio.appendRow(item_piano)

                        # Livello 3: Locali (per questo piano)
                        query_locali = QSqlQuery(self.db)
                        query_locali.prepare("SELECT locale_id, nome_locale FROM Locali WHERE piano_id = ? ORDER BY nome_locale")
                        query_locali.addBindValue(piano_id)
                        if query_locali.exec():
                            while query_locali.next():
                                locale_id = query_locali.value(0)
                                nome_locale = query_locali.value(1)

                                item_locale = QStandardItem(nome_locale)
                                item_locale.setIcon(icon_room)
                                item_locale.setData(locale_id, Qt.UserRole)
                                item_locale.setData("locale", Qt.UserRole + 1)
                                item_locale.setEditable(False)

                                item_piano.appendRow(item_locale)

                # Espandi i primi livelli
        self.tree_view.expandToDepth(1)

    def on_selection_changed(self, current, previous):
        """Attivato quando l'utente clicca sull'albero."""
        if not current.isValid(): return

        item_type = current.data(Qt.UserRole + 1)

        if item_type == "locale":
            locale_id = current.data(Qt.UserRole)
            # Emette il segnale con l'ID del locale selezionato
            self.locale_selected_signal.emit(locale_id)
        elif item_type == "root":
             # Se clicca su "Tutte le porte", emettiamo -1 (codice per "tutto")
             self.locale_selected_signal.emit(-1)
        else:
            # Se clicca su Edificio o Piano, per ora non facciamo nulla (o potremmo filtrare anche per quelli)
            pass
