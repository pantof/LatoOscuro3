# This Python file uses the following encoding: utf-8

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox
)
from PySide6.QtSql import QSqlDatabase, QSqlQuery
from PySide6.QtCore import Qt

from widget.catalogo_dialog import CatalogoDialog


class CatalogoWidget(QWidget):
    """Vista completa del catalogo materiali hardware con CRUD."""

    COLS = ["Nome Articolo", "Tipo", "Marca", "Modello", "Garanzia std.", "Fornitore", "Installazioni"]

    def __init__(self, db: QSqlDatabase, parent=None):
        super().__init__(parent)
        self.db = db
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Titolo + barra ricerca
        top = QHBoxLayout()
        top.addWidget(QLabel("<b>Catalogo Materiali</b>"))
        top.addStretch()
        top.addWidget(QLabel("Cerca:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Filtra per nome, tipo, marca, modello…")
        self.search_edit.setMaximumWidth(280)
        self.search_edit.textChanged.connect(self._filter)
        top.addWidget(self.search_edit)
        layout.addLayout(top)

        # Tabella
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.doubleClicked.connect(self._modifica)
        layout.addWidget(self.table)

        # Pulsanti
        btn_row = QHBoxLayout()
        self.btn_aggiungi = QPushButton("+ Nuovo Articolo")
        self.btn_modifica = QPushButton("Modifica")
        self.btn_elimina  = QPushButton("Elimina")
        self.btn_aggiorna = QPushButton("⟳ Aggiorna")
        self.btn_aggiungi.clicked.connect(self._aggiungi)
        self.btn_modifica.clicked.connect(self._modifica)
        self.btn_elimina.clicked.connect(self._elimina)
        self.btn_aggiorna.clicked.connect(self.load_data)
        btn_row.addWidget(self.btn_aggiungi)
        btn_row.addWidget(self.btn_modifica)
        btn_row.addWidget(self.btn_elimina)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_aggiorna)
        layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Dati
    # ------------------------------------------------------------------

    def load_data(self):
        self.search_edit.clear()
        self._rows = []
        q = QSqlQuery(self.db)
        q.exec("""
            SELECT c.articolo_id,
                   c.nome_articolo,
                   t.nome_tipo,
                   COALESCE(c.marca,  ''),
                   COALESCE(c.modello,''),
                   c.garanzia_standard_mesi,
                   COALESCE(c.fornitore_preferito,''),
                   COUNT(d.dispositivo_id) AS n_inst
            FROM Catalogo_Materiali c
            JOIN Tipi_Dispositivi t ON c.tipo_id = t.tipo_id
            LEFT JOIN Inventario_Dispositivi d ON d.articolo_id = c.articolo_id
            GROUP BY c.articolo_id
            ORDER BY t.nome_tipo, c.nome_articolo
        """)
        while q.next():
            garanzia = q.value(5)
            self._rows.append({
                "id":    q.value(0),
                "cells": [
                    q.value(1),
                    q.value(2),
                    q.value(3),
                    q.value(4),
                    f"{int(garanzia)} mesi" if garanzia else "—",
                    q.value(6),
                    str(q.value(7)),
                ],
            })
        self._render(self._rows)

    def _render(self, rows):
        self.table.setRowCount(0)
        for row_data in rows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for col, val in enumerate(row_data["cells"]):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                if col == 0:
                    item.setData(Qt.UserRole, row_data["id"])
                self.table.setItem(row, col, item)

    def _filter(self, text: str):
        if not text:
            self._render(self._rows)
            return
        t = text.lower()
        filtered = [r for r in self._rows
                    if any(t in cell.lower() for cell in r["cells"][:5])]
        self._render(filtered)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def _selected_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _aggiungi(self):
        dlg = CatalogoDialog(self.db, parent=self)
        if dlg.exec():
            self.load_data()

    def _modifica(self):
        aid = self._selected_id()
        if aid is None:
            QMessageBox.information(self, "Nessuna selezione", "Seleziona un articolo.")
            return
        dlg = CatalogoDialog(self.db, articolo_id=aid, parent=self)
        if dlg.exec():
            self.load_data()

    def _elimina(self):
        aid = self._selected_id()
        if aid is None:
            QMessageBox.information(self, "Nessuna selezione", "Seleziona un articolo.")
            return
        # Conta installazioni attive
        q = QSqlQuery(self.db)
        q.prepare("SELECT COUNT(*) FROM Inventario_Dispositivi WHERE articolo_id=?")
        q.addBindValue(aid)
        n_inst = 0
        if q.exec() and q.next():
            n_inst = q.value(0)

        nome = self.table.item(self.table.currentRow(), 0).text()
        msg = f"Eliminare '{nome}' dal catalogo?"
        if n_inst > 0:
            msg += f"\n\nAttenzione: questo articolo è installato in {n_inst} postazione/i.\nIl collegamento al catalogo verrà rimosso ma le installazioni rimarranno."

        reply = QMessageBox.question(self, "Conferma eliminazione", msg,
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        # Scollega prima le installazioni (articolo_id → NULL)
        q2 = QSqlQuery(self.db)
        q2.prepare("UPDATE Inventario_Dispositivi SET articolo_id=NULL WHERE articolo_id=?")
        q2.addBindValue(aid)
        q2.exec()

        q3 = QSqlQuery(self.db)
        q3.prepare("DELETE FROM Catalogo_Materiali WHERE articolo_id=?")
        q3.addBindValue(aid)
        if q3.exec():
            self.load_data()
        else:
            QMessageBox.critical(self, "Errore DB", q3.lastError().text())
