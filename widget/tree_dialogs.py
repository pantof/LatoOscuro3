# This Python file uses the following encoding: utf-8

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QTextEdit, QDialogButtonBox, QMessageBox
)
from PySide6.QtSql import QSqlDatabase, QSqlQuery


class EdificioDialog(QDialog):
    def __init__(self, db: QSqlDatabase, edificio_id: int = None, parent=None):
        super().__init__(parent)
        self.db = db
        self.edificio_id = edificio_id
        self.setWindowTitle("Modifica Edificio" if edificio_id else "Nuovo Edificio")
        self.setMinimumWidth(400)
        self._setup_ui()
        if edificio_id:
            self._load()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.nome_edit = QLineEdit()
        self.indirizzo_edit = QLineEdit()
        self.note_edit = QTextEdit()
        self.note_edit.setMaximumHeight(70)
        form.addRow("Nome *:", self.nome_edit)
        form.addRow("Indirizzo:", self.indirizzo_edit)
        form.addRow("Note:", self.note_edit)
        layout.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("Salva")
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _load(self):
        q = QSqlQuery(self.db)
        q.prepare("SELECT nome_edificio, indirizzo, note FROM Edifici WHERE edificio_id=?")
        q.addBindValue(self.edificio_id)
        if q.exec() and q.next():
            self.nome_edit.setText(q.value(0) or "")
            self.indirizzo_edit.setText(q.value(1) or "")
            self.note_edit.setPlainText(q.value(2) or "")

    def _save(self):
        nome = self.nome_edit.text().strip()
        if not nome:
            QMessageBox.warning(self, "Campo obbligatorio", "Inserisci il nome dell'edificio.")
            return
        q = QSqlQuery(self.db)
        if self.edificio_id is None:
            q.prepare("INSERT INTO Edifici (nome_edificio, indirizzo, note) VALUES (?,?,?)")
        else:
            q.prepare("UPDATE Edifici SET nome_edificio=?, indirizzo=?, note=? WHERE edificio_id=?")
        q.addBindValue(nome)
        q.addBindValue(self.indirizzo_edit.text().strip() or None)
        q.addBindValue(self.note_edit.toPlainText().strip() or None)
        if self.edificio_id is not None:
            q.addBindValue(self.edificio_id)
        if q.exec():
            self.accept()
        else:
            QMessageBox.critical(self, "Errore DB", q.lastError().text())


class PianoDialog(QDialog):
    def __init__(self, db: QSqlDatabase, edificio_id: int = None, piano_id: int = None, parent=None):
        super().__init__(parent)
        self.db = db
        self.edificio_id = edificio_id
        self.piano_id = piano_id
        self.setWindowTitle("Modifica Piano" if piano_id else "Nuovo Piano")
        self.setMinimumWidth(400)
        self._setup_ui()
        self._load_edifici()
        if piano_id:
            self._load()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.nome_edit = QLineEdit()
        self.nome_edit.setPlaceholderText("es. Piano Terra, Piano 1, Seminterrato")
        self.edificio_combo = QComboBox()
        form.addRow("Nome piano *:", self.nome_edit)
        form.addRow("Edificio *:", self.edificio_combo)
        layout.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("Salva")
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _load_edifici(self):
        self.edificio_combo.clear()
        q = QSqlQuery(self.db)
        if q.exec("SELECT edificio_id, nome_edificio FROM Edifici ORDER BY nome_edificio"):
            while q.next():
                self.edificio_combo.addItem(q.value(1), q.value(0))
        if self.edificio_id is not None:
            idx = self.edificio_combo.findData(self.edificio_id)
            if idx >= 0:
                self.edificio_combo.setCurrentIndex(idx)

    def _load(self):
        q = QSqlQuery(self.db)
        q.prepare("SELECT nome_piano, edificio_id FROM Piani WHERE piano_id=?")
        q.addBindValue(self.piano_id)
        if q.exec() and q.next():
            self.nome_edit.setText(q.value(0) or "")
            idx = self.edificio_combo.findData(q.value(1))
            if idx >= 0:
                self.edificio_combo.setCurrentIndex(idx)

    def _save(self):
        nome = self.nome_edit.text().strip()
        if not nome:
            QMessageBox.warning(self, "Campo obbligatorio", "Inserisci il nome del piano.")
            return
        q = QSqlQuery(self.db)
        if self.piano_id is None:
            q.prepare("INSERT INTO Piani (nome_piano, edificio_id) VALUES (?,?)")
        else:
            q.prepare("UPDATE Piani SET nome_piano=?, edificio_id=? WHERE piano_id=?")
        q.addBindValue(nome)
        q.addBindValue(self.edificio_combo.currentData())
        if self.piano_id is not None:
            q.addBindValue(self.piano_id)
        if q.exec():
            self.accept()
        else:
            QMessageBox.critical(self, "Errore DB", q.lastError().text())


class LocaleDialog(QDialog):
    def __init__(self, db: QSqlDatabase, piano_id: int = None, locale_id: int = None, parent=None):
        super().__init__(parent)
        self.db = db
        self.piano_id = piano_id
        self.locale_id = locale_id
        self.setWindowTitle("Modifica Locale" if locale_id else "Nuovo Locale")
        self.setMinimumWidth(400)
        self._setup_ui()
        self._load_piani()
        if locale_id:
            self._load()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.nome_edit = QLineEdit()
        self.descrizione_edit = QLineEdit()
        self.piano_combo = QComboBox()
        form.addRow("Nome locale *:", self.nome_edit)
        form.addRow("Descrizione:", self.descrizione_edit)
        form.addRow("Piano:", self.piano_combo)
        layout.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("Salva")
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _load_piani(self):
        self.piano_combo.clear()
        self.piano_combo.addItem("— Nessuno —", None)
        q = QSqlQuery(self.db)
        if q.exec("""
            SELECT p.piano_id, e.nome_edificio || ' > ' || p.nome_piano
            FROM Piani p JOIN Edifici e ON p.edificio_id = e.edificio_id
            ORDER BY e.nome_edificio, p.nome_piano
        """):
            while q.next():
                self.piano_combo.addItem(q.value(1), q.value(0))
        if self.piano_id is not None:
            idx = self.piano_combo.findData(self.piano_id)
            if idx >= 0:
                self.piano_combo.setCurrentIndex(idx)

    def _load(self):
        q = QSqlQuery(self.db)
        q.prepare("SELECT nome_locale, descrizione, piano_id FROM Locali WHERE locale_id=?")
        q.addBindValue(self.locale_id)
        if q.exec() and q.next():
            self.nome_edit.setText(q.value(0) or "")
            self.descrizione_edit.setText(q.value(1) or "")
            idx = self.piano_combo.findData(q.value(2))
            if idx >= 0:
                self.piano_combo.setCurrentIndex(idx)

    def _save(self):
        nome = self.nome_edit.text().strip()
        if not nome:
            QMessageBox.warning(self, "Campo obbligatorio", "Inserisci il nome del locale.")
            return
        q = QSqlQuery(self.db)
        if self.locale_id is None:
            q.prepare("INSERT INTO Locali (nome_locale, descrizione, piano_id) VALUES (?,?,?)")
        else:
            q.prepare("UPDATE Locali SET nome_locale=?, descrizione=?, piano_id=? WHERE locale_id=?")
        q.addBindValue(nome)
        q.addBindValue(self.descrizione_edit.text().strip() or None)
        q.addBindValue(self.piano_combo.currentData())
        if self.locale_id is not None:
            q.addBindValue(self.locale_id)
        if q.exec():
            self.accept()
        else:
            QMessageBox.critical(self, "Errore DB", q.lastError().text())


class PortaTreeDialog(QDialog):
    """Dialog leggero per creare/rinominare una porta dall'albero."""
    def __init__(self, db: QSqlDatabase, locale_id: int = None, porta_id: int = None, parent=None):
        super().__init__(parent)
        self.db = db
        self.locale_id = locale_id
        self.porta_id = porta_id
        self.setWindowTitle("Modifica Porta" if porta_id else "Nuova Porta")
        self.setMinimumWidth(400)
        self._setup_ui()
        self._load_locali()
        if porta_id:
            self._load()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.nome_edit = QLineEdit()
        self.locale_combo = QComboBox()
        self.note_edit = QTextEdit()
        self.note_edit.setMaximumHeight(70)
        form.addRow("Nome porta *:", self.nome_edit)
        form.addRow("Locale:", self.locale_combo)
        form.addRow("Note:", self.note_edit)
        layout.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("Salva")
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _load_locali(self):
        self.locale_combo.clear()
        self.locale_combo.addItem("— Nessuno —", None)
        q = QSqlQuery(self.db)
        if q.exec("SELECT locale_id, nome_locale FROM Locali ORDER BY nome_locale"):
            while q.next():
                self.locale_combo.addItem(q.value(1), q.value(0))
        if self.locale_id is not None:
            idx = self.locale_combo.findData(self.locale_id)
            if idx >= 0:
                self.locale_combo.setCurrentIndex(idx)

    def _load(self):
        q = QSqlQuery(self.db)
        q.prepare("SELECT nome_porta, locale_id, note FROM Porte WHERE porta_id=?")
        q.addBindValue(self.porta_id)
        if q.exec() and q.next():
            self.nome_edit.setText(q.value(0) or "")
            idx = self.locale_combo.findData(q.value(1))
            if idx >= 0:
                self.locale_combo.setCurrentIndex(idx)
            self.note_edit.setPlainText(q.value(2) or "")

    def _save(self):
        nome = self.nome_edit.text().strip()
        if not nome:
            QMessageBox.warning(self, "Campo obbligatorio", "Inserisci il nome della porta.")
            return
        q = QSqlQuery(self.db)
        if self.porta_id is None:
            q.prepare("INSERT INTO Porte (nome_porta, locale_id, note) VALUES (?,?,?)")
        else:
            q.prepare("UPDATE Porte SET nome_porta=?, locale_id=?, note=? WHERE porta_id=?")
        q.addBindValue(nome)
        q.addBindValue(self.locale_combo.currentData())
        q.addBindValue(self.note_edit.toPlainText().strip() or None)
        if self.porta_id is not None:
            q.addBindValue(self.porta_id)
        if q.exec():
            self.accept()
        else:
            QMessageBox.critical(self, "Errore DB", q.lastError().text())
