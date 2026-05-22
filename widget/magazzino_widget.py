# This Python file uses the following encoding: utf-8

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMessageBox
)
from PySide6.QtSql import QSqlDatabase, QSqlQuery
from PySide6.QtCore import Qt, Signal

from widget.materiale_dialog import MaterialeDialog
from widget.collega_porta_dialog import CollegaPortaDialog


class MagazzinoWidget(QWidget):
    """Vista del magazzino materiali fisici con CRUD completo."""

    COLS = [
        "Articolo", "Tipo", "Marca/Modello",
        "Matricola/SN", "Acquistato il", "Fornitore",
        "N. Fattura", "Garanzia", "Stato", "Collegato a"
    ]

    def __init__(self, db: QSqlDatabase, parent=None):
        super().__init__(parent)
        self.db = db
        self._rows: list[dict] = []
        self._setup_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Barra superiore: titolo + filtri
        top = QHBoxLayout()
        top.addWidget(QLabel("<b>Magazzino Materiali</b>"))
        top.addStretch()

        top.addWidget(QLabel("Stato:"))
        self.stato_combo = QComboBox()
        self.stato_combo.addItems([
            "Tutti",
            "In magazzino",
            "Installato",
            "In riparazione",
            "Dismesso",
        ])
        self.stato_combo.currentTextChanged.connect(self._apply_filters)
        top.addWidget(self.stato_combo)

        top.addWidget(QLabel("Cerca:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Articolo, matricola, fornitore…")
        self.search_edit.setMaximumWidth(240)
        self.search_edit.textChanged.connect(self._apply_filters)
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

        # Pulsanti azione
        btn_row = QHBoxLayout()
        self.btn_aggiungi = QPushButton("+ Nuovo Materiale")
        self.btn_collega  = QPushButton("Collega a Porta")
        self.btn_modifica = QPushButton("Modifica")
        self.btn_elimina  = QPushButton("Elimina")
        self.btn_aggiorna = QPushButton("Aggiorna")

        self.btn_aggiungi.setToolTip("Registra un nuovo materiale fisico ricevuto dal fornitore")
        self.btn_collega.setToolTip("Collega il materiale selezionato a una porta (installazione)")

        self.btn_aggiungi.clicked.connect(self._aggiungi)
        self.btn_collega.clicked.connect(self._collega_porta)
        self.btn_modifica.clicked.connect(self._modifica)
        self.btn_elimina.clicked.connect(self._elimina)
        self.btn_aggiorna.clicked.connect(self.load_data)

        btn_row.addWidget(self.btn_aggiungi)
        btn_row.addWidget(self.btn_collega)
        btn_row.addWidget(self.btn_modifica)
        btn_row.addWidget(self.btn_elimina)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_aggiorna)
        layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Caricamento dati
    # ------------------------------------------------------------------

    def load_data(self):
        """Carica tutti i materiali dal DB e aggiorna la vista."""
        self._rows = []
        q = QSqlQuery(self.db)
        q.exec("""
            SELECT m.materiale_id,
                   c.nome_articolo,
                   t.nome_tipo,
                   COALESCE(c.marca,'') || ' ' || COALESCE(c.modello,'') AS marca_modello,
                   COALESCE(m.matricola,''),
                   COALESCE(m.data_acquisto,''),
                   COALESCE(m.fornitore,''),
                   COALESCE(m.num_fattura,''),
                   m.garanzia_mesi,
                   m.stato,
                   COALESCE(p.nome_porta,'—') AS porta,
                   m.articolo_id
            FROM Materiali m
            JOIN Catalogo_Materiali c ON m.articolo_id = c.articolo_id
            JOIN Tipi_Dispositivi t   ON c.tipo_id = t.tipo_id
            LEFT JOIN Inventario_Dispositivi id ON id.materiale_id = m.materiale_id
            LEFT JOIN Porte p ON id.porta_id = p.porta_id
            ORDER BY m.stato, t.nome_tipo, c.nome_articolo
        """)
        while q.next():
            garanzia = q.value(8)
            # Formatta data acquisto
            da = q.value(5)
            if da:
                from PySide6.QtCore import QDate
                d = QDate.fromString(da, "yyyy-MM-dd")
                da = d.toString("dd/MM/yyyy") if d.isValid() else da

            self._rows.append({
                "id":           q.value(0),
                "articolo_id":  q.value(11),
                "stato":        q.value(9),
                "cells": [
                    q.value(1),                                        # Articolo
                    q.value(2),                                        # Tipo
                    q.value(3).strip(),                                # Marca/Modello
                    q.value(4),                                        # Matricola/SN
                    da,                                                # Acquistato il
                    q.value(6),                                        # Fornitore
                    q.value(7),                                        # N. Fattura
                    f"{int(garanzia)} mesi" if garanzia else "—",      # Garanzia
                    q.value(9),                                        # Stato
                    q.value(10),                                       # Collegato a
                ],
            })
        self._apply_filters()

    def _apply_filters(self):
        stato_filter = self.stato_combo.currentText()
        text_filter  = self.search_edit.text().lower()

        filtered = self._rows
        if stato_filter != "Tutti":
            filtered = [r for r in filtered if r["stato"] == stato_filter]
        if text_filter:
            filtered = [r for r in filtered
                        if any(text_filter in str(c).lower() for c in r["cells"][:8])]
        self._render(filtered)

    def _render(self, rows: list[dict]):
        self.table.setRowCount(0)
        for row_data in rows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for col, val in enumerate(row_data["cells"]):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                if col == 0:
                    item.setData(Qt.UserRole, row_data["id"])
                self.table.setItem(row, col, item)

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
        dlg = MaterialeDialog(self.db, parent=self)
        if dlg.exec():
            self.load_data()

    def _modifica(self):
        mid = self._selected_id()
        if mid is None:
            QMessageBox.information(self, "Nessuna selezione",
                                    "Seleziona un materiale dalla lista.")
            return
        dlg = MaterialeDialog(self.db, materiale_id=mid, parent=self)
        if dlg.exec():
            self.load_data()

    def _collega_porta(self):
        mid = self._selected_id()
        if mid is None:
            QMessageBox.information(self, "Nessuna selezione",
                                    "Seleziona un materiale da collegare.")
            return
        # Verifica che sia in magazzino
        row = self.table.currentRow()
        stato = self.table.item(row, 8).text() if self.table.item(row, 8) else ""
        if stato not in ("In magazzino", ""):
            QMessageBox.warning(
                self, "Non disponibile",
                f"Il materiale e' nello stato '{stato}'.\n"
                "Solo i materiali 'In magazzino' possono essere installati."
            )
            return
        dlg = CollegaPortaDialog(self.db, materiale_id=mid, parent=self)
        if dlg.exec():
            self.load_data()

    def _elimina(self):
        mid = self._selected_id()
        if mid is None:
            QMessageBox.information(self, "Nessuna selezione",
                                    "Seleziona un materiale da eliminare.")
            return

        # Controlla se installato
        q = QSqlQuery(self.db)
        q.prepare("SELECT COUNT(*) FROM Inventario_Dispositivi WHERE materiale_id=?")
        q.addBindValue(mid)
        n_inst = 0
        if q.exec() and q.next():
            n_inst = q.value(0)

        row = self.table.currentRow()
        nome = self.table.item(row, 0).text() if self.table.item(row, 0) else f"#{mid}"
        matricola = self.table.item(row, 3).text() if self.table.item(row, 3) else ""
        label = f"{nome}" + (f" (SN: {matricola})" if matricola else "")

        msg = f"Eliminare '{label}' dal magazzino?"
        if n_inst > 0:
            msg += (f"\n\nAttenzione: questo materiale e' collegato a {n_inst} "
                    "installazione/i. Il collegamento verra' rimosso ma le "
                    "installazioni rimarranno.")

        reply = QMessageBox.question(self, "Conferma eliminazione", msg,
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        # Scollega installazioni
        q2 = QSqlQuery(self.db)
        q2.prepare("UPDATE Inventario_Dispositivi SET materiale_id=NULL WHERE materiale_id=?")
        q2.addBindValue(mid)
        q2.exec()

        q3 = QSqlQuery(self.db)
        q3.prepare("DELETE FROM Materiali WHERE materiale_id=?")
        q3.addBindValue(mid)
        if q3.exec():
            self.load_data()
        else:
            QMessageBox.critical(self, "Errore DB", q3.lastError().text())
