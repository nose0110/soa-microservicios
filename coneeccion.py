
import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = {
    "host": "dpg-d8erk01o3t8c73fpjd90-a.oregon-postgres.render.com",
    "port": 5432,
    "database": "shopnow_db_tntz",
    "user": "shopnow",
    "password": "UffNPW73ok38VpCf4DRSJQPWeDGgiPpo"  # ⭐ Pon la real aquí
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def ejecutar_consulta(query, params=None):
    """Para SELECT y SPs que modifican datos"""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute(query, params)
        resultados = cursor.fetchall()
        conn.commit()  # ✅ ¡AGREGAR ESTO!
        return [dict(row) for row in resultados]
    except Exception as e:
        print(f"❌ Error en consulta: {e}")
        conn.rollback()  # ✅ Revertir si hay error
        return []
    finally:
        cursor.close()
        conn.close()
        
def ejecutar_comando(query, params=None):
    """Para INSERT/UPDATE/DELETE - retorna filas afectadas"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        conn.commit()
        return cursor.rowcount
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()