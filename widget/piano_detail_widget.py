# This Python file uses the following encoding: utf-8

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QLabel,
    QTableWidget, QTableWidgetItem, QPushButton,
    QMessageBox, QHeaderView, QAbstractItemView
)
from PySide6.QtSql import QSqlDatabase, QSqlQuery
from PySide6.QtCore import Qt


class PianoDetailWidget(QWidget):

    COLS_LOCALI = ["Locale", "Descrizione", "N. Porte"]

    def __init__(self, db: QSqlDatabase, parent=None):
        super().__init__(parent)
        self.db = db
        self.current_piano_id = None
        self._setup_ui()
        self.clear_form()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.nome_edit     = QLineEdit()
        self.edificio_edit = QLineEdit()
        self.edificio_edit.setReadOnly(True)
        self.edificio_edit.setStyleSheet("background-color: #f0f0f0;")
        form.addRow("Nome Piano:", self.nome_edit)
        form.addRow("Edificio:", self.edificio_edit)
        layout.addLayout(form)

        self.save_btn = QPushButton("Salva Modifiche Piano")
        self.save_btn.clicked.connect(self._save)
        layout.addWidget(self.save_btn)

        layout.addWidget(QLabel("Locali:"))
        self.locali_table = QTableWidget()
        self.locali_table.setColumnCount(len(self.COLS_LOCALI))
        self.locali_table.setHorizontalHeaderLabels(self.COLS_LOCALI)
        self.locali_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.locali_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.locali_table.verticalHeader().setVisible(False)
        self.locali_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.locali_table)

    def clear_form(self):
        self.current_piano_id = None
        self.nome_edit.clear()
        self.edificio_edit.clear()
        self.locali_table.setRowCount(0)
        self.setEnabled(False)

    def load_piano_data(self, piano_id: int):
        self.clear_form()
        self.current_piano_id = piano_id

        q = QSqlQuery(self.db)
        q.prepare("""
            SELECT p.nome_piano, e.nome_edificio
            FROM Piani p JOIN Edifici e ON p.edificio_id = e.edificio_id
            WHERE p.piano_id = ?
        """)
        q.addBindValue(piano_id)
        if not (q.exec() and q.next()):
            return
        self.nome_edit.setText(q.value(0) or "")
        self.edificio_edit.setText(q.value(1) or "")

        q2 = QSqlQuery(self.db)
        q2.prepare("""
            SELECT l.nome_locale, COALESCE(l.descrizione, ''), COUNT(po.porta_id)
            FROM Locali l
            LEFT JOIN Porte po ON po.locale_id = l.locale_id
            WHERE l.piano_id = ?
            GROUP BY l.locale_id, l.nome_locale, l.descrizione
            ORDER BY l.nome_locale
        """)
        q2.addBindValue(piano_id)
        if q2.exec():
            while q2.next():
                row = self.locali_table.rowCount()
                self.locali_table.insertRow(row)
                for col, val in enumerate([q2.value(0), q2.value(1), str(q2.value(2))]):
                    item = QTableWidgetItem(val)
                    item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                    self.locali_table.setItem(row, col, item)

        self.setEnabled(True)

    def _save(self):
        if self.current_piano_id is None:
            return
        q = QSqlQuery(self.db)
        q.prepare("UPDATE Piani SET nome_piano=? WHERE piano_id=?")
        q.addBindValue(self.nome_edit.text().strip())
        q.addBindValue(self.current_piano_id)
        if q.exec():
            QMessageBox.information(self, "Salvato", "Piano aggiornato.")
        else:
            QMessageBox.critical(self, "Errore DB", q.lastError().text())
