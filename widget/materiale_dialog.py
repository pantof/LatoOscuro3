# This Python file uses the following encoding: utf-8

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QComboBox, QSpinBox, QDateEdit, QTextEdit,
    QPushButton, QDialogButtonBox, QMessageBox
)
from PySide6.QtSql import QSqlDatabase, QSqlQuery
from PySide6.QtCore import Qt, QDate


class MaterialeDialog(QDialog):
    """
    Dialog per registrare/modificare un materiale fisico in magazzino.

    Parametri
    ---------
    db           : connessione Qt SQL
    materiale_id : se None -> nuovo inserimento, altrimenti modifica
    articolo_id  : pre-seleziona un articolo del catalogo (usato quando
                   si apre il dialog dal catalogo)
    """

    def __init__(self, db: QSqlDatabase,
                 materiale_id: int | None = None,
                 articolo_id: int | None = None,
                 parent=None):
        super().__init__(parent)
        self.db = db
        self.materiale_id = materiale_id
        self._preselect_articolo_id = articolo_id

        self.setWindowTitle(
            "Modifica Materiale" if materiale_id else "Nuovo Materiale in Magazzino"
        )
        self.setMinimumWidth(480)
        self._setup_ui()
        self._load_articoli()
        if materiale_id:
            self._load_data()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        box = QGroupBox("Dati materiale fisico")
        form = QFormLayout(box)

        # Articolo di catalogo
        self.articolo_combo = QComboBox()
        self.articolo_combo.setMinimumWidth(300)
        self.articolo_combo.currentIndexChanged.connect(self._on_articolo_changed)

        # Info articolo selezionato (sola lettura)
        self.info_label = QLabel()
        self.info_label.setStyleSheet(
            "color:#555; font-size:11px; padding:2px 0;"
        )

        # Campi fisici
        self.matricola_edit = QLineEdit()
        self.matricola_edit.setPlaceholderText("Numero di serie / SN")

        self.data_acquisto_edit = QDateEdit(QDate.currentDate())
        self.data_acquisto_edit.setCalendarPopup(True)
        self.data_acquisto_edit.setDisplayFormat("dd/MM/yyyy")

        self.fornitore_edit = QLineEdit()
        self.fornitore_edit.setPlaceholderText("Nome fornitore")

        self.fattura_edit = QLineEdit()
        self.fattura_edit.setPlaceholderText("Es. FT-2026-0123")

        self.garanzia_spin = QSpinBox()
        self.garanzia_spin.setRange(0, 120)
        self.garanzia_spin.setSuffix(" mesi")
        self.garanzia_spin.setSpecialValueText("Nessuna garanzia")

        self.stato_combo = QComboBox()
        self.stato_combo.addItems([
            "In magazzino",
            "Installato",
            "In riparazione",
            "Dismesso",
        ])

        self.note_edit = QTextEdit()
        self.note_edit.setMaximumHeight(65)
        self.note_edit.setPlaceholderText("Note aggiuntive…")

        form.addRow("Articolo catalogo *:", self.articolo_combo)
        form.addRow("",                      self.info_label)
        form.addRow("Matricola / SN:",       self.matricola_edit)
        form.addRow("Data acquisto:",        self.data_acquisto_edit)
        form.addRow("Fornitore:",            self.fornitore_edit)
        form.addRow("N. Fattura:",           self.fattura_edit)
        form.addRow("Garanzia (override):",  self.garanzia_spin)
        form.addRow("Stato:",                self.stato_combo)
        form.addRow("Note:",                 self.note_edit)
        layout.addWidget(box)

        # Bottoni
        btn_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        btn_box.accepted.connect(self._save)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    # ------------------------------------------------------------------
    # Caricamento dati
    # ------------------------------------------------------------------

    def _load_articoli(self):
        """Popola il combo con tutti gli articoli del catalogo."""
        self.articolo_combo.blockSignals(True)
        self.articolo_combo.clear()
        self.articolo_combo.addItem("— Seleziona articolo —", None)

        self._articoli: list[dict] = []
        q = QSqlQuery(self.db)
        q.exec("""
            SELECT c.articolo_id, c.nome_articolo,
                   t.nome_tipo,
                   COALESCE(c.marca,''),
                   COALESCE(c.modello,''),
                   c.garanzia_standard_mesi,
                   COALESCE(c.fornitore_preferito,'')
            FROM Catalogo_Materiali c
            JOIN Tipi_Dispositivi t ON c.tipo_id = t.tipo_id
            ORDER BY t.nome_tipo, c.nome_articolo
        """)
        while q.next():
            d = {
                "id":        q.value(0),
                "nome":      q.value(1),
                "tipo":      q.value(2),
                "marca":     q.value(3),
                "modello":   q.value(4),
                "garanzia":  q.value(5),
                "fornitore": q.value(6),
            }
            self._articoli.append(d)
            label = f"{d['nome']}  ({d['tipo']})"
            self.articolo_combo.addItem(label, d["id"])

        self.articolo_combo.blockSignals(False)

        # Pre-selezione eventuale
        if self._preselect_articolo_id is not None:
            idx = self.articolo_combo.findData(self._preselect_articolo_id)
            if idx != -1:
                self.articolo_combo.setCurrentIndex(idx)

    def _on_articolo_changed(self, _index: int):
        aid = self.articolo_combo.currentData()
        if aid is None:
            self.info_label.clear()
            return
        for d in self._articoli:
            if d["id"] == aid:
                parts = [d["marca"], d["modello"]] if (d["marca"] or d["modello"]) else []
                self.info_label.setText(
                    f"{d['tipo']}"
                    + (f"  |  {' '.join(p for p in parts if p)}" if parts else "")
                    + (f"  |  Garanzia std. {int(d['garanzia'])} mesi" if d["garanzia"] else "")
                )
                # Pre-compila garanzia solo se il campo è a 0 (non già modificato)
                if self.garanzia_spin.value() == 0 and d["garanzia"]:
                    self.garanzia_spin.setValue(int(d["garanzia"]))
                # Pre-compila fornitore solo se vuoto
                if not self.fornitore_edit.text() and d["fornitore"]:
                    self.fornitore_edit.setText(d["fornitore"])
                break

    def _load_data(self):
        """Carica i dati di un materiale esistente (modalità modifica)."""
        q = QSqlQuery(self.db)
        q.prepare("""
            SELECT articolo_id, matricola, data_acquisto, fornitore,
                   num_fattura, garanzia_mesi, stato, note
            FROM Materiali
            WHERE materiale_id = ?
        """)
        q.addBindValue(self.materiale_id)
        if not (q.exec() and q.next()):
            QMessageBox.critical(self, "Errore DB", q.lastError().text())
            return

        aid = q.value(0)
        idx = self.articolo_combo.findData(aid)
        self.articolo_combo.setCurrentIndex(idx if idx != -1 else 0)

        self.matricola_edit.setText(q.value(1) or "")

        if q.value(2):
            self.data_acquisto_edit.setDate(
                QDate.fromString(q.value(2), "yyyy-MM-dd")
            )

        self.fornitore_edit.setText(q.value(3) or "")
        self.fattura_edit.setText(q.value(4) or "")
        self.garanzia_spin.setValue(int(q.value(5)) if q.value(5) else 0)

        idx_stato = self.stato_combo.findText(q.value(6) or "In magazzino")
        self.stato_combo.setCurrentIndex(idx_stato if idx_stato != -1 else 0)

        self.note_edit.setPlainText(q.value(7) or "")

    # ------------------------------------------------------------------
    # Salvataggio
    # ------------------------------------------------------------------

    def _save(self):
        aid = self.articolo_combo.currentData()
        if aid is None:
            QMessageBox.warning(self, "Articolo mancante",
                                "Seleziona un articolo dal catalogo.")
            return

        garanzia = self.garanzia_spin.value() if self.garanzia_spin.value() > 0 else None

        q = QSqlQuery(self.db)
        if self.materiale_id is None:
            q.prepare("""
                INSERT INTO Materiali
                    (articolo_id, matricola, data_acquisto, fornitore,
                     num_fattura, garanzia_mesi, stato, note)
                VALUES (?,?,?,?,?,?,?,?)
            """)
        else:
            q.prepare("""
                UPDATE Materiali
                SET articolo_id=?, matricola=?, data_acquisto=?, fornitore=?,
                    num_fattura=?, garanzia_mesi=?, stato=?, note=?
                WHERE materiale_id=?
            """)

        q.addBindValue(aid)
        q.addBindValue(self.matricola_edit.text().strip() or None)
        q.addBindValue(self.data_acquisto_edit.date().toString("yyyy-MM-dd"))
        q.addBindValue(self.fornitore_edit.text().strip() or None)
        q.addBindValue(self.fattura_edit.text().strip() or None)
        q.addBindValue(garanzia)
        q.addBindValue(self.stato_combo.currentText())
        q.addBindValue(self.note_edit.toPlainText().strip() or None)
        if self.materiale_id is not None:
            q.addBindValue(self.materiale_id)

        if q.exec():
            self.accept()
        else:
            QMessageBox.critical(self, "Errore DB", q.lastError().text())
