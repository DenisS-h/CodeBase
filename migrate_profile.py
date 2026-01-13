from database import get_db_connection

def migrate():
    print("Iniciando migración para foto de perfil...")
    conn = get_db_connection()
    try:
        # Agregar columna foto_perfil
        conn.execute('ALTER TABLE usuarios ADD COLUMN foto_perfil TEXT')
        print("✅ Columna 'foto_perfil' agregada exitosamente")
    except Exception as e:
        if 'duplicate column name' in str(e).lower():
            print("ℹ️ La columna 'foto_perfil' ya existe")
        else:
            print(f"❌ Error al agregar columna: {e}")
            
    conn.commit()
    conn.close()
    print("Migración completada.")

if __name__ == '__main__':
    migrate()
