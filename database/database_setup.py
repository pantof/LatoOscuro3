# This Python file uses the following encoding: utf-8

import sqlite3
import os
from PySide6.QtSql import QSqlDatabase, QSqlError
from PySide6.QtWidgets import QMessageBox

DB_V4 = "inventario_hardware_v4.db"
NOME_DATABASE = "inventario_hardware_v5.db"


def crea_database_v5():
    if os.path.exists(NOME_DATABASE):
        return

    print(f"Creo il file database '{NOME_DATABASE}'...")
    conn = None
    try:
        conn = sqlite3.connect(NOME_DATABASE)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")

        cursor.executescript("""
        CREATE TABLE Edifici (
            edificio_id   INTEGER PRIMARY KEY,
            nome_edificio TEXT NOT NULL UNIQUE,
            indirizzo     TEXT,
            note          TEXT
        );

        CREATE TABLE Piani (
            piano_id    INTEGER PRIMARY KEY,
            nome_piano  TEXT NOT NULL,
            edificio_id INTEGER NOT NULL,
            FOREIGN KEY (edificio_id) REFERENCES Edifici (edificio_id) ON DELETE CASCADE,
            UNIQUE(nome_piano, edificio_id)
        );

        CREATE TABLE Locali (
            locale_id   INTEGER PRIMARY KEY,
            nome_locale TEXT NOT NULL UNIQUE,
            descrizione TEXT,
            piano_id    INTEGER,
            FOREIGN KEY (piano_id) REFERENCES Piani (piano_id) ON DELETE SET NULL
        );

        CREATE TABLE Porte (
            porta_id   INTEGER PRIMARY KEY,
            nome_porta TEXT NOT NULL UNIQUE,
            locale_id  INTEGER,
            note       TEXT,
            FOREIGN KEY (locale_id) REFERENCES Locali (locale_id)
        );

        CREATE TABLE Tipi_Dispositivi (
            tipo_id    INTEGER PRIMARY KEY,
            nome_tipo  TEXT NOT NULL UNIQUE,
            descrizione TEXT
        );

        -- NUOVA TABELLA: catalogo hardware indipendente dalle installazioni
        CREATE TABLE Catalogo_Materiali (
            articolo_id            INTEGER PRIMARY KEY,
            nome_articolo          TEXT NOT NULL,
            tipo_id                INTEGER NOT NULL,
            marca                  TEXT,
            modello                TEXT,
            descrizione            TEXT,
            garanzia_standard_mesi INTEGER,
            fornitore_preferito    TEXT,
            note                   TEXT,
            FOREIGN KEY (tipo_id) REFERENCES Tipi_Dispositivi (tipo_id)
        );

        CREATE TABLE Inventario_Dispositivi (
            dispositivo_id        INTEGER PRIMARY KEY,
            articolo_id           INTEGER,           -- FK catalogo (NULL = installazione manuale)
            modello               TEXT NOT NULL,
            matricola             TEXT UNIQUE,
            descrizione           TEXT,
            fornitore             TEXT,
            data_installazione    DATE,
            garanzia_mesi         INTEGER,
            stato                 TEXT DEFAULT 'Operativo',
            tipo_id               INTEGER NOT NULL,
            parent_dispositivo_id INTEGER,
            locale_id             INTEGER,
            porta_id              INTEGER,
            FOREIGN KEY (articolo_id)            REFERENCES Catalogo_Materiali (articolo_id),
            FOREIGN KEY (tipo_id)                REFERENCES Tipi_Dispositivi (tipo_id),
            FOREIGN KEY (parent_dispositivo_id)  REFERENCES Inventario_Dispositivi (dispositivo_id),
            FOREIGN KEY (locale_id)              REFERENCES Locali (locale_id),
            FOREIGN KEY (porta_id)               REFERENCES Porte (porta_id) ON DELETE CASCADE
        );

        CREATE TABLE SistemiEsterni (
            sistema_id        INTEGER PRIMARY KEY,
            nome_sistema      TEXT NOT NULL UNIQUE,
            tipo_sistema      TEXT,
            referente_tecnico TEXT
        );

        CREATE TABLE Interconnessioni (
            interconnessione_id     INTEGER PRIMARY KEY,
            dispositivo_id          INTEGER NOT NULL,
            sistema_id              INTEGER NOT NULL,
            descrizione_connessione TEXT NOT NULL,
            tipo_segnale            TEXT,
            note                    TEXT,
            FOREIGN KEY (dispositivo_id) REFERENCES Inventario_Dispositivi (dispositivo_id) ON DELETE CASCADE,
            FOREIGN KEY (sistema_id)     REFERENCES SistemiEsterni (sistema_id)
        );
        """)
        conn.commit()
        print("Schema database v5 creato.")
    except sqlite3.Error as e:
        print(f"Errore creazione database: {e}")
    finally:
        if conn:
            conn.close()


def _migra_da_v4():
    """Copia i dati dal DB v4 (se presente) nel nuovo v5."""
    if not os.path.exists(DB_V4):
        return False
    print(f"Migrazione dati da '{DB_V4}' a '{NOME_DATABASE}'...")
    try:
        conn = sqlite3.connect(NOME_DATABASE)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = OFF;")
        cursor.execute(f"ATTACH DATABASE '{DB_V4}' AS v4")

        tables = ["Edifici", "Piani", "Locali", "Porte", "Tipi_Dispositivi",
                  "SistemiEsterni"]
        for t in tables:
            cursor.execute(f"INSERT OR IGNORE INTO {t} SELECT * FROM v4.{t}")

        # Inventario_Dispositivi: articolo_id non c'era in v4, viene NULL
        cursor.execute("""
            INSERT OR IGNORE INTO Inventario_Dispositivi
                (dispositivo_id, modello, matricola, descrizione, fornitore,
                 data_installazione, garanzia_mesi, stato, tipo_id,
                 parent_dispositivo_id, locale_id, porta_id)
            SELECT dispositivo_id, modello, matricola, descrizione, fornitore,
                   data_installazione, garanzia_mesi, stato, tipo_id,
                   parent_dispositivo_id, locale_id, porta_id
            FROM v4.Inventario_Dispositivi
        """)
        cursor.execute("""
            INSERT OR IGNORE INTO Interconnessioni SELECT * FROM v4.Interconnessioni
        """)
        cursor.execute("DETACH DATABASE v4")
        cursor.execute("PRAGMA foreign_keys = ON;")
        conn.commit()
        print("Migrazione completata.")
        return True
    except sqlite3.Error as e:
        print(f"Errore migrazione: {e}")
        return False
    finally:
        if conn:
            conn.close()


def popola_dati_esempio_v5():
    print("Controllo popolamento dati v5...")
    try:
        conn = sqlite3.connect(NOME_DATABASE)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")

        cursor.execute("SELECT COUNT(*) FROM Tipi_Dispositivi")
        if cursor.fetchone()[0] > 0:
            print("Database già popolato.")
            conn.close()
            return

        print("Database vuoto, inserisco dati di esempio v5...")

        # Tipi dispositivi
        tipi = [
            (1, "Centralina",        "Controller accessi"),
            (2, "Lettore",           "Lettore badge / biometrico"),
            (3, "Serratura",         "Serratura elettrica / elettromeccanica"),
            (4, "Modulo I/O",        "Scatola interfaccia ingressi/uscite"),
            (5, "Contatto Magnetico","Sensore apertura porta"),
            (6, "Maniglia",          "Maniglia con lettore integrato"),
        ]
        cursor.executemany("INSERT INTO Tipi_Dispositivi VALUES (?,?,?)", tipi)

        # Catalogo materiali
        catalogo = [
            (1, "Centralina Axis A1001",    1, "Axis",    "A1001",    "Controller 2 porte IP",               36, "Axis Communications"),
            (2, "Lettore HID R10",          2, "HID",     "R10",      "Lettore prossimità 125 kHz",           24, "HID Global"),
            (3, "Lettore BioLite N2",       2, "Suprema", "BioLite N2","Biometrico impronte + RFID 13.56 MHz",24, "Suprema"),
            (4, "Modulo I/O Generic",       4, None,      "Modulo I/O","Scatola interfaccia generica",        None, None),
            (5, "Contatto Magnetico RM85",  5, "RISCO",   "RM85",     "Contatto da incasso",                  24, "RISCO Group"),
            (6, "Serratura Elettrica Libra",3, "ISEO",    "Libra",    "Serratura fail-safe 12V",              60, "ISEO"),
            (7, "Maniglia RFID Allegion",   6, "Allegion","AD-400",   "Maniglia con lettore RFID integrato",  24, "Allegion"),
        ]
        cursor.executemany(
            "INSERT INTO Catalogo_Materiali (articolo_id,nome_articolo,tipo_id,marca,modello,descrizione,garanzia_standard_mesi,fornitore_preferito) VALUES (?,?,?,?,?,?,?,?)",
            catalogo
        )

        # Edifici, Piani, Locali
        cursor.execute("INSERT INTO Edifici VALUES (1,'Edificio A','Via Roma 1, Milano',NULL)")
        cursor.execute("INSERT INTO Edifici VALUES (2,'Edificio B - Magazzino','Via Po 10, Milano',NULL)")
        cursor.execute("INSERT INTO Piani VALUES (1,'Piano 1',1)")
        cursor.execute("INSERT INTO Piani VALUES (2,'Piano Terra',1)")
        cursor.execute("INSERT INTO Piani VALUES (3,'Piano Terra',2)")
        cursor.execute("INSERT INTO Locali VALUES (1,'Locale CED','Rack Principale Controllo Accessi',1)")
        cursor.execute("INSERT INTO Locali VALUES (2,'Reception','Guardia all ingresso',2)")

        # Porte
        cursor.execute("INSERT INTO Porte VALUES (1,'Ingresso Principale',2,NULL)")
        cursor.execute("INSERT INTO Porte VALUES (2,'Porta Sala Server',1,NULL)")

        # Sistemi esterni
        cursor.execute("INSERT INTO SistemiEsterni (nome_sistema,tipo_sistema) VALUES ('Impianto Antincendio','Sicurezza')")

        # Installazioni (con articolo_id → da catalogo)
        # Centralina nel CED — art.1, garanzia 36m, installata 2024-01-15
        cursor.execute("""
            INSERT INTO Inventario_Dispositivi
                (articolo_id,modello,matricola,fornitore,data_installazione,garanzia_mesi,stato,tipo_id,locale_id)
            VALUES (1,'Axis A1001','AX-001-2024','Axis Communications','2024-01-15',36,'Operativo',1,1)
        """)
        # Lettore Ingresso Principale — art.2, garanzia scaduta
        cursor.execute("""
            INSERT INTO Inventario_Dispositivi
                (articolo_id,modello,matricola,fornitore,data_installazione,garanzia_mesi,stato,tipo_id,parent_dispositivo_id,porta_id)
            VALUES (2,'HID R10','HID-R10-0042','HID Global','2022-03-10',24,'Operativo',2,1,1)
        """)
        # Modulo I/O — art.4, nessuna garanzia
        cursor.execute("""
            INSERT INTO Inventario_Dispositivi
                (articolo_id,modello,matricola,descrizione,fornitore,data_installazione,stato,tipo_id,parent_dispositivo_id,porta_id)
            VALUES (4,'Modulo I/O Generic','IO-2022-003','Scatola sopra porta','Generico','2022-03-10','Operativo',4,1,1)
        """)
        # Lettore Sala Server — art.3, garanzia valida
        cursor.execute("""
            INSERT INTO Inventario_Dispositivi
                (articolo_id,modello,matricola,fornitore,data_installazione,garanzia_mesi,stato,tipo_id,parent_dispositivo_id,porta_id)
            VALUES (3,'BioLite N2','BIO-N2-2026-01','Suprema','2026-03-01',24,'Operativo',2,1,2)
        """)

        cursor.execute("""
            INSERT INTO Interconnessioni (dispositivo_id,sistema_id,descrizione_connessione,tipo_segnale)
            VALUES (3,1,'Input Sblocco Emergenza','Contatto secco NO')
        """)

        conn.commit()
        print("Dati di esempio v5 inseriti.")
    except sqlite3.Error as e:
        print(f"Errore popolamento: {e}")
    finally:
        if conn:
            conn.close()


def setup_database():
    crea_database_v5()
    migrato = False
    if not os.path.exists(NOME_DATABASE) or os.path.getsize(NOME_DATABASE) == 0:
        pass  # verrà creato sopra
    else:
        # controlla se è già popolato
        pass
    # Prova migrazione da v4 se il DB v5 è vuoto
    try:
        conn = sqlite3.connect(NOME_DATABASE)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM Tipi_Dispositivi")
        count = c.fetchone()[0]
        conn.close()
        if count == 0:
            migrato = _migra_da_v4()
    except Exception:
        pass
    if not migrato:
        popola_dati_esempio_v5()


def connect_db() -> QSqlDatabase | None:
    if not os.path.exists(NOME_DATABASE):
        setup_database()

    db = QSqlDatabase.addDatabase("QSQLITE", "qt_sql_default_connection")
    db.setDatabaseName(NOME_DATABASE)

    if not db.open():
        QMessageBox.critical(None, "Errore Database",
            f"Impossibile connettersi al database:\n{db.lastError().text()}")
        return None

    print("Connessione QtSql al database v5 stabilita.")
    query = db.exec("PRAGMA foreign_keys = ON;")
    if not query.isActive():
        print(f"Errore abilitazione Foreign Keys: {query.lastError().text()}")
    return db
