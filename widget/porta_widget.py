# This Python file uses the following encoding: utf-8

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QTextEdit, QLabel,
    QTableWidget, QTableWidgetItem, QListWidget,
    QPushButton, QMessageBox, QSplitter, QHeaderView, QAbstractItemView
)
from PySide6.QtSql import QSqlDatabase, QSqlQuery, QSqlError
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor

from widget.dispositivo_dialog import DispositivoDialog
from widget.collega_porta_dialog import CollegaPortaDialog

# Soglia (giorni) entro cui la garanzia è considerata "in scadenza"
SOGLIA_SCADENZA_GIORNI = 90

# Colori riga garanzia
COLOR_SCADUTA   = QColor(255, 170, 170)   # rosso chiaro
COLOR_IN_SCADENZA = QColor(255, 220, 130) # giallo/arancio


class PortaDetailWidget(QWidget):

    COLS_DEV = ["Tipo", "Modello", "Matricola/SN", "Centralina", "Installato il", "Garanzia", "Scade il", "Stato", "Fornitore", ""]

    def __init__(self, db: QSqlDatabase, parent=None):
        super().__init__(parent)
        if not db or not db.isOpen():
            QMessageBox.critical(self, "Errore", "Connessione al database non valida.")
            return
        self.db = db
        self.current_porta_id = None
        self._setup_ui()
        self._populate_combos()
        self.clear_form()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)

        # Intestazione porta
        form = QFormLayout()
        self.nome_edit = QLineEdit()
        self.locale_combo = QComboBox()
        self.posizione_edit = QLineEdit()
        self.posizione_edit.setReadOnly(True)
        self.posizione_edit.setStyleSheet("background-color: #f0f0f0;")
        self.note_edit = QTextEdit()
        self.note_edit.setMaximumHeight(60)

        form.addRow("Nome Porta:", self.nome_edit)
        form.addRow("Locale:", self.locale_combo)
        form.addRow("Posizione:", self.posizione_edit)
        main_layout.addLayout(form)
        main_layout.addWidget(QLabel("Note:"))
        main_layout.addWidget(self.note_edit)

        self.save_button = QPushButton("Salva Modifiche Porta")
        self.save_button.clicked.connect(self._save_porta)
        main_layout.addWidget(self.save_button)

        # Splitter verticale: dispositivi | interconnessioni
        splitter = QSplitter(Qt.Vertical)

        # --- Sezione Dispositivi ---
        dev_widget = QWidget()
        dev_layout = QVBoxLayout(dev_widget)
        dev_layout.setContentsMargins(0, 0, 0, 0)
        dev_layout.addWidget(QLabel("Dispositivi installati sulla porta:"))

        self.dev_table = QTableWidget()
        self.dev_table.setColumnCount(len(self.COLS_DEV))
        self.dev_table.setHorizontalHeaderLabels(self.COLS_DEV)
        self.dev_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.dev_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.dev_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.dev_table.verticalHeader().setVisible(False)
        self.dev_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.dev_table.horizontalHeader().setStretchLastSection(True)
        dev_layout.addWidget(self.dev_table)

        btn_row = QHBoxLayout()
        self.btn_installa = QPushButton("Collega da Magazzino")
        self.btn_aggiungi = QPushButton("+ Aggiungi Manuale")
        self.btn_modifica = QPushButton("Modifica")
        self.btn_rimuovi  = QPushButton("Rimuovi")
        self.btn_installa.setToolTip("Collega un materiale fisico presente in magazzino a questa porta")
        self.btn_aggiungi.setToolTip("Aggiungi un dispositivo manuale senza passare dal magazzino")
        self.btn_installa.clicked.connect(self._collega_da_magazzino)
        self.btn_aggiungi.clicked.connect(self._aggiungi_dispositivo)
        self.btn_modifica.clicked.connect(self._modifica_dispositivo)
        self.btn_rimuovi.clicked.connect(self._rimuovi_dispositivo)
        btn_row.addWidget(self.btn_installa)
        btn_row.addWidget(self.btn_aggiungi)
        btn_row.addWidget(self.btn_modifica)
        btn_row.addWidget(self.btn_rimuovi)
        btn_row.addStretch()
        dev_layout.addLayout(btn_row)

        # Legenda colori garanzia
        legenda = QLabel(
            "  Garanzia:  "
            "<span style='background:#ffaaaa;padding:1px 6px'>Scaduta</span>  "
            "<span style='background:#ffdc82;padding:1px 6px'>In scadenza (&lt;90 gg)</span>"
        )
        legenda.setTextFormat(Qt.RichText)
        dev_layout.addWidget(legenda)

        # --- Sezione Interconnessioni ---
        conn_widget = QWidget()
        conn_layout = QVBoxLayout(conn_widget)
        conn_layout.setContentsMargins(0, 0, 0, 0)
        conn_layout.addWidget(QLabel("Interconnessioni (via dispositivi):"))
        self.connessioni_list = QListWidget()
        conn_layout.addWidget(self.connessioni_list)

        splitter.addWidget(dev_widget)
        splitter.addWidget(conn_widget)
        splitter.setSizes([300, 120])
        main_layout.addWidget(splitter)

        self.locale_combo.currentIndexChanged.connect(self._update_posizione)

    # ------------------------------------------------------------------
    # Caricamento dati
    # ------------------------------------------------------------------

    def _populate_combos(self):
        self.locale_combo.blockSignals(True)
        self.locale_combo.clear()
        self.locale_combo.addItem("— Nessuno —", None)
        query = QSqlQuery(self.db)
        if query.exec("SELECT locale_id, nome_locale FROM Locali ORDER BY nome_locale"):
            while query.next():
                self.locale_combo.addItem(query.value(1), query.value(0))
        self.locale_combo.blockSignals(False)

    def clear_form(self):
        self.current_porta_id = None
        self.nome_edit.clear()
        self.note_edit.clear()
        self.locale_combo.blockSignals(True)
        self.locale_combo.setCurrentIndex(0)
        self.locale_combo.blockSignals(False)
        self.posizione_edit.clear()
        self.dev_table.setRowCount(0)
        self.connessioni_list.clear()
        self.setEnabled(False)

    def load_porta_data(self, porta_id: int):
        self.clear_form()
        self.current_porta_id = porta_id

        q = QSqlQuery(self.db)
        q.prepare("SELECT nome_porta, locale_id, note FROM Porte WHERE porta_id = ?")
        q.addBindValue(porta_id)
        if not (q.exec() and q.next()):
            self._db_error(q.lastError())
            return

        self.nome_edit.setText(q.value(0) or "")
        self.note_edit.setPlainText(q.value(2) or "")

        locale_id = q.value(1)
        self.locale_combo.blockSignals(True)
        idx = self.locale_combo.findData(locale_id)
        self.locale_combo.setCurrentIndex(idx if idx != -1 else 0)
        self.locale_combo.blockSignals(False)
        self._update_posizione()

        self._load_dispositivi(porta_id)
        self._load_interconnessioni(porta_id)
        self.setEnabled(True)

    def _load_dispositivi(self, porta_id: int):
        self.dev_table.setRowCount(0)
        q = QSqlQuery(self.db)
        q.prepare("""
            SELECT d.dispositivo_id, t.nome_tipo, d.modello, d.matricola,
                   COALESCE(c.modello, '—') AS centralina,
                   d.data_installazione, d.garanzia_mesi, d.stato, d.fornitore,
                   CASE WHEN d.articolo_id IS NOT NULL THEN 1 ELSE 0 END AS da_catalogo
            FROM Inventario_Dispositivi d
            JOIN Tipi_Dispositivi t ON d.tipo_id = t.tipo_id
            LEFT JOIN Inventario_Dispositivi c ON d.parent_dispositivo_id = c.dispositivo_id
            WHERE d.porta_id = ?
            ORDER BY t.nome_tipo, d.modello
        """)
        q.addBindValue(porta_id)
        if not q.exec():
            self._db_error(q.lastError())
            return

        today = QDate.currentDate()
        while q.next():
            dispositivo_id  = q.value(0)
            tipo            = q.value(1) or ""
            modello         = q.value(2) or ""
            matricola       = q.value(3) or ""
            centralina      = q.value(4) or "—"
            data_inst_str   = q.value(5) or ""
            garanzia_mesi   = q.value(6)
            stato           = q.value(7) or ""
            fornitore       = q.value(8) or ""
            da_catalogo     = bool(q.value(9))

            # Data installazione formattata
            if data_inst_str:
                data_inst = QDate.fromString(data_inst_str, "yyyy-MM-dd")
                data_inst_fmt = data_inst.toString("dd/MM/yyyy")
            else:
                data_inst = None
                data_inst_fmt = ""

            # Calcolo scadenza e colore
            scadenza_fmt = "—"
            row_color = None
            if data_inst and garanzia_mesi:
                scadenza = data_inst.addMonths(int(garanzia_mesi))
                scadenza_fmt = scadenza.toString("dd/MM/yyyy")
                days_left = today.daysTo(scadenza)
                if days_left < 0:
                    row_color = COLOR_SCADUTA
                elif days_left <= SOGLIA_SCADENZA_GIORNI:
                    row_color = COLOR_IN_SCADENZA

            garanzia_txt = f"{int(garanzia_mesi)} mesi" if garanzia_mesi else "—"

            badge = "📦 catalogo" if da_catalogo else "✏ manuale"
            values = [tipo, modello, matricola, centralina, data_inst_fmt,
                      garanzia_txt, scadenza_fmt, stato, fornitore, badge]

            row = self.dev_table.rowCount()
            self.dev_table.insertRow(row)
            for col, text in enumerate(values):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                if col == 0:
                    item.setData(Qt.UserRole, dispositivo_id)
                if row_color:
                    item.setBackground(row_color)
                self.dev_table.setItem(row, col, item)

    def _load_interconnessioni(self, porta_id: int):
        self.connessioni_list.clear()
        q = QSqlQuery(self.db)
        q.prepare("""
            SELECT se.nome_sistema, ic.descrizione_connessione, d.modello, ic.tipo_segnale
            FROM Interconnessioni ic
            JOIN SistemiEsterni se ON ic.sistema_id = se.sistema_id
            JOIN Inventario_Dispositivi d ON ic.dispositivo_id = d.dispositivo_id
            WHERE d.porta_id = ?
            ORDER BY se.nome_sistema
        """)
        q.addBindValue(porta_id)
        if not q.exec():
            self._db_error(q.lastError())
            return
        while q.next():
            segnale = f" [{q.value(3)}]" if q.value(3) else ""
            self.connessioni_list.addItem(
                f"{q.value(0)}{segnale}  ←  {q.value(1)}  (su {q.value(2)})"
            )

    def _update_posizione(self):
        self.posizione_edit.clear()
        locale_id = self.locale_combo.currentData()
        if locale_id is None:
            return
        q = QSqlQuery(self.db)
        q.prepare("""
            SELECT e.nome_edificio, p.nome_piano, l.nome_locale
            FROM Locali l
            JOIN Piani p ON l.piano_id = p.piano_id
            JOIN Edifici e ON p.edificio_id = e.edificio_id
            WHERE l.locale_id = ?
        """)
        q.addBindValue(locale_id)
        if q.exec() and q.next():
            self.posizione_edit.setText(
                f"{q.value(0)}  >  {q.value(1)}  >  {q.value(2)}"
            )
        else:
            self.posizione_edit.setText(self.locale_combo.currentText())

    # ------------------------------------------------------------------
    # Azioni dispositivi
    # ------------------------------------------------------------------

    def _collega_da_magazzino(self):
        if self.current_porta_id is None:
            return
        nome_porta = self.nome_edit.text() or f"Porta {self.current_porta_id}"
        dlg = CollegaPortaDialog(
            self.db,
            porta_id=self.current_porta_id,
            nome_porta=nome_porta,
            parent=self
        )
        if dlg.exec():
            self._load_dispositivi(self.current_porta_id)
            self._load_interconnessioni(self.current_porta_id)

    def _aggiungi_dispositivo(self):
        if self.current_porta_id is None:
            return
        dlg = DispositivoDialog(self.db, self.current_porta_id, parent=self)
        if dlg.exec():
            self._load_dispositivi(self.current_porta_id)
            self._load_interconnessioni(self.current_porta_id)

    def _modifica_dispositivo(self):
        row = self.dev_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Nessuna selezione", "Seleziona prima un dispositivo.")
            return
        dev_id = self.dev_table.item(row, 0).data(Qt.UserRole)
        dlg = DispositivoDialog(self.db, self.current_porta_id, dev_id, parent=self)
        if dlg.exec():
            self._load_dispositivi(self.current_porta_id)

    def _rimuovi_dispositivo(self):
        row = self.dev_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Nessuna selezione", "Seleziona prima un dispositivo.")
            return
        dev_id  = self.dev_table.item(row, 0).data(Qt.UserRole)
        modello = self.dev_table.item(row, 1).text()
        reply = QMessageBox.question(
            self, "Conferma rimozione",
            f"Rimuovere '{modello}'?\nAnche le interconnessioni collegate saranno eliminate.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        q = QSqlQuery(self.db)
        q.prepare("DELETE FROM Inventario_Dispositivi WHERE dispositivo_id = ?")
        q.addBindValue(dev_id)
        if q.exec():
            self._load_dispositivi(self.current_porta_id)
            self._load_interconnessioni(self.current_porta_id)
        else:
            self._db_error(q.lastError())

    # ------------------------------------------------------------------
    # Salvataggio porta
    # ------------------------------------------------------------------

    def _save_porta(self):
        if self.current_porta_id is None:
            return
        q = QSqlQuery(self.db)
        q.prepare("UPDATE Porte SET nome_porta=?, locale_id=?, note=? WHERE porta_id=?")
        q.addBindValue(self.nome_edit.text().strip())
        q.addBindValue(self.locale_combo.currentData())
        q.addBindValue(self.note_edit.toPlainText().strip() or None)
        q.addBindValue(self.current_porta_id)
        if q.exec():
            QMessageBox.information(self, "Salvato", "Dati porta salvati.")
        else:
            self._db_error(q.lastError())

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def _db_error(self, err: QSqlError):
        QMessageBox.critical(self, "Errore Database", err.text())
