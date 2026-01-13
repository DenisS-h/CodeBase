from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection, USE_POSTGRESQL

class Usuario:
    @staticmethod
    def crear(nombre_completo, email, password, es_admin=0, activo=1):
        conn = get_db_connection()
        cursor = conn.cursor()
        password_hash = generate_password_hash(password)
        
        try:
            if USE_POSTGRESQL:
                cursor.execute('INSERT INTO usuarios (nombre_completo, email, password, es_admin, activo, requiere_cambio_password) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id', 
                             (nombre_completo, email, password_hash, es_admin, activo, 0))
                usuario_id = cursor.fetchone()[0]
            else:
                cursor.execute('INSERT INTO usuarios (nombre_completo, email, password, es_admin, activo, requiere_cambio_password) VALUES (?, ?, ?, ?, ?, ?)', 
                             (nombre_completo, email, password_hash, es_admin, activo, 0))
                usuario_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return usuario_id
        except Exception as e:
            print(f"Error al crear usuario: {e}")
            conn.close()
            return None
    
    @staticmethod
    def obtener_por_email(email):
        conn = get_db_connection()
        usuario = conn.execute('SELECT * FROM usuarios WHERE email = ?', (email,)).fetchone()
        conn.close()
        return usuario
    
    @staticmethod
    def obtener_por_id(usuario_id):
        conn = get_db_connection()
        usuario = conn.execute('SELECT * FROM usuarios WHERE id = ?', (usuario_id,)).fetchone()
        conn.close()
        return usuario
    
    @staticmethod
    def verificar_password(email, password):
        usuario = Usuario.obtener_por_email(email)
        if usuario and check_password_hash(usuario['password'], password):
            return usuario
        return None

    @staticmethod
    def obtener_todos():
        conn = get_db_connection()
        usuarios = conn.execute('SELECT * FROM usuarios ORDER BY fecha_registro DESC').fetchall()
        conn.close()
        return usuarios

    @staticmethod
    def actualizar_estado(usuario_id, activo):
        conn = get_db_connection()
        conn.execute('UPDATE usuarios SET activo = ? WHERE id = ?', (1 if activo else 0, usuario_id))
        conn.commit()
        conn.close()

    @staticmethod
    def admin_cambiar_password(usuario_id, password):
        conn = get_db_connection()
        password_hash = generate_password_hash(password)
        conn.execute('UPDATE usuarios SET password = ? WHERE id = ?', (password_hash, usuario_id))
        conn.commit()
        conn.close()

    @staticmethod
    def actualizar_datos(usuario_id, email, foto_perfil=None):
        conn = get_db_connection()
        if foto_perfil:
            conn.execute('UPDATE usuarios SET email = ?, foto_perfil = ? WHERE id = ?', (email, foto_perfil, usuario_id))
        else:
            conn.execute('UPDATE usuarios SET email = ? WHERE id = ?', (email, usuario_id))
        conn.commit()
        conn.close()

    @staticmethod
    def marcar_cambio_password(usuario_id, requiere=True):
        conn = get_db_connection()
        conn.execute('UPDATE usuarios SET requiere_cambio_password = ? WHERE id = ?', (1 if requiere else 0, usuario_id))
        conn.commit()
        conn.close()

class Unidad:
    @staticmethod
    def obtener_todas():
        conn = get_db_connection()
        unidades = conn.execute('SELECT * FROM unidades ORDER BY orden').fetchall()
        conn.close()
        return unidades
    
    @staticmethod
    def obtener_por_id(unidad_id):
        conn = get_db_connection()
        unidad = conn.execute('SELECT * FROM unidades WHERE id = ?', (unidad_id,)).fetchone()
        conn.close()
        return unidad

class Leccion:
    @staticmethod
    def obtener_por_unidad(unidad_id):
        conn = get_db_connection()
        lecciones = conn.execute('SELECT * FROM lecciones WHERE unidad_id = ? ORDER BY orden', (unidad_id,)).fetchall()
        conn.close()
        return lecciones
    
    @staticmethod
    def obtener_por_id(leccion_id):
        conn = get_db_connection()
        leccion = conn.execute('SELECT * FROM lecciones WHERE id = ?', (leccion_id,)).fetchone()
        conn.close()
        return leccion
    
    @staticmethod
    def obtener_primera_de_unidad(unidad_id):
        """Obtiene la primera lección de una unidad (orden = 1)"""
        conn = get_db_connection()
        leccion = conn.execute('SELECT * FROM lecciones WHERE unidad_id = ? ORDER BY orden LIMIT 1', (unidad_id,)).fetchone()
        conn.close()
        return leccion

class Ejercicio:
    @staticmethod
    def obtener_por_leccion(leccion_id):
        conn = get_db_connection()
        ejercicios = conn.execute('SELECT * FROM ejercicios WHERE leccion_id = ? ORDER BY id', (leccion_id,)).fetchall()
        conn.close()
        return ejercicios
    
    @staticmethod
    def obtener_por_id(ejercicio_id):
        conn = get_db_connection()
        ejercicio = conn.execute('SELECT * FROM ejercicios WHERE id = ?', (ejercicio_id,)).fetchone()
        conn.close()
        return ejercicio
    
    @staticmethod
    def contar_por_leccion(leccion_id):
        """Cuenta el número de ejercicios en una lección"""
        conn = get_db_connection()
        result = conn.execute('SELECT COUNT(*) as total FROM ejercicios WHERE leccion_id = ?', (leccion_id,)).fetchone()
        conn.close()
        return result['total'] if result else 0

class Progreso:
    @staticmethod
    def obtener_progreso_usuario(usuario_id):
        """Obtiene el progreso completo del usuario con calificaciones"""
        conn = get_db_connection()
        progreso = conn.execute('''
            SELECT l.*, p.completada, p.calificacion, p.aprobada, p.intentos, u.numero as unidad_numero
            FROM lecciones l
            LEFT JOIN progreso_usuario p ON l.id = p.leccion_id AND p.usuario_id = ?
            LEFT JOIN unidades u ON l.unidad_id = u.id
            ORDER BY u.orden, l.orden
        ''', (usuario_id,)).fetchall()
        conn.close()
        return progreso
    
    @staticmethod
    def obtener_leccion_usuario(usuario_id, leccion_id):
        """Obtiene el progreso de una lección específica para un usuario"""
        conn = get_db_connection()
        progreso = conn.execute('''
            SELECT * FROM progreso_usuario 
            WHERE usuario_id = ? AND leccion_id = ?
        ''', (usuario_id, leccion_id)).fetchone()
        conn.close()
        return progreso
    
    @staticmethod
    def guardar_calificacion(usuario_id, leccion_id, calificacion, respuestas_correctas, total_ejercicios):
        """
        Guarda la calificación de una lección.
        Solo actualiza si la nueva calificación es mayor que la anterior.
        
        Args:
            usuario_id: ID del usuario
            leccion_id: ID de la lección
            calificacion: Calificación obtenida (0-10)
            respuestas_correctas: Número de respuestas correctas
            total_ejercicios: Total de ejercicios en la lección
        
        Returns:
            dict con información del resultado
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar si ya existe un registro
        existe = cursor.execute('''
            SELECT id, calificacion, aprobada, intentos FROM progreso_usuario 
            WHERE usuario_id = ? AND leccion_id = ?
        ''', (usuario_id, leccion_id)).fetchone()
        
        aprobada = 1 if calificacion >= 7.0 else 0
        calificacion_redondeada = round(calificacion, 2)
        
        if existe:
            # Ya existe: incrementar intentos y actualizar solo si la calificación es mejor
            nuevos_intentos = (existe['intentos'] or 0) + 1
            calificacion_anterior = existe['calificacion'] or 0
            
            if calificacion_redondeada > calificacion_anterior:
                # Nueva calificación es mejor
                cursor.execute('''
                    UPDATE progreso_usuario 
                    SET calificacion = ?, aprobada = ?, intentos = ?, 
                        completada = 1, fecha_completado = CURRENT_TIMESTAMP
                    WHERE usuario_id = ? AND leccion_id = ?
                ''', (calificacion_redondeada, aprobada, nuevos_intentos, usuario_id, leccion_id))
                calificacion_guardada = calificacion_redondeada
                es_mejor = True
            else:
                # Mantener calificación anterior, solo actualizar intentos
                cursor.execute('''
                    UPDATE progreso_usuario 
                    SET intentos = ?
                    WHERE usuario_id = ? AND leccion_id = ?
                ''', (nuevos_intentos, usuario_id, leccion_id))
                calificacion_guardada = calificacion_anterior
                es_mejor = False
                aprobada = existe['aprobada']  # Mantener estado anterior
        else:
            # Primer intento: insertar nuevo registro
            cursor.execute('''
                INSERT INTO progreso_usuario 
                (usuario_id, leccion_id, completada, calificacion, aprobada, intentos, fecha_completado)
                VALUES (?, ?, 1, ?, ?, 1, CURRENT_TIMESTAMP)
            ''', (usuario_id, leccion_id, calificacion_redondeada, aprobada))
            calificacion_guardada = calificacion_redondeada
            es_mejor = True
        
        conn.commit()
        conn.close()
        
        return {
            'calificacion': calificacion_redondeada,
            'calificacion_guardada': calificacion_guardada,
            'aprobada': aprobada == 1,
            'es_mejor': es_mejor,
            'respuestas_correctas': respuestas_correctas,
            'total_ejercicios': total_ejercicios
        }
    
    @staticmethod
    def verificar_leccion_desbloqueada(usuario_id, leccion_id):
        """
        Verifica si una lección está desbloqueada para un usuario.
        
        Una lección está desbloqueada si:
        - Es la primera lección de la primera unidad (siempre disponible)
        - Es la primera lección de una unidad posterior y la unidad anterior está completada
        - La lección anterior (en la misma unidad) fue aprobada con >= 7
        
        Returns:
            tuple (desbloqueada: bool, mensaje: str)
        """
        conn = get_db_connection()
        
        # Obtener información de la lección
        leccion = conn.execute('SELECT * FROM lecciones WHERE id = ?', (leccion_id,)).fetchone()
        if not leccion:
            conn.close()
            return False, "Lección no encontrada"
        
        unidad_id = leccion['unidad_id']
        orden_leccion = leccion['orden']
        
        # Obtener información de la unidad
        unidad = conn.execute('SELECT * FROM unidades WHERE id = ?', (unidad_id,)).fetchone()
        orden_unidad = unidad['orden'] if unidad else 1
        
        # Caso 1: Primera lección de la primera unidad - siempre disponible
        if orden_unidad == 1 and orden_leccion == 1:
            conn.close()
            return True, "Primera lección disponible"
        
        # Caso 2: Primera lección de una unidad posterior
        if orden_leccion == 1 and orden_unidad > 1:
            # Verificar que la unidad anterior esté completada
            unidad_anterior = conn.execute(
                'SELECT id FROM unidades WHERE orden = ?', (orden_unidad - 1,)
            ).fetchone()
            
            if unidad_anterior:
                # Verificar que todas las lecciones de la unidad anterior estén aprobadas
                lecciones_no_aprobadas = conn.execute('''
                    SELECT COUNT(*) as pendientes FROM lecciones l
                    LEFT JOIN progreso_usuario p ON l.id = p.leccion_id AND p.usuario_id = ?
                    WHERE l.unidad_id = ? AND (p.aprobada IS NULL OR p.aprobada = 0)
                ''', (usuario_id, unidad_anterior['id'])).fetchone()
                
                if lecciones_no_aprobadas['pendientes'] > 0:
                    conn.close()
                    return False, "Debes completar la unidad anterior con calificación mínima de 7/10 en todas las lecciones"
            
            conn.close()
            return True, "Unidad anterior completada"
        
        # Caso 3: Lección posterior en la misma unidad
        # Buscar la lección anterior en la misma unidad
        leccion_anterior = conn.execute('''
            SELECT l.id, l.titulo, p.calificacion, p.aprobada
            FROM lecciones l
            LEFT JOIN progreso_usuario p ON l.id = p.leccion_id AND p.usuario_id = ?
            WHERE l.unidad_id = ? AND l.orden = ?
        ''', (usuario_id, unidad_id, orden_leccion - 1)).fetchone()
        
        if leccion_anterior:
            if leccion_anterior['aprobada'] == 1:
                conn.close()
                return True, "Lección anterior aprobada"
            else:
                calificacion = leccion_anterior['calificacion'] or 0
                conn.close()
                return False, f"Debes obtener mínimo 7/10 en '{leccion_anterior['titulo']}' (tu calificación actual: {calificacion}/10)"
        
        conn.close()
        return True, "Lección disponible"
    
    @staticmethod
    def obtener_estadisticas(usuario_id):
        """Obtiene estadísticas generales del usuario"""
        conn = get_db_connection()
        stats = conn.execute('''
            SELECT 
                COUNT(DISTINCT CASE WHEN p.aprobada = 1 THEN p.leccion_id END) as lecciones_aprobadas,
                COUNT(DISTINCT CASE WHEN p.completada = 1 THEN p.leccion_id END) as lecciones_completadas,
                COUNT(DISTINCT l.id) as total_lecciones,
                COALESCE(AVG(CASE WHEN p.calificacion > 0 THEN p.calificacion END), 0) as promedio_general
            FROM lecciones l
            LEFT JOIN progreso_usuario p ON l.id = p.leccion_id AND p.usuario_id = ?
        ''', (usuario_id,)).fetchone()
        conn.close()
        return stats
    
    @staticmethod
    def obtener_progreso_unidades(usuario_id):
        """Obtiene el progreso de cada unidad con calificaciones"""
        conn = get_db_connection()
        progreso_unidades = conn.execute('''
            SELECT 
                u.id as unidad_id,
                u.numero,
                u.titulo,
                u.orden,
                COUNT(DISTINCT l.id) as total_lecciones,
                COUNT(DISTINCT CASE WHEN p.aprobada = 1 THEN l.id END) as lecciones_aprobadas,
                COALESCE(AVG(CASE WHEN p.calificacion > 0 THEN p.calificacion END), 0) as promedio_unidad,
                CASE 
                    WHEN COUNT(DISTINCT l.id) > 0 AND 
                         COUNT(DISTINCT CASE WHEN p.aprobada = 1 THEN l.id END) = COUNT(DISTINCT l.id)
                    THEN 1
                    ELSE 0
                END as unidad_completada
            FROM unidades u
            LEFT JOIN lecciones l ON u.id = l.unidad_id
            LEFT JOIN progreso_usuario p ON l.id = p.leccion_id AND p.usuario_id = ?
            GROUP BY u.id, u.numero, u.titulo, u.orden
            ORDER BY u.orden
        ''', (usuario_id,)).fetchall()
        conn.close()
        return progreso_unidades
    
    @staticmethod
    def calcular_promedio_final(usuario_id):
        """
        Calcula el promedio final de la asignatura.
        
        Promedio Final = Σ(promedios_unidades) / 5
        
        Returns:
            float: Promedio final (0-10)
        """
        progreso_unidades = Progreso.obtener_progreso_unidades(usuario_id)
        
        if not progreso_unidades:
            return 0.0
        
        total_promedios = sum(pu['promedio_unidad'] or 0 for pu in progreso_unidades)
        num_unidades = len(progreso_unidades)
        
        if num_unidades == 0:
            return 0.0
        
        return round(total_promedios / num_unidades, 2)