# This Python file uses the following encoding: utf-8

import sqlite3
import os
from PySide6.QtSql import QSqlDatabase, QSqlError
from PySide6.QtWidgets import QMessageBox

DB_V5 = "inventario_hardware_v5.db"
NOME_DATABASE = "inventario_hardware_v6.db"

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
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
    tipo_id     INTEGER PRIMARY KEY,
    nome_tipo   TEXT NOT NULL UNIQUE,
    descrizione TEXT
);
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
CREATE TABLE Materiali (
    materiale_id  INTEGER PRIMARY KEY,
    articolo_id   INTEGER NOT NULL,
    matricola     TEXT,
    data_acquisto DATE,
    fornitore     TEXT,
    num_fattura   TEXT,
    garanzia_mesi INTEGER,
    stato         TEXT NOT NULL DEFAULT 'In magazzino',
    note          TEXT,
    FOREIGN KEY (articolo_id) REFERENCES Catalogo_Materiali (articolo_id)
);
CREATE TABLE Inventario_Dispositivi (
    dispositivo_id        INTEGER PRIMARY KEY,
    materiale_id          INTEGER,
    articolo_id           INTEGER,
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
    FOREIGN KEY (materiale_id)           REFERENCES Materiali (materiale_id),
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
"""

# ---------------------------------------------------------------------------
# Creazione
# ---------------------------------------------------------------------------

def crea_database_v6():
    if os.path.exists(NOME_DATABASE):
        return
    print(f"Creo '{NOME_DATABASE}'...")
    conn = None
    try:
        conn = sqlite3.connect(NOME_DATABASE)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        print("Schema v6 creato.")
    except sqlite3.Error as e:
        print(f"Errore creazione DB: {e}")
    finally:
        if conn:
            conn.close()

# ---------------------------------------------------------------------------
# Migrazione da v5
# ---------------------------------------------------------------------------

def _migra_da_v5() -> bool:
    if not os.path.exists(DB_V5):
        return False
    print(f"Migrazione dati da '{DB_V5}' a '{NOME_DATABASE}'...")
    try:
        conn = sqlite3.connect(NOME_DATABASE)
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys = OFF;")
        cur.execute(f"ATTACH DATABASE '{DB_V5}' AS v5")

        for t in ["Edifici", "Piani", "Locali", "Porte",
                  "Tipi_Dispositivi", "Catalogo_Materiali", "SistemiEsterni"]:
            cur.execute(f"INSERT OR IGNORE INTO {t} SELECT * FROM v5.{t}")

        # Inventario_Dispositivi: materiale_id non esisteva in v5 → NULL
        cur.execute("""
            INSERT OR IGNORE INTO Inventario_Dispositivi
                (dispositivo_id, articolo_id, modello, matricola, descrizione,
                 fornitore, data_installazione, garanzia_mesi, stato, tipo_id,
                 parent_dispositivo_id, locale_id, porta_id)
            SELECT dispositivo_id, articolo_id, modello, matricola, descrizione,
                   fornitore, data_installazione, garanzia_mesi, stato, tipo_id,
                   parent_dispositivo_id, locale_id, porta_id
            FROM v5.Inventario_Dispositivi
        """)
        cur.execute("INSERT OR IGNORE INTO Interconnessioni SELECT * FROM v5.Interconnessioni")
        cur.execute("DETACH DATABASE v5")
        cur.execute("PRAGMA foreign_keys = ON;")
        conn.commit()
        print("Migrazione da v5 completata.")
        return True
    except sqlite3.Error as e:
        print(f"Errore migrazione: {e}")
        return False
    finally:
        if conn:
            conn.close()

# ---------------------------------------------------------------------------
# Dati di esempio
# ---------------------------------------------------------------------------

def popola_dati_esempio_v6():
    print("Popolamento dati di esempio v6...")
    try:
        conn = sqlite3.connect(NOME_DATABASE)
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys = ON;")

        cur.execute("SELECT COUNT(*) FROM Tipi_Dispositivi")
        if cur.fetchone()[0] > 0:
            print("DB già popolato — aggiungo solo materiali di esempio se mancano.")
            cur.execute("SELECT COUNT(*) FROM Materiali")
            if cur.fetchone()[0] == 0:
                _inserisci_materiali_esempio(cur)
                conn.commit()
            conn.close()
            return

        print("DB vuoto — inserisco tutti i dati di esempio...")
        # Tipi
        cur.executemany("INSERT INTO Tipi_Dispositivi VALUES (?,?,?)", [
            (1, "Centralina",        "Controller accessi"),
            (2, "Lettore",           "Lettore badge / biometrico"),
            (3, "Serratura",         "Serratura elettrica / elettromeccanica"),
            (4, "Modulo I/O",        "Scatola interfaccia ingressi/uscite"),
            (5, "Contatto Magnetico","Sensore apertura porta"),
            (6, "Maniglia",          "Maniglia con lettore integrato"),
        ])
        # Catalogo
        cur.executemany(
            "INSERT INTO Catalogo_Materiali "
            "(articolo_id,nome_articolo,tipo_id,marca,modello,descrizione,"
            "garanzia_standard_mesi,fornitore_preferito) VALUES (?,?,?,?,?,?,?,?)", [
            (1,"Centralina Axis A1001",   1,"Axis",   "A1001",   "Controller 2 porte IP",            36,"Axis Communications"),
            (2,"Lettore HID R10",         2,"HID",    "R10",     "Lettore prossimità 125 kHz",        24,"HID Global"),
            (3,"Lettore BioLite N2",      2,"Suprema","BioLite N2","Biometrico impronte + RFID",      24,"Suprema"),
            (4,"Modulo I/O Generic",      4, None,    "Modulo I/O","Scatola interfaccia generica",   None, None),
            (5,"Contatto Magnetico RM85", 5,"RISCO",  "RM85",    "Contatto da incasso",               24,"RISCO Group"),
            (6,"Serratura Elettrica Libra",3,"ISEO",  "Libra",   "Serratura fail-safe 12V",           60,"ISEO"),
            (7,"Maniglia RFID Allegion",  6,"Allegion","AD-400", "Maniglia con lettore RFID integrato",24,"Allegion"),
        ])
        # Edifici / Piani / Locali / Porte
        cur.execute("INSERT INTO Edifici VALUES (1,'Edificio A','Via Roma 1, Milano',NULL)")
        cur.execute("INSERT INTO Edifici VALUES (2,'Edificio B - Magazzino','Via Po 10, Milano',NULL)")
        cur.execute("INSERT INTO Piani VALUES (1,'Piano 1',1)")
        cur.execute("INSERT INTO Piani VALUES (2,'Piano Terra',1)")
        cur.execute("INSERT INTO Piani VALUES (3,'Piano Terra',2)")
        cur.execute("INSERT INTO Locali VALUES (1,'Locale CED','Rack Principale Controllo Accessi',1)")
        cur.execute("INSERT INTO Locali VALUES (2,'Reception','Guardia all ingresso',2)")
        cur.execute("INSERT INTO Porte VALUES (1,'Ingresso Principale',2,NULL)")
        cur.execute("INSERT INTO Porte VALUES (2,'Porta Sala Server',1,NULL)")
        cur.execute("INSERT INTO SistemiEsterni (nome_sistema,tipo_sistema) VALUES ('Impianto Antincendio','Sicurezza')")

        # Materiali — alcuni già installati, alcuni in magazzino
        _inserisci_materiali_esempio(cur)

        # Installazioni: collegano i materiali già installati alle porte
        # mat_id=1 centralina (CED, non su porta)
        cur.execute("""
            INSERT INTO Inventario_Dispositivi
                (materiale_id,articolo_id,modello,matricola,fornitore,
                 data_installazione,garanzia_mesi,stato,tipo_id,locale_id)
            VALUES (1,1,'Axis A1001','AX-001-2024','Axis Communications',
                    '2024-01-15',36,'Operativo',1,1)
        """)
        # mat_id=2 lettore HID su Ingresso Principale
        cur.execute("""
            INSERT INTO Inventario_Dispositivi
                (materiale_id,articolo_id,modello,matricola,fornitore,
                 data_installazione,garanzia_mesi,stato,tipo_id,
                 parent_dispositivo_id,porta_id)
            VALUES (2,2,'HID R10','HID-R10-0042','HID Global',
                    '2022-03-10',24,'Operativo',2,1,1)
        """)
        # mat_id=3 modulo I/O su Ingresso Principale
        cur.execute("""
            INSERT INTO Inventario_Dispositivi
                (materiale_id,articolo_id,modello,matricola,descrizione,fornitore,
                 data_installazione,stato,tipo_id,parent_dispositivo_id,porta_id)
            VALUES (3,4,'Modulo I/O Generic','IO-2022-003','Scatola sopra porta','Generico',
                    '2022-03-10','Operativo',4,1,1)
        """)
        # mat_id=4 BioLite N2 su Sala Server
        cur.execute("""
            INSERT INTO Inventario_Dispositivi
                (materiale_id,articolo_id,modello,matricola,fornitore,
                 data_installazione,garanzia_mesi,stato,tipo_id,
                 parent_dispositivo_id,porta_id)
            VALUES (4,3,'BioLite N2','BIO-N2-2026-01','Suprema',
                    '2026-03-01',24,'Operativo',2,1,2)
        """)
        cur.execute("""
            INSERT INTO Interconnessioni (dispositivo_id,sistema_id,descrizione_connessione,tipo_segnale)
            VALUES (3,1,'Input Sblocco Emergenza','Contatto secco NO')
        """)

        conn.commit()
        print("Dati di esempio v6 inseriti.")
    except sqlite3.Error as e:
        print(f"Errore popolamento: {e}")
    finally:
        if conn:
            conn.close()


def _inserisci_materiali_esempio(cur):
    """Inserisce materiali di esempio (sia installati che in magazzino)."""
    cur.executemany(
        "INSERT OR IGNORE INTO Materiali "
        "(materiale_id,articolo_id,matricola,data_acquisto,fornitore,"
        "num_fattura,garanzia_mesi,stato,note) VALUES (?,?,?,?,?,?,?,?,?)", [
        # --- già installati ---
        (1, 1,"AX-001-2024",  "2023-12-10","Axis Communications","FT-2023-0892",36,"Installato", None),
        (2, 2,"HID-R10-0042", "2022-01-15","HID Global",         "FT-2022-0101",24,"Installato", None),
        (3, 4,"IO-2022-003",  "2022-01-15","Generico",           "FT-2022-0101",None,"Installato",None),
        (4, 3,"BIO-N2-2026-01","2026-01-20","Suprema",           "FT-2026-0045",24,"Installato", None),
        # --- in magazzino (disponibili per l'installazione) ---
        (5, 2,"HID-R10-0101", "2026-04-05","HID Global",         "FT-2026-0210",24,"In magazzino","Scorta lettori ingresso"),
        (6, 2,"HID-R10-0102", "2026-04-05","HID Global",         "FT-2026-0210",24,"In magazzino","Scorta lettori ingresso"),
        (7, 5,"RM85-A001",    "2026-04-10","RISCO Group",        "FT-2026-0211",24,"In magazzino", None),
        (8, 6,"LIBRA-0055",   "2026-03-22","ISEO",               "FT-2026-0188",60,"In magazzino","Porta principale magazzino"),
        (9, 7,"AD400-0012",   "2026-05-01","Allegion",           "FT-2026-0301",24,"In magazzino", None),
    ])

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def setup_database():
    crea_database_v6()
    try:
        conn = sqlite3.connect(NOME_DATABASE)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM Tipi_Dispositivi")
        vuoto = c.fetchone()[0] == 0
        conn.close()
    except Exception:
        vuoto = True

    if vuoto:
        if not _migra_da_v5():
            popola_dati_esempio_v6()
    else:
        # DB già popolato: aggiungi materiali di esempio se la tabella è vuota
        popola_dati_esempio_v6()


def connect_db() -> QSqlDatabase | None:
    if not os.path.exists(NOME_DATABASE):
        setup_database()

    db = QSqlDatabase.addDatabase("QSQLITE", "qt_sql_default_connection")
    db.setDatabaseName(NOME_DATABASE)

    if not db.open():
        QMessageBox.critical(None, "Errore Database",
            f"Impossibile connettersi:\n{db.lastError().text()}")
        return None

    print("Connessione QtSql al database v6 stabilita.")
    db.exec("PRAGMA foreign_keys = ON;")
    return db
