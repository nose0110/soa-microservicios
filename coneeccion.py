import os
import psycopg2
from psycopg2.extras import RealDictCursor

def get_connection():
    """Obtener conexión desde DATABASE_URL de entorno"""
    
    # 🔑 Leer variable de entorno (Render la inyecta automáticamente)
    database_url = os.environ.get("DATABASE_URL")
    
    if not database_url:
        # Fallback para desarrollo local (OPCIONAL)
        # ⚠️ NUNCA uses la contraseña real de Render aquí
        database_url = "postgresql://shopnow:localhost_password@localhost:5432/shopnow_db"
    
    # Conectar con SSL obligatorio (Render lo requiere)
    return psycopg2.connect(database_url, sslmode='require')

def ejecutar_consulta(query, params=None):
    """Para SELECT y SPs que modifican datos"""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute(query, params)
        resultados = cursor.fetchall()
        conn.commit()  # ✅ Importante para SPs de inserción/actualización
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
        print(f"❌ Error en comando: {e}")
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()