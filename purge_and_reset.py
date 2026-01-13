from database import get_db_connection
import sqlite3

def purge_database():
    print("⚠️  INICIANDO PURGADO DE BASE DE DATOS...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 1. Obtener datos del admin actual (el primero que encuentre)
        print("🔍 Buscando administrador...")
        admin = cursor.execute('SELECT * FROM usuarios WHERE es_admin = 1 LIMIT 1').fetchone()
        
        if not admin:
            print("❌ No se encontró administrador para preservar. Abortando.")
            return

        admin_data = dict(admin)
        print(f"✅ Administrador encontrado: {admin_data['nombre_completo']} ({admin_data['email']})")
        
        # 2. Borrar datos de tablas objetivo
        print("🗑️  Borrando historial de progreso...")
        cursor.execute('DELETE FROM progreso_usuario')
        
        print("🗑️  Borrando todos los usuarios...")
        cursor.execute('DELETE FROM usuarios')
        
        # 3. Reiniciar contadores autoincrementables
        print("🔄 Reiniciando secuencias de IDs...")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='usuarios'")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='progreso_usuario'")
        
        # 4. Insertar admin con ID 1
        print("Restaurando administrador con ID 1...")
        
        # Preparar query basada en columnas detectadas en admin_data
        # Asumiendo que admin_data tiene todas las columnas necesarias
        
        # Para evitar problemas con columnas, especificamos las que conocemos que son críticas
        # y dejamos que las demás tomen valores por defecto o NULL si es seguro,
        # pero mejor usamos las variables exactas del modelo actual.
        
        query = '''
            INSERT INTO usuarios (
                id, nombre_completo, email, password, 
                es_admin, activo, puntos_totales, racha_dias, 
                requiere_cambio_password, foto_perfil
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        
        # Valores para el admin restaurado (ID forzado a 1)
        # Reseteamos puntos y racha también? El usuario pidió "reinicies los contadores", 
        # pero dijo "borres toda la informacion... a excepcion de las credenciales del admin".
        # Asumiré que estadísticas de admin también se pueden resetear o mantener. 
        # "que el admin pase a tener el id 1" -> Suena a reset total.
        # Mantendremos credenciales (email, pass, nombre) y lo demás clean o default.
        
        cursor.execute(query, (
            1, # ID forzado
            admin_data['nombre_completo'],
            admin_data['email'],
            admin_data['password'],
            1, # es_admin
            1, # activo
            0, # puntos (reset)
            0, # racha (reset)
            0, # requiere_cambio (reset)
            admin_data['foto_perfil'] # Mantener foto si tiene
        ))
        
        conn.commit()
        print("✅ Base de datos purgada y administrador restaurado correctamente.")
        
    except Exception as e:
        print(f"❌ Error crítico: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    purge_database()
