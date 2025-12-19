"""
Módulo de gestión de la base de datos SQLite para los modelos de medidores.
"""
import sqlite3
from pathlib import Path

class DatabaseManager:
    """
    Gestiona las operaciones CRUD para los modelos de medidores en una base de datos SQLite.
    """
    def __init__(self, db_name="medidores.db"):
        """
        Inicializa el gestor y se conecta a la base de datos.
        Crea la tabla de modelos si no existe.
        
        :param db_name: Nombre del archivo de la base de datos.
        """
        self.db_path = Path(__file__).parent / db_name
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
        except sqlite3.Error as e:
            print(f"Error al crear la tabla: {e}")

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
    def add_model(self, nombre, constante, k=1.0, ds=-0.2, di=0.5):
        """Añade un nuevo modelo a la base de datos."""
        sql = '''INSERT INTO modelos(nombre, constante, k, ds, di)
                 VALUES(?,?,?,?,?)'''
        cursor = self.conn.cursor()
        cursor.execute(sql, (nombre, constante, k, ds, di))
        self.conn.commit()
        return cursor.lastrowid

    def get_all_models(self):
        """Recupera todos los modelos de la base de datos."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM modelos ORDER BY nombre")
        return cursor.fetchall()

    def update_model(self, model_id, nombre, constante, k, ds, di):
        """Actualiza un modelo existente."""
        sql = '''UPDATE modelos
                 SET nombre = ?, constante = ?, k = ?, ds = ?, di = ?
                 WHERE id = ?'''
        cursor = self.conn.cursor()
        cursor.execute(sql, (nombre, constante, k, ds, di, model_id))
        self.conn.commit()

    def delete_model(self, model_id):
        """Elimina un modelo por su ID."""
        sql = 'DELETE FROM modelos WHERE id = ?'
        cursor = self.conn.cursor()
        cursor.execute(sql, (model_id,))
        self.conn.commit()

    def close(self):
        """Cierra la conexión a la base de datos."""
        if self.conn:
            self.conn.close()

    def save_calibration_data(self, fecha, hora, calibrador, constante, modelo, tension, intensidad, di, ds, tabla_calibracion, temperatura=None):
        """Guarda los datos de calibración en la tabla 'calibracion_history'."""
        sql = '''INSERT INTO calibracion_history(fecha, hora, calibrador, constante, modelo, tension, intensidad, di, ds, tabla_calibracion, temperatura)
                 VALUES(?,?,?,?,?,?,?,?,?,?,?)'''
        cursor = self.conn.cursor()
        cursor.execute(sql, (fecha, hora, calibrador, constante, modelo, tension, intensidad, di, ds, tabla_calibracion, temperatura))
        self.conn.commit()

    def get_all_calibration_data(self, fecha=None, calibrador=None, modelo=None):
        """
        Recupera todos los datos de calibración de la tabla 'calibracion_history',
        con opción de filtrar por fecha, calibrador y modelo.
        """
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM calibracion_history"
        conditions = []
        params = []

        if fecha:
            conditions.append("fecha = ?")
            params.append(fecha)
        
        if calibrador:
            # Usamos LIKE para búsquedas parciales y sin distinción de mayúsculas/minúsculas
            conditions.append("LOWER(calibrador) LIKE ?")
            params.append(f"%{calibrador.lower()}%")

        if modelo:
            conditions.append("LOWER(modelo) LIKE ?")
            params.append(f"%{modelo.lower()}%")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY fecha DESC, hora DESC"
        
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]  # Convertir sqlite3.Row a diccionario

    def get_calibration_data(self, calibration_id):
        """Recupera los datos de calibración por ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM calibracion_history WHERE id = ?", (calibration_id,))
        row = cursor.fetchone()
        return dict(row) if row else None