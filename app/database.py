"""
Módulo de gestión de la base de datos SQLite para los modelos de medidores.
"""
import sqlite3
import os
import sys
from pathlib import Path

def get_app_data_path(app_name="TVK6Nexo"):
    """
    Obtiene una ruta segura y persistente para almacenar los datos de la aplicación.
    Crea el directorio si no existe.
    """
    if sys.platform.startswith('win'):
        # Windows: C:\Users\<Usuario>\AppData\Roaming\<AppName>
        path = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
    elif sys.platform.startswith('darwin'):
        # macOS: ~/Library/Application Support/<AppName>
        path = Path.home() / 'Library' / 'Application Support'
    else:
        # Linux: ~/.local/share/<AppName>
        path = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share'))

    app_data_path = path / app_name
    # Crear el directorio si no existe
    app_data_path.mkdir(parents=True, exist_ok=True)
    return app_data_path

class DatabaseManager:
    """
    Gestiona las operaciones CRUD para los modelos de medidores en una base de datos SQLite.
    """
    def __init__(self, db_name="medidores.db"):
        """
        Inicializa el gestor y se conecta a la base de datos.
        La base de datos se almacena en una carpeta de datos de aplicación específica del usuario.
        
        :param db_name: Nombre del archivo de la base de datos.
        """
        # Obtener la ruta de datos de la aplicación y construir la ruta completa de la BD
        app_data_dir = get_app_data_path()
        self.db_path = app_data_dir / db_name
        print(f"INFO: La base de datos se encuentra en: {self.db_path}")

        self.conn = None
        self.create_connection()
        self.create_table()

    def create_connection(self):
        """Crea una conexión a la base de datos SQLite."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # Permite acceder a las columnas por nombre
        except sqlite3.Error as e:
            print(f"Error al conectar con la base de datos: {e}")

    def create_table(self):
        """Crea la tabla 'modelos' si no existe."""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS modelos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            constante REAL NOT NULL,
            k REAL NOT NULL,
            ds REAL NOT NULL,
            di REAL NOT NULL
        );
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(create_table_sql)
            self.conn.commit()
            self.create_history_table()
            self.create_calibrators_table()
            self._migrate_database() # Añadimos la llamada a la migración
        except sqlite3.Error as e:
            print(f"Error al crear la tabla: {e}")

    def _migrate_database(self):
        """
        Aplica migraciones a la base de datos para asegurar que el esquema esté actualizado.
        """
        try:
            cursor = self.conn.cursor()
            # Migración: Añadir columna 'temperatura' a 'calibracion_history' si no existe
            cursor.execute("PRAGMA table_info(calibracion_history)")
            columns = [info['name'] for info in cursor.fetchall()]
            if 'temperatura' not in columns:
                print("INFO: Aplicando migración -> Añadiendo columna 'temperatura' a la tabla 'calibracion_history'.")
                cursor.execute("ALTER TABLE calibracion_history ADD COLUMN temperatura TEXT")
                self.conn.commit()

            # Migración: Añadir columna 'calibrador_id' a 'calibracion_history' si no existe
            cursor.execute("PRAGMA table_info(calibracion_history)")
            columns = [info['name'] for info in cursor.fetchall()]
            if 'calibrador_id' not in columns:
                print("INFO: Aplicando migración -> Añadiendo columna 'calibrador_id' a la tabla 'calibracion_history'.")
                cursor.execute("ALTER TABLE calibracion_history ADD COLUMN calibrador_id INTEGER REFERENCES calibradores(id)")
                self.conn.commit()

            # Migración: Añadir columna 'seriales_medidores' a 'calibracion_history' si no existe
            cursor.execute("PRAGMA table_info(calibracion_history)")
            columns = [info['name'] for info in cursor.fetchall()]
            if 'seriales_medidores' not in columns:
                print("INFO: Aplicando migración -> Añadiendo columna 'seriales_medidores' a la tabla 'calibracion_history'.")
                cursor.execute("ALTER TABLE calibracion_history ADD COLUMN seriales_medidores TEXT")

            # Migración: Añadir columna 'imagen_path' a 'modelos' si no existe
            cursor.execute("PRAGMA table_info(modelos)")
            modelos_columns = [info['name'] for info in cursor.fetchall()]
            if 'imagen_path' not in modelos_columns:
                print("INFO: Aplicando migración -> Añadiendo columna 'imagen_path' a la tabla 'modelos'.")
                cursor.execute("ALTER TABLE modelos ADD COLUMN imagen_path TEXT")
                self.conn.commit()

            # Migración: Crear tabla 'calibradores' si no existe
            cursor.execute("PRAGMA table_info(calibradores)")
            if not cursor.fetchall(): # Si la tabla no existe, la lista estará vacía
                print("INFO: Aplicando migración -> Creando tabla 'calibradores'.")
                self.create_calibrators_table()

        except sqlite3.Error as e:
            print(f"Error durante la migración de la base de datos: {e}")

    def create_calibrators_table(self):
        """Crea la tabla 'calibradores' si no existe."""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS calibradores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            identificador TEXT NOT NULL UNIQUE,
            imagen_path TEXT
        );"""
        cursor = self.conn.cursor()
        cursor.execute(create_table_sql)
        self.conn.commit()

    def create_history_table(self):
        """Crea la tabla 'calibracion_history' si no existe."""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS calibracion_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            hora TEXT NOT NULL,
            calibrador TEXT,
            constante TEXT,
            modelo TEXT,

            tension TEXT,
            temperatura TEXT,

            intensidad TEXT,
            di TEXT,
            ds TEXT,

            tabla_calibracion TEXT);"""
        cursor = self.conn.cursor()
        cursor.execute(create_table_sql)
        self.conn.commit()
    def add_model(self, nombre, constante, k=1.0, ds=-0.2, di=0.5, imagen_path=None):
        """Añade un nuevo modelo a la base de datos."""
        sql = '''INSERT INTO modelos(nombre, constante, k, ds, di, imagen_path)
                 VALUES(?,?,?,?,?,?)'''
        cursor = self.conn.cursor()
        cursor.execute(sql, (nombre, constante, k, ds, di, imagen_path))
        self.conn.commit()
        return cursor.lastrowid

    def get_all_models(self):
        """Recupera todos los modelos de la base de datos."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM modelos ORDER BY nombre")
        return cursor.fetchall()

    def get_model_by_name(self, nombre):
        """Recupera un modelo por su nombre."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM modelos WHERE nombre = ?", (nombre,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_model(self, model_id, nombre, constante, k, ds, di, imagen_path=None):
        """Actualiza un modelo existente."""
        sql = '''UPDATE modelos
                 SET nombre = ?, constante = ?, k = ?, ds = ?, di = ?, imagen_path = ?
                 WHERE id = ?'''
        cursor = self.conn.cursor()
        cursor.execute(sql, (nombre, constante, k, ds, di, imagen_path, model_id))
        self.conn.commit()

    def delete_model(self, model_id):
        """Elimina un modelo por su ID."""
        sql = 'DELETE FROM modelos WHERE id = ?'
        cursor = self.conn.cursor()
        cursor.execute(sql, (model_id,))
        self.conn.commit()

    # --- CRUD para Calibradores ---

    def add_calibrator(self, nombre, identificador, imagen_path=None):
        """Añade un nuevo calibrador a la base de datos."""
        sql = '''INSERT INTO calibradores(nombre, identificador, imagen_path)
                 VALUES(?,?,?)'''
        cursor = self.conn.cursor()
        cursor.execute(sql, (nombre, identificador, imagen_path))
        self.conn.commit()
        return cursor.lastrowid

    def get_all_calibrators(self):
        """Recupera todos los calibradores de la base de datos."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM calibradores ORDER BY nombre")
        return cursor.fetchall()

    def get_calibrator_by_name(self, nombre):
        """Recupera un calibrador por su nombre. Devuelve el primero que encuentra."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM calibradores WHERE nombre = ?", (nombre,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_calibrator(self, calibrator_id, nombre, identificador, imagen_path=None):
        """Actualiza un calibrador existente."""
        sql = '''UPDATE calibradores
                 SET nombre = ?, identificador = ?, imagen_path = ?
                 WHERE id = ?'''
        cursor = self.conn.cursor()
        cursor.execute(sql, (nombre, identificador, imagen_path, calibrator_id))
        self.conn.commit()

    def delete_calibrator(self, calibrator_id):
        """Elimina un calibrador por su ID."""
        sql = 'DELETE FROM calibradores WHERE id = ?'
        cursor = self.conn.cursor()
        cursor.execute(sql, (calibrator_id,))
        self.conn.commit()

    def close(self):
        """Cierra la conexión a la base de datos."""
        if self.conn:
            self.conn.close()

    def save_calibration_data(self, fecha, hora, calibrador_id, constante, modelo, tension, intensidad, di, ds, tabla_calibracion, temperatura=None, seriales_medidores=None):
        """Guarda los datos de calibración en la tabla 'calibracion_history'."""
        # El campo 'calibrador' (texto) se deja en blanco para nuevos registros, se usará calibrador_id.
        sql = '''INSERT INTO calibracion_history(fecha, hora, calibrador_id, constante, modelo, tension, intensidad, di, ds, tabla_calibracion, temperatura, seriales_medidores)
                 VALUES(?,?,?,?,?,?,?,?,?,?,?,?)'''
        cursor = self.conn.cursor()
        cursor.execute(sql, (fecha, hora, calibrador_id, constante, modelo, tension, intensidad, di, ds, tabla_calibracion, temperatura, seriales_medidores))
        self.conn.commit()

    def get_all_calibration_data(self, fecha=None, calibrador=None, modelo=None):
        """
        Recupera todos los datos de calibración de la tabla 'calibracion_history',
        con opción de filtrar por fecha, calibrador y modelo. Ahora une con la
        tabla de calibradores para obtener el nombre.
        """
        cursor = self.conn.cursor()
        
        # Usamos COALESCE para mostrar el nombre del calibrador desde la tabla de calibradores si existe el ID,
        # o el nombre antiguo del campo de texto si no (para datos antiguos).
        query = """
            SELECT 
                h.*, 
                COALESCE(c.nombre, h.calibrador) as calibrador_nombre
            FROM calibracion_history h
            LEFT JOIN calibradores c ON h.calibrador_id = c.id
        """
        conditions = []
        params = []

        if fecha:
            conditions.append("h.fecha = ?")
            params.append(fecha)
        
        if calibrador:
            # La búsqueda ahora se hace sobre el nombre del calibrador (nuevo o antiguo)
            conditions.append("LOWER(COALESCE(c.nombre, h.calibrador)) LIKE ?")
            params.append(f"%{calibrador.lower()}%")

        if modelo:
            conditions.append("LOWER(h.modelo) LIKE ?")
            params.append(f"%{modelo.lower()}%")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY h.fecha DESC, h.hora DESC"
        
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]  # Convertir sqlite3.Row a diccionario

    def get_calibration_data(self, calibration_id):
        """Recupera los datos de calibración por ID, uniendo con la tabla de calibradores."""
        cursor = self.conn.cursor()
        query = """
            SELECT 
                h.*, 
                COALESCE(c.nombre, h.calibrador) as calibrador_nombre
            FROM calibracion_history h
            LEFT JOIN calibradores c ON h.calibrador_id = c.id
            WHERE h.id = ?
        """
        cursor.execute(query, (calibration_id,))
        row = cursor.fetchone()
        return dict(row) if row else None