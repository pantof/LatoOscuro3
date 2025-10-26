# This Python file uses the following encoding: utf-8

# if __name__ == "__main__":
#     pass
import sqlite3
import os
from PySide6.QtSql import QSqlDatabase, QSqlError
from PySide6.QtWidgets import QMessageBox

NOME_DATABASE = "inventario_hardware_v3.db" # Versione 3

def crea_database_v3():
    """
    Crea lo schema del database v3, aggiungendo Edifici e Piani
    e normalizzando la tabella Locali.
    """
    if os.path.exists(NOME_DATABASE):
        return  # Esiste già

    print(f"Creo il file database '{NOME_DATABASE}'...")
    conn = None
    try:
        conn = sqlite3.connect(NOME_DATABASE)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")

        schema_sql = """

        -- NUOVA TABELLA: Edifici
        CREATE TABLE Edifici (
            edificio_id INTEGER PRIMARY KEY,
            nome_edificio TEXT NOT NULL UNIQUE,
            indirizzo TEXT,
            note TEXT
        );

        -- NUOVA TABELLA: Piani (collegata a Edifici)
        CREATE TABLE Piani (
            piano_id INTEGER PRIMARY KEY,
            nome_piano TEXT NOT NULL, -- Es. "Piano 1", "PT", "Livello -1"
            edificio_id INTEGER NOT NULL,
            FOREIGN KEY (edificio_id) REFERENCES Edifici (edificio_id)
                ON DELETE CASCADE, -- Se elimino un edificio, elimino i suoi piani
            UNIQUE(nome_piano, edificio_id) -- Evita "Piano 1" duplicati nello stesso edificio
        );

        -- TABELLA MODIFICATA: Locali
        CREATE TABLE Locali (
            locale_id INTEGER PRIMARY KEY,
            nome_locale TEXT NOT NULL UNIQUE,
            descrizione TEXT,
            -- I campi 'edificio' e 'piano' (testo) sono stati rimossi
            -- Sostituiti da un link alla tabella Piani
            piano_id INTEGER,
            FOREIGN KEY (piano_id) REFERENCES Piani (piano_id)
                ON DELETE SET NULL -- Se elimino un piano, il locale resta "flottante"
        );

        -- Il resto dello schema rimane invariato
        CREATE TABLE Porte (
            porta_id INTEGER PRIMARY KEY, nome_porta TEXT NOT NULL UNIQUE,
            locale_id INTEGER, note TEXT,
            FOREIGN KEY (locale_id) REFERENCES Locali (locale_id)
        );
        CREATE TABLE Tipi_Dispositivi (
            tipo_id INTEGER PRIMARY KEY, nome_tipo TEXT NOT NULL UNIQUE,
            descrizione TEXT
        );
        CREATE TABLE Inventario_Dispositivi (
            dispositivo_id INTEGER PRIMARY KEY, modello TEXT NOT NULL,
            matricola TEXT UNIQUE, descrizione TEXT, data_installazione DATE,
            stato TEXT DEFAULT 'Operativo', tipo_id INTEGER NOT NULL,
            parent_dispositivo_id INTEGER, locale_id INTEGER, porta_id INTEGER,
            FOREIGN KEY (tipo_id) REFERENCES Tipi_Dispositivi (tipo_id),
            FOREIGN KEY (parent_dispositivo_id) REFERENCES Inventario_Dispositivi (dispositivo_id),
            FOREIGN KEY (locale_id) REFERENCES Locali (locale_id),
            FOREIGN KEY (porta_id) REFERENCES Porte (porta_id)
        );
        CREATE TABLE SistemiEsterni (
            sistema_id INTEGER PRIMARY KEY, nome_sistema TEXT NOT NULL UNIQUE,
            tipo_sistema TEXT, referente_tecnico TEXT
        );
        CREATE TABLE Interconnessioni (
            interconnessione_id INTEGER PRIMARY KEY,
            dispositivo_id INTEGER NOT NULL, sistema_id INTEGER NOT NULL,
            descrizione_connessione TEXT NOT NULL, tipo_segnale TEXT, note TEXT,
            FOREIGN KEY (dispositivo_id) REFERENCES Inventario_Dispositivi (dispositivo_id),
            FOREIGN KEY (sistema_id) REFERENCES SistemiEsterni (sistema_id)
        );
        """
        cursor.executescript(schema_sql)
        conn.commit()
        print("Schema database v3 creato.")
    except sqlite3.Error as e:
        print(f"Errore creazione database: {e}")
    finally:
        if conn:
            conn.close()

def popola_dati_esempio_v3():
    """
    Popola il database v3 con dati di esempio SE è vuoto.
    """
    print("Controllo popolamento dati v3...")
    try:
        conn = sqlite3.connect(NOME_DATABASE)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")

        cursor.execute("SELECT COUNT(*) FROM Porte")
        if cursor.fetchone()[0] > 0:
            print("Database già popolato.")
            conn.close()
            return

        print("Database vuoto, inserisco dati di esempio v3...")

        # 1. Popola le nuove tabelle
        cursor.execute("""
            INSERT INTO Edifici (edificio_id, nome_edificio, indirizzo)
            VALUES (1, 'Edificio A', 'Via Roma 1, Milano');
        """)
        cursor.execute("""
            INSERT INTO Edifici (edificio_id, nome_edificio, indirizzo)
            VALUES (2, 'Edificio B - Magazzino', 'Via Po 10, Milano');
        """)

        cursor.execute("INSERT INTO Piani (piano_id, nome_piano, edificio_id) VALUES (1, 'Piano 1', 1);")
        cursor.execute("INSERT INTO Piani (piano_id, nome_piano, edificio_id) VALUES (2, 'Piano Terra', 1);")
        cursor.execute("INSERT INTO Piani (piano_id, nome_piano, edificio_id) VALUES (3, 'Piano Terra', 2);")

        # 2. Modifica l'inserimento dei Locali
        # Ora 'Locale CED' è collegato al 'Piano 1' (piano_id=1)
        cursor.execute("""
            INSERT INTO Locali (locale_id, nome_locale, descrizione, piano_id)
            VALUES (1, 'Locale CED', 'Rack Principale Controllo Accessi', 1);
        """)
        # Aggiungiamo un altro locale
        cursor.execute("""
            INSERT INTO Locali (locale_id, nome_locale, descrizione, piano_id)
            VALUES (2, 'Reception', 'Guardia all ingresso', 2);
        """)

        # 3. Il resto (Porte, Tipi, etc.) rimane quasi uguale
        cursor.execute("INSERT INTO Tipi_Dispositivi (nome_tipo) VALUES ('Centralina'), ('Lettore'), ('Serratura'), ('Scatola Interfaccia');")

        # La porta "Ingresso Principale" è nel locale "Reception" (locale_id=2)
        cursor.execute("INSERT INTO Porte (porta_id, nome_porta, locale_id) VALUES (1, 'Ingresso Principale', 2);")
        # La porta "Sala Server" è nel locale "Locale CED" (locale_id=1)
        cursor.execute("INSERT INTO Porte (porta_id, nome_porta, locale_id) VALUES (2, 'Porta Sala Server', 1);")

        cursor.execute("INSERT INTO SistemiEsterni (nome_sistema, tipo_sistema) VALUES ('Impianto Antincendio', 'Sicurezza');")

        # La Centralina (dispositivo_id=1) è nel Locale CED (locale_id=1)
        cursor.execute("INSERT INTO Inventario_Dispositivi (modello, tipo_id, locale_id) VALUES ('Axis A1001', 1, 1);")

        # Dispositivi su 'Ingresso Principale' (porta_id=1), collegati alla Centralina (parent=1)
        cursor.execute("INSERT INTO Inventario_Dispositivi (modello, tipo_id, parent_dispositivo_id, porta_id) VALUES ('HID R10', 2, 1, 1);")
        cursor.execute("INSERT INTO Inventario_Dispositivi (modello, tipo_id, parent_dispositivo_id, porta_id, descrizione) VALUES ('Modulo I/O', 4, 1, 1, 'Scatola sopra porta');") # id=3

        # Dispositivi su 'Porta Sala Server' (porta_id=2), collegati alla Centralina (parent=1)
        cursor.execute("INSERT INTO Inventario_Dispositivi (modello, tipo_id, parent_dispositivo_id, porta_id) VALUES ('BioLite N2', 2, 1, 2);")

        cursor.execute("INSERT INTO Interconnessioni (dispositivo_id, sistema_id, descrizione_connessione) VALUES (3, 1, 'Input Sblocco Emergenza');")

        conn.commit()
        print("Dati di esempio v3 inseriti.")
    except sqlite3.Error as e:
        print(f"Errore popolamento: {e}")
    finally:
        if conn:
            conn.close()

def setup_database():
    """Funzione unica per creare e popolare il DB."""
    # Aggiorniamo il nome del file DB
    global NOME_DATABASE
    NOME_DATABASE = "inventario_hardware_v3.db"

    crea_database_v3()
    popola_dati_esempio_v3()

def connect_db() -> QSqlDatabase | None:
    """
    Crea la connessione QtSql al database v3 e la restituisce.
    """
    # Controlla che il setup sia stato eseguito
    if not os.path.exists(NOME_DATABASE):
        setup_database()

    db = QSqlDatabase.addDatabase("QSQLITE", "qt_sql_default_connection")
    db.setDatabaseName(NOME_DATABASE)

    if not db.open():
        QMessageBox.critical(None, "Errore Database",
            f"Impossibile connettersi al database:\n{db.lastError().text()}")
        return None

    print("Connessione QtSql al database v3 stabilita.")
    query = db.exec("PRAGMA foreign_keys = ON;")
    if not query.isActive():
         print(f"Errore abilitazione Foreign Keys: {query.lastError().text()}")

    return db
