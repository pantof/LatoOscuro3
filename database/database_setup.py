# This Python file uses the following encoding: utf-8

import sqlite3
import os
from PySide6.QtSql import QSqlDatabase, QSqlError
from PySide6.QtWidgets import QMessageBox

NOME_DATABASE = "inventario_hardware_v4.db"

def crea_database_v4():
    if os.path.exists(NOME_DATABASE):
        return

    print(f"Creo il file database '{NOME_DATABASE}'...")
    conn = None
    try:
        conn = sqlite3.connect(NOME_DATABASE)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")

        schema_sql = """
        CREATE TABLE Edifici (
            edificio_id INTEGER PRIMARY KEY,
            nome_edificio TEXT NOT NULL UNIQUE,
            indirizzo TEXT,
            note TEXT
        );

        CREATE TABLE Piani (
            piano_id INTEGER PRIMARY KEY,
            nome_piano TEXT NOT NULL,
            edificio_id INTEGER NOT NULL,
            FOREIGN KEY (edificio_id) REFERENCES Edifici (edificio_id) ON DELETE CASCADE,
            UNIQUE(nome_piano, edificio_id)
        );

        CREATE TABLE Locali (
            locale_id INTEGER PRIMARY KEY,
            nome_locale TEXT NOT NULL UNIQUE,
            descrizione TEXT,
            piano_id INTEGER,
            FOREIGN KEY (piano_id) REFERENCES Piani (piano_id) ON DELETE SET NULL
        );

        CREATE TABLE Porte (
            porta_id INTEGER PRIMARY KEY,
            nome_porta TEXT NOT NULL UNIQUE,
            locale_id INTEGER,
            note TEXT,
            FOREIGN KEY (locale_id) REFERENCES Locali (locale_id)
        );

        CREATE TABLE Tipi_Dispositivi (
            tipo_id INTEGER PRIMARY KEY,
            nome_tipo TEXT NOT NULL UNIQUE,
            descrizione TEXT
        );

        CREATE TABLE Inventario_Dispositivi (
            dispositivo_id   INTEGER PRIMARY KEY,
            modello          TEXT NOT NULL,
            matricola        TEXT UNIQUE,
            descrizione      TEXT,
            fornitore        TEXT,
            data_installazione DATE,
            garanzia_mesi    INTEGER,
            stato            TEXT DEFAULT 'Operativo',
            tipo_id          INTEGER NOT NULL,
            parent_dispositivo_id INTEGER,
            locale_id        INTEGER,
            porta_id         INTEGER,
            FOREIGN KEY (tipo_id)               REFERENCES Tipi_Dispositivi (tipo_id),
            FOREIGN KEY (parent_dispositivo_id)  REFERENCES Inventario_Dispositivi (dispositivo_id),
            FOREIGN KEY (locale_id)             REFERENCES Locali (locale_id),
            FOREIGN KEY (porta_id)              REFERENCES Porte (porta_id) ON DELETE CASCADE
        );

        CREATE TABLE SistemiEsterni (
            sistema_id       INTEGER PRIMARY KEY,
            nome_sistema     TEXT NOT NULL UNIQUE,
            tipo_sistema     TEXT,
            referente_tecnico TEXT
        );

        CREATE TABLE Interconnessioni (
            interconnessione_id  INTEGER PRIMARY KEY,
            dispositivo_id       INTEGER NOT NULL,
            sistema_id           INTEGER NOT NULL,
            descrizione_connessione TEXT NOT NULL,
            tipo_segnale         TEXT,
            note                 TEXT,
            FOREIGN KEY (dispositivo_id) REFERENCES Inventario_Dispositivi (dispositivo_id) ON DELETE CASCADE,
            FOREIGN KEY (sistema_id)     REFERENCES SistemiEsterni (sistema_id)
        );
        """
        cursor.executescript(schema_sql)
        conn.commit()
        print("Schema database v4 creato.")
    except sqlite3.Error as e:
        print(f"Errore creazione database: {e}")
    finally:
        if conn:
            conn.close()


def popola_dati_esempio_v4():
    print("Controllo popolamento dati v4...")
    try:
        conn = sqlite3.connect(NOME_DATABASE)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")

        cursor.execute("SELECT COUNT(*) FROM Porte")
        if cursor.fetchone()[0] > 0:
            print("Database già popolato.")
            conn.close()
            return

        print("Database vuoto, inserisco dati di esempio v4...")

        cursor.execute("INSERT INTO Edifici VALUES (1, 'Edificio A', 'Via Roma 1, Milano', NULL)")
        cursor.execute("INSERT INTO Edifici VALUES (2, 'Edificio B - Magazzino', 'Via Po 10, Milano', NULL)")

        cursor.execute("INSERT INTO Piani VALUES (1, 'Piano 1', 1)")
        cursor.execute("INSERT INTO Piani VALUES (2, 'Piano Terra', 1)")
        cursor.execute("INSERT INTO Piani VALUES (3, 'Piano Terra', 2)")

        cursor.execute("INSERT INTO Locali VALUES (1, 'Locale CED', 'Rack Principale Controllo Accessi', 1)")
        cursor.execute("INSERT INTO Locali VALUES (2, 'Reception', 'Guardia all ingresso', 2)")

        cursor.execute("INSERT INTO Tipi_Dispositivi (nome_tipo) VALUES ('Centralina')")
        cursor.execute("INSERT INTO Tipi_Dispositivi (nome_tipo) VALUES ('Lettore')")
        cursor.execute("INSERT INTO Tipi_Dispositivi (nome_tipo) VALUES ('Serratura')")
        cursor.execute("INSERT INTO Tipi_Dispositivi (nome_tipo) VALUES ('Modulo I/O')")

        cursor.execute("INSERT INTO Porte VALUES (1, 'Ingresso Principale', 2, NULL)")
        cursor.execute("INSERT INTO Porte VALUES (2, 'Porta Sala Server', 1, NULL)")

        cursor.execute("INSERT INTO SistemiEsterni (nome_sistema, tipo_sistema) VALUES ('Impianto Antincendio', 'Sicurezza')")

        # Centralina nel CED — garanzia 36 mesi, installata 2024-01-15 → scade 2027-01-15 (valida)
        cursor.execute("""
            INSERT INTO Inventario_Dispositivi
            (modello, matricola, fornitore, data_installazione, garanzia_mesi, stato, tipo_id, locale_id)
            VALUES ('Axis A1001', 'AX-001-2024', 'Axis Communications', '2024-01-15', 36, 'Operativo', 1, 1)
        """)

        # Lettore Ingresso Principale — garanzia 24 mesi, installato 2022-03-10 → scaduta 2024-03-10
        cursor.execute("""
            INSERT INTO Inventario_Dispositivi
            (modello, matricola, fornitore, data_installazione, garanzia_mesi, stato, tipo_id, parent_dispositivo_id, porta_id)
            VALUES ('HID R10', 'HID-R10-0042', 'HID Global', '2022-03-10', 24, 'Operativo', 2, 1, 1)
        """)

        # Modulo I/O Ingresso Principale — nessuna garanzia registrata
        cursor.execute("""
            INSERT INTO Inventario_Dispositivi
            (modello, matricola, descrizione, fornitore, data_installazione, garanzia_mesi, stato, tipo_id, parent_dispositivo_id, porta_id)
            VALUES ('Modulo I/O Generic', 'IO-2022-003', 'Scatola sopra porta', 'Generico', '2022-03-10', NULL, 'Operativo', 4, 1, 1)
        """)

        # Lettore Sala Server — garanzia 24 mesi, installato 2026-03-01 → scade 2028-03-01 (valida)
        cursor.execute("""
            INSERT INTO Inventario_Dispositivi
            (modello, matricola, fornitore, data_installazione, garanzia_mesi, stato, tipo_id, parent_dispositivo_id, porta_id)
            VALUES ('BioLite N2', 'BIO-N2-2026-01', 'Suprema', '2026-03-01', 24, 'Operativo', 2, 1, 2)
        """)

        cursor.execute("""
            INSERT INTO Interconnessioni (dispositivo_id, sistema_id, descrizione_connessione, tipo_segnale)
            VALUES (3, 1, 'Input Sblocco Emergenza', 'Contatto secco NO')
        """)

        conn.commit()
        print("Dati di esempio v4 inseriti.")
    except sqlite3.Error as e:
        print(f"Errore popolamento: {e}")
    finally:
        if conn:
            conn.close()


def setup_database():
    crea_database_v4()
    popola_dati_esempio_v4()


def connect_db() -> QSqlDatabase | None:
    if not os.path.exists(NOME_DATABASE):
        setup_database()

    db = QSqlDatabase.addDatabase("QSQLITE", "qt_sql_default_connection")
    db.setDatabaseName(NOME_DATABASE)

    if not db.open():
        QMessageBox.critical(None, "Errore Database",
            f"Impossibile connettersi al database:\n{db.lastError().text()}")
        return None

    print("Connessione QtSql al database v4 stabilita.")
    query = db.exec("PRAGMA foreign_keys = ON;")
    if not query.isActive():
        print(f"Errore abilitazione Foreign Keys: {query.lastError().text()}")

    return db
