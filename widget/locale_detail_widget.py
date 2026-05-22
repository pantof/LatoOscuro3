# This Python file uses the following encoding: utf-8

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QLabel,
    QTableWidget, QTableWidgetItem, QPushButton,
    QMessageBox, QHeaderView, QAbstractItemView
)
from PySide6.QtSql import QSqlDatabase, QSqlQuery
from PySide6.QtCore import Qt, Signal

from widget.tree_dialogs import PortaTreeDialog


class LocaleDetailWidget(QWidget):

    content_changed = Signal()   # emesso dopo aggiunta porta → aggiorna albero
    COLS_PORTE = ["Porta", "Note", "N. Dispositivi"]

    def __init__(self, db: QSqlDatabase, parent=None):
        super().__init__(parent)
        self.db = db
        self.current_locale_id = None
        self._setup_ui()
        self.clear_form()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.nome_edit        = QLineEdit()
        self.descrizione_edit = QLineEdit()
        self.posizione_edit   = QLineEdit()
        self.posizione_edit.setReadOnly(True)
        self.posizione_edit.setStyleSheet("background-color: #f0f0f0;")
        form.addRow("Nome Locale:", self.nome_edit)
        form.addRow("Descrizione:", self.descrizione_edit)
        form.addRow("Posizione:", self.posizione_edit)
        layout.addLayout(form)

        self.save_btn = QPushButton("Salva Modifiche Locale")
        self.save_btn.clicked.connect(self._save)
        layout.addWidget(self.save_btn)

        # Intestazione lista porte con pulsante Aggiungi
        porte_header = QHBoxLayout()
        porte_header.addWidget(QLabel("Porte in questo locale:"))
        porte_header.addStretch()
        self.btn_aggiungi_porta = QPushButton("+ Aggiungi Porta")
        self.btn_aggiungi_porta.clicked.connect(self._aggiungi_porta)
        porte_header.addWidget(self.btn_aggiungi_porta)
        layout.addLayout(porte_header)

        self.porte_table = QTableWidget()
        self.porte_table.setColumnCount(len(self.COLS_PORTE))
        self.porte_table.setHorizontalHeaderLabels(self.COLS_PORTE)
        self.porte_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.porte_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.porte_table.verticalHeader().setVisible(False)
        self.porte_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.porte_table)

    # ------------------------------------------------------------------

    def clear_form(self):
        self.current_locale_id = None
        self.nome_edit.clear()
        self.descrizione_edit.clear()
        self.posizione_edit.clear()
        self.porte_table.setRowCount(0)
        self.setEnabled(False)

    def load_locale_data(self, locale_id: int):
        self.clear_form()
        self.current_locale_id = locale_id

        q = QSqlQuery(self.db)
        q.prepare("""
            SELECT l.nome_locale, COALESCE(l.descrizione, ''),
                   COALESCE(e.nome_edificio, ''), COALESCE(p.nome_piano, '')
            FROM Locali l
            LEFT JOIN Piani   p ON l.piano_id    = p.piano_id
            LEFT JOIN Edifici e ON p.edificio_id = e.edificio_id
            WHERE l.locale_id = ?
        """)
        q.addBindValue(locale_id)
        if not (q.exec() and q.next()):
            return
        self.nome_edit.setText(q.value(0) or "")
        self.descrizione_edit.setText(q.value(1) or "")
        edificio, piano = q.value(2), q.value(3)
        if edificio:
            self.posizione_edit.setText(f"{edificio}  >  {piano}")

        self._load_porte(locale_id)
        self.setEnabled(True)

    def _load_porte(self, locale_id: int):
        self.porte_table.setRowCount(0)
        q = QSqlQuery(self.db)
        q.prepare("""
            SELECT po.nome_porta, COALESCE(po.note, ''), COUNT(d.dispositivo_id)
            FROM Porte po
            LEFT JOIN Inventario_Dispositivi d ON d.porta_id = po.porta_id
            WHERE po.locale_id = ?
            GROUP BY po.porta_id, po.nome_porta, po.note
            ORDER BY po.nome_porta
        """)
        q.addBindValue(locale_id)
        if q.exec():
            while q.next():
                row = self.porte_table.rowCount()
                self.porte_table.insertRow(row)
                for col, val in enumerate([q.value(0), q.value(1), str(q.value(2))]):
                    item = QTableWidgetItem(val)
                    item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                    self.porte_table.setItem(row, col, item)

    def _aggiungi_porta(self):
        if self.current_locale_id is None:
            return
        dlg = PortaTreeDialog(self.db, locale_id=self.current_locale_id, parent=self)
        if dlg.exec():
            self._load_porte(self.current_locale_id)
            self.content_changed.emit()

    def _save(self):
        if self.current_locale_id is None:
            return
        q = QSqlQuery(self.db)
        q.prepare("UPDATE Locali SET nome_locale=?, descrizione=? WHERE locale_id=?")
        q.addBindValue(self.nome_edit.text().strip())
        q.addBindValue(self.descrizione_edit.text().strip() or None)
        q.addBindValue(self.current_locale_id)
        if q.exec():
            QMessageBox.information(self, "Salvato", "Locale aggiornato.")
            self.content_changed.emit()
        else:
            QMessageBox.critical(self, "Errore DB", q.lastError().text())
