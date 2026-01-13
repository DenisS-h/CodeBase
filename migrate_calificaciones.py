"""
Script de migración para cambiar el sistema de puntos a calificaciones sobre 10.

Este script:
1. Agrega la columna 'calificacion' (REAL, 0.0 a 10.0) a progreso_usuario
2. Agrega la columna 'aprobada' (BOOLEAN, 0 o 1) a progreso_usuario
3. Migra los datos existentes (convierte puntos a calificación estimada)
4. Elimina la dependencia de puntos_requeridos de las lecciones
"""

import sqlite3
import os

DATABASE_PATH = os.path.join('instance', 'aprendizaje.db')

def migrate():
    """Ejecuta la migración del sistema de puntos a calificaciones."""
    print("=" * 60)
    print("MIGRACIÓN: Sistema de Puntos → Sistema de Calificaciones")
    print("=" * 60)
    
    if not os.path.exists(DATABASE_PATH):
        print("❌ Error: No se encontró la base de datos.")
        print(f"   Ruta esperada: {DATABASE_PATH}")
        return False
    
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # 1. Verificar y agregar columna 'calificacion' a progreso_usuario
        print("\n📊 Paso 1: Verificando columna 'calificacion'...")
        cursor.execute("PRAGMA table_info(progreso_usuario)")
        columns = [col['name'] for col in cursor.fetchall()]
        
        if 'calificacion' not in columns:
            cursor.execute('ALTER TABLE progreso_usuario ADD COLUMN calificacion REAL DEFAULT 0.0')
            print("   ✅ Columna 'calificacion' agregada a progreso_usuario")
        else:
            print("   ℹ️  Columna 'calificacion' ya existe")
        
        # 2. Verificar y agregar columna 'aprobada' a progreso_usuario
        print("\n✓ Paso 2: Verificando columna 'aprobada'...")
        cursor.execute("PRAGMA table_info(progreso_usuario)")
        columns = [col['name'] for col in cursor.fetchall()]
        
        if 'aprobada' not in columns:
            cursor.execute('ALTER TABLE progreso_usuario ADD COLUMN aprobada INTEGER DEFAULT 0')
            print("   ✅ Columna 'aprobada' agregada a progreso_usuario")
        else:
            print("   ℹ️  Columna 'aprobada' ya existe")
        
        # 3. Migrar datos existentes (convertir puntos a calificación)
        print("\n🔄 Paso 3: Migrando datos existentes...")
        
        # Obtener progreso existente con puntos
        cursor.execute('''
            SELECT pu.id, pu.puntos_obtenidos, pu.completada, l.id as leccion_id
            FROM progreso_usuario pu
            JOIN lecciones l ON pu.leccion_id = l.id
            WHERE pu.completada = 1
        ''')
        progresos = cursor.fetchall()
        
        migrados = 0
        for prog in progresos:
            # Obtener total de ejercicios de la lección
            cursor.execute('SELECT COUNT(*) as total FROM ejercicios WHERE leccion_id = ?', (prog['leccion_id'],))
            result = cursor.fetchone()
            total_ejercicios = result['total'] if result else 0
            
            if total_ejercicios > 0:
                # Cada ejercicio vale 10 puntos por defecto
                puntos_maximos = total_ejercicios * 10
                puntos_obtenidos = prog['puntos_obtenidos'] or 0
                
                # Calcular calificación (0-10)
                calificacion = min((puntos_obtenidos / puntos_maximos) * 10, 10.0)
                aprobada = 1 if calificacion >= 7.0 else 0
                
                # Actualizar registro
                cursor.execute('''
                    UPDATE progreso_usuario 
                    SET calificacion = ?, aprobada = ?
                    WHERE id = ?
                ''', (round(calificacion, 2), aprobada, prog['id']))
                migrados += 1
        
        print(f"   ✅ {migrados} registros de progreso migrados")
        
        # 4. Actualizar lecciones para quitar dependencia de puntos_requeridos
        print("\n🔓 Paso 4: Ajustando requisitos de lecciones...")
        cursor.execute('UPDATE lecciones SET puntos_requeridos = 0')
        print("   ✅ Puntos requeridos establecidos a 0 (desbloqueo por aprobación)")
        
        conn.commit()
        print("\n" + "=" * 60)
        print("✅ MIGRACIÓN COMPLETADA EXITOSAMENTE")
        print("=" * 60)
        print("\nResumen del nuevo sistema:")
        print("  • Calificaciones de 0 a 10")
        print("  • Mínimo 7/10 para aprobar y desbloquear siguiente")
        print("  • Intentos ilimitados")
        print("  • Se guarda solo la mejor calificación")
        
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error durante la migración: {e}")
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
