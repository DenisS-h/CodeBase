from database import get_db_connection

def migrate():
    print("Iniciando migración para cambio de contraseña obligatorio...")
    conn = get_db_connection()
    try:
        # Agregar columna requiere_cambio_password
        # 0: No requiere, 1: Requiere
        conn.execute('ALTER TABLE usuarios ADD COLUMN requiere_cambio_password BOOLEAN DEFAULT 0')
        print("✅ Columna 'requiere_cambio_password' agregada exitosamente")
    except Exception as e:
        if 'duplicate column name' in str(e).lower():
            print("ℹ️ La columna 'requiere_cambio_password' ya existe")
        else:
            print(f"❌ Error al agregar columna: {e}")
            
    conn.commit()
    conn.close()
    print("Migración completada.")

if __name__ == '__main__':
    migrate()
