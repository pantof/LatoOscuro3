# This Python file uses the following encoding: utf-8

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QComboBox, QSpinBox, QDateEdit, QTextEdit,
    QPushButton, QDialogButtonBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QSplitter, QMessageBox
)
from PySide6.QtSql import QSqlDatabase, QSqlQuery
from PySide6.QtCore import Qt, QDate


class InstallazionDialog(QDialog):
    """
    Dialog a due passi:
      1. Seleziona un articolo dal catalogo (con ricerca)
      2. Inserisci i dettagli dell'installazione (SN, data, garanzia override, ecc.)
    """

    COLS_CAT = ["Nome Articolo", "Tipo", "Marca", "Modello", "Garanzia std.", "Fornitore"]

    def __init__(self, db: QSqlDatabase, porta_id: int, nome_porta: str, parent=None):
        super().__init__(parent)
        self.db = db
        self.porta_id = porta_id
        self.nome_porta = nome_porta
        self._catalog_rows: list[dict] = []
        self._selected: dict | None = None

        self.setWindowTitle(f"Installa materiale — {nome_porta}")
        self.setMinimumSize(780, 580)
        self._setup_ui()
        self._load_catalog()
        self._load_centraline()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Info porta
        porta_label = QLabel(f"<b>Porta di destinazione:</b>  {self.nome_porta}")
        porta_label.setStyleSheet("padding: 4px; background: #eef2ff; border-radius: 3px;")
        layout.addWidget(porta_label)

        splitter = QSplitter(Qt.Vertical)

        # ---- PASSO 1: Catalogo ----
        box1 = QGroupBox("1.  Seleziona articolo dal catalogo")
        v1 = QVBoxLayout(box1)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Cerca:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Filtra per nome, tipo, marca, modello…")
        self.search_edit.textChanged.connect(self._filter_catalog)
        search_row.addWidget(self.search_edit)
        v1.addLayout(search_row)

        self.cat_table = QTableWidget()
        self.cat_table.setColumnCount(len(self.COLS_CAT))
        self.cat_table.setHorizontalHeaderLabels(self.COLS_CAT)
        self.cat_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.cat_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.cat_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.cat_table.verticalHeader().setVisible(False)
        self.cat_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.cat_table.horizontalHeader().setStretchLastSection(True)
        self.cat_table.itemSelectionChanged.connect(self._on_catalog_selected)
        v1.addWidget(self.cat_table)

        # ---- PASSO 2: Dettagli installazione ----
        box2 = QGroupBox("2.  Dettagli installazione")
        form = QFormLayout(box2)

        self.articolo_label = QLabel("<i>— nessun articolo selezionato —</i>")
        self.articolo_label.setStyleSheet("color: #888;")

        self.matricola_edit = QLineEdit()
        self.matricola_edit.setPlaceholderText("Numero di serie / SN")

        self.data_edit = QDateEdit(QDate.currentDate())
        self.data_edit.setCalendarPopup(True)
        self.data_edit.setDisplayFormat("dd/MM/yyyy")

        self.garanzia_spin = QSpinBox()
        self.garanzia_spin.setRange(0, 120)
        self.garanzia_spin.setSuffix(" mesi")
        self.garanzia_spin.setSpecialValueText("Nessuna garanzia")

        self.centralina_combo = QComboBox()

        self.stato_combo = QComboBox()
        self.stato_combo.addItems(["Operativo", "In Manutenzione", "Guasto", "Dismesso"])

        self.note_edit = QTextEdit()
        self.note_edit.setMaximumHeight(55)
        self.note_edit.setPlaceholderText("Note specifiche di questa installazione…")

        form.addRow("Articolo:",            self.articolo_label)
        form.addRow("Matricola / SN:",      self.matricola_edit)
        form.addRow("Data installazione:",  self.data_edit)
        form.addRow("Garanzia (override):", self.garanzia_spin)
        form.addRow("Centralina rif.:",     self.centralina_combo)
        form.addRow("Stato:",               self.stato_combo)
        form.addRow("Note:",                self.note_edit)

        splitter.addWidget(box1)
        splitter.addWidget(box2)
        splitter.setSizes([300, 240])
        layout.addWidget(splitter)

        # Buttons
        btn_box = QDialogButtonBox()
        self.btn_installa = QPushButton("✓  Installa")
        self.btn_installa.setEnabled(False)
        btn_box.addButton(self.btn_installa, QDialogButtonBox.AcceptRole)
        btn_box.addButton(QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self._save)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    # ------------------------------------------------------------------
    # Caricamento dati
    # ------------------------------------------------------------------

    def _load_catalog(self):
        self._catalog_rows = []
        q = QSqlQuery(self.db)
        q.exec("""
            SELECT c.articolo_id, c.nome_articolo, t.nome_tipo,
                   COALESCE(c.marca,''), COALESCE(c.modello,''),
                   c.garanzia_standard_mesi, COALESCE(c.fornitore_preferito,''),
                   c.tipo_id
            FROM Catalogo_Materiali c
            JOIN Tipi_Dispositivi t ON c.tipo_id = t.tipo_id
            ORDER BY t.nome_tipo, c.nome_articolo
        """)
        while q.next():
            self._catalog_rows.append({
                "id":       q.value(0),
                "nome":     q.value(1),
                "tipo":     q.value(2),
                "marca":    q.value(3),
                "modello":  q.value(4),
                "garanzia": q.value(5),
                "fornitore":q.value(6),
                "tipo_id":  q.value(7),
            })
        self._render_catalog(self._catalog_rows)

    def _render_catalog(self, rows: list[dict]):
        self.cat_table.setRowCount(0)
        for r in rows:
            row = self.cat_table.rowCount()
            self.cat_table.insertRow(row)
            gar = f"{int(r['garanzia'])} mesi" if r["garanzia"] else "—"
            for col, val in enumerate([r["nome"], r["tipo"], r["marca"], r["modello"], gar, r["fornitore"]]):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                if col == 0:
                    item.setData(Qt.UserRole, r["id"])
                self.cat_table.setItem(row, col, item)

    def _filter_catalog(self, text: str):
        if not text:
            self._render_catalog(self._catalog_rows)
            return
        t = text.lower()
        filtered = [r for r in self._catalog_rows
                    if t in r["nome"].lower() or t in r["tipo"].lower()
                    or t in r["marca"].lower() or t in r["modello"].lower()]
        self._render_catalog(filtered)

    def _load_centraline(self):
        self.centralina_combo.clear()
        self.centralina_combo.addItem("— Nessuna —", None)
        q = QSqlQuery(self.db)
        if q.exec("""
            SELECT d.dispositivo_id,
                   d.modello || '  (SN: ' || COALESCE(d.matricola,'—') || ')'
            FROM Inventario_Dispositivi d
            JOIN Tipi_Dispositivi t ON d.tipo_id = t.tipo_id
            WHERE LOWER(t.nome_tipo) = 'centralina'
            ORDER BY d.modello
        """):
            while q.next():
                self.centralina_combo.addItem(q.value(1), q.value(0))

    # ------------------------------------------------------------------
    # Interazione
    # ------------------------------------------------------------------

    def _on_catalog_selected(self):
        items = self.cat_table.selectedItems()
        if not items:
            self._selected = None
            self.articolo_label.setText("<i>— nessun articolo selezionato —</i>")
            self.articolo_label.setStyleSheet("color: #888;")
            self.btn_installa.setEnabled(False)
            return

        row = self.cat_table.currentRow()
        aid = self.cat_table.item(row, 0).data(Qt.UserRole)

        # Cerca il record completo nella cache
        for r in self._catalog_rows:
            if r["id"] == aid:
                self._selected = r
                break
        else:
            return

        self.articolo_label.setText(
            f"<b>{self._selected['nome']}</b>"
            f"  —  {self._selected['tipo']}"
            f"  |  {self._selected['marca']} {self._selected['modello']}"
        )
        self.articolo_label.setStyleSheet("color: #1a1a2e; font-size: 11px;")

        # Pre-compila garanzia dal catalogo (override disponibile)
        g = self._selected["garanzia"]
        self.garanzia_spin.setValue(int(g) if g else 0)

        self.btn_installa.setEnabled(True)

    # ------------------------------------------------------------------
    # Salvataggio
    # ------------------------------------------------------------------

    def _save(self):
        if self._selected is None:
            QMessageBox.warning(self, "Selezione mancante",
                                "Seleziona un articolo dal catalogo prima di procedere.")
            return

        garanzia = self.garanzia_spin.value() if self.garanzia_spin.value() > 0 else None

        q = QSqlQuery(self.db)
        q.prepare("""
            INSERT INTO Inventario_Dispositivi
                (articolo_id, modello, tipo_id, fornitore, matricola,
                 data_installazione, garanzia_mesi, stato, descrizione,
                 parent_dispositivo_id, porta_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """)
        q.addBindValue(self._selected["id"])
        q.addBindValue(self._selected["modello"] or self._selected["nome"])
        q.addBindValue(self._selected["tipo_id"])
        q.addBindValue(self._selected["fornitore"] or None)
        q.addBindValue(self.matricola_edit.text().strip() or None)
        q.addBindValue(self.data_edit.date().toString("yyyy-MM-dd"))
        q.addBindValue(garanzia)
        q.addBindValue(self.stato_combo.currentText())
        q.addBindValue(self.note_edit.toPlainText().strip() or None)
        q.addBindValue(self.centralina_combo.currentData())
        q.addBindValue(self.porta_id)

        if q.exec():
            self.accept()
        else:
            QMessageBox.critical(self, "Errore DB", q.lastError().text())
