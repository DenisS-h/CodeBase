from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
from database import init_db, get_db_connection
from models import Usuario, Unidad, Leccion, Progreso, Ejercicio
# Email service deshabilitado para Render.com (SMTP no funciona)
# from email_service import init_mail, enviar_email_bienvenida, debug_email_config
import os
import random
import time
from werkzeug.utils import secure_filename
from flask import send_from_directory
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
# Usar variable de entorno para SECRET_KEY, con fallback para desarrollo local
app.secret_key = os.getenv('SECRET_KEY', 'clave_secreta_super_segura_12345')

# Servicio de email deshabilitado para Render.com
# init_mail(app)
# debug_email_config()

# Configuración de subida de archivos
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/uploads/perfiles')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Asegurar que existe el directorio
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

with app.app_context():
    init_db()

# Contexto procesador para hacer las unidades disponibles en todos los templates
@app.context_processor
def inject_unidades():
    unidades = Unidad.obtener_todas()
    return dict(unidades=unidades)

# Decoradores de autenticación
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('login'))
        
        # Verificar si es admin en sesión primero para evitar consultas extra
        if not session.get('es_admin'):
            # Doble verificación en BD por seguridad
            usuario = Usuario.obtener_por_id(session['usuario_id'])
            if not usuario or not usuario['es_admin']:
                flash('Acceso denegado. Se requieren permisos de administrador.', 'error')
                return redirect(url_for('dashboard'))
            # Actualizar sesión si es necesario
            session['es_admin'] = 1
        
        return f(*args, **kwargs)
    return decorated_function

def user_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('login'))
        
        # Si es admin, redirigir al panel de admin
        if session.get('es_admin'):
            return redirect(url_for('admin_dashboard'))
            
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if 'usuario_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.before_request
def check_password_change_required():
    """Middleware para forzar cambio de contraseña si es necesario"""
    # Lista de endpoints permitidos (estáticos, logout, cambio de pass)
    allowed_endpoints = ['static', 'logout', 'cambiar_password_obligatorio']
    
    if 'usuario_id' in session and session.get('requiere_cambio'):
        if request.endpoint and request.endpoint not in allowed_endpoints:
            return redirect(url_for('cambiar_password_obligatorio'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        usuario = Usuario.verificar_password(email, password)
        
        if usuario:
            session['usuario_id'] = usuario['id']
            session['nombre'] = usuario['nombre_completo']
            session['racha'] = usuario['racha_dias']
            session['es_admin'] = usuario['es_admin']
            
            # Verificar si requiere cambio de contraseña
            try:
                session['requiere_cambio'] = usuario['requiere_cambio_password']
            except:
                session['requiere_cambio'] = 0
            
            if usuario['activo'] == 0:
                session.clear()
                flash('Tu cuenta ha sido desactivada. Contacta al administrador.', 'error')
                return render_template('login.html')
                
            flash('¡Bienvenido de nuevo!', 'success')
            
            if usuario['es_admin']:
                return redirect(url_for('admin_dashboard'))
                
            return redirect(url_for('dashboard'))
        else:
            flash('Email o contraseña incorrectos', 'error')
    
    return render_template('login.html')

@app.route('/recuperar-password', methods=['GET', 'POST'])
def recuperar_password():
    if request.method == 'POST':
        email = request.form.get('email')
        usuario = Usuario.obtener_por_email(email)
        
        if usuario:
            # Generar contraseña temporal aleatoria (8 caracteres)
            chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            password_temporal = ''.join(random.choice(chars) for _ in range(8))
            
            # Actualizar contraseña en la base de datos
            Usuario.admin_cambiar_password(usuario['id'], password_temporal)
            
            # Marcar que requiere cambio de contraseña obligatorio
            Usuario.marcar_cambio_password(usuario['id'], True)
            
            # Email deshabilitado para Render.com
            # from email_service import enviar_email_recuperacion
            # if enviar_email_recuperacion(usuario['nombre_completo'], email, password_temporal):
            #     flash('Se ha enviado una nueva contraseña a tu correo', 'success')
            #     return redirect(url_for('login'))
            # else:
            #     flash('Error al enviar el correo. Intenta nuevamente.', 'error')
            
            # Mostrar contraseña temporal directamente (solo para desarrollo/producción sin email)
            flash(f'Tu nueva contraseña temporal es: {password_temporal}. Por favor, cámbiala después de iniciar sesión.', 'info')
            return redirect(url_for('login'))
        else:
            flash('Si el correo existe, recibirás instrucciones en breve', 'info')
            return redirect(url_for('login'))
            
    return render_template('recuperar_password.html')

@app.route('/cambiar-password-obligatorio', methods=['GET', 'POST'])
def cambiar_password_obligatorio():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
        
    if not session.get('requiere_cambio'):
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        password = request.form.get('password')
        confirmar_password = request.form.get('confirmar_password')
        
        if password != confirmar_password:
            flash('Las contraseñas no coinciden', 'error')
            return render_template('cambiar_password_obligatorio.html')
            
        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres', 'error')
            return render_template('cambiar_password_obligatorio.html')
            
        # Actualizar contraseña y quitar flag
        Usuario.admin_cambiar_password(session['usuario_id'], password)
        Usuario.marcar_cambio_password(session['usuario_id'], False)
        
        # Actualizar sesión
        session['requiere_cambio'] = 0
        flash('Contraseña actualizada exitosamente. ¡Bienvenido!', 'success')
        return redirect(url_for('dashboard'))
        
    return render_template('cambiar_password_obligatorio.html')

@app.route('/perfil', methods=['GET', 'POST'])
@user_required
def perfil():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
        
    usuario = Usuario.obtener_por_id(session['usuario_id'])
    
    if request.method == 'POST':
        email = request.form.get('email')
        file = request.files.get('foto_perfil')
        
        # Validar email único si cambió
        if email != usuario['email']:
            if Usuario.obtener_por_email(email):
                flash('El correo electrónico ya está en uso', 'error')
                return render_template('perfil.html', usuario=usuario)
        
        filename = usuario['foto_perfil'] # Mantener el actual si no hay cambios
        
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Agregar timestamp para evitar cache
            import time
            filename = f"{int(time.time())}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            # Actualizar sesión con nueva foto
            session['foto_perfil'] = filename
            
        Usuario.actualizar_datos(usuario['id'], email, filename if file else None)
        
        # Actualizar email en sesión también
        session['email'] = email
        
        flash('Perfil actualizado exitosamente', 'success')
        return redirect(url_for('perfil'))
        
    return render_template('perfil.html', usuario=usuario)

@app.route('/uploads/perfiles/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/check-email/<email>')
def check_email(email):
    usuario = Usuario.obtener_por_email(email)
    return jsonify({'exists': bool(usuario)})

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        password = request.form.get('password')
        confirmar_password = request.form.get('confirmar_password')
        
        if password != confirmar_password:
            flash('Las contraseñas no coinciden', 'error')
            return render_template('registro.html')
        
        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres', 'error')
            return render_template('registro.html')
        
        if Usuario.obtener_por_email(email):
            flash('El email ya está registrado', 'error')
            return render_template('registro.html')
        
        usuario_id = Usuario.crear(nombre, email, password)
        
        if usuario_id:
            # Email de bienvenida deshabilitado para Render.com
            # enviar_email_bienvenida(nombre, email)
            
            session['usuario_id'] = usuario_id
            session['nombre'] = nombre
            session['racha'] = 0
            flash('¡Registro exitoso! Comienza tu aprendizaje', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Error al crear la cuenta', 'error')
    
    return render_template('registro.html')

@app.route('/aprender')
@app.route('/aprender/<int:unidad_id>')
@user_required
def aprender(unidad_id=1):
    
    # Obtener todas las unidades para el menú
    todas_unidades = Unidad.obtener_todas()
    
    # Obtener información de la unidad seleccionada
    unidad = Unidad.obtener_por_id(unidad_id)
    if not unidad:
        flash('Unidad no encontrada', 'error')
        return redirect(url_for('dashboard'))
    
    lecciones = Leccion.obtener_por_unidad(unidad_id)
    
    # Obtener PDFs de la unidad
    conn = get_db_connection()
    pdfs = conn.execute('''
        SELECT * FROM contenido_pdf 
        WHERE unidad_id = ? 
        ORDER BY fecha_subida DESC
    ''', (unidad_id,)).fetchall()
    conn.close()
    pdfs_list = [dict(pdf) for pdf in pdfs]
    
    return render_template('aprender.html', 
                         unidad=unidad,
                         lecciones=lecciones,
                         todas_unidades=todas_unidades,
                         pdfs=pdfs_list)

@app.route('/dashboard')
@user_required
def dashboard():
    usuario_id = session['usuario_id']
    usuario = Usuario.obtener_por_id(usuario_id)
    
    # Validar que el usuario existe (por si se reinicializó la base de datos)
    if not usuario:
        session.clear()
        flash('Tu sesión ha expirado. Por favor, inicia sesión nuevamente', 'error')
        return redirect(url_for('login'))
    
    unidades = Unidad.obtener_todas()
    progreso = Progreso.obtener_progreso_usuario(usuario_id)
    stats = Progreso.obtener_estadisticas(usuario_id)
    progreso_unidades = Progreso.obtener_progreso_unidades(usuario_id)
    
    # Calcular promedio final
    promedio_final = Progreso.calcular_promedio_final(usuario_id)
    
    session['racha'] = usuario['racha_dias']
    
    # Crear diccionario de progreso por lección_id para acceso rápido
    progreso_dict = {}
    for p in progreso:
        progreso_dict[p['id']] = dict(p)
    
    # Obtener todas las lecciones de cada unidad y combinar con progreso
    # También calcular estado de desbloqueo
    unidades_progreso = {}
    for unidad in unidades:
        lecciones = Leccion.obtener_por_unidad(unidad['id'])
        lecciones_con_progreso = []
        
        for leccion in lecciones:
            leccion_dict = dict(leccion)
            
            # Verificar si está desbloqueada
            desbloqueada, mensaje_bloqueo = Progreso.verificar_leccion_desbloqueada(usuario_id, leccion['id'])
            leccion_dict['desbloqueada'] = desbloqueada
            leccion_dict['mensaje_bloqueo'] = mensaje_bloqueo
            
            if leccion['id'] in progreso_dict:
                prog = progreso_dict[leccion['id']]
                leccion_dict['completada'] = prog.get('completada', 0) or 0
                leccion_dict['calificacion'] = prog.get('calificacion', 0) or 0
                leccion_dict['aprobada'] = prog.get('aprobada', 0) or 0
                leccion_dict['intentos'] = prog.get('intentos', 0) or 0
            else:
                leccion_dict['completada'] = 0
                leccion_dict['calificacion'] = 0
                leccion_dict['aprobada'] = 0
                leccion_dict['intentos'] = 0
            
            lecciones_con_progreso.append(leccion_dict)
        
        unidades_progreso[unidad['id']] = lecciones_con_progreso
    
    # Convertir progreso_unidades a diccionario para fácil acceso
    progreso_unidades_dict = {}
    todas_completadas = True
    for pu in progreso_unidades:
        pu_dict = dict(pu)
        progreso_unidades_dict[pu_dict['unidad_id']] = pu_dict
        if not pu_dict['unidad_completada']:
            todas_completadas = False
    
    return render_template('dashboard.html', 
                         usuario=usuario,
                         unidades=unidades,
                         unidades_progreso=unidades_progreso,
                         progreso_unidades=progreso_unidades_dict,
                         todas_unidades_completadas=todas_completadas,
                         promedio_final=promedio_final,
                         stats=stats)

# NUEVAS RUTAS PARA LECCIONES

@app.route('/leccion/<int:leccion_id>')
@user_required
def leccion(leccion_id):
    
    usuario_id = session['usuario_id']
    usuario = Usuario.obtener_por_id(usuario_id)
    
    # Validar que el usuario existe (por si se reinicializó la base de datos)
    if not usuario:
        session.clear()
        flash('Tu sesión ha expirado. Por favor, inicia sesión nuevamente', 'error')
        return redirect(url_for('login'))
    
    leccion_data = Leccion.obtener_por_id(leccion_id)
    
    if not leccion_data:
        flash('Lección no encontrada', 'error')
        return redirect(url_for('dashboard'))
    
    # Verificar si la lección está desbloqueada (nuevo sistema de calificaciones)
    desbloqueada, mensaje = Progreso.verificar_leccion_desbloqueada(usuario_id, leccion_id)
    if not desbloqueada:
        flash(mensaje, 'error')
        return redirect(url_for('dashboard'))
    
    # Obtener ejercicios de la lección
    ejercicios_raw = Ejercicio.obtener_por_leccion(leccion_id)
    total_ejercicios = len(ejercicios_raw)
    
    # Mezclar opciones aleatoriamente para cada ejercicio de opción múltiple
    ejercicios = []
    letras_base = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']
    
    for ejercicio in ejercicios_raw:
        ejercicio_dict = dict(ejercicio)
        
        # Solo mezclar si es opción múltiple
        if ejercicio_dict['tipo'] == 'opcion_multiple':
            # Separar las opciones
            opciones_lista = ejercicio_dict['opciones'].split('|')
            
            # Crear lista de tuplas (letra, texto)
            opciones_con_letras = []
            for opcion in opciones_lista:
                partes = opcion.split(')', 1)
                if len(partes) == 2:
                    letra_original = partes[0].strip()
                    texto = partes[1].strip()
                    opciones_con_letras.append((letra_original, texto))
            
            # Encontrar la respuesta correcta original
            respuesta_correcta_original = ejercicio_dict['respuesta_correcta'].strip().lower()
            respuesta_correcta_texto = None
            
            # Buscar el texto de la respuesta correcta
            for letra, texto in opciones_con_letras:
                if letra.lower() == respuesta_correcta_original:
                    respuesta_correcta_texto = texto
                    break
            
            # Mezclar las opciones aleatoriamente
            random.shuffle(opciones_con_letras)
            
            # Generar letras suficientes para todas las opciones
            num_opciones = len(opciones_con_letras)
            # Usar las letras base disponibles, o generar más si es necesario
            if num_opciones <= len(letras_base):
                letras_opciones = letras_base[:num_opciones]
            else:
                # Si hay más de 26 opciones, usar letras duplicadas con números (a1, a2, etc.)
                letras_opciones = letras_base.copy()
                for i in range(len(letras_base), num_opciones):
                    letra_base = letras_base[i % len(letras_base)]
                    numero = (i // len(letras_base)) + 1
                    letras_opciones.append(f"{letra_base}{numero}")
            
            # Reconstruir las opciones con nuevas letras
            opciones_mezcladas = []
            nueva_respuesta_correcta = None
            
            for i, (letra_original, texto) in enumerate(opciones_con_letras):
                nueva_letra = letras_opciones[i] if i < len(letras_opciones) else letra_original
                opciones_mezcladas.append(f"{nueva_letra}) {texto}")
                
                # Si este texto es la respuesta correcta, guardar la nueva letra
                if texto == respuesta_correcta_texto:
                    nueva_respuesta_correcta = nueva_letra.lower() if isinstance(nueva_letra, str) else str(nueva_letra).lower()
            
            # Actualizar el ejercicio con opciones mezcladas y nueva respuesta correcta
            ejercicio_dict['opciones'] = '|'.join(opciones_mezcladas)
            ejercicio_dict['respuesta_correcta'] = nueva_respuesta_correcta or ejercicio_dict['respuesta_correcta']
        
        ejercicios.append(ejercicio_dict)
    
    # Obtener unidad
    unidad = Unidad.obtener_por_id(leccion_data['unidad_id'])
    
    # Verificar progreso actual
    progreso = Progreso.obtener_leccion_usuario(usuario_id, leccion_id)
    
    return render_template('leccion.html',
                         leccion=leccion_data,
                         unidad=unidad,
                         ejercicios=ejercicios,
                         total_ejercicios=total_ejercicios,
                         usuario=usuario,
                         progreso=progreso)

@app.route('/verificar_respuesta', methods=['POST'])
@user_required
def verificar_respuesta():
    if 'usuario_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    
    usuario_id = session['usuario_id']
    usuario = Usuario.obtener_por_id(usuario_id)
    
    if not usuario:
        session.clear()
        return jsonify({'error': 'Sesión expirada'}), 401
    
    data = request.get_json()
    ejercicio_id = data.get('ejercicio_id')
    respuesta_usuario = data.get('respuesta')
    
    ejercicio = Ejercicio.obtener_por_id(ejercicio_id)
    
    if not ejercicio:
        return jsonify({'error': 'Ejercicio no encontrado'}), 404
    
    # Obtener la respuesta correcta mezclada del request (enviada desde el frontend)
    respuesta_correcta_mezclada = data.get('respuesta_correcta_mezclada')
    
    # Manejar diferentes tipos de ejercicios
    if ejercicio['tipo'] == 'fill_in_blank':
        # Para fill in the blank, el usuario escribe el código completo
        respuesta_correcta_db = ejercicio['respuesta_correcta'].strip().lower()
        respuesta_usuario_lower = respuesta_usuario.strip().lower()
        
        # Normalizar espacios en blanco múltiples y saltos de línea
        respuesta_usuario_normalizada = ' '.join(respuesta_usuario_lower.split())
        
        # Si la respuesta tiene múltiples partes separadas por |
        if '|' in respuesta_correcta_db:
            partes_correctas = [p.strip().lower() for p in respuesta_correcta_db.split('|')]
            es_correcta = all(
                parte in respuesta_usuario_normalizada or 
                f' {parte} ' in f' {respuesta_usuario_normalizada} ' or
                respuesta_usuario_normalizada.startswith(parte + ' ') or
                respuesta_usuario_normalizada.endswith(' ' + parte) or
                respuesta_usuario_normalizada == parte
                for parte in partes_correctas
            )
            respuesta_correcta_verificar = '|'.join(partes_correctas)
        else:
            respuesta_correcta_normalizada = respuesta_correcta_db.strip().lower()
            es_correcta = (
                respuesta_correcta_normalizada in respuesta_usuario_normalizada or
                f' {respuesta_correcta_normalizada} ' in f' {respuesta_usuario_normalizada} ' or
                respuesta_usuario_normalizada.startswith(respuesta_correcta_normalizada + ' ') or
                respuesta_usuario_normalizada.endswith(' ' + respuesta_correcta_normalizada) or
                respuesta_usuario_normalizada == respuesta_correcta_normalizada or
                respuesta_usuario_normalizada.startswith(respuesta_correcta_normalizada + '(') or
                respuesta_usuario_normalizada.endswith('(' + respuesta_correcta_normalizada + ')')
            )
            respuesta_correcta_verificar = respuesta_correcta_normalizada
    elif ejercicio['tipo'] == 'verdadero_falso':
        respuesta_correcta_db = ejercicio['respuesta_correcta'].strip().lower()
        respuesta_usuario_lower = respuesta_usuario.strip().lower()
        es_correcta = respuesta_usuario_lower == respuesta_correcta_db
        respuesta_correcta_verificar = respuesta_correcta_db
    else:
        # Para opción múltiple
        respuesta_correcta_mezclada = data.get('respuesta_correcta_mezclada')
        if respuesta_correcta_mezclada:
            respuesta_correcta_verificar = respuesta_correcta_mezclada.strip().lower()
        else:
            respuesta_correcta_verificar = ejercicio['respuesta_correcta'].strip().lower()
        
        es_correcta = respuesta_usuario.strip().lower() == respuesta_correcta_verificar
    
    # Determinar qué respuesta correcta mostrar en el feedback
    respuesta_correcta_feedback = None
    if not es_correcta:
        if ejercicio['tipo'] == 'fill_in_blank':
            if '|' in ejercicio['respuesta_correcta']:
                respuesta_correcta_feedback = '|'.join([p.strip() for p in ejercicio['respuesta_correcta'].split('|')])
            else:
                respuesta_correcta_feedback = ejercicio['respuesta_correcta'].strip()
        elif ejercicio['tipo'] == 'opcion_multiple':
            respuesta_correcta_mezclada = data.get('respuesta_correcta_mezclada')
            respuesta_correcta_feedback = respuesta_correcta_mezclada if respuesta_correcta_mezclada else ejercicio['respuesta_correcta'].strip()
        elif ejercicio['tipo'] == 'verdadero_falso':
            respuesta_correcta_feedback = ejercicio['respuesta_correcta'].strip().capitalize()
        else:
            respuesta_correcta_feedback = ejercicio['respuesta_correcta'].strip()
    
    return jsonify({
        'correcta': es_correcta,
        'explicacion': ejercicio['explicacion'],
        'respuesta_correcta': respuesta_correcta_feedback
    })

@app.route('/completar_leccion', methods=['POST'])
@user_required
def completar_leccion():
    print(">>> PETICION RECIBIDA EN /completar_leccion")
    try:
        if 'usuario_id' not in session:
            print(">>> ERROR: No hay usuario_id en sesión")
            return jsonify({'error': 'No autorizado'}), 401
        
        usuario_id = session['usuario_id']
        usuario = Usuario.obtener_por_id(usuario_id)
        
        if not usuario:
            session.clear()
            return jsonify({'error': 'Sesión expirada'}), 401
        
        data = request.get_json()
        leccion_id = data.get('leccion_id')
        respuestas_correctas = data.get('respuestas_correctas', 0)
        total_ejercicios = data.get('total_ejercicios', 0)
        
        # Calcular calificación (0-10)
        if total_ejercicios > 0:
            calificacion = (respuestas_correctas / total_ejercicios) * 10
        else:
            calificacion = 0
        
        # Obtener información de la lección
        leccion_data = Leccion.obtener_por_id(leccion_id)
        unidad_id = leccion_data['unidad_id'] if leccion_data else None
        
        # Guardar calificación (solo si es mejor que la anterior)
        resultado = Progreso.guardar_calificacion(
            usuario_id, 
            leccion_id, 
            calificacion,
            respuestas_correctas,
            total_ejercicios
        )
        
        # Verificar si la unidad está completa
        unidad_completada = False
        todas_unidades_completadas = False
        
        if unidad_id:
            progreso_unidades = Progreso.obtener_progreso_unidades(usuario_id)
            for pu in progreso_unidades:
                if pu['unidad_id'] == unidad_id:
                    unidad_completada = pu['unidad_completada'] == 1
                    break
            
            # Verificar si todas las unidades están completadas
            todas_completadas = True
            for pu in progreso_unidades:
                if pu['unidad_completada'] == 0:
                    todas_completadas = False
                    break
            todas_unidades_completadas = todas_completadas
        
        # Calcular promedio final actualizado
        promedio_final = Progreso.calcular_promedio_final(usuario_id)
        
        # Determinar mensaje según resultado
        if resultado['aprobada']:
            if resultado['es_mejor']:
                mensaje = f'¡Excelente! Obtuviste {resultado["calificacion"]}/10. Lección aprobada.'
            else:
                mensaje = f'Obtuviste {calificacion:.1f}/10. Tu mejor calificación sigue siendo {resultado["calificacion_guardada"]}/10.'
        else:
            mensaje = f'Obtuviste {resultado["calificacion"]}/10. Necesitas mínimo 7/10 para desbloquear la siguiente lección. ¡Inténtalo de nuevo!'
        
        return jsonify({
            'success': True,
            'calificacion': resultado['calificacion'],
            'calificacion_guardada': resultado['calificacion_guardada'],
            'aprobada': resultado['aprobada'],
            'es_mejor': resultado['es_mejor'],
            'respuestas_correctas': respuestas_correctas,
            'total_ejercicios': total_ejercicios,
            'mensaje': mensaje,
            'unidad_completada': unidad_completada,
            'todas_unidades_completadas': todas_unidades_completadas,
            'promedio_final': promedio_final
        })
    except Exception as e:
        import traceback
        print(f"ERROR en completar_leccion: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada correctamente', 'info')
    return redirect(url_for('login'))

# RUTAS DE ADMINISTRACIÓN


@app.route('/calificaciones')
@user_required
def calificaciones():
    usuario_id = session['usuario_id']
    usuario = Usuario.obtener_por_id(usuario_id)
    
    # Obtener progreso detallado
    progreso_raw = Progreso.obtener_progreso_usuario(usuario_id)
    progreso_unidades_raw = Progreso.obtener_progreso_unidades(usuario_id)
    
    # Organizar por unidades
    unidades_map = {}
    for item in progreso_raw:
        unidad_num = item['unidad_numero']
        if unidad_num not in unidades_map:
            unidades_map[unidad_num] = {
                'numero': unidad_num,
                'titulo': '', 
                'lecciones': [],
                'promedio': 0,
                'completada': True
            }
        
        leccion = dict(item)
        unidades_map[unidad_num]['lecciones'].append(leccion)
        
        if not item['aprobada']:
            unidades_map[unidad_num]['completada'] = False

    # Calcular promedios por unidad y obtener títulos
    unidades_info = Unidad.obtener_todas()
    for u in unidades_info:
        if u['numero'] in unidades_map:
            unidades_map[u['numero']]['titulo'] = u['titulo']
    
    # Calcular promedios por unidad desde progreso_unidades_raw
    for pu in progreso_unidades_raw:
        if pu['numero'] in unidades_map:
            unidades_map[pu['numero']]['promedio'] = round(pu['promedio_unidad'] or 0, 2)
    
    # Calcular promedio final
    promedio_final = Progreso.calcular_promedio_final(usuario_id)

    return render_template('calificaciones.html', 
                         usuario=usuario, 
                         unidades_progreso=unidades_map,
                         promedio_final=promedio_final)

@app.route('/certificado')
@user_required
def certificado():
    usuario_id = session['usuario_id']
    usuario = Usuario.obtener_por_id(usuario_id)
    
    # Verificar si completó todas las unidades
    progreso_unidades = Progreso.obtener_progreso_unidades(usuario_id)
    
    todas_completadas = True
    total_unidades = len(progreso_unidades)
    unidades_completadas = 0
    
    for pu in progreso_unidades:
        if pu['unidad_completada']:
            unidades_completadas += 1
        else:
            todas_completadas = False
            
    porcentaje_avance = int((unidades_completadas / total_unidades) * 100) if total_unidades > 0 else 0
    
    # Calcular promedio final
    promedio_final = Progreso.calcular_promedio_final(usuario_id)
    
    return render_template('certificado.html', 
                         usuario=usuario, 
                         todas_completadas=todas_completadas,
                         porcentaje_avance=porcentaje_avance,
                         promedio_final=promedio_final,
                         fecha=usuario['fecha_registro'])

@app.route('/admin')
@admin_required
def admin_dashboard():
    stats = {
        'total_usuarios': len(Usuario.obtener_todos()),
        'unidades': len(Unidad.obtener_todas())
    }
    return render_template('admin/dashboard.html', stats=stats)

@app.route('/admin/usuarios')
@admin_required
def admin_usuarios():
    usuarios = Usuario.obtener_todos()
    return render_template('admin/usuarios.html', usuarios=usuarios)

@app.route('/admin/usuarios/<int:usuario_id>/estado', methods=['POST'])
@admin_required
def admin_cambiar_estado(usuario_id):
    data = request.get_json()
    activo = data.get('activo')
    
    # Evitar desactivarse a uno mismo
    if usuario_id == session['usuario_id']:
        return jsonify({'success': False, 'message': 'No puedes desactivar tu propia cuenta'}), 400
        
    Usuario.actualizar_estado(usuario_id, activo)
    return jsonify({'success': True})

@app.route('/admin/usuarios/<int:usuario_id>/password', methods=['POST'])
@admin_required
def admin_cambiar_password(usuario_id):
    data = request.get_json()
    new_password = data.get('password')
    
    if len(new_password) < 6:
        return jsonify({'success': False, 'message': 'La contraseña debe tener al menos 6 caracteres'}), 400
        
    Usuario.admin_cambiar_password(usuario_id, new_password)
    return jsonify({'success': True})

@app.route('/admin/progreso')
@admin_required
def admin_progreso():
    """Página para ver el progreso detallado de todos los usuarios"""
    usuarios = Usuario.obtener_todos()
    unidades = Unidad.obtener_todas()
    
    # Obtener progreso detallado de cada usuario
    usuarios_progreso = []
    for usuario in usuarios:
        if not usuario['es_admin']:  # Solo mostrar estudiantes
            progreso_usuario = Progreso.obtener_progreso_usuario(usuario['id'])
            progreso_unidades = Progreso.obtener_progreso_unidades(usuario['id'])
            promedio_final = Progreso.calcular_promedio_final(usuario['id'])
            stats = Progreso.obtener_estadisticas(usuario['id'])
            
            usuarios_progreso.append({
                'usuario': usuario,
                'progreso': progreso_usuario,
                'progreso_unidades': progreso_unidades,
                'promedio_final': promedio_final,
                'stats': stats
            })
    
    return render_template('admin/progreso.html', 
                         usuarios_progreso=usuarios_progreso,
                         unidades=unidades)

@app.route('/admin/contenido')
@admin_required
def admin_contenido():
    """Página principal para gestionar contenido"""
    return render_template('admin/contenido.html')

@app.route('/admin/contenido/ejercicios')
@admin_required
def admin_ejercicios():
    """Página para gestionar ejercicios"""
    unidades = Unidad.obtener_todas()
    lecciones_por_unidad = {}
    for unidad in unidades:
        lecciones = Leccion.obtener_por_unidad(unidad['id'])
        # Convertir objetos Row a diccionarios para que sean serializables a JSON
        lecciones_por_unidad[unidad['id']] = [dict(leccion) for leccion in lecciones]
    
    return render_template('admin/ejercicios.html',
                         unidades=unidades,
                         lecciones_por_unidad=lecciones_por_unidad)

@app.route('/admin/contenido/pdf')
@admin_required
def admin_pdf():
    """Página para gestionar PDFs"""
    unidades = Unidad.obtener_todas()
    return render_template('admin/pdf.html', unidades=unidades)

@app.route('/admin/contenido/ejercicios/<int:leccion_id>', methods=['GET'])
@admin_required
def admin_obtener_ejercicios(leccion_id):
    """Obtener todos los ejercicios de una lección"""
    ejercicios = Ejercicio.obtener_por_leccion(leccion_id)
    ejercicios_list = [dict(ej) for ej in ejercicios]
    return jsonify({'success': True, 'ejercicios': ejercicios_list})

@app.route('/admin/contenido/ejercicio', methods=['POST'])
@admin_required
def admin_agregar_ejercicio():
    """Agregar un nuevo ejercicio a una lección"""
    data = request.get_json()
    
    leccion_id = data.get('leccion_id')
    tipo = data.get('tipo')
    pregunta = data.get('pregunta')
    opciones = data.get('opciones', '')
    respuesta_correcta = data.get('respuesta_correcta')
    explicacion = data.get('explicacion', '')
    puntos = data.get('puntos', 10)
    
    if not all([leccion_id, tipo, pregunta, respuesta_correcta]):
        return jsonify({'success': False, 'message': 'Faltan campos requeridos'}), 400
    
    # Verificar que la lección existe
    leccion = Leccion.obtener_por_id(leccion_id)
    if not leccion:
        return jsonify({'success': False, 'message': 'Lección no encontrada'}), 404
    
    # Insertar ejercicio
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO ejercicios (leccion_id, tipo, pregunta, opciones, respuesta_correcta, explicacion, puntos)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (leccion_id, tipo, pregunta, opciones, respuesta_correcta, explicacion, puntos))
        conn.commit()
        ejercicio_id = cursor.lastrowid
        conn.close()
        return jsonify({'success': True, 'ejercicio_id': ejercicio_id})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/contenido/ejercicio/<int:ejercicio_id>', methods=['PUT', 'DELETE'])
@admin_required
def admin_gestionar_ejercicio(ejercicio_id):
    """Actualizar o eliminar un ejercicio"""
    conn = get_db_connection()
    
    if request.method == 'DELETE':
        try:
            conn.execute('DELETE FROM ejercicios WHERE id = ?', (ejercicio_id,))
            conn.commit()
            conn.close()
            return jsonify({'success': True})
        except Exception as e:
            conn.close()
            return jsonify({'success': False, 'message': str(e)}), 500
    
    elif request.method == 'PUT':
        data = request.get_json()
        try:
            conn.execute('''
                UPDATE ejercicios 
                SET tipo = ?, pregunta = ?, opciones = ?, respuesta_correcta = ?, explicacion = ?, puntos = ?
                WHERE id = ?
            ''', (
                data.get('tipo'),
                data.get('pregunta'),
                data.get('opciones', ''),
                data.get('respuesta_correcta'),
                data.get('explicacion', ''),
                data.get('puntos', 10),
                ejercicio_id
            ))
            conn.commit()
            conn.close()
            return jsonify({'success': True})
        except Exception as e:
            conn.close()
            return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/contenido/unidad/<int:unidad_id>', methods=['POST'])
@admin_required
def admin_actualizar_unidad(unidad_id):
    """Actualizar información de una unidad"""
    data = request.get_json()
    
    titulo = data.get('titulo')
    descripcion = data.get('descripcion')
    
    unidad = Unidad.obtener_por_id(unidad_id)
    if not unidad:
        return jsonify({'success': False, 'message': 'Unidad no encontrada'}), 404
    
    conn = get_db_connection()
    try:
        if titulo:
            conn.execute('UPDATE unidades SET titulo = ? WHERE id = ?', (titulo, unidad_id))
        if descripcion:
            conn.execute('UPDATE unidades SET descripcion = ? WHERE id = ?', (descripcion, unidad_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/contenido/leccion/<int:leccion_id>', methods=['POST'])
@admin_required
def admin_actualizar_leccion(leccion_id):
    """Actualizar información de una lección"""
    data = request.get_json()
    
    titulo = data.get('titulo')
    descripcion = data.get('descripcion')
    
    leccion = Leccion.obtener_por_id(leccion_id)
    if not leccion:
        return jsonify({'success': False, 'message': 'Lección no encontrada'}), 404
    
    conn = get_db_connection()
    try:
        if titulo:
            conn.execute('UPDATE lecciones SET titulo = ? WHERE id = ?', (titulo, leccion_id))
        if descripcion:
            conn.execute('UPDATE lecciones SET descripcion = ? WHERE id = ?', (descripcion, leccion_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/contenido/pdf/<int:unidad_id>', methods=['GET'])
@admin_required
def admin_obtener_pdfs(unidad_id):
    """Obtener todos los PDFs de una unidad"""
    conn = get_db_connection()
    pdfs = conn.execute('''
        SELECT * FROM contenido_pdf 
        WHERE unidad_id = ? 
        ORDER BY fecha_subida DESC
    ''', (unidad_id,)).fetchall()
    conn.close()
    pdfs_list = [dict(pdf) for pdf in pdfs]
    return jsonify({'success': True, 'pdfs': pdfs_list})

@app.route('/admin/contenido/pdf/<int:pdf_id>', methods=['DELETE'])
@admin_required
def admin_eliminar_pdf(pdf_id):
    """Eliminar un PDF"""
    conn = get_db_connection()
    try:
        # Obtener información del PDF antes de eliminarlo
        pdf = conn.execute('SELECT * FROM contenido_pdf WHERE id = ?', (pdf_id,)).fetchone()
        if not pdf:
            conn.close()
            return jsonify({'success': False, 'message': 'PDF no encontrado'}), 404
        
        # Eliminar archivo físico
        upload_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/uploads/pdf')
        filepath = os.path.join(upload_folder, pdf['ruta_archivo'])
        if os.path.exists(filepath):
            os.remove(filepath)
        
        # Eliminar registro de la base de datos
        conn.execute('DELETE FROM contenido_pdf WHERE id = ?', (pdf_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/contenido/pdf', methods=['POST'])
@admin_required
def admin_subir_pdf():
    """Subir y procesar un PDF para una unidad"""
    if 'archivo' not in request.files:
        return jsonify({'success': False, 'message': 'No se envió ningún archivo'}), 400
    
    archivo = request.files['archivo']
    unidad_id = request.form.get('unidad_id')
    
    if archivo.filename == '':
        return jsonify({'success': False, 'message': 'No se seleccionó ningún archivo'}), 400
    
    if not unidad_id:
        return jsonify({'success': False, 'message': 'Debe especificar una unidad'}), 400
    
    # Verificar extensión
    if not archivo.filename.lower().endswith('.pdf'):
        return jsonify({'success': False, 'message': 'El archivo debe ser un PDF'}), 400
    
    # Eliminar PDFs anteriores de esta unidad si existen
    conn = get_db_connection()
    pdfs_anteriores = conn.execute('SELECT * FROM contenido_pdf WHERE unidad_id = ?', (unidad_id,)).fetchall()
    upload_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/uploads/pdf')
    os.makedirs(upload_folder, exist_ok=True)
    
    for pdf_ant in pdfs_anteriores:
        filepath_ant = os.path.join(upload_folder, pdf_ant['ruta_archivo'])
        if os.path.exists(filepath_ant):
            os.remove(filepath_ant)
        conn.execute('DELETE FROM contenido_pdf WHERE id = ?', (pdf_ant['id'],))
    
    # Guardar el nuevo archivo
    filename = secure_filename(f"unidad_{unidad_id}_{int(time.time())}.pdf")
    filepath = os.path.join(upload_folder, filename)
    archivo.save(filepath)
    
    # Procesamiento básico del PDF (extracción de texto)
    texto_extraido = ""
    try:
        import PyPDF2
        with open(filepath, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            for page in pdf_reader.pages:
                texto_extraido += page.extract_text() + "\n"
    except ImportError:
        texto_extraido = None
    except Exception as e:
        texto_extraido = f"Error al extraer texto: {str(e)}"
    
    # Guardar información del PDF procesado
    try:
        conn.execute('''
            INSERT INTO contenido_pdf (unidad_id, nombre_archivo, ruta_archivo, texto_extraido, fecha_subida)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (unidad_id, archivo.filename, filename, texto_extraido))
        conn.commit()
        conn.close()
        
        if texto_extraido:
            preview = texto_extraido[:500] + '...' if len(texto_extraido) > 500 else texto_extraido
        else:
            preview = "Para extraer texto del PDF, instale PyPDF2: pip install PyPDF2"
        
        return jsonify({
            'success': True,
            'message': 'PDF guardado exitosamente',
            'texto_preview': preview,
            'archivo': filename
        })
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': f'Error al guardar información: {str(e)}'}), 500

@app.route('/uploads/pdf/<filename>')
def uploaded_pdf(filename):
    """Servir archivos PDF"""
    upload_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/uploads/pdf')
    return send_from_directory(upload_folder, filename)

if __name__ == '__main__':
    # Usar puerto dinámico para Render.com, con fallback para desarrollo local
    port = int(os.getenv('PORT', 5000))
    # Desactivar debug en producción
    debug_mode = os.getenv('FLASK_ENV') == 'development'
    app.run(debug=debug_mode, host='0.0.0.0', port=port)