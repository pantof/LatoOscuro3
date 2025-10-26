# This Python file uses the following encoding: utf-8

# if __name__ == "__main__":
#     pass
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import (
    qInstallMessageHandler, QtMsgType, QMessageLogContext
)
# Importa QSqlDatabase per poterla usare alla chiusura
from PySide6.QtSql import QSqlDatabase

# Importa le nostre funzioni/classi dagli altri file
from database.database_setup import setup_database, connect_db
from main_window import MainWindow

def qt_message_handler(mode, context, message):
    """ Un gestore per silenziare i warning di QtSql se non sono errori. """
    if mode == QtMsgType.QtWarningMsg and "QSqlQuery" in message:
        return # Silenzia i warning comuni di QSqlQuery
    # Stampa gli altri messaggi (info, debug, errori critici)
    print(f"Qt: {message}")

if __name__ == "__main__":

    # 1. Installa il gestore di messaggi per un output più pulito
    qInstallMessageHandler(qt_message_handler)

    # 2. Crea e popola il file DB (se necessario)
    # Questo usa sqlite3 standard, prima che Qt parta
    setup_database()

    # 3. Avvia l'applicazione Qt
    app = QApplication(sys.argv)

    # 4. Stabilisci la connessione QtSql (UNA SOLA VOLTA)
    db_connection = connect_db()

    if db_connection is None:
        print("Impossibile connettersi al database. Uscita.")
        sys.exit(1)

    # 5. Crea la finestra principale e passale la connessione
    window = MainWindow(db=db_connection)
    window.show()

    # 6. Esegui l'app
    exit_code = app.exec()

    # 7. Chiudi la connessione DB *solo* alla fine
    db_connection.close()

    # Questa riga ora funzionerà perché QSqlDatabase è importato
    QSqlDatabase.removeDatabase("qt_sql_default_connection")

    print("Connessione DB chiusa. Uscita pulita.")
    sys.exit(exit_code)
