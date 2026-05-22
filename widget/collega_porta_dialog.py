# This Python file uses the following encoding: utf-8

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QComboBox, QSpinBox, QDateEdit, QTextEdit,
    QPushButton, QDialogButtonBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMessageBox
)
from PySide6.QtSql import QSqlDatabase, QSqlQuery
from PySide6.QtCore import Qt, QDate


class CollegaPortaDialog(QDialog):
    """
    Dialog bidirezionale per collegare un materiale fisico a una porta.

    Modalita' A — dalla porta  (porta_id noto, materiale_id=None):
        Mostra tabella materiali "In magazzino"; l'utente ne sceglie uno.

    Modalita' B — dal magazzino (materiale_id noto, porta_id=None):
        Mostra un combo con tutte le porte; l'utente sceglie la destinazione.

    In entrambi i casi al salvataggio:
      - INSERT INTO Inventario_Dispositivi ...
      - UPDATE Materiali SET stato='Installato' WHERE materiale_id=?
    """

    COLS_MAG = ["Articolo", "Tipo", "Marca/Modello", "Matricola/SN", "Garanzia"]

    def __init__(self, db: QSqlDatabase,
                 porta_id: int | None = None,
                 materiale_id: int | None = None,
                 nome_porta: str = "",
                 parent=None):
        super().__init__(parent)

        if porta_id is None and materiale_id is None:
            raise ValueError("Specificare porta_id oppure materiale_id.")

        self.db = db
        self.porta_id = porta_id
        self.materiale_id = materiale_id
        self.nome_porta = nome_porta

        self._mag_rows: list[dict] = []
        self._sel_materiale: dict | None = None

        if porta_id is not None:
            self.setWindowTitle(f"Collega materiale — {nome_porta or f'Porta {porta_id}'}")
        else:
            self.setWindowTitle("Collega materiale a porta")

        self.setMinimumSize(700, 500)
        self._setup_ui()
        self._load_centraline()

        if porta_id is not None:
            # Modalita' A: mostra magazzino disponibile
            self._load_magazzino()
        else:
            # Modalita' B: carica info materiale e porte disponibili
            self._load_materiale_info()
            self._load_porte()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # --- Sezione selezione (dipende dalla modalita') ---
        if self.porta_id is not None:
            # A: tabella materiali in magazzino
            box_sel = QGroupBox("1.  Seleziona materiale dal magazzino")
            v1 = QVBoxLayout(box_sel)
            self.mag_table = QTableWidget()
            self.mag_table.setColumnCount(len(self.COLS_MAG))
            self.mag_table.setHorizontalHeaderLabels(self.COLS_MAG)
            self.mag_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self.mag_table.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.mag_table.setSelectionMode(QAbstractItemView.SingleSelection)
            self.mag_table.verticalHeader().setVisible(False)
            self.mag_table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeToContents
            )
            self.mag_table.horizontalHeader().setStretchLastSection(True)
            self.mag_table.itemSelectionChanged.connect(self._on_mag_selected)
            v1.addWidget(self.mag_table)
            layout.addWidget(box_sel)
        else:
            # B: label informativa sul materiale + combo porte
            self.info_label = QLabel()
            self.info_label.setStyleSheet(
                "padding:6px; background:#eef2ff; border-radius:3px;"
            )
            layout.addWidget(self.info_label)

        # --- Sezione dettagli installazione ---
        step_num = "2." if self.porta_id is not None else "1."
        box2 = QGroupBox(f"{step_num}  Dettagli installazione")
        form = QFormLayout(box2)

        if self.porta_id is None:
            # Combo scelta porta
            self.porta_combo = QComboBox()
            self.porta_combo.setMinimumWidth(300)
            form.addRow("Porta destinazione *:", self.porta_combo)

        self.data_edit = QDateEdit(QDate.currentDate())
        self.data_edit.setCalendarPopup(True)
        self.data_edit.setDisplayFormat("dd/MM/yyyy")

        self.centralina_combo = QComboBox()

        self.stato_combo = QComboBox()
        self.stato_combo.addItems(["Operativo", "In Manutenzione", "Guasto"])

        self.note_edit = QTextEdit()
        self.note_edit.setMaximumHeight(55)
        self.note_edit.setPlaceholderText("Note specifiche di questa installazione…")

        form.addRow("Data installazione:", self.data_edit)
        form.addRow("Centralina rif.:",    self.centralina_combo)
        form.addRow("Stato:",              self.stato_combo)
        form.addRow("Note:",               self.note_edit)
        layout.addWidget(box2)

        # Bottoni
        btn_box = QDialogButtonBox()
        self.btn_collega = QPushButton("Collega")
        self.btn_collega.setEnabled(self.materiale_id is not None)
        btn_box.addButton(self.btn_collega, QDialogButtonBox.AcceptRole)
        btn_box.addButton(QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self._save)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    # ------------------------------------------------------------------
    # Caricamento dati
    # ------------------------------------------------------------------

    def _load_magazzino(self):
        """Modalita' A — carica materiali In magazzino."""
        self._mag_rows = []
        q = QSqlQuery(self.db)
        q.exec("""
            SELECT m.materiale_id,
                   c.nome_articolo,
                   t.nome_tipo,
                   COALESCE(c.marca,'') || ' ' || COALESCE(c.modello,'') AS mm,
                   COALESCE(m.matricola,''),
                   m.garanzia_mesi,
                   c.articolo_id,
                   c.tipo_id
            FROM Materiali m
            JOIN Catalogo_Materiali c ON m.articolo_id = c.articolo_id
            JOIN Tipi_Dispositivi t   ON c.tipo_id = t.tipo_id
            WHERE m.stato = 'In magazzino'
            ORDER BY t.nome_tipo, c.nome_articolo
        """)
        while q.next():
            garanzia = q.value(5)
            self._mag_rows.append({
                "id":         q.value(0),
                "articolo_id":q.value(6),
                "tipo_id":    q.value(7),
                "nome":       q.value(1),
                "tipo":       q.value(2),
                "mm":         q.value(3).strip(),
                "matricola":  q.value(4),
                "garanzia":   garanzia,
                "gar_txt":    f"{int(garanzia)} mesi" if garanzia else "—",
            })
        self._render_magazzino(self._mag_rows)

    def _render_magazzino(self, rows: list[dict]):
        self.mag_table.setRowCount(0)
        for r in rows:
            row = self.mag_table.rowCount()
            self.mag_table.insertRow(row)
            for col, val in enumerate([r["nome"], r["tipo"], r["mm"],
                                        r["matricola"], r["gar_txt"]]):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                if col == 0:
                    item.setData(Qt.UserRole, r["id"])
                self.mag_table.setItem(row, col, item)

    def _on_mag_selected(self):
        items = self.mag_table.selectedItems()
        if not items:
            self._sel_materiale = None
            self.btn_collega.setEnabled(False)
            return
        mid = self.mag_table.item(self.mag_table.currentRow(), 0).data(Qt.UserRole)
        for r in self._mag_rows:
            if r["id"] == mid:
                self._sel_materiale = r
                break
        self.btn_collega.setEnabled(self._sel_materiale is not None)

    def _load_materiale_info(self):
        """Modalita' B — mostra info materiale fisso."""
        q = QSqlQuery(self.db)
        q.prepare("""
            SELECT c.nome_articolo, t.nome_tipo,
                   COALESCE(c.marca,''), COALESCE(c.modello,''),
                   COALESCE(m.matricola,''),
                   m.garanzia_mesi,
                   c.articolo_id, c.tipo_id
            FROM Materiali m
            JOIN Catalogo_Materiali c ON m.articolo_id = c.articolo_id
            JOIN Tipi_Dispositivi t   ON c.tipo_id = t.tipo_id
            WHERE m.materiale_id = ?
        """)
        q.addBindValue(self.materiale_id)
        if q.exec() and q.next():
            self._sel_materiale = {
                "id":          self.materiale_id,
                "articolo_id": q.value(6),
                "tipo_id":     q.value(7),
                "nome":        q.value(0),
                "tipo":        q.value(1),
                "mm":          f"{q.value(2)} {q.value(3)}".strip(),
                "matricola":   q.value(4),
                "garanzia":    q.value(5),
            }
            garanzia = q.value(5)
            gar_txt = f"{int(garanzia)} mesi" if garanzia else "—"
            self.info_label.setText(
                f"<b>{q.value(0)}</b>  |  {q.value(1)}"
                f"  |  {q.value(2)} {q.value(3)}"
                f"  |  SN: {q.value(4) or '—'}"
                f"  |  Garanzia: {gar_txt}"
            )

    def _load_porte(self):
        """Modalita' B — popola combo porte."""
        self.porta_combo.clear()
        self.porta_combo.addItem("— Seleziona porta —", None)
        q = QSqlQuery(self.db)
        q.exec("""
            SELECT p.porta_id,
                   p.nome_porta || '  (' ||
                   COALESCE(e.nome_edificio,'') || ' > ' ||
                   COALESCE(pi.nome_piano,'') || ' > ' ||
                   COALESCE(l.nome_locale,'') || ')' AS label
            FROM Porte p
            LEFT JOIN Locali l  ON p.locale_id  = l.locale_id
            LEFT JOIN Piani  pi ON l.piano_id    = pi.piano_id
            LEFT JOIN Edifici e ON pi.edificio_id = e.edificio_id
            ORDER BY e.nome_edificio, pi.nome_piano, l.nome_locale, p.nome_porta
        """)
        while q.next():
            self.porta_combo.addItem(q.value(1), q.value(0))

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
    # Salvataggio
    # ------------------------------------------------------------------

    def _save(self):
        # Determina porta_id finale
        if self.porta_id is not None:
            final_porta_id = self.porta_id
        else:
            final_porta_id = self.porta_combo.currentData()
            if final_porta_id is None:
                QMessageBox.warning(self, "Porta mancante",
                                    "Seleziona una porta di destinazione.")
                return

        # Determina materiale scelto
        if self._sel_materiale is None:
            QMessageBox.warning(self, "Materiale mancante",
                                "Seleziona un materiale dal magazzino.")
            return

        mat = self._sel_materiale
        data_inst = self.data_edit.date().toString("yyyy-MM-dd")

        # 1. Inserisci installazione
        q = QSqlQuery(self.db)
        q.prepare("""
            INSERT INTO Inventario_Dispositivi
                (materiale_id, articolo_id, modello, matricola, fornitore,
                 tipo_id, data_installazione, garanzia_mesi, stato,
                 descrizione, parent_dispositivo_id, porta_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """)
        q.addBindValue(mat["id"])
        q.addBindValue(mat["articolo_id"])
        # modello: preferisce campo modello dall'articolo, fallback nome
        q.addBindValue(mat["mm"] or mat["nome"])
        q.addBindValue(mat["matricola"] or None)
        q.addBindValue(None)                                  # fornitore (dal materiale, non qui)
        q.addBindValue(mat["tipo_id"])
        q.addBindValue(data_inst)
        q.addBindValue(int(mat["garanzia"]) if mat["garanzia"] else None)
        q.addBindValue(self.stato_combo.currentText())
        q.addBindValue(self.note_edit.toPlainText().strip() or None)
        q.addBindValue(self.centralina_combo.currentData())
        q.addBindValue(final_porta_id)

        if not q.exec():
            QMessageBox.critical(self, "Errore DB", q.lastError().text())
            return

        # 2. Aggiorna stato materiale -> Installato
        q2 = QSqlQuery(self.db)
        q2.prepare("UPDATE Materiali SET stato='Installato' WHERE materiale_id=?")
        q2.addBindValue(mat["id"])
        if not q2.exec():
            QMessageBox.critical(self, "Errore DB", q2.lastError().text())
            return

        self.accept()
