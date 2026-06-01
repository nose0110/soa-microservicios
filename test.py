# test_profesor_db.py
from coneeccion import ejecutar_consulta, ejecutar_comando

print("🔍 Probando conexión a BD del profesor...\n")

try:
    # 1. Verificar conexión
    resultado = ejecutar_consulta("SELECT current_user, current_database();")
    print(f"✅ Conectado como: {resultado[0]['current_user']}")
    print(f"✅ Base de datos: {resultado[0]['current_database']}\n")
    
    # 2. Verificar si puedes crear tablas
    print("🧪 Probando CREATE TABLE con prefijo ZA_...")
    try:
        ejecutar_comando("""
            CREATE TABLE IF NOT EXISTS ZA_prueba_conexion (
                id SERIAL PRIMARY KEY,
                mensaje TEXT,
                fecha TIMESTAMP DEFAULT NOW()
            );
        """)
        print("✅ ¡Puedes crear tablas!")
        
        # Insertar prueba
        ejecutar_comando("INSERT INTO ZA_prueba_conexion (mensaje) VALUES (%s);", 
                        ("Prueba ZA_ funciona",))
        
        # Leer prueba
        datos = ejecutar_consulta("SELECT * FROM ZA_prueba_conexion LIMIT 1;")
        print(f"✅ Dato insertado: {datos[0]['mensaje']}")
        
        # Limpiar
        ejecutar_comando("DROP TABLE IF EXISTS ZA_prueba_conexion;")
        print("✅ Tabla de prueba eliminada\n")
        
    except Exception as e:
        print(f"⚠️ No puedes crear tablas: {str(e)[:150]}\n")
    
    # 3. Verificar si puedes crear funciones (SPs)
    print("🧪 Probando CREATE FUNCTION con prefijo ZA_...")
    try:
        ejecutar_comando("""
            CREATE OR REPLACE FUNCTION ZA_prueba_funcion()
            RETURNS TEXT AS $$ BEGIN RETURN 'SP funciona'; END; $$ LANGUAGE plpgsql;
        """)
        print("✅ ¡Puedes crear Stored Procedures!")
        
        # Probar la función
        resultado = ejecutar_consulta("SELECT ZA_prueba_funcion();")
        print(f"✅ SP ejecutado: {resultado[0]['za_prueba_funcion']}")
        
        # Limpiar
        ejecutar_comando("DROP FUNCTION IF EXISTS ZA_prueba_funcion();")
        print("✅ Función de prueba eliminada\n")
        
    except Exception as e:
        print(f"⚠️ No puedes crear funciones: {str(e)[:150]}\n")
    
    print("="*50)
    print("📋 RESULTADO:")
    print("="*50)
    print("✅ ¡Puedes trabajar en la BD del profesor!")
    print("✅ Usa el prefijo ZA_ en TODOS tus objetos")
    print("✅ Así el profesor identificará tu trabajo")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("\n💡 Verifica:")
    print("  1. La contraseña en db/connection.py")
    print("  2. Que tengas conexión a internet")
    print("  3. Pide ayuda al profesor si el error persiste")