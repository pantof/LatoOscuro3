# This Python file uses the following encoding: utf-8

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PySide6.QtSql import QSqlDatabase, QSqlQuery
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor

SOGLIA_SCADENZA_GIORNI = 90
COLOR_SCADUTA     = QColor(255, 170, 170)
COLOR_IN_SCADENZA = QColor(255, 220, 130)


class GaranzieWidget(QWidget):

    COLS = [
        "Edificio", "Piano", "Locale", "Porta",
        "Tipo", "Modello", "Matricola/SN",
        "Data Installaz.", "Garanzia", "Scade il",
        "Stato", "Fornitore"
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

        # Barra filtri
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Filtro:"))

        self.btn_tutte       = QPushButton("Tutte")
        self.btn_scadute     = QPushButton("Scadute")
        self.btn_in_scadenza = QPushButton(f"In scadenza (<{SOGLIA_SCADENZA_GIORNI}gg)")
        self.btn_valide      = QPushButton("Valide")
        self.btn_aggiorna    = QPushButton("⟳ Aggiorna")

        for btn in [self.btn_tutte, self.btn_scadute, self.btn_in_scadenza, self.btn_valide]:
            btn.setCheckable(True)
            bar.addWidget(btn)
        self.btn_tutte.setChecked(True)

        bar.addStretch()
        bar.addWidget(self.btn_aggiorna)
        layout.addLayout(bar)

        # Tabella
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        # Legenda
        legenda = QLabel(
            "  Garanzia:  "
            "<span style='background:#ffaaaa;padding:1px 6px'>Scaduta</span>  "
            "<span style='background:#ffdc82;padding:1px 6px'>In scadenza (&lt;90 gg)</span>"
        )
        legenda.setTextFormat(Qt.RichText)
        layout.addWidget(legenda)

        # Segnali
        self.btn_tutte.clicked.connect(lambda: self._set_filter("tutte"))
        self.btn_scadute.clicked.connect(lambda: self._set_filter("scadute"))
        self.btn_in_scadenza.clicked.connect(lambda: self._set_filter("in_scadenza"))
        self.btn_valide.clicked.connect(lambda: self._set_filter("valide"))
        self.btn_aggiorna.clicked.connect(self.load_data)

    # ------------------------------------------------------------------
    # Dati
    # ------------------------------------------------------------------

    def load_data(self):
        self._rows = []
        today = QDate.currentDate()

        q = QSqlQuery(self.db)
        ok = q.exec("""
            SELECT
                COALESCE(e.nome_edificio, '—'),
                COALESCE(p.nome_piano,    '—'),
                COALESCE(l.nome_locale,   '—'),
                COALESCE(po.nome_porta,   '—'),
                t.nome_tipo,
                d.modello,
                COALESCE(d.matricola, ''),
                COALESCE(d.data_installazione, ''),
                d.garanzia_mesi,
                COALESCE(d.stato, ''),
                COALESCE(d.fornitore, '')
            FROM Inventario_Dispositivi d
            JOIN Tipi_Dispositivi t ON d.tipo_id = t.tipo_id
            LEFT JOIN Porte   po ON d.porta_id   = po.porta_id
            LEFT JOIN Locali  l  ON COALESCE(po.locale_id, d.locale_id) = l.locale_id
            LEFT JOIN Piani   p  ON l.piano_id   = p.piano_id
            LEFT JOIN Edifici e  ON p.edificio_id = e.edificio_id
            WHERE d.garanzia_mesi IS NOT NULL AND d.garanzia_mesi > 0
            ORDER BY e.nome_edificio, p.nome_piano, l.nome_locale, po.nome_porta, d.modello
        """)
        if not ok:
            return

        while q.next():
            data_inst_str = q.value(7)
            garanzia_mesi = q.value(8)

            data_inst_fmt = ""
            scadenza_fmt  = "—"
            color  = None
            status = "valida"

            if data_inst_str:
                data_inst = QDate.fromString(data_inst_str, "yyyy-MM-dd")
                data_inst_fmt = data_inst.toString("dd/MM/yyyy")
                if garanzia_mesi:
                    scadenza = data_inst.addMonths(int(garanzia_mesi))
                    scadenza_fmt = scadenza.toString("dd/MM/yyyy")
                    days_left = today.daysTo(scadenza)
                    if days_left < 0:
                        color  = COLOR_SCADUTA
                        status = "scaduta"
                    elif days_left <= SOGLIA_SCADENZA_GIORNI:
                        color  = COLOR_IN_SCADENZA
                        status = "in_scadenza"

            garanzia_txt = f"{int(garanzia_mesi)} mesi" if garanzia_mesi else "—"

            self._rows.append({
                "cells": [
                    q.value(0), q.value(1), q.value(2), q.value(3),
                    q.value(4), q.value(5), q.value(6),
                    data_inst_fmt, garanzia_txt, scadenza_fmt,
                    q.value(9), q.value(10)
                ],
                "color":  color,
                "status": status,
            })

        self._render(self._current_filter())

    # ------------------------------------------------------------------
    # Filtro e render
    # ------------------------------------------------------------------

    def _current_filter(self) -> str:
        if self.btn_scadute.isChecked():     return "scadute"
        if self.btn_in_scadenza.isChecked(): return "in_scadenza"
        if self.btn_valide.isChecked():      return "valide"
        return "tutte"

    def _set_filter(self, name: str):
        for btn, n in [
            (self.btn_tutte,       "tutte"),
            (self.btn_scadute,     "scadute"),
            (self.btn_in_scadenza, "in_scadenza"),
            (self.btn_valide,      "valide"),
        ]:
            btn.setChecked(n == name)
        self._render(name)

    def _render(self, filter_name: str):
        self.table.setRowCount(0)
        for row_data in self._rows:
            if filter_name != "tutte" and row_data["status"] != filter_name:
                continue
            row = self.table.rowCount()
            self.table.insertRow(row)
            for col, text in enumerate(row_data["cells"]):
                item = QTableWidgetItem(str(text))
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                if row_data["color"]:
                    item.setBackground(row_data["color"])
                self.table.setItem(row, col, item)
