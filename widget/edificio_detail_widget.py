# This Python file uses the following encoding: utf-8

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QLabel, QTableWidget, QTableWidgetItem, QPushButton,
    QMessageBox, QHeaderView, QAbstractItemView
)
from PySide6.QtSql import QSqlDatabase, QSqlQuery
from PySide6.QtCore import Qt, Signal

from widget.tree_dialogs import PianoDialog


class EdificioDetailWidget(QWidget):

    content_changed = Signal()   # emesso dopo aggiunta piano → aggiorna albero
    COLS_PIANI = ["Piano", "N. Locali", "N. Porte"]

    def __init__(self, db: QSqlDatabase, parent=None):
        super().__init__(parent)
        self.db = db
        self.current_edificio_id = None
        self._setup_ui()
        self.clear_form()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.nome_edit      = QLineEdit()
        self.indirizzo_edit = QLineEdit()
        self.note_edit      = QTextEdit()
        self.note_edit.setMaximumHeight(70)
        form.addRow("Nome Edificio:", self.nome_edit)
        form.addRow("Indirizzo:", self.indirizzo_edit)
        layout.addLayout(form)
        layout.addWidget(QLabel("Note:"))
        layout.addWidget(self.note_edit)

        self.save_btn = QPushButton("Salva Modifiche Edificio")
        self.save_btn.clicked.connect(self._save)
        layout.addWidget(self.save_btn)

        # Intestazione lista piani con pulsante Aggiungi
        piani_header = QHBoxLayout()
        piani_header.addWidget(QLabel("Piani dell'edificio:"))
        piani_header.addStretch()
        self.btn_aggiungi_piano = QPushButton("+ Aggiungi Piano")
        self.btn_aggiungi_piano.clicked.connect(self._aggiungi_piano)
        piani_header.addWidget(self.btn_aggiungi_piano)
        layout.addLayout(piani_header)

        self.piani_table = QTableWidget()
        self.piani_table.setColumnCount(len(self.COLS_PIANI))
        self.piani_table.setHorizontalHeaderLabels(self.COLS_PIANI)
        self.piani_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.piani_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.piani_table.verticalHeader().setVisible(False)
        self.piani_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.piani_table)

    # ------------------------------------------------------------------

    def clear_form(self):
        self.current_edificio_id = None
        self.nome_edit.clear()
        self.indirizzo_edit.clear()
        self.note_edit.clear()
        self.piani_table.setRowCount(0)
        self.setEnabled(False)

    def load_edificio_data(self, edificio_id: int):
        self.clear_form()
        self.current_edificio_id = edificio_id

        q = QSqlQuery(self.db)
        q.prepare("SELECT nome_edificio, indirizzo, note FROM Edifici WHERE edificio_id=?")
        q.addBindValue(edificio_id)
        if not (q.exec() and q.next()):
            return
        self.nome_edit.setText(q.value(0) or "")
        self.indirizzo_edit.setText(q.value(1) or "")
        self.note_edit.setPlainText(q.value(2) or "")

        self._load_piani(edificio_id)
        self.setEnabled(True)

    def _load_piani(self, edificio_id: int):
        self.piani_table.setRowCount(0)
        q = QSqlQuery(self.db)
        q.prepare("""
            SELECT p.nome_piano,
                   COUNT(DISTINCT l.locale_id),
                   COUNT(DISTINCT po.porta_id)
            FROM Piani p
            LEFT JOIN Locali l  ON l.piano_id    = p.piano_id
            LEFT JOIN Porte  po ON po.locale_id  = l.locale_id
            WHERE p.edificio_id = ?
            GROUP BY p.piano_id, p.nome_piano
            ORDER BY p.nome_piano
        """)
        q.addBindValue(edificio_id)
        if q.exec():
            while q.next():
                row = self.piani_table.rowCount()
                self.piani_table.insertRow(row)
                for col, val in enumerate([q.value(0), str(q.value(1)), str(q.value(2))]):
                    item = QTableWidgetItem(val)
                    item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                    self.piani_table.setItem(row, col, item)

    def _aggiungi_piano(self):
        if self.current_edificio_id is None:
            return
        dlg = PianoDialog(self.db, edificio_id=self.current_edificio_id, parent=self)
        if dlg.exec():
            self._load_piani(self.current_edificio_id)
            self.content_changed.emit()

    def _save(self):
        if self.current_edificio_id is None:
            return
        q = QSqlQuery(self.db)
        q.prepare("UPDATE Edifici SET nome_edificio=?, indirizzo=?, note=? WHERE edificio_id=?")
        q.addBindValue(self.nome_edit.text().strip())
        q.addBindValue(self.indirizzo_edit.text().strip() or None)
        q.addBindValue(self.note_edit.toPlainText().strip() or None)
        q.addBindValue(self.current_edificio_id)
        if q.exec():
            QMessageBox.information(self, "Salvato", "Edificio aggiornato.")
            self.content_changed.emit()
        else:
            QMessageBox.critical(self, "Errore DB", q.lastError().text())
