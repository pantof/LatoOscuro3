# This Python file uses the following encoding: utf-8

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeView, QToolBar, QMessageBox, QMenu
)
from PySide6.QtCore import Qt, Signal, QModelIndex, QPoint
from PySide6.QtSql import QSqlDatabase, QSqlQuery
from PySide6.QtGui import QStandardItemModel, QStandardItem

from widget.tree_dialogs import EdificioDialog, PianoDialog, LocaleDialog, PortaTreeDialog


class LocationManagerWidget(QWidget):

    item_selected = Signal(str, int)
    tree_changed  = Signal()          # emesso dopo ogni CRUD sull'albero

    def __init__(self, db: QSqlDatabase, parent=None):
        super().__init__(parent)
        if not db or not db.isOpen():
            QMessageBox.critical(self, "Errore", "Connessione DB non valida.")
            return
        self.db = db
        self.setup_ui()
        self.load_location_tree()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.toolbar = QToolBar()
        style = self.style()

        self.refresh_action = self.toolbar.addAction(
            style.standardIcon(style.StandardPixmap.SP_BrowserReload), "Aggiorna"
        )
        self.refresh_action.triggered.connect(self.load_location_tree)

        self.add_edificio_action = self.toolbar.addAction(
            style.standardIcon(style.StandardPixmap.SP_DirHomeIcon), "Nuovo Edificio"
        )
        self.add_edificio_action.triggered.connect(self._add_edificio)

        layout.addWidget(self.toolbar)

        self.tree_view = QTreeView()
        self.tree_view.setHeaderHidden(True)
        self.model = QStandardItemModel()
        self.tree_view.setModel(self.model)
        self.tree_view.setEditTriggers(QTreeView.NoEditTriggers)
        self.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.tree_view)

        self.tree_view.clicked.connect(self.on_item_clicked)

    # ------------------------------------------------------------------
    # Caricamento albero
    # ------------------------------------------------------------------

    def load_location_tree(self):
        self.model.clear()
        style = self.style()
        icon_building = style.standardIcon(style.StandardPixmap.SP_DirHomeIcon)
        icon_floor    = style.standardIcon(style.StandardPixmap.SP_DirOpenIcon)
        icon_room     = style.standardIcon(style.StandardPixmap.SP_DirIcon)
        icon_door     = style.standardIcon(style.StandardPixmap.SP_FileIcon)

        q_ed = QSqlQuery(self.db)
        if not q_ed.exec("SELECT edificio_id, nome_edificio FROM Edifici ORDER BY nome_edificio"):
            return

        while q_ed.next():
            edificio_id = q_ed.value(0)
            item_ed = QStandardItem(q_ed.value(1))
            item_ed.setIcon(icon_building)
            item_ed.setData(edificio_id, Qt.UserRole)
            item_ed.setData("edificio", Qt.UserRole + 1)
            item_ed.setEditable(False)
            self.model.appendRow(item_ed)

            q_pi = QSqlQuery(self.db)
            q_pi.prepare("SELECT piano_id, nome_piano FROM Piani WHERE edificio_id=? ORDER BY nome_piano")
            q_pi.addBindValue(edificio_id)
            if not q_pi.exec():
                continue

            while q_pi.next():
                piano_id = q_pi.value(0)
                item_pi = QStandardItem(q_pi.value(1))
                item_pi.setIcon(icon_floor)
                item_pi.setData(piano_id, Qt.UserRole)
                item_pi.setData("piano", Qt.UserRole + 1)
                item_pi.setEditable(False)
                item_ed.appendRow(item_pi)

                q_lo = QSqlQuery(self.db)
                q_lo.prepare("SELECT locale_id, nome_locale FROM Locali WHERE piano_id=? ORDER BY nome_locale")
                q_lo.addBindValue(piano_id)
                if not q_lo.exec():
                    continue

                while q_lo.next():
                    locale_id = q_lo.value(0)
                    item_lo = QStandardItem(q_lo.value(1))
                    item_lo.setIcon(icon_room)
                    item_lo.setData(locale_id, Qt.UserRole)
                    item_lo.setData("locale", Qt.UserRole + 1)
                    item_lo.setEditable(False)
                    item_pi.appendRow(item_lo)

                    q_po = QSqlQuery(self.db)
                    q_po.prepare("SELECT porta_id, nome_porta FROM Porte WHERE locale_id=? ORDER BY nome_porta")
                    q_po.addBindValue(locale_id)
                    if not q_po.exec():
                        continue

                    while q_po.next():
                        item_po = QStandardItem(q_po.value(1))
                        item_po.setIcon(icon_door)
                        item_po.setData(q_po.value(0), Qt.UserRole)
                        item_po.setData("porta", Qt.UserRole + 1)
                        item_po.setEditable(False)
                        item_lo.appendRow(item_po)

        self.tree_view.expandToDepth(1)

    # ------------------------------------------------------------------
    # Click sull'albero
    # ------------------------------------------------------------------

    def on_item_clicked(self, index: QModelIndex):
        if not index.isValid():
            return
        item = self.model.itemFromIndex(index)
        if not item:
            return
        item_type = item.data(Qt.UserRole + 1)
        item_id   = item.data(Qt.UserRole)
        if item_type and item_id is not None:
            self.item_selected.emit(item_type, item_id)

    # ------------------------------------------------------------------
    # Menu contestuale
    # ------------------------------------------------------------------

    def _show_context_menu(self, pos: QPoint):
        index = self.tree_view.indexAt(pos)
        menu  = QMenu(self)

        if not index.isValid():
            menu.addAction("Nuovo Edificio").triggered.connect(self._add_edificio)
        else:
            item      = self.model.itemFromIndex(index)
            item_type = item.data(Qt.UserRole + 1)
            item_id   = item.data(Qt.UserRole)
            nome      = item.text()

            if item_type == "edificio":
                menu.addAction("Aggiungi Piano").triggered.connect(
                    lambda: self._add_piano(item_id))
                menu.addSeparator()
                menu.addAction("Modifica Edificio").triggered.connect(
                    lambda: self._edit_edificio(item_id))
                menu.addAction("Elimina Edificio").triggered.connect(
                    lambda: self._delete("Edificio", "edificio_id", item_id, nome,
                                        "Tutti i piani, locali, porte e dispositivi collegati saranno eliminati."))
            elif item_type == "piano":
                menu.addAction("Aggiungi Locale").triggered.connect(
                    lambda: self._add_locale(item_id))
                menu.addSeparator()
                menu.addAction("Modifica Piano").triggered.connect(
                    lambda: self._edit_piano(item_id))
                menu.addAction("Elimina Piano").triggered.connect(
                    lambda: self._delete("Piani", "piano_id", item_id, nome,
                                        "Tutti i locali e le porte collegate saranno eliminati."))
            elif item_type == "locale":
                menu.addAction("Aggiungi Porta").triggered.connect(
                    lambda: self._add_porta(item_id))
                menu.addSeparator()
                menu.addAction("Modifica Locale").triggered.connect(
                    lambda: self._edit_locale(item_id))
                menu.addAction("Elimina Locale").triggered.connect(
                    lambda: self._delete("Locali", "locale_id", item_id, nome,
                                        "Tutte le porte e i dispositivi collegati saranno eliminati."))
            elif item_type == "porta":
                menu.addAction("Modifica Porta").triggered.connect(
                    lambda: self._edit_porta(item_id))
                menu.addSeparator()
                menu.addAction("Elimina Porta").triggered.connect(
                    lambda: self._delete("Porte", "porta_id", item_id, nome,
                                        "Tutti i dispositivi installati saranno eliminati."))

        if not menu.isEmpty():
            menu.exec(self.tree_view.viewport().mapToGlobal(pos))

    # ------------------------------------------------------------------
    # CRUD — Edifici
    # ------------------------------------------------------------------

    def _add_edificio(self):
        dlg = EdificioDialog(self.db, parent=self)
        if dlg.exec():
            self._refresh()

    def _edit_edificio(self, edificio_id: int):
        dlg = EdificioDialog(self.db, edificio_id, parent=self)
        if dlg.exec():
            self._refresh()

    # ------------------------------------------------------------------
    # CRUD — Piani
    # ------------------------------------------------------------------

    def _add_piano(self, edificio_id: int):
        dlg = PianoDialog(self.db, edificio_id=edificio_id, parent=self)
        if dlg.exec():
            self._refresh()

    def _edit_piano(self, piano_id: int):
        dlg = PianoDialog(self.db, piano_id=piano_id, parent=self)
        if dlg.exec():
            self._refresh()

    # ------------------------------------------------------------------
    # CRUD — Locali
    # ------------------------------------------------------------------

    def _add_locale(self, piano_id: int):
        dlg = LocaleDialog(self.db, piano_id=piano_id, parent=self)
        if dlg.exec():
            self._refresh()

    def _edit_locale(self, locale_id: int):
        dlg = LocaleDialog(self.db, locale_id=locale_id, parent=self)
        if dlg.exec():
            self._refresh()

    # ------------------------------------------------------------------
    # CRUD — Porte
    # ------------------------------------------------------------------

    def _add_porta(self, locale_id: int):
        dlg = PortaTreeDialog(self.db, locale_id=locale_id, parent=self)
        if dlg.exec():
            self._refresh()

    def _edit_porta(self, porta_id: int):
        dlg = PortaTreeDialog(self.db, porta_id=porta_id, parent=self)
        if dlg.exec():
            self._refresh()

    # ------------------------------------------------------------------
    # Elimina generico
    # ------------------------------------------------------------------

    def _delete(self, table: str, pk_col: str, pk_val: int, nome: str, warning: str):
        reply = QMessageBox.question(
            self, f"Elimina '{nome}'",
            f"Eliminare '{nome}'?\n{warning}",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        q = QSqlQuery(self.db)
        q.prepare(f"DELETE FROM {table} WHERE {pk_col}=?")
        q.addBindValue(pk_val)
        if q.exec():
            self._refresh()
        else:
            QMessageBox.critical(self, "Errore DB", q.lastError().text())

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def _refresh(self):
        self.load_location_tree()
        self.tree_changed.emit()
