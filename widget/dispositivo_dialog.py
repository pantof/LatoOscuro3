# This Python file uses the following encoding: utf-8

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QSpinBox, QDateEdit, QTextEdit, QDialogButtonBox, QMessageBox
)
from PySide6.QtSql import QSqlDatabase, QSqlQuery
from PySide6.QtCore import QDate


class DispositivoDialog(QDialog):

    STATI = ["Operativo", "In Manutenzione", "Guasto", "Dismesso"]

    def __init__(self, db: QSqlDatabase, porta_id: int, dispositivo_id: int = None, parent=None):
        super().__init__(parent)
        self.db = db
        self.porta_id = porta_id
        self.dispositivo_id = dispositivo_id

        self.setWindowTitle("Aggiungi Dispositivo" if dispositivo_id is None else "Modifica Dispositivo")
        self.setMinimumWidth(420)

        self._setup_ui()
        self._load_tipi()
        if dispositivo_id is not None:
            self._load_dispositivo()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.tipo_combo = QComboBox()

        self.modello_edit = QLineEdit()
        self.modello_edit.setPlaceholderText("es. Axis A1001")

        self.matricola_edit = QLineEdit()
        self.matricola_edit.setPlaceholderText("Numero di serie / SN")

        self.fornitore_edit = QLineEdit()
        self.fornitore_edit.setPlaceholderText("es. Axis Communications")

        self.data_inst_edit = QDateEdit()
        self.data_inst_edit.setCalendarPopup(True)
        self.data_inst_edit.setDate(QDate.currentDate())
        self.data_inst_edit.setDisplayFormat("dd/MM/yyyy")

        self.garanzia_spin = QSpinBox()
        self.garanzia_spin.setRange(0, 120)
        self.garanzia_spin.setSuffix(" mesi")
        self.garanzia_spin.setSpecialValueText("Nessuna garanzia")

        self.stato_combo = QComboBox()
        self.stato_combo.addItems(self.STATI)

        self.descrizione_edit = QTextEdit()
        self.descrizione_edit.setMaximumHeight(70)
        self.descrizione_edit.setPlaceholderText("Note aggiuntive...")

        form.addRow("Tipo *:", self.tipo_combo)
        form.addRow("Modello *:", self.modello_edit)
        form.addRow("Matricola / SN:", self.matricola_edit)
        form.addRow("Fornitore:", self.fornitore_edit)
        form.addRow("Data installazione:", self.data_inst_edit)
        form.addRow("Garanzia:", self.garanzia_spin)
        form.addRow("Stato:", self.stato_combo)
        form.addRow("Descrizione:", self.descrizione_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Salva")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_tipi(self):
        self.tipo_combo.clear()
        query = QSqlQuery(self.db)
        if query.exec("SELECT tipo_id, nome_tipo FROM Tipi_Dispositivi ORDER BY nome_tipo"):
            while query.next():
                self.tipo_combo.addItem(query.value(1), query.value(0))

    def _load_dispositivo(self):
        query = QSqlQuery(self.db)
        query.prepare("""
            SELECT modello, matricola, fornitore, data_installazione,
                   garanzia_mesi, stato, descrizione, tipo_id
            FROM Inventario_Dispositivi WHERE dispositivo_id = ?
        """)
        query.addBindValue(self.dispositivo_id)
        if not (query.exec() and query.next()):
            return

        self.modello_edit.setText(query.value(0) or "")
        self.matricola_edit.setText(query.value(1) or "")
        self.fornitore_edit.setText(query.value(2) or "")

        data_str = query.value(3)
        if data_str:
            self.data_inst_edit.setDate(QDate.fromString(data_str, "yyyy-MM-dd"))

        garanzia = query.value(4)
        self.garanzia_spin.setValue(int(garanzia) if garanzia else 0)

        stato = query.value(5) or "Operativo"
        idx = self.stato_combo.findText(stato)
        if idx >= 0:
            self.stato_combo.setCurrentIndex(idx)

        self.descrizione_edit.setPlainText(query.value(6) or "")

        tipo_id = query.value(7)
        idx = self.tipo_combo.findData(tipo_id)
        if idx >= 0:
            self.tipo_combo.setCurrentIndex(idx)

    def _save(self):
        if not self.modello_edit.text().strip():
            QMessageBox.warning(self, "Campo obbligatorio", "Inserisci il modello del dispositivo.")
            return

        garanzia = self.garanzia_spin.value() if self.garanzia_spin.value() > 0 else None

        query = QSqlQuery(self.db)
        if self.dispositivo_id is None:
            query.prepare("""
                INSERT INTO Inventario_Dispositivi
                    (modello, matricola, fornitore, data_installazione, garanzia_mesi,
                     stato, descrizione, tipo_id, porta_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """)
        else:
            query.prepare("""
                UPDATE Inventario_Dispositivi
                SET modello=?, matricola=?, fornitore=?, data_installazione=?,
                    garanzia_mesi=?, stato=?, descrizione=?, tipo_id=?
                WHERE dispositivo_id=?
            """)

        query.addBindValue(self.modello_edit.text().strip())
        query.addBindValue(self.matricola_edit.text().strip() or None)
        query.addBindValue(self.fornitore_edit.text().strip() or None)
        query.addBindValue(self.data_inst_edit.date().toString("yyyy-MM-dd"))
        query.addBindValue(garanzia)
        query.addBindValue(self.stato_combo.currentText())
        query.addBindValue(self.descrizione_edit.toPlainText().strip() or None)
        query.addBindValue(self.tipo_combo.currentData())

        if self.dispositivo_id is None:
            query.addBindValue(self.porta_id)
        else:
            query.addBindValue(self.dispositivo_id)

        if query.exec():
            self.accept()
        else:
            QMessageBox.critical(self, "Errore DB", query.lastError().text())
