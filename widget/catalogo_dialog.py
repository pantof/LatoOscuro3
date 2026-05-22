# This Python file uses the following encoding: utf-8

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QSpinBox, QTextEdit, QDialogButtonBox, QMessageBox
)
from PySide6.QtSql import QSqlDatabase, QSqlQuery


class CatalogoDialog(QDialog):
    """Dialog per aggiungere o modificare un articolo nel catalogo materiali."""

    def __init__(self, db: QSqlDatabase, articolo_id: int = None, parent=None):
        super().__init__(parent)
        self.db = db
        self.articolo_id = articolo_id
        self.setWindowTitle("Modifica Articolo" if articolo_id else "Nuovo Articolo Catalogo")
        self.setMinimumWidth(440)
        self._setup_ui()
        self._load_tipi()
        if articolo_id:
            self._load()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.nome_edit       = QLineEdit()
        self.nome_edit.setPlaceholderText("es. Lettore HID R10")
        self.tipo_combo      = QComboBox()
        self.marca_edit      = QLineEdit()
        self.marca_edit.setPlaceholderText("es. HID Global")
        self.modello_edit    = QLineEdit()
        self.modello_edit.setPlaceholderText("es. R10")
        self.fornitore_edit  = QLineEdit()
        self.garanzia_spin   = QSpinBox()
        self.garanzia_spin.setRange(0, 120)
        self.garanzia_spin.setSuffix(" mesi")
        self.garanzia_spin.setSpecialValueText("Non specificata")
        self.descrizione_edit = QTextEdit()
        self.descrizione_edit.setMaximumHeight(70)
        self.descrizione_edit.setPlaceholderText("Specifiche tecniche, note, ecc.")
        self.note_edit = QTextEdit()
        self.note_edit.setMaximumHeight(50)

        form.addRow("Nome articolo *:", self.nome_edit)
        form.addRow("Tipo *:", self.tipo_combo)
        form.addRow("Marca:", self.marca_edit)
        form.addRow("Modello:", self.modello_edit)
        form.addRow("Fornitore preferito:", self.fornitore_edit)
        form.addRow("Garanzia standard:", self.garanzia_spin)
        form.addRow("Descrizione:", self.descrizione_edit)
        form.addRow("Note:", self.note_edit)
        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("Salva")
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _load_tipi(self):
        self.tipo_combo.clear()
        q = QSqlQuery(self.db)
        if q.exec("SELECT tipo_id, nome_tipo FROM Tipi_Dispositivi ORDER BY nome_tipo"):
            while q.next():
                self.tipo_combo.addItem(q.value(1), q.value(0))

    def _load(self):
        q = QSqlQuery(self.db)
        q.prepare("""
            SELECT nome_articolo, tipo_id, marca, modello, fornitore_preferito,
                   garanzia_standard_mesi, descrizione, note
            FROM Catalogo_Materiali WHERE articolo_id = ?
        """)
        q.addBindValue(self.articolo_id)
        if not (q.exec() and q.next()):
            return
        self.nome_edit.setText(q.value(0) or "")
        idx = self.tipo_combo.findData(q.value(1))
        if idx >= 0:
            self.tipo_combo.setCurrentIndex(idx)
        self.marca_edit.setText(q.value(2) or "")
        self.modello_edit.setText(q.value(3) or "")
        self.fornitore_edit.setText(q.value(4) or "")
        self.garanzia_spin.setValue(int(q.value(5)) if q.value(5) else 0)
        self.descrizione_edit.setPlainText(q.value(6) or "")
        self.note_edit.setPlainText(q.value(7) or "")

    def _save(self):
        nome = self.nome_edit.text().strip()
        if not nome:
            QMessageBox.warning(self, "Campo obbligatorio", "Inserisci il nome dell'articolo.")
            return

        garanzia = self.garanzia_spin.value() if self.garanzia_spin.value() > 0 else None

        q = QSqlQuery(self.db)
        if self.articolo_id is None:
            q.prepare("""
                INSERT INTO Catalogo_Materiali
                    (nome_articolo, tipo_id, marca, modello, fornitore_preferito,
                     garanzia_standard_mesi, descrizione, note)
                VALUES (?,?,?,?,?,?,?,?)
            """)
        else:
            q.prepare("""
                UPDATE Catalogo_Materiali
                SET nome_articolo=?, tipo_id=?, marca=?, modello=?, fornitore_preferito=?,
                    garanzia_standard_mesi=?, descrizione=?, note=?
                WHERE articolo_id=?
            """)

        q.addBindValue(nome)
        q.addBindValue(self.tipo_combo.currentData())
        q.addBindValue(self.marca_edit.text().strip() or None)
        q.addBindValue(self.modello_edit.text().strip() or None)
        q.addBindValue(self.fornitore_edit.text().strip() or None)
        q.addBindValue(garanzia)
        q.addBindValue(self.descrizione_edit.toPlainText().strip() or None)
        q.addBindValue(self.note_edit.toPlainText().strip() or None)
        if self.articolo_id is not None:
            q.addBindValue(self.articolo_id)

        if q.exec():
            self.accept()
        else:
            QMessageBox.critical(self, "Errore DB", q.lastError().text())
