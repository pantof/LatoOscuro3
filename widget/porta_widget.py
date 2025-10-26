# This Python file uses the following encoding: utf-8

# if __name__ == "__main__":
#     pass
# In 'porta_widget.py'

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QTextEdit, QListWidget, QPushButton, QMessageBox, QSplitter, QLabel
)
from PySide6.QtSql import QSqlDatabase, QSqlQuery, QSqlError
from PySide6.QtCore import Qt

class PortaDetailWidget(QWidget):

    def __init__(self, db: QSqlDatabase, parent=None):
        # ... (il costruttore __init__ rimane identico) ...
        super().__init__(parent)

        if not db or not db.isOpen():
            QMessageBox.critical(self, "Errore", "Connessione al database non valida.")
            return

        self.db = db
        self.current_porta_id = None

        self.setup_ui()
        self.populate_combos()
        self.clear_form()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)

        form_layout = QFormLayout()
        self.nome_edit = QLineEdit()

        # --- MODIFICA 1: Aggiungiamo un campo 'Posizione' ---
        self.posizione_completa_edit = QLineEdit()
        self.posizione_completa_edit.setReadOnly(True) # Sola lettura
        self.posizione_completa_edit.setStyleSheet("background-color: #f0f0f0;") # Grigio

        self.locale_combo = QComboBox() # Per *modificare* il locale

        self.note_edit = QTextEdit()
        self.note_edit.setMaximumHeight(100)

        form_layout.addRow("Nome Porta:", self.nome_edit)
        form_layout.addRow("Assegna a Locale:", self.locale_combo) # Questo serve per l'assegnazione
        form_layout.addRow("Posizione Completa:", self.posizione_completa_edit) # Questo per la visualizzazione

        main_layout.addLayout(form_layout)
        main_layout.addWidget(QLabel("Note:"))
        main_layout.addWidget(self.note_edit)

        # ... (Il resto di setup_ui con QSplitter e QListWidget rimane identico) ...
        list_splitter = QSplitter(Qt.Vertical)

        self.dispositivi_list = QListWidget()
        self.connessioni_list = QListWidget()

        dispositivi_widget = QWidget()
        dis_layout = QVBoxLayout(dispositivi_widget); dis_layout.setContentsMargins(0,0,0,0)
        dis_layout.addWidget(QLabel("Dispositivi installati sulla porta:"))
        dis_layout.addWidget(self.dispositivi_list)

        connessioni_widget = QWidget()
        conn_layout = QVBoxLayout(connessioni_widget); conn_layout.setContentsMargins(0,0,0,0)
        conn_layout.addWidget(QLabel("Interconnessioni (via dispositivi):"))
        conn_layout.addWidget(self.connessioni_list)

        list_splitter.addWidget(dispositivi_widget)
        list_splitter.addWidget(connessioni_widget)
        main_layout.addWidget(list_splitter)

        self.save_button = QPushButton("Salva Modifiche")
        self.save_button.clicked.connect(self.save_data)
        main_layout.addWidget(self.save_button)

        # Colleghiamo il cambio del combo box all'aggiornamento della posizione
        self.locale_combo.currentIndexChanged.connect(self.update_posizione_completa)


    def populate_combos(self):
        # ... (Questa funzione rimane identica) ...
        self.locale_combo.clear()
        self.locale_combo.addItem("Nessuno", None)

        query = QSqlQuery(self.db)
        if query.exec("SELECT locale_id, nome_locale FROM Locali ORDER BY nome_locale"):
            while query.next():
                self.locale_combo.addItem(query.value(1), query.value(0))
        else:
            self.show_db_error(query.lastError())

    def clear_form(self):
        # ... (Dobbiamo aggiungere il nuovo campo) ...
        self.current_porta_id = None
        self.nome_edit.clear()
        self.note_edit.clear()
        self.locale_combo.setCurrentIndex(0)
        self.posizione_completa_edit.clear() # Aggiunto
        self.dispositivi_list.clear()
        self.connessioni_list.clear()
        self.setEnabled(False)

    def load_porta_data(self, porta_id: int):
        self.clear_form()
        self.current_porta_id = porta_id

        query_porta = QSqlQuery(self.db)
        query_porta.prepare("SELECT nome_porta, locale_id, note FROM Porte WHERE porta_id = ?")
        query_porta.addBindValue(porta_id)

        if query_porta.exec() and query_porta.next():
            self.nome_edit.setText(query_porta.value(0))
            locale_id = query_porta.value(1)
            self.note_edit.setPlainText(query_porta.value(2))

            # Imposta il valore nel ComboBox (questo triggera l'aggiornamento della posizione)
            idx = self.locale_combo.findData(locale_id)
            if idx != -1:
                self.locale_combo.setCurrentIndex(idx)
            else:
                self.locale_combo.setCurrentIndex(0) # "Nessuno"
        else:
            self.show_db_error(query_porta.lastError()); return

        # ... (Le query per Dispositivi e Interconnessioni rimangono identiche) ...
        # Query 2: Dispositivi sulla porta
        query_dev = QSqlQuery(self.db)
        query_dev.prepare("""...""") # Identica
        query_dev.addBindValue(porta_id)
        if query_dev.exec():
             while query_dev.next():
                testo = f"[{query_dev.value(1)}] {query_dev.value(0)} (SN: {query_dev.value(2)})"
                self.dispositivi_list.addItem(testo)

        # Query 3: Interconnessioni
        query_conn = QSqlQuery(self.db)
        query_conn.prepare("""...""") # Identica
        query_conn.addBindValue(porta_id)
        if query_conn.exec():
            while query_conn.next():
                testo = f"{query_conn.value(0)} <- {query_conn.value(1)} (su {query_conn.value(2)})"
                self.connessioni_list.addItem(testo)

        self.setEnabled(True)

    # --- MODIFICA 2: Nuova funzione per aggiornare la posizione ---
    def update_posizione_completa(self):
        """
        Chiamato quando il combo box 'locale_combo' cambia.
        Esegue una query JOIN per trovare il percorso completo.
        """
        self.posizione_completa_edit.clear()
        current_locale_id = self.locale_combo.currentData() # Prende l'ID

        if current_locale_id is None:
            return

        query = QSqlQuery(self.db)
        query.prepare("""
            SELECT e.nome_edificio, p.nome_piano, l.nome_locale
            FROM Locali l
            JOIN Piani p ON l.piano_id = p.piano_id
            JOIN Edifici e ON p.edificio_id = e.edificio_id
            WHERE l.locale_id = ?
        """)
        query.addBindValue(current_locale_id)

        if query.exec() and query.next():
            percorso = f"{query.value(0)}  >  {query.value(1)}  >  {query.value(2)}"
            self.posizione_completa_edit.setText(percorso)
        elif query.lastError().isValid():
            self.show_db_error(query.lastError())
        else:
            # Potrebbe essere un locale non associato a un piano
            self.posizione_completa_edit.setText(self.locale_combo.currentText())


    def save_data(self):
        # ... (Questa funzione rimane identica) ...
        if self.current_porta_id is None: return

        query = QSqlQuery(self.db)
        query.prepare("""
            UPDATE Porte SET nome_porta = ?, locale_id = ?, note = ?
            WHERE porta_id = ?
        """)
        query.addBindValue(self.nome_edit.text())
        query.addBindValue(self.locale_combo.currentData()) # Salva l'ID del locale
        query.addBindValue(self.note_edit.toPlainText())
        query.addBindValue(self.current_porta_id)

        if query.exec():
            QMessageBox.information(self, "Successo", "Dati porta salvati.")
        else:
            self.show_db_error(query.lastError())

    def show_db_error(self, err: QSqlError):
        # ... (Questa funzione rimane identica) ...
        QMessageBox.critical(self, "Errore Query", f"Errore database: {err.text()}")
