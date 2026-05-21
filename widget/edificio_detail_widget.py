# This Python file uses the following encoding: utf-8

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QLabel, QTableWidget, QTableWidgetItem, QPushButton,
    QMessageBox, QHeaderView, QAbstractItemView
)
from PySide6.QtSql import QSqlDatabase, QSqlQuery, QSqlError
from PySide6.QtCore import Qt


class EdificioDetailWidget(QWidget):

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
        self.nome_edit     = QLineEdit()
        self.indirizzo_edit = QLineEdit()
        self.note_edit     = QTextEdit()
        self.note_edit.setMaximumHeight(70)
        form.addRow("Nome Edificio:", self.nome_edit)
        form.addRow("Indirizzo:", self.indirizzo_edit)
        layout.addLayout(form)
        layout.addWidget(QLabel("Note:"))
        layout.addWidget(self.note_edit)

        self.save_btn = QPushButton("Salva Modifiche Edificio")
        self.save_btn.clicked.connect(self._save)
        layout.addWidget(self.save_btn)

        layout.addWidget(QLabel("Piani:"))
        self.piani_table = QTableWidget()
        self.piani_table.setColumnCount(len(self.COLS_PIANI))
        self.piani_table.setHorizontalHeaderLabels(self.COLS_PIANI)
        self.piani_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.piani_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.piani_table.verticalHeader().setVisible(False)
        self.piani_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.piani_table)

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

        q2 = QSqlQuery(self.db)
        q2.prepare("""
            SELECT p.nome_piano,
                   COUNT(DISTINCT l.locale_id),
                   COUNT(DISTINCT po.porta_id)
            FROM Piani p
            LEFT JOIN Locali l  ON l.piano_id = p.piano_id
            LEFT JOIN Porte  po ON po.locale_id = l.locale_id
            WHERE p.edificio_id = ?
            GROUP BY p.piano_id, p.nome_piano
            ORDER BY p.nome_piano
        """)
        q2.addBindValue(edificio_id)
        if q2.exec():
            while q2.next():
                row = self.piani_table.rowCount()
                self.piani_table.insertRow(row)
                for col, val in enumerate([q2.value(0), str(q2.value(1)), str(q2.value(2))]):
                    item = QTableWidgetItem(val)
                    item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                    self.piani_table.setItem(row, col, item)

        self.setEnabled(True)

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
        else:
            QMessageBox.critical(self, "Errore DB", q.lastError().text())
