import sqlite3
from datetime import datetime
import os
from urllib.parse import urlparse

# Detectar si estamos en producción (Render.com) o desarrollo local
DATABASE_URL = os.getenv('DATABASE_URL')

# Si hay DATABASE_URL, usar PostgreSQL; si no, usar SQLite
USE_POSTGRESQL = DATABASE_URL is not None

if USE_POSTGRESQL:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    # Parsear la URL de la base de datos
    parsed = urlparse(DATABASE_URL)
    DB_CONFIG = {
        'dbname': parsed.path[1:],  # Remover el '/' inicial
        'user': parsed.username,
        'password': parsed.password,
        'host': parsed.hostname,
        'port': parsed.port
    }
else:
    DATABASE_PATH = os.path.join('instance', 'aprendizaje.db')

class DatabaseConnection:
    """Wrapper para conexiones de base de datos que funciona con SQLite y PostgreSQL"""
    def __init__(self, conn, use_postgresql):
        self.conn = conn
        self.use_postgresql = use_postgresql
        if not use_postgresql:
            conn.row_factory = sqlite3.Row
    
    def execute(self, sql, params=None):
        """Ejecuta una consulta SQL adaptada para la base de datos correspondiente"""
        if self.use_postgresql:
            # Adaptar ? a %s para PostgreSQL
            sql = sql.replace('?', '%s')
            cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            # Devolver un objeto que tenga fetchone y fetchall
            class CursorWrapper:
                def __init__(self, cursor, use_postgresql):
                    self.cursor = cursor
                    self.use_postgresql = use_postgresql
                
                def fetchone(self):
                    row = self.cursor.fetchone()
                    return row if row else None
                
                def fetchall(self):
                    return self.cursor.fetchall()
                
                @property
                def lastrowid(self):
                    # PostgreSQL no tiene lastrowid, se usa RETURNING en la consulta
                    return None
            return CursorWrapper(cursor, True)
        else:
            # SQLite usa ? directamente
            cursor = self.conn.cursor()
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            return cursor
    
    def commit(self):
        """Hace commit de la transacción"""
        self.conn.commit()
    
    def close(self):
        """Cierra la conexión"""
        self.conn.close()
    
    @property
    def cursor(self):
        """Obtiene un cursor para operaciones avanzadas"""
        if self.use_postgresql:
            return self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        else:
            return self.conn.cursor()

def get_db_connection():
    """Obtiene una conexión a la base de datos (PostgreSQL o SQLite)"""
    if USE_POSTGRESQL:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = False
        return DatabaseConnection(conn, True)
    else:
        os.makedirs('instance', exist_ok=True)
        conn = sqlite3.connect(DATABASE_PATH)
        return DatabaseConnection(conn, False)

def adapt_sql(sql):
    """Adapta sentencias SQL para PostgreSQL o SQLite"""
    if USE_POSTGRESQL:
        # Adaptar para PostgreSQL
        sql = sql.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
        sql = sql.replace('BOOLEAN DEFAULT 0', 'BOOLEAN DEFAULT FALSE')
        sql = sql.replace('BOOLEAN DEFAULT 1', 'BOOLEAN DEFAULT TRUE')
        sql = sql.replace('INTEGER DEFAULT 0', 'INTEGER DEFAULT 0')  # Ya es compatible
        # SQLite usa ? para parámetros, PostgreSQL usa %s
        sql = sql.replace('?', '%s')
    return sql

def init_db():
    """Inicializa la base de datos con las tablas necesarias.
    Solo crea las tablas si no existen y solo inserta datos si la base de datos está vacía.
    No modifica ni elimina datos existentes."""
    
    conn = get_db_connection()
    if USE_POSTGRESQL:
        cursor = conn.cursor()
    else:
        cursor = conn.cursor()
    
    # Tabla de usuarios
    sql = '''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_completo TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            racha_dias INTEGER DEFAULT 0,
            puntos_totales INTEGER DEFAULT 0,
            nivel_actual INTEGER DEFAULT 1
        )
    '''
    cursor.execute(adapt_sql(sql))
    
    # Tabla de unidades (basado en el PEA)
    sql = '''
        CREATE TABLE IF NOT EXISTS unidades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero INTEGER NOT NULL,
            titulo TEXT NOT NULL,
            descripcion TEXT,
            orden INTEGER NOT NULL
        )
    '''
    cursor.execute(adapt_sql(sql))
    
    # Tabla de lecciones
    sql = '''
        CREATE TABLE IF NOT EXISTS lecciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unidad_id INTEGER NOT NULL,
            titulo TEXT NOT NULL,
            descripcion TEXT,
            puntos_requeridos INTEGER DEFAULT 0,
            orden INTEGER NOT NULL,
            FOREIGN KEY (unidad_id) REFERENCES unidades (id)
        )
    '''
    cursor.execute(adapt_sql(sql))
    
    # Tabla de ejercicios
    sql = '''
        CREATE TABLE IF NOT EXISTS ejercicios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            leccion_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            pregunta TEXT NOT NULL,
            opciones TEXT,
            respuesta_correcta TEXT NOT NULL,
            explicacion TEXT,
            puntos INTEGER DEFAULT 10,
            FOREIGN KEY (leccion_id) REFERENCES lecciones (id)
        )
    '''
    cursor.execute(adapt_sql(sql))
    
    # Tabla de progreso del usuario
    sql = '''
        CREATE TABLE IF NOT EXISTS progreso_usuario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            leccion_id INTEGER NOT NULL,
            completada BOOLEAN DEFAULT 0,
            calificacion REAL DEFAULT 0.0,
            aprobada INTEGER DEFAULT 0,
            intentos INTEGER DEFAULT 0,
            fecha_completado TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
            FOREIGN KEY (leccion_id) REFERENCES lecciones (id),
            UNIQUE(usuario_id, leccion_id)
        )
    '''
    cursor.execute(adapt_sql(sql))
    
    # Tabla para contenido PDF subido por admin
    sql = '''
        CREATE TABLE IF NOT EXISTS contenido_pdf (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unidad_id INTEGER NOT NULL,
            nombre_archivo TEXT NOT NULL,
            ruta_archivo TEXT NOT NULL,
            texto_extraido TEXT,
            fecha_subida TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (unidad_id) REFERENCES unidades (id)
        )
    '''
    cursor.execute(adapt_sql(sql))
    
    # Insertar unidades del curso de Python
    unidades_data = [
        (1, 'Introducción con Python', 'En esta unidad conocerás qué es Python y prepararás tu entorno para escribir tus primeras instrucciones. Aprenderás cómo el ordenador interpreta el código y cómo mostrar resultados en pantalla', 1),
        (2, 'Tipos de datos en Python', 'Para resolver problemas reales, necesitas manejar distintos tipos de información. Aprenderás a diferenciar entre texto, números y valores lógicos, y cómo guardarlos en la memoria', 2),
        (3, 'Operadores y condicionales', 'Aquí aprenderás a hacer que tu programa tome decisiones. Usarás símbolos matemáticos para comparar datos y crearás reglas para que el código haga cosas distintas según el caso', 3),
        (4, 'Listas y diccionarios', 'En lugar de tener datos sueltos, aprenderás a agruparlos. Verás cómo manejar colecciones de elementos de forma ordenada y cómo usar etiquetas para encontrar información rápidamente', 4),
        (5, 'Ciclos', 'La verdadera potencia de la programación es la repetición. Aprenderás a crear bucles que procesen miles de datos en segundos sin que tengas que escribir código extra', 5)
    ]
    
    cursor.execute('SELECT COUNT(*) FROM unidades')
    if cursor.fetchone()[0] == 0:
        cursor.executemany('''
            INSERT INTO unidades (numero, titulo, descripcion, orden)
            VALUES (?, ?, ?, ?)
        ''', unidades_data)
        
        # Insertar lecciones para Unidad 1: Introducción con Python
        lecciones_u1 = [
            (1, '¿Qué es Python y por qué es tan popular?', 'Conoce Python, sus características y por qué es uno de los lenguajes más utilizados en el mundo', 0, 1),
            (1, 'Tu primera línea de código: La función print()', 'Aprende a usar print() para mostrar mensajes y resultados en pantalla', 10, 2),
            (1, 'Cómo recibir información del usuario con input()', 'Usa input() para leer datos que el usuario escribe desde el teclado', 20, 3),
            (1, 'Comentarios: Cómo dejar notas en tu código para humanos', 'Aprende a escribir comentarios que expliquen tu código sin afectar su ejecución', 30, 4)
        ]
        
        cursor.executemany('''
            INSERT INTO lecciones (unidad_id, titulo, descripcion, puntos_requeridos, orden)
            VALUES (?, ?, ?, ?, ?)
        ''', lecciones_u1)
        
        # Insertar lecciones para Unidad 2: Tipos de datos en Python
        lecciones_u2 = [
            (2, 'Variables: Qué son y cómo nombrar tus contenedores de datos', 'Aprende qué son las variables y las reglas para nombrarlas correctamente en Python', 40, 1),
            (2, 'Textos (Strings) y números (Integers y Floats)', 'Diferencia entre textos, números enteros y decimales, y cómo usarlos', 50, 2),
            (2, 'Valores de verdad (Booleans): El concepto de Verdadero y Falso', 'Comprende los valores booleanos True y False y su importancia en la programación', 60, 3),
            (2, 'Conversión de datos: Cómo transformar un texto en un número y viceversa', 'Aprende a convertir entre diferentes tipos de datos usando int(), float() y str()', 70, 4)
        ]
        
        cursor.executemany('''
            INSERT INTO lecciones (unidad_id, titulo, descripcion, puntos_requeridos, orden)
            VALUES (?, ?, ?, ?, ?)
        ''', lecciones_u2)
        
        # Insertar lecciones para Unidad 3: Operadores y condicionales
        lecciones_u3 = [
            (3, 'Operadores aritméticos (suma, resta, multiplicación, división)', 'Usa los operadores +, -, *, / y otros para realizar cálculos matemáticos', 80, 1),
            (3, 'Comparaciones (mayor que, menor que, igual a)', 'Compara valores usando operadores como >, <, ==, != para tomar decisiones', 90, 2),
            (3, 'La estructura if y else: Tomando el camino A o el camino B', 'Crea programas que tomen decisiones usando las estructuras if y else', 100, 3),
            (3, 'Condiciones múltiples con elif y conectores lógicos (and, or)', 'Maneja múltiples condiciones usando elif y combina condiciones con and y or', 110, 4)
        ]
        
        cursor.executemany('''
            INSERT INTO lecciones (unidad_id, titulo, descripcion, puntos_requeridos, orden)
            VALUES (?, ?, ?, ?, ?)
        ''', lecciones_u3)
        
        # Insertar lecciones para Unidad 4: Listas y diccionarios
        lecciones_u4 = [
            (4, 'Listas: Cómo guardar muchos elementos en un solo lugar', 'Crea y usa listas para almacenar múltiples elementos de forma ordenada', 120, 1),
            (4, 'Manipulación de listas: Añadir, quitar y ordenar elementos', 'Aprende métodos como append(), remove(), insert() y sort() para modificar listas', 130, 2),
            (4, 'Diccionarios: Organizar datos mediante "Clave" y "Valor"', 'Usa diccionarios para almacenar datos organizados por claves y valores', 140, 3),
            (4, 'Acceder y modificar información dentro de un diccionario', 'Aprende a leer, actualizar y eliminar elementos de un diccionario', 150, 4)
        ]
        
        cursor.executemany('''
            INSERT INTO lecciones (unidad_id, titulo, descripcion, puntos_requeridos, orden)
            VALUES (?, ?, ?, ?, ?)
        ''', lecciones_u4)
        
        # Insertar lecciones para Unidad 5: Ciclos
        lecciones_u5 = [
            (5, 'El ciclo for: Cómo recorrer listas y grupos de datos', 'Usa el ciclo for para procesar cada elemento de una lista automáticamente', 160, 1),
            (5, 'La función range() para repeticiones numeradas', 'Genera secuencias de números con range() para controlar repeticiones', 170, 2),
            (5, 'El ciclo while: Repetir acciones mientras una condición sea cierta', 'Crea bucles que se ejecuten mientras una condición se cumpla usando while', 180, 3),
            (5, 'Cómo detener un ciclo o saltar pasos (break y continue)', 'Controla el flujo de los ciclos usando break para detener y continue para saltar iteraciones', 190, 4)
        ]
        
        cursor.executemany('''
            INSERT INTO lecciones (unidad_id, titulo, descripcion, puntos_requeridos, orden)
            VALUES (?, ?, ?, ?, ?)
        ''', lecciones_u5)
        
        # Obtener los IDs de las lecciones después de insertarlas
        cursor.execute('SELECT id FROM lecciones WHERE unidad_id = 1 AND orden = 1')
        leccion_u1_l1_id = cursor.fetchone()[0]  # ¿Qué es Python y por qué es tan popular?
        
        cursor.execute('SELECT id FROM lecciones WHERE unidad_id = 1 AND orden = 2')
        leccion_u1_l2_id = cursor.fetchone()[0]  # Tu primera línea de código: La función print()
        
        cursor.execute('SELECT id FROM lecciones WHERE unidad_id = 1 AND orden = 3')
        leccion_u1_l3_id = cursor.fetchone()[0]  # Cómo recibir información del usuario con input()
        
        cursor.execute('SELECT id FROM lecciones WHERE unidad_id = 1 AND orden = 4')
        leccion_u1_l4_id = cursor.fetchone()[0]  # Comentarios: Cómo dejar notas en tu código para humanos
        
        cursor.execute('SELECT id FROM lecciones WHERE unidad_id = 2 AND orden = 1')
        leccion_u2_l1_id = cursor.fetchone()[0]  # Variables: Qué son y cómo nombrar tus contenedores de datos
        
        cursor.execute('SELECT id FROM lecciones WHERE unidad_id = 2 AND orden = 2')
        leccion_u2_l2_id = cursor.fetchone()[0]  # Textos (Strings) y números (Integers y Floats)
        
        cursor.execute('SELECT id FROM lecciones WHERE unidad_id = 2 AND orden = 3')
        leccion_u2_l3_id = cursor.fetchone()[0]  # Valores de verdad (Booleans)
        
        cursor.execute('SELECT id FROM lecciones WHERE unidad_id = 2 AND orden = 4')
        leccion_u2_l4_id = cursor.fetchone()[0]  # Conversión de datos
        
        cursor.execute('SELECT id FROM lecciones WHERE unidad_id = 4 AND orden = 1')
        leccion_u4_l1_id = cursor.fetchone()[0]  # Listas: Cómo guardar muchos elementos
        
        cursor.execute('SELECT id FROM lecciones WHERE unidad_id = 4 AND orden = 2')
        leccion_u4_l2_id = cursor.fetchone()[0]  # Manipulación de listas
        
        cursor.execute('SELECT id FROM lecciones WHERE unidad_id = 4 AND orden = 3')
        leccion_u4_l3_id = cursor.fetchone()[0]  # Diccionarios: Organizar datos
        
        cursor.execute('SELECT id FROM lecciones WHERE unidad_id = 4 AND orden = 4')
        leccion_u4_l4_id = cursor.fetchone()[0]  # Acceder y modificar información dentro de un diccionario
        
        cursor.execute('SELECT id FROM lecciones WHERE unidad_id = 3 AND orden = 1')
        leccion_u3_l1_id = cursor.fetchone()[0]  # Operadores aritméticos
        
        cursor.execute('SELECT id FROM lecciones WHERE unidad_id = 3 AND orden = 2')
        leccion_u3_l2_id = cursor.fetchone()[0]  # Comparaciones
        
        cursor.execute('SELECT id FROM lecciones WHERE unidad_id = 3 AND orden = 3')
        leccion_u3_l3_id = cursor.fetchone()[0]  # La estructura if y else
        
        cursor.execute('SELECT id FROM lecciones WHERE unidad_id = 3 AND orden = 4')
        leccion_u3_l4_id = cursor.fetchone()[0]  # Condiciones múltiples con elif y conectores lógicos
        
        cursor.execute('SELECT id FROM lecciones WHERE unidad_id = 5 AND orden = 1')
        leccion_u5_l1_id = cursor.fetchone()[0]  # El ciclo for
        
        cursor.execute('SELECT id FROM lecciones WHERE unidad_id = 5 AND orden = 2')
        leccion_u5_l2_id = cursor.fetchone()[0]  # La función range()
        
        cursor.execute('SELECT id FROM lecciones WHERE unidad_id = 5 AND orden = 3')
        leccion_u5_l3_id = cursor.fetchone()[0]  # El ciclo while
        
        cursor.execute('SELECT id FROM lecciones WHERE unidad_id = 5 AND orden = 4')
        leccion_u5_l4_id = cursor.fetchone()[0]  # break y continue
        
        # Ejercicios para la Lección 1 de Unidad 1: ¿Qué es Python?
        ejercicios_u1_l1 = [
            (leccion_u1_l1_id, 'opcion_multiple', '¿Qué es Python?', 
             'a) Un animal|b) Un lenguaje de programación de alto nivel|c) Solo un editor de texto|d) Un sistema operativo',
             'b', 'Python es un lenguaje de programación de alto nivel, interpretado y de propósito general', 10),
            (leccion_u1_l1_id, 'opcion_multiple', '¿Por qué Python es tan popular?', 
             'a) Es difícil de aprender|b) Tiene una sintaxis clara y fácil de leer, es versátil y tiene una gran comunidad|c) Solo funciona en Windows|d) No tiene librerías',
             'b', 'Python es popular por su sintaxis clara, versatilidad, gran cantidad de librerías y una comunidad activa', 10),
            (leccion_u1_l1_id, 'opcion_multiple', '¿En qué áreas se usa comúnmente Python?', 
             'a) Solo en desarrollo web|b) Desarrollo web, ciencia de datos, inteligencia artificial, automatización y más|c) Solo para juegos|d) Solo para bases de datos',
             'b', 'Python se usa en desarrollo web, ciencia de datos, IA, automatización, desarrollo de aplicaciones y muchas otras áreas', 10),
            (leccion_u1_l1_id, 'opcion_multiple', '¿Python es un lenguaje interpretado o compilado?', 
             'a) Solo compilado|b) Interpretado, lo que significa que se ejecuta línea por línea|c) Ambos|d) Ninguno',
             'b', 'Python es un lenguaje interpretado, lo que significa que el código se ejecuta línea por línea sin necesidad de compilarlo primero', 10),
            (leccion_u1_l1_id, 'opcion_multiple', '¿Qué característica hace que Python sea fácil de aprender?', 
             'a) Su sintaxis compleja|b) Su sintaxis clara y legible que se parece al lenguaje natural|c) Requiere muchos símbolos especiales|d) Es muy verboso',
             'b', 'Python tiene una sintaxis clara y legible que se parece al lenguaje natural, lo que facilita su aprendizaje', 10)
        ]
        
        cursor.executemany('''
            INSERT INTO ejercicios (leccion_id, tipo, pregunta, opciones, respuesta_correcta, explicacion, puntos)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ejercicios_u1_l1)
        
        # Ejercicios para la Lección 2 de Unidad 1: La función print() - 10 ejercicios totales (5 opción múltiple + 5 fill_in_blank)
        ejercicios_u1_l2 = [
            # Opción múltiple (5 ejercicios)
            (leccion_u1_l2_id, 'opcion_multiple', '¿Qué función se usa en Python para mostrar mensajes en pantalla?', 
             'a) show()|b) print()|c) display()|d) output()',
             'b', 'La función print() se usa para mostrar mensajes en pantalla en Python', 10),
            (leccion_u1_l2_id, 'opcion_multiple', '¿Cómo puedes mostrar múltiples valores en un solo print()?', 
             'a) Separándolos con comas|b) Usando múltiples print()|c) No se puede|d) Solo con +',
             'a', 'Puedes separar múltiples valores con comas en print(), por ejemplo: print("Hola", nombre, "tienes", edad)', 10),
            (leccion_u1_l2_id, 'opcion_multiple', 'Selecciona el código correcto para mostrar el mensaje "Bienvenido":', 
             'a) print Bienvenido|b) print("Bienvenido")|c) print Bienvenido()|d) mostrar("Bienvenido")',
             'b', 'La sintaxis correcta es print("Bienvenido") con paréntesis y comillas alrededor del texto', 10),
            (leccion_u1_l2_id, 'opcion_multiple', 'Selecciona el código que mostrará el nombre almacenado en la variable "nombre":', 
             'a) print nombre|b) print("nombre")|c) print(nombre)|d) print nombre()',
             'c', 'Para mostrar el valor de una variable, se usa print(nombre) sin comillas. Con comillas mostraría el texto literal "nombre"', 10),
            (leccion_u1_l2_id, 'opcion_multiple', '¿Qué código mostrará "Edad: 25" (sin salto de línea después)?', 
             'a) print("Edad:", 25)|b) print("Edad: 25", end="")|c) print("Edad: 25")|d) print("Edad:", 25, end="")',
             'b', 'El parámetro end="" evita que print() agregue un salto de línea al final', 10),
            # Fill in the blank (5 ejercicios)
            (leccion_u1_l2_id, 'fill_in_blank', 'Completa el siguiente código para mostrar el mensaje "Hola mundo" en pantalla:<br><code>___("Hola mundo")</code>', 
             '', 'print', 'La función print() se usa para mostrar mensajes en pantalla', 10),
            (leccion_u1_l2_id, 'fill_in_blank', 'Completa el siguiente código para mostrar el valor de la variable edad:<br><code>print(___)</code>', 
             '', 'edad', 'Para mostrar una variable, se usa su nombre sin comillas dentro de print()', 10),
            (leccion_u1_l2_id, 'fill_in_blank', 'Completa el siguiente código para evitar el salto de línea al final:<br><code>print("Texto", end=___)</code>', 
             '', '""', 'El parámetro end="" evita que print() agregue un salto de línea', 10),
            (leccion_u1_l2_id, 'fill_in_blank', 'Completa el siguiente código para mostrar un mensaje con formato:<br><code>___("Mi nombre es", nombre)</code>', 
             '', 'print', 'La función print() permite mostrar múltiples valores separados por comas', 10),
            (leccion_u1_l2_id, 'fill_in_blank', 'Completa el siguiente código para mostrar múltiples valores usando las variables nombre y edad:<br><code>print("Hola", ___, "tienes", ___)</code>', 
             '', 'nombre|edad', 'Puedes separar múltiples valores con comas en print()', 10)
        ]
        
        cursor.executemany('''
            INSERT INTO ejercicios (leccion_id, tipo, pregunta, opciones, respuesta_correcta, explicacion, puntos)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ejercicios_u1_l2)
        
        # Ejercicios para la Lección 3 de Unidad 1: La función input() - 10 ejercicios totales
        ejercicios_u1_l3 = [
            # Opción múltiple (5 ejercicios)
            (leccion_u1_l3_id, 'opcion_multiple', '¿Qué función se usa para leer lo que el usuario escribe?', 
             'a) read()|b) input()|c) get()|d) scan()',
             'b', 'La función input() se usa para leer datos que el usuario escribe desde el teclado', 10),
            (leccion_u1_l3_id, 'opcion_multiple', '¿Qué tipo de dato devuelve siempre input()?', 
             'a) Integer|b) Float|c) String|d) Booleano',
             'c', 'input() siempre devuelve un String, incluso si el usuario escribe números', 10),
            (leccion_u1_l3_id, 'opcion_multiple', 'Selecciona el código correcto para pedirle al usuario su edad:', 
             'a) edad = input|b) edad = input("¿Cuántos años tienes? ")|c) edad = input()|d) edad = leer("¿Cuántos años tienes? ")',
             'b', 'input("mensaje") muestra el mensaje y espera la entrada del usuario. El resultado se guarda en la variable', 10),
            (leccion_u1_l3_id, 'opcion_multiple', '¿Qué código guardará correctamente un número entero ingresado por el usuario?', 
             'a) numero = input("Ingresa un número: ")|b) numero = int(input("Ingresa un número: "))|c) numero = input(int)|d) numero = input("Ingresa un número: ").to_int()',
             'b', 'int(input("mensaje")) convierte la entrada del usuario (que es String) a un número entero', 10),
            (leccion_u1_l3_id, 'opcion_multiple', 'Selecciona el código que pedirá dos valores y los sumará correctamente:', 
             'a) a = input(); b = input(); suma = a + b|b) a = int(input()); b = int(input()); suma = a + b|c) a = input(int); b = input(int); suma = a + b|d) a = input(); b = input(); suma = int(a + b)',
             'b', 'Necesitas convertir ambas entradas a int antes de sumarlas, de lo contrario se concatenarían como strings', 10),
            # Fill in the blank (5 ejercicios)
            (leccion_u1_l3_id, 'fill_in_blank', 'Completa el siguiente código para leer el nombre del usuario:<br><code>nombre = ___("¿Cuál es tu nombre? ")</code>', 
             'input', 'input', 'La función input() se usa para leer datos que el usuario escribe', 10),
            (leccion_u1_l3_id, 'fill_in_blank', 'Completa el siguiente código para convertir la entrada a número entero:<br><code>edad = ___(input("¿Cuántos años tienes? "))</code>', 
             'int', 'int', 'La función int() convierte un String a un número entero', 10),
            (leccion_u1_l3_id, 'fill_in_blank', 'Completa el siguiente código para leer y convertir a número:<br><code>numero = ___(___("Ingresa un número: "))</code>', 
             'int|input', 'int|input', 'int(input()) convierte la entrada del usuario a un número entero', 10),
            (leccion_u1_l3_id, 'fill_in_blank', 'Completa el siguiente código para leer el nombre y mostrarlo:<br><code>nombre = input("Nombre: ")<br>print("Hola", ___)</code>', 
             'nombre', 'nombre', 'La variable nombre contiene el valor ingresado por el usuario', 10),
            (leccion_u1_l3_id, 'fill_in_blank', 'Completa el siguiente código para leer dos números y sumarlos:<br><code>a = int(input("Primer número: "))<br>b = ___(___("Segundo número: "))<br>suma = a + b</code>', 
             'int|input', 'int|input', 'Ambas entradas deben convertirse a int antes de sumarlas', 10)
        ]
        
        cursor.executemany('''
            INSERT INTO ejercicios (leccion_id, tipo, pregunta, opciones, respuesta_correcta, explicacion, puntos)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ejercicios_u1_l3)
        
        # Ejercicios para la Lección 4 de Unidad 1: Comentarios - 10 ejercicios totales (5 opción múltiple + 5 fill_in_blank)
        ejercicios_u1_l4 = [
            # Opción múltiple (5 ejercicios)
            (leccion_u1_l4_id, 'opcion_multiple', '¿Qué símbolo se usa en Python para crear un comentario de una línea?', 
             'a) //|b) #|c) /*|d) --',
             'b', 'En Python, el símbolo # se usa para crear comentarios de una línea', 10),
            (leccion_u1_l4_id, 'opcion_multiple', '¿Qué sucede con los comentarios cuando Python ejecuta el código?', 
             'a) Se ejecutan como código|b) Se ignoran completamente, no afectan la ejecución|c) Causan errores|d) Solo se muestran en pantalla',
             'b', 'Los comentarios son ignorados por Python y no afectan la ejecución del programa', 10),
            (leccion_u1_l4_id, 'opcion_multiple', '¿Cómo se crea un comentario de múltiples líneas en Python?', 
             'a) Usando múltiples #|b) Usando triple comillas simples o dobles (""")|c) Usando /* */|d) No se puede',
             'b', 'En Python, los comentarios de múltiples líneas se crean usando triple comillas simples (\'\'\') o dobles (""")', 10),
            (leccion_u1_l4_id, 'opcion_multiple', 'Selecciona el código que tiene un comentario correcto:', 
             'a) # Este es un comentario|b) // Este es un comentario|c) /* Este es un comentario */|d) -- Este es un comentario',
             'a', 'En Python, los comentarios de una línea se crean con el símbolo #', 10),
            (leccion_u1_l4_id, 'opcion_multiple', '¿Cuál es el propósito principal de los comentarios en el código?', 
             'a) Hacer que el código funcione mejor|b) Explicar el código para que otros programadores lo entiendan|c) Aumentar la velocidad del programa|d) Crear variables',
             'b', 'Los comentarios ayudan a explicar el código para que otros programadores (y tú mismo en el futuro) puedan entenderlo mejor', 10),
            # Fill in the blank (5 ejercicios)
            (leccion_u1_l4_id, 'fill_in_blank', 'Completa el siguiente código para agregar un comentario que explique qué hace el código:<br><code>___ Calcula la suma de dos números<br>suma = 5 + 3</code>', 
             '', '#', 'El símbolo # se usa para crear comentarios de una línea en Python', 10),
            (leccion_u1_l4_id, 'fill_in_blank', 'Completa el siguiente código para agregar un comentario después de la línea de código:<br><code>nombre = input("Nombre: ")  ___ Obtiene el nombre del usuario</code>', 
             '', '#', 'Los comentarios pueden ir al final de una línea de código usando #', 10),
            (leccion_u1_l4_id, 'fill_in_blank', 'Completa el siguiente código para crear un comentario de múltiples líneas (usa triple comillas):<br><code>___<br>Este programa calcula el área de un círculo<br>___</code>', 
             '', '"""|"""', 'Los comentarios de múltiples líneas se crean con triple comillas dobles (""")', 10),
            (leccion_u1_l4_id, 'fill_in_blank', 'Completa el siguiente código para documentar la función con un comentario:<br><code>___ Función que saluda al usuario<br>print("Hola, bienvenido")</code>', 
             '', '#', 'Los comentarios se usan para documentar qué hace una función o bloque de código', 10),
            (leccion_u1_l4_id, 'fill_in_blank', 'Completa el siguiente código para agregar un comentario explicativo:<br><code>edad = int(input("Edad: "))  ___ Convierte la entrada a número entero</code>', 
             '', '#', 'Los comentarios ayudan a explicar operaciones complejas como la conversión de tipos', 10)
        ]
        
        cursor.executemany('''
            INSERT INTO ejercicios (leccion_id, tipo, pregunta, opciones, respuesta_correcta, explicacion, puntos)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ejercicios_u1_l4)
        
        # Ejercicios para la Lección 1 de Unidad 2: Variables - 10 ejercicios totales (5 opción múltiple + 3 verdadero/falso + 2 fill_in_blank)
        ejercicios_u2_l1 = [
            # Opción múltiple (5 ejercicios)
            (leccion_u2_l1_id, 'opcion_multiple', '¿Qué es una variable en Python?', 
             'a) Un valor fijo que no cambia|b) Un contenedor que almacena datos y puede cambiar su valor|c) Solo números|d) Un comando especial',
             'b', 'Una variable es un contenedor que almacena datos y puede cambiar su valor durante la ejecución del programa', 10),
            (leccion_u2_l1_id, 'opcion_multiple', '¿Cuál es la forma correcta de declarar una variable en Python?', 
             'a) var nombre = "Python"|b) nombre = "Python"|c) declare nombre = "Python"|d) nombre := "Python"',
             'b', 'En Python, las variables se declaran simplemente asignando un valor con el operador =', 10),
            (leccion_u2_l1_id, 'opcion_multiple', '¿Qué nombre de variable es válido en Python?', 
             'a) 2nombre|b) nombre-usuario|c) nombre_usuario|d) nombre usuario',
             'c', 'Los nombres de variables pueden contener letras, números y guiones bajos, pero no pueden empezar con número ni contener espacios', 10),
            (leccion_u2_l1_id, 'opcion_multiple', '¿Puede una variable cambiar de valor en Python?', 
             'a) No, nunca|b) Sí, las variables pueden cambiar de valor|c) Solo si es un número|d) Solo una vez',
             'b', 'Las variables en Python pueden cambiar de valor durante la ejecución del programa', 10),
            (leccion_u2_l1_id, 'opcion_multiple', '¿Qué caracteres puede contener el nombre de una variable en Python?', 
             'a) Solo letras|b) Letras, números y guiones bajos (pero no puede empezar con número)|c) Cualquier carácter|d) Solo números',
             'b', 'Los nombres de variables pueden contener letras, números y guiones bajos, pero deben empezar con letra o guión bajo', 10),
            
            # Verdadero/Falso (3 ejercicios)
            (leccion_u2_l1_id, 'verdadero_falso', 'En Python, los nombres de variables distinguen entre mayúsculas y minúsculas', 
             '', 'verdadero', 'Python es case-sensitive. "Nombre" y "nombre" son variables diferentes', 10),
            (leccion_u2_l1_id, 'verdadero_falso', 'Una variable puede empezar con un número', 
             '', 'falso', 'Los nombres de variables no pueden empezar con un número. Deben empezar con letra o guión bajo', 10),
            (leccion_u2_l1_id, 'verdadero_falso', 'En Python, las variables pueden cambiar de tipo durante la ejecución', 
             '', 'verdadero', 'Python es dinámico. Una variable puede ser int y luego cambiar a str, por ejemplo: x = 5 luego x = "hola"', 10),
            
            # Fill in the blank (2 ejercicios)
            (leccion_u2_l1_id, 'fill_in_blank', 'Completa el código para declarar una variable llamada "edad" con el valor 25:<br><code>___ = 25</code>', 
             '', 'edad', 'Las variables se declaran usando el nombre seguido del operador = y el valor', 10),
            (leccion_u2_l1_id, 'fill_in_blank', 'Completa el código para declarar una variable llamada "nombre" con el valor "Python":<br><code>___ = "Python"</code>', 
             '', 'nombre', 'Las variables de tipo String se declaran con comillas alrededor del valor', 10)
        ]
        
        cursor.executemany('''
            INSERT INTO ejercicios (leccion_id, tipo, pregunta, opciones, respuesta_correcta, explicacion, puntos)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ejercicios_u2_l1)
        
        # Ejercicios para la Lección 2 de Unidad 2: Textos (Strings) y números - 10 ejercicios totales (4 opción múltiple + 3 verdadero/falso + 3 fill_in_blank)
        ejercicios_u2_l2 = [
            # Opción múltiple (4 ejercicios)
            (leccion_u2_l2_id, 'opcion_multiple', '¿Qué es un tipo de dato String?', 
             'a) Un valor verdadero o falso|b) Un número decimal|c) Un número entero|d) Una secuencia de caracteres o texto',
             'd', 'Un String es un tipo de dato que almacena una secuencia de caracteres o texto, como "Hola" o "Python"', 10),
            
            (leccion_u2_l2_id, 'opcion_multiple', '¿Cómo se representa un String en Python?', 
             'a) Entre comillas simples o dobles|b) Solo con números|c) Con corchetes|d) Sin comillas',
             'a', 'En Python, los Strings se representan entre comillas simples (\') o dobles (")', 10),
            
            (leccion_u2_l2_id, 'opcion_multiple', '¿Qué es un tipo de dato Integer?', 
             'a) Un número decimal|b) Un número entero sin decimales|c) Un texto|d) Un valor booleano',
             'b', 'Un Integer (int) es un tipo de dato que almacena números enteros, como 5, -10, 100', 10),
            
            (leccion_u2_l2_id, 'opcion_multiple', '¿Qué es un tipo de dato Float?', 
             'a) Un número entero|b) Un número decimal o de punto flotante|c) Un texto|d) Un valor booleano',
             'b', 'Un Float es un tipo de dato que almacena números decimales o de punto flotante, como 3.14, 2.5, -0.5', 10),
            
            # Verdadero/Falso (3 ejercicios)
            (leccion_u2_l2_id, 'verdadero_falso', 'En Python, el String "123" y el Integer 123 son el mismo tipo de dato', 
             '', 'falso', 'No son el mismo tipo. "123" es un String (texto) y 123 es un Integer (número). Necesitas convertir con int() para hacer operaciones matemáticas', 10),
            
            (leccion_u2_l2_id, 'verdadero_falso', 'Los números decimales en Python son de tipo Float', 
             '', 'verdadero', 'Los números con punto decimal como 3.14, 2.5 son de tipo Float (float)', 10),
            
            (leccion_u2_l2_id, 'verdadero_falso', 'Un String puede contener solo letras', 
             '', 'falso', 'Un String puede contener letras, números, símbolos y espacios. Por ejemplo: "Hola123" o "Python 3.10" son Strings válidos', 10),
            
            # Fill in the blank (3 ejercicios)
            (leccion_u2_l2_id, 'fill_in_blank', 'Completa el código para declarar una variable de tipo String con el valor "Python":<br><code>lenguaje = ___</code>', 
             '', '"Python"', 'Los Strings se declaran con comillas alrededor del valor', 10),
            
            (leccion_u2_l2_id, 'fill_in_blank', 'Completa el código para declarar una variable de tipo Integer con el valor 42:<br><code>numero = ___</code>', 
             '', '42', 'Los números enteros se declaran sin comillas ni punto decimal', 10),
            
            (leccion_u2_l2_id, 'fill_in_blank', 'Completa el código para declarar una variable de tipo Float con el valor 3.14:<br><code>pi = ___</code>', 
             '', '3.14', 'Los números decimales se declaran con punto decimal y sin comillas', 10)
        ]
        
        cursor.executemany('''
            INSERT INTO ejercicios (leccion_id, tipo, pregunta, opciones, respuesta_correcta, explicacion, puntos)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ejercicios_u2_l2)
        
        # Ejercicios para la Lección 3 de Unidad 2: Valores de verdad (Booleans) - 10 ejercicios totales (4 opción múltiple + 3 verdadero/falso + 3 fill_in_blank)
        ejercicios_u2_l3 = [
            # Opción múltiple (4 ejercicios)
            (leccion_u2_l3_id, 'opcion_multiple', '¿Qué es un tipo de dato Booleano?', 
             'a) Un número|b) Un texto|c) Un valor que solo puede ser True o False|d) Un decimal',
             'c', 'Un Booleano (bool) es un tipo de dato que solo puede tener dos valores: True (verdadero) o False (falso)', 10),
            
            (leccion_u2_l3_id, 'opcion_multiple', '¿Cuál de los siguientes es un valor Booleano válido en Python?', 
             'a) 1|b) "True"|c) True|d) 0',
             'c', 'True es un valor Booleano. Los valores 1 y 0 son números, y "True" es un String', 10),
            
            (leccion_u2_l3_id, 'opcion_multiple', '¿Qué valor Booleano representa "falso" en Python?', 
             'a) true|b) FALSE|c) False|d) 0',
             'c', 'En Python, los valores booleanos son True y False con mayúscula inicial. "false" o "FALSE" no son válidos', 10),
            
            (leccion_u2_l3_id, 'opcion_multiple', '¿Cuándo se usan los valores booleanos en programación?', 
             'a) Solo para números|b) Para tomar decisiones y controlar el flujo del programa|c) Solo para textos|d) Nunca se usan',
             'b', 'Los valores booleanos se usan principalmente para tomar decisiones en estructuras condicionales como if/else', 10),
            
            # Verdadero/Falso (3 ejercicios)
            (leccion_u2_l3_id, 'verdadero_falso', 'En Python, True y False son valores booleanos con mayúscula inicial', 
             '', 'verdadero', 'En Python, los valores booleanos deben escribirse con mayúscula inicial: True y False (no true/false)', 10),
            
            (leccion_u2_l3_id, 'verdadero_falso', 'El valor 0 en Python es equivalente al Booleano False', 
             '', 'verdadero', 'En Python, el valor 0 se considera "falsy" y puede usarse en contextos booleanos como False, pero no es exactamente lo mismo que el Booleano False', 10),
            
            (leccion_u2_l3_id, 'verdadero_falso', 'Un Booleano puede tener más de dos valores', 
             '', 'falso', 'Un Booleano solo puede tener dos valores: True o False. No puede tener otros valores', 10),
            
            # Fill in the blank (3 ejercicios)
            (leccion_u2_l3_id, 'fill_in_blank', 'Completa el código para declarar una variable booleana que indique que algo está activo:<br><code>activo = ___</code>', 
             '', 'True', 'Los valores booleanos en Python son True o False (con mayúscula inicial)', 10),
            
            (leccion_u2_l3_id, 'fill_in_blank', 'Completa el código para declarar una variable booleana que indique que algo está desactivado:<br><code>desactivado = ___</code>', 
             '', 'False', 'False es el valor booleano que representa "falso" o "desactivado"', 10),
            
            (leccion_u2_l3_id, 'fill_in_blank', 'Completa el código para verificar si una condición es verdadera usando un Booleano:<br><code>if condicion == ___:<br>    print("Es verdadero")</code>', 
             '', 'True', 'Se compara con True para verificar si una condición es verdadera', 10)
        ]
        
        cursor.executemany('''
            INSERT INTO ejercicios (leccion_id, tipo, pregunta, opciones, respuesta_correcta, explicacion, puntos)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ejercicios_u2_l3)
        
        # Ejercicios para la Lección 4 de Unidad 2: Conversión de datos - 10 ejercicios totales (4 opción múltiple + 3 verdadero/falso + 3 fill_in_blank)
        ejercicios_u2_l4 = [
            # Opción múltiple (4 ejercicios)
            (leccion_u2_l4_id, 'opcion_multiple', '¿Qué función se usa para convertir un String a Integer en Python?', 
             'a) str()|b) int()|c) float()|d) bool()',
             'b', 'La función int() convierte un String a Integer (número entero)', 10),
            
            (leccion_u2_l4_id, 'opcion_multiple', '¿Qué función se usa para convertir un número a String en Python?', 
             'a) int()|b) float()|c) str()|d) bool()',
             'c', 'La función str() convierte cualquier tipo de dato a String (texto)', 10),
            
            (leccion_u2_l4_id, 'opcion_multiple', '¿Qué función se usa para convertir un String a número decimal (Float)?', 
             'a) int()|b) float()|c) str()|d) bool()',
             'b', 'La función float() convierte un String a número decimal (Float)', 10),
            
            (leccion_u2_l4_id, 'opcion_multiple', 'Si tienes numero = "123", ¿qué código lo convierte a Integer?', 
             'a) int(numero)|b) str(numero)|c) float(numero)|d) numero.to_int()',
             'a', 'int(numero) convierte el String "123" al Integer 123', 10),
            
            # Verdadero/Falso (3 ejercicios)
            (leccion_u2_l4_id, 'verdadero_falso', 'Puedes convertir el String "3.14" a Integer usando int("3.14")', 
             '', 'falso', 'No puedes convertir directamente "3.14" a Integer porque tiene decimales. Primero debes convertir a float() y luego a int(), o usar int(float("3.14"))', 10),
            
            (leccion_u2_l4_id, 'verdadero_falso', 'La función str() puede convertir cualquier tipo de dato a String', 
             '', 'verdadero', 'La función str() puede convertir números, booleanos y otros tipos a String. Por ejemplo: str(42) devuelve "42"', 10),
            
            (leccion_u2_l4_id, 'verdadero_falso', 'Puedes sumar directamente un String y un Integer sin convertir', 
             '', 'falso', 'No puedes sumar directamente un String y un Integer. Necesitas convertir uno de ellos, por ejemplo: int(texto) o str(numero)', 10),
            
            # Fill in the blank (3 ejercicios)
            (leccion_u2_l4_id, 'fill_in_blank', 'Completa el código para convertir el String "100" a Integer:<br><code>numero = ___(___)</code>', 
             '', 'int|"100"', 'Usa int() para convertir un String a Integer. La sintaxis es int("100")', 10),
            
            (leccion_u2_l4_id, 'fill_in_blank', 'Completa el código para convertir el número 42 a String:<br><code>texto = ___(___)</code>', 
             '', 'str|42', 'Usa str() para convertir un número a String. La sintaxis es str(42)', 10),
            
            (leccion_u2_l4_id, 'fill_in_blank', 'Completa el código para convertir el String "3.14" a Float:<br><code>decimal = ___(___)</code>', 
             '', 'float|"3.14"', 'Usa float() para convertir un String a número decimal. La sintaxis es float("3.14")', 10)
        ]
        
        cursor.executemany('''
            INSERT INTO ejercicios (leccion_id, tipo, pregunta, opciones, respuesta_correcta, explicacion, puntos)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ejercicios_u2_l4)
        
        # Ejercicios para la Lección 1 de Unidad 3: Operadores aritméticos - 10 ejercicios totales (4 opción múltiple + 3 verdadero/falso + 3 fill_in_blank)
        ejercicios_u3_l1 = [
            # Opción múltiple (4 ejercicios)
            (leccion_u3_l1_id, 'opcion_multiple', '¿Qué operador se usa para la suma en Python?',
             'a) sum()|b) +|c) add()|d) plus()',
             'b', 'El operador + se usa para sumar dos números en Python', 10),
            
            (leccion_u3_l1_id, 'opcion_multiple', '¿Qué operador se usa para la división entera (sin decimales)?',
             'a) /|b) //|c) %|d) div()',
             'b', 'El operador // realiza división entera, descartando la parte decimal', 10),
            
            (leccion_u3_l1_id, 'opcion_multiple', '¿Qué operador se usa para obtener el resto de una división (módulo)?',
             'a) /|b) //|c) %|d) mod()',
             'c', 'El operador % devuelve el resto de una división. Por ejemplo: 10 % 3 = 1', 10),
            
            (leccion_u3_l1_id, 'opcion_multiple', '¿Qué operador se usa para la exponenciación (elevar a una potencia)?',
             'a) ^|b) **|c) pow()|d) exp()',
             'b', 'El operador ** se usa para exponenciación. Por ejemplo: 2 ** 3 = 8', 10),
            
            # Verdadero/Falso (3 ejercicios)
            (leccion_u3_l1_id, 'verdadero_falso', 'El operador / siempre devuelve un número decimal (float) en Python',
             '', 'verdadero', 'En Python 3, el operador / siempre devuelve un float, incluso si divides dos enteros. Por ejemplo: 10 / 2 = 5.0', 10),
            
            (leccion_u3_l1_id, 'verdadero_falso', 'El operador // puede usarse solo con números enteros',
             '', 'falso', 'El operador // puede usarse con cualquier número. Si divides 7.5 // 2, el resultado es 3.0 (float)', 10),
            
            (leccion_u3_l1_id, 'verdadero_falso', 'La expresión 2 ** 3 es equivalente a 2 * 2 * 2',
             '', 'verdadero', 'El operador ** eleva el número a una potencia. 2 ** 3 = 8, que es igual a 2 * 2 * 2 = 8', 10),
            
            # Fill in the blank (3 ejercicios)
            (leccion_u3_l1_id, 'fill_in_blank', 'Completa el código para sumar dos números y mostrar el resultado:<br><code>a = 5<br>b = 3<br><br>suma = a ___ b<br>print(___)</code>',
             '', '+|suma', 'El operador + se usa para sumar dos números y luego se muestra el resultado con print()', 10),
            
            (leccion_u3_l1_id, 'fill_in_blank', 'Completa el código para realizar división entera y mostrar el resultado:<br><code>dividendo = 10<br>divisor = 3<br><br>resultado = dividendo ___ divisor<br>print(___"Resultado:", resultado)</code>',
             '', '//|"', 'El operador // realiza división entera. Falta la comilla inicial en print()', 10),
            
            (leccion_u3_l1_id, 'fill_in_blank', 'Completa el código para calcular la potencia usando concatenación (sin print):<br><code>base = 2<br>exponente = 4<br><br>potencia = base ___ exponente<br>mensaje = "2 elevado a 4 es " + str(___)</code>',
             '', '**|potencia', 'El operador ** se usa para exponenciación. Se usa str() para convertir a texto y concatenar', 10)
        ]
        
        cursor.executemany('''
            INSERT INTO ejercicios (leccion_id, tipo, pregunta, opciones, respuesta_correcta, explicacion, puntos)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ejercicios_u3_l1)
        
        # Ejercicios para la Lección 2 de Unidad 3: Comparaciones - 10 ejercicios totales (4 opción múltiple + 3 verdadero/falso + 3 fill_in_blank)
        ejercicios_u3_l2 = [
            # Opción múltiple (4 ejercicios)
            (leccion_u3_l2_id, 'opcion_multiple', '¿Qué operador se usa para verificar si dos valores son iguales?',
             'a) =|b) ==|c) ===|d) equals()',
             'b', 'El operador == verifica si dos valores son iguales. El operador = se usa para asignación', 10),
            
            (leccion_u3_l2_id, 'opcion_multiple', '¿Qué operador se usa para verificar si un valor es mayor que otro?',
             'a) >|b) >=|c) <|d) =>',
             'a', 'El operador > verifica si el valor de la izquierda es mayor que el de la derecha', 10),
            
            (leccion_u3_l2_id, 'opcion_multiple', '¿Qué operador se usa para verificar si dos valores son diferentes?',
             'a) =!|b) !=|c) <>|d) not()',
             'b', 'El operador != verifica si dos valores son diferentes (no iguales)', 10),
            
            (leccion_u3_l2_id, 'opcion_multiple', '¿Qué operador verifica si un valor es mayor o igual que otro?',
             'a) =>|b) >=|c) >|d) =<',
             'b', 'El operador >= verifica si el valor de la izquierda es mayor o igual que el de la derecha', 10),
            
            # Verdadero/Falso (3 ejercicios)
            (leccion_u3_l2_id, 'verdadero_falso', 'El operador == devuelve True si los valores son iguales y False si son diferentes',
             '', 'verdadero', 'El operador == compara dos valores y devuelve True si son iguales, False si son diferentes', 10),
            
            (leccion_u3_l2_id, 'verdadero_falso', 'En Python, puedes comparar Strings usando operadores de comparación',
             '', 'verdadero', 'Puedes comparar Strings usando operadores como ==, !=, <, >. Las comparaciones se hacen alfabéticamente', 10),
            
            (leccion_u3_l2_id, 'verdadero_falso', 'La expresión 5 > 10 devuelve True',
             '', 'falso', 'La expresión 5 > 10 es falsa porque 5 no es mayor que 10. Devuelve False', 10),
            
            # Fill in the blank (3 ejercicios)
            (leccion_u3_l2_id, 'fill_in_blank', 'Completa el código para verificar si dos números son iguales:<br><code>a = 10<br>b = 10<br><br>if a ___ b:<br>    print("Los números son iguales")<br>else:<br>    print("Los números son diferentes")</code>',
             '', '==', 'El operador == verifica si dos valores son iguales', 10),
            
            (leccion_u3_l2_id, 'fill_in_blank', 'Completa el código usando operador ternario (sin if/else tradicional):<br><code>edad = 20<br>mensaje = "Es mayor de edad" if edad ___ 18 else "Es menor de edad"<br>print(mensaje)</code>',
             '', '>', 'El operador > verifica si el valor es mayor. Se usa operador ternario para asignar el mensaje', 10),
            
            (leccion_u3_l2_id, 'fill_in_blank', 'Completa el código guardando el resultado en una variable:<br><code>numero = 5<br>es_diferente = numero ___ 0<br>if es_diferente:<br>    print("El número no es cero")</code>',
             '', '!=', 'El operador != verifica si dos valores son diferentes. El resultado se guarda en una variable booleana', 10)
        ]
        
        cursor.executemany('''
            INSERT INTO ejercicios (leccion_id, tipo, pregunta, opciones, respuesta_correcta, explicacion, puntos)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ejercicios_u3_l2)
        
        # Ejercicios para la Lección 3 de Unidad 3: La estructura if y else - 10 ejercicios totales (4 opción múltiple + 3 verdadero/falso + 3 fill_in_blank)
        ejercicios_u3_l3 = [
            # Opción múltiple (4 ejercicios)
            (leccion_u3_l3_id, 'opcion_multiple', '¿Qué palabra clave se usa para iniciar una estructura condicional en Python?',
             'a) when|b) if|c) check|d) condition',
             'b', 'La palabra clave if se usa para iniciar una estructura condicional en Python', 10),
            
            (leccion_u3_l3_id, 'opcion_multiple', '¿Qué palabra clave se usa para el caso alternativo cuando la condición es falsa?',
             'a) otherwise|b) else|c) elif|d) then',
             'b', 'La palabra clave else se usa para ejecutar código cuando la condición del if es falsa', 10),
            
            (leccion_u3_l3_id, 'opcion_multiple', '¿Cuál es la sintaxis correcta para una estructura if en Python?',
             'a) if condicion { código }|b) if condicion: código|c) if (condicion) { código }|d) if condicion then código',
             'b', 'En Python, la sintaxis es: if condicion: seguido de código con indentación', 10),
            
            (leccion_u3_l3_id, 'opcion_multiple', '¿Qué símbolo se usa para indicar el bloque de código dentro de un if en Python?',
             'a) Llaves { }|b) Paréntesis ( )|c) Indentación (espacios o tabs)|d) Corchetes [ ]',
             'c', 'En Python, la indentación (espacios o tabs) indica el bloque de código que pertenece al if', 10),
            
            # Verdadero/Falso (3 ejercicios)
            (leccion_u3_l3_id, 'verdadero_falso', 'En Python, el bloque de código dentro de un if debe tener indentación',
             '', 'verdadero', 'En Python, la indentación es obligatoria para indicar qué código pertenece al bloque del if', 10),
            
            (leccion_u3_l3_id, 'verdadero_falso', 'Puedes tener múltiples bloques else después de un if',
             '', 'falso', 'Solo puede haber un bloque else después de un if. Para múltiples condiciones alternativas, usa elif', 10),
            
            (leccion_u3_l3_id, 'verdadero_falso', 'El bloque else siempre se ejecuta cuando la condición del if es falsa',
             '', 'verdadero', 'El bloque else se ejecuta siempre que la condición del if sea False', 10),
            
            # Fill in the blank (3 ejercicios)
            (leccion_u3_l3_id, 'fill_in_blank', 'Completa el código para verificar si una persona es mayor de edad:<br><code>edad = 20<br><br>___ edad >= 18:<br>    print("Es mayor de edad")<br>    puede_votar = True<br>else:<br>    print("Es menor de edad")<br>    puede_votar = False</code>',
             '', 'if', 'La palabra clave if inicia una estructura condicional', 10),
            
            (leccion_u3_l3_id, 'fill_in_blank', 'Completa el código para determinar si un número es par o impar:<br><code>numero = 7<br><br>if numero % 2 == 0:<br>    resultado = ___<br>else:<br>    resultado = "impar"<br>print("El número es", resultado)</code>',
             '', '"par"', 'Cuando el número es par, se debe asignar la cadena "par" a la variable resultado', 10),
            
            (leccion_u3_l3_id, 'fill_in_blank', 'Completa el código para verificar si un número es positivo:<br><code>numero = -5<br>signo = "negativo o cero"<br><br>___ numero > 0:<br>    signo = "positivo"<br>print("El número es", signo)</code>',
             '', 'if', 'La palabra clave if inicia la estructura condicional', 10)
        ]
        
        cursor.executemany('''
            INSERT INTO ejercicios (leccion_id, tipo, pregunta, opciones, respuesta_correcta, explicacion, puntos)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ejercicios_u3_l3)
        
        # Ejercicios para la Lección 4 de Unidad 3: Condiciones múltiples con elif y conectores lógicos - 10 ejercicios totales (4 opción múltiple + 3 verdadero/falso + 3 fill_in_blank)
        ejercicios_u3_l4 = [
            # Opción múltiple (4 ejercicios)
            (leccion_u3_l4_id, 'opcion_multiple', '¿Qué palabra clave se usa para agregar condiciones adicionales después de un if?',
             'a) else if|b) elif|c) elseif|d) and if',
             'b', 'La palabra clave elif (else if) se usa para agregar condiciones adicionales después de un if', 10),
            
            (leccion_u3_l4_id, 'opcion_multiple', '¿Qué operador lógico se usa para verificar que AMBAS condiciones sean verdaderas?',
             'a) or|b) and|c) not|d) &&',
             'b', 'El operador and devuelve True solo si ambas condiciones son verdaderas', 10),
            
            (leccion_u3_l4_id, 'opcion_multiple', '¿Qué operador lógico se usa para verificar que AL MENOS UNA condición sea verdadera?',
             'a) and|b) or|c) not|d) ||',
             'b', 'El operador or devuelve True si al menos una de las condiciones es verdadera', 10),
            
            (leccion_u3_l4_id, 'opcion_multiple', '¿Cuál es el orden correcto de ejecución en una estructura if-elif-else?',
             'a) Se ejecutan todos los bloques|b) Se ejecuta el primer bloque cuya condición sea verdadera|c) Se ejecuta solo el else|d) Se ejecutan en orden inverso',
             'b', 'Python ejecuta el primer bloque (if o elif) cuya condición sea verdadera. Si ninguna es verdadera, ejecuta el else', 10),
            
            # Verdadero/Falso (3 ejercicios)
            (leccion_u3_l4_id, 'verdadero_falso', 'Puedes tener múltiples bloques elif después de un if',
             '', 'verdadero', 'Puedes tener tantos bloques elif como necesites después de un if para manejar múltiples condiciones', 10),
            
            (leccion_u3_l4_id, 'verdadero_falso', 'El operador and devuelve True si ambas condiciones son verdaderas',
             '', 'verdadero', 'El operador and devuelve True solo si ambas condiciones son verdaderas. Si alguna es falsa, devuelve False', 10),
            
            (leccion_u3_l4_id, 'verdadero_falso', 'El operador or devuelve True solo si ambas condiciones son verdaderas',
             '', 'falso', 'El operador or devuelve True si al menos una de las condiciones es verdadera. Solo devuelve False si ambas son falsas', 10),
            
            # Fill in the blank (3 ejercicios)
            (leccion_u3_l4_id, 'fill_in_blank', 'Completa el código para clasificar la edad de una persona:<br><code>edad = 15<br><br>if edad < 13:<br>    categoria = "Niño"<br>    print("Es un niño")<br>___ edad < 18:<br>    categoria = "Adolescente"<br>else:<br>    categoria = "Adulto"</code>',
             '', 'elif', 'La palabra clave elif se usa para agregar condiciones adicionales después de un if', 10),
            
            (leccion_u3_l4_id, 'fill_in_blank', 'Completa el código usando expresión booleana directa (sin if/else):<br><code>edad = 20<br>tiene_licencia = True<br><br>puede_conducir = edad >= 18 ___ tiene_licencia<br>if puede_conducir:<br>    print("Puede conducir")</code>',
             '', 'and', 'El operador and verifica que ambas condiciones sean verdaderas. El resultado se guarda directamente en una variable', 10),
            
            (leccion_u3_l4_id, 'fill_in_blank', 'Completa el código para determinar el descuento según la edad y membresía:<br><code>edad = 25<br>tiene_membresia = True<br>descuento = 0<br><br>if edad < 18:<br>    descuento = 10<br>    print("Descuento para menores")<br>___ edad < 65 ___ tiene_membresia:<br>    descuento = 20<br>    print("Descuento para miembros")<br>else:<br>    descuento = 5<br>    print("Descuento estándar")</code>',
             '', 'elif|and', 'Se usa elif para la condición adicional y and para verificar que ambas condiciones sean verdaderas', 10)
        ]
        
        cursor.executemany('''
            INSERT INTO ejercicios (leccion_id, tipo, pregunta, opciones, respuesta_correcta, explicacion, puntos)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ejercicios_u3_l4)
        
        # Ejercicios para la Lección 1 de Unidad 4: Listas - 10 ejercicios totales (4 opción múltiple + 3 verdadero/falso + 3 fill_in_blank)
        ejercicios_u4_l1 = [
            # Opción múltiple (4 ejercicios)
            (leccion_u4_l1_id, 'opcion_multiple', '¿Qué es una lista en Python?',
             'a) Un solo valor|b) Una colección ordenada de elementos que puede contener diferentes tipos de datos|c) Solo números|d) Solo texto',
             'b', 'Una lista es una colección ordenada de elementos que puede contener diferentes tipos de datos como números, strings, etc.', 10),
            
            (leccion_u4_l1_id, 'opcion_multiple', '¿Cómo se crea una lista vacía en Python?',
             'a) lista = []|b) lista = ()|c) lista = {}|d) lista = list',
             'a', 'Una lista vacía se crea usando corchetes vacíos: lista = []', 10),
            
            (leccion_u4_l1_id, 'opcion_multiple', '¿Cuál es la forma correcta de crear una lista con los números 1, 2, 3?',
             'a) lista = 1, 2, 3|b) lista = [1, 2, 3]|c) lista = (1, 2, 3)|d) lista = {1, 2, 3}',
             'b', 'Las listas se crean usando corchetes y los elementos separados por comas: [1, 2, 3]', 10),
            
            (leccion_u4_l1_id, 'opcion_multiple', '¿Cómo se accede al primer elemento de una lista llamada "numeros"?',
             'a) numeros(0)|b) numeros[0]|c) numeros{0}|d) numeros.0',
             'b', 'Los elementos de una lista se acceden usando corchetes con el índice. El primer elemento tiene índice 0', 10),
            
            # Verdadero/Falso (3 ejercicios)
            (leccion_u4_l1_id, 'verdadero_falso', 'Las listas en Python pueden contener elementos de diferentes tipos de datos',
             '', 'verdadero', 'Las listas en Python pueden contener números, strings, booleanos y otros tipos de datos mezclados', 10),
            
            (leccion_u4_l1_id, 'verdadero_falso', 'El primer elemento de una lista tiene índice 1',
             '', 'falso', 'En Python, el primer elemento de una lista tiene índice 0, no 1', 10),
            
            (leccion_u4_l1_id, 'verdadero_falso', 'Una lista puede estar vacía',
             '', 'verdadero', 'Una lista puede estar vacía. Se crea con lista = []', 10),
            
            # Fill in the blank (3 ejercicios)
            (leccion_u4_l1_id, 'fill_in_blank', 'Completa el código para crear una lista con los nombres "Ana", "Luis" y "María":<br><code>nombres = [___, ___, ___]</code>',
             '', '"Ana"|"Luis"|"María"', 'Los elementos de una lista se separan por comas y los strings van entre comillas', 10),
            
            (leccion_u4_l1_id, 'fill_in_blank', 'Completa el código para acceder al segundo elemento de la lista:<br><code>frutas = ["manzana", "banana", "naranja"]<br>segunda_fruta = frutas[___]</code>',
             '', '1', 'El segundo elemento tiene índice 1 porque el primero tiene índice 0', 10),
            
            (leccion_u4_l1_id, 'fill_in_blank', 'Completa el código para crear una lista vacía:<br><code>mi_lista = ___</code>',
             '', '[]', 'Una lista vacía se crea con corchetes vacíos', 10)
        ]
        
        cursor.executemany('''
            INSERT INTO ejercicios (leccion_id, tipo, pregunta, opciones, respuesta_correcta, explicacion, puntos)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ejercicios_u4_l1)
        
        # Ejercicios para la Lección 2 de Unidad 4: Manipulación de listas - 10 ejercicios totales (4 opción múltiple + 3 verdadero/falso + 3 fill_in_blank)
        ejercicios_u4_l2 = [
            # Opción múltiple (4 ejercicios)
            (leccion_u4_l2_id, 'opcion_multiple', '¿Qué método se usa para agregar un elemento al final de una lista?',
             'a) add()|b) append()|c) insert()|d) push()',
             'b', 'El método append() agrega un elemento al final de la lista', 10),
            
            (leccion_u4_l2_id, 'opcion_multiple', '¿Qué método se usa para eliminar un elemento específico de una lista?',
             'a) delete()|b) remove()|c) pop()|d) clear()',
             'b', 'El método remove() elimina la primera ocurrencia del elemento especificado', 10),
            
            (leccion_u4_l2_id, 'opcion_multiple', '¿Qué método se usa para insertar un elemento en una posición específica?',
             'a) append()|b) insert()|c) add()|d) push()',
             'b', 'El método insert() permite insertar un elemento en una posición específica: insert(posicion, elemento)', 10),
            
            (leccion_u4_l2_id, 'opcion_multiple', '¿Qué método se usa para ordenar una lista de forma ascendente?',
             'a) order()|b) sort()|c) arrange()|d) organize()',
             'b', 'El método sort() ordena los elementos de la lista de forma ascendente', 10),
            
            # Verdadero/Falso (3 ejercicios)
            (leccion_u4_l2_id, 'verdadero_falso', 'El método append() agrega un elemento al final de la lista',
             '', 'verdadero', 'append() siempre agrega el elemento al final de la lista', 10),
            
            (leccion_u4_l2_id, 'verdadero_falso', 'El método remove() elimina todos los elementos iguales de la lista',
             '', 'falso', 'remove() solo elimina la primera ocurrencia del elemento especificado', 10),
            
            (leccion_u4_l2_id, 'verdadero_falso', 'El método sort() modifica la lista original',
             '', 'verdadero', 'sort() modifica la lista original, no crea una nueva lista ordenada', 10),
            
            # Fill in the blank (3 ejercicios)
            (leccion_u4_l2_id, 'fill_in_blank', 'Completa el código para agregar el elemento "pera" al final de la lista:<br><code>frutas = ["manzana", "banana"]<br>frutas.___("pera")</code>',
             '', 'append', 'El método append() agrega un elemento al final de la lista', 10),
            
            (leccion_u4_l2_id, 'fill_in_blank', 'Completa el código para eliminar "banana" de la lista:<br><code>frutas = ["manzana", "banana", "naranja"]<br>frutas.___("banana")</code>',
             '', 'remove', 'El método remove() elimina la primera ocurrencia del elemento especificado', 10),
            
            (leccion_u4_l2_id, 'fill_in_blank', 'Completa el código para insertar "uva" en la posición 1:<br><code>frutas = ["manzana", "banana"]<br>frutas.___(1, "uva")</code>',
             '', 'insert', 'El método insert() inserta un elemento en la posición especificada', 10)
        ]
        
        cursor.executemany('''
            INSERT INTO ejercicios (leccion_id, tipo, pregunta, opciones, respuesta_correcta, explicacion, puntos)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ejercicios_u4_l2)
        
        # Ejercicios para la Lección 3 de Unidad 4: Diccionarios - 10 ejercicios totales (4 opción múltiple + 3 verdadero/falso + 3 fill_in_blank)
        ejercicios_u4_l3 = [
            # Opción múltiple (4 ejercicios)
            (leccion_u4_l3_id, 'opcion_multiple', '¿Qué es un diccionario en Python?',
             'a) Una lista ordenada|b) Una colección de pares clave-valor|c) Solo números|d) Solo texto',
             'b', 'Un diccionario es una colección de pares clave-valor donde cada elemento tiene una clave única', 10),
            
            (leccion_u4_l3_id, 'opcion_multiple', '¿Cómo se crea un diccionario vacío en Python?',
             'a) dict = []|b) dict = {}|c) dict = ()|d) dict = dict',
             'b', 'Un diccionario vacío se crea usando llaves vacías: dict = {}', 10),
            
            (leccion_u4_l3_id, 'opcion_multiple', '¿Cuál es la forma correcta de crear un diccionario con la clave "nombre" y valor "Juan"?',
             'a) dict = nombre: "Juan"|b) dict = {"nombre": "Juan"}|c) dict = [nombre, "Juan"]|d) dict = (nombre, "Juan")',
             'b', 'Los diccionarios usan llaves y cada par clave-valor se separa por comas: {"nombre": "Juan"}', 10),
            
            (leccion_u4_l3_id, 'opcion_multiple', '¿Cómo se accede al valor de la clave "edad" en un diccionario llamado "persona"?',
             'a) persona(edad)|b) persona["edad"]|c) persona{edad}|d) persona.edad',
             'b', 'Los valores de un diccionario se acceden usando corchetes con la clave: persona["edad"]', 10),
            
            # Verdadero/Falso (3 ejercicios)
            (leccion_u4_l3_id, 'verdadero_falso', 'Las claves de un diccionario deben ser únicas',
             '', 'verdadero', 'Cada clave en un diccionario debe ser única. Si se repite, se sobrescribe el valor anterior', 10),
            
            (leccion_u4_l3_id, 'verdadero_falso', 'Un diccionario puede tener valores de diferentes tipos de datos',
             '', 'verdadero', 'Un diccionario puede contener valores de diferentes tipos: números, strings, listas, etc.', 10),
            
            (leccion_u4_l3_id, 'verdadero_falso', 'Las claves de un diccionario pueden ser números',
             '', 'verdadero', 'Las claves pueden ser strings, números u otros tipos inmutables', 10),
            
            # Fill in the blank (3 ejercicios)
            (leccion_u4_l3_id, 'fill_in_blank', 'Completa el código para crear un diccionario con información de una persona y mostrar el nombre:<br><code>nombre_clave = "nombre"<br>edad_clave = ___<br>persona = {nombre_clave: "Ana", edad_clave: 25, "ciudad": "Madrid"}<br>print("Nombre:", persona["nombre"])<br>print("Edad:", persona[edad_clave])</code>',
             '', '"edad"', 'Las claves de un diccionario van entre comillas cuando son strings', 10),
            
            (leccion_u4_l3_id, 'fill_in_blank', 'Completa el código para acceder y mostrar información del diccionario:<br><code>persona = {"nombre": "Luis", "edad": 30, "profesion": "Ingeniero"}<br>clave_nombre = ___<br>nombre = persona[clave_nombre]<br>edad = persona["edad"]<br>print(f"{nombre} tiene {edad} años")</code>',
             '', '"nombre"', 'Se accede al valor usando la clave entre corchetes y comillas', 10),
            
            (leccion_u4_l3_id, 'fill_in_blank', 'Completa el código para crear un diccionario vacío y luego agregar elementos:<br><code>estudiante = ___<br>estudiante["nombre"] = "María"<br>estudiante["nota"] = 95<br>print(estudiante)</code>',
             '', '{}', 'Un diccionario vacío se crea con llaves vacías y luego se pueden agregar elementos', 10)
        ]
        
        cursor.executemany('''
            INSERT INTO ejercicios (leccion_id, tipo, pregunta, opciones, respuesta_correcta, explicacion, puntos)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ejercicios_u4_l3)
        
        # Ejercicios para la Lección 4 de Unidad 4: Acceder y modificar información dentro de un diccionario - 10 ejercicios totales (4 opción múltiple + 3 verdadero/falso + 3 fill_in_blank)
        ejercicios_u4_l4 = [
            # Opción múltiple (4 ejercicios)
            (leccion_u4_l4_id, 'opcion_multiple', '¿Cómo se actualiza el valor de una clave existente en un diccionario?',
             'a) update()|b) Asignando directamente: diccionario["clave"] = valor|c) modify()|d) change()',
             'b', 'Se actualiza asignando directamente: diccionario["clave"] = nuevo_valor', 10),
            
            (leccion_u4_l4_id, 'opcion_multiple', '¿Qué método se usa para eliminar un elemento de un diccionario?',
             'a) remove()|b) delete()|c) pop()|d) clear()',
             'c', 'El método pop() elimina un elemento del diccionario usando su clave', 10),
            
            (leccion_u4_l4_id, 'opcion_multiple', '¿Qué método se usa para obtener todas las claves de un diccionario?',
             'a) keys()|b) get_keys()|c) all_keys()|d) key_list()',
             'a', 'El método keys() devuelve todas las claves del diccionario', 10),
            
            (leccion_u4_l4_id, 'opcion_multiple', '¿Qué método se usa para obtener todos los valores de un diccionario?',
             'a) values()|b) get_values()|c) all_values()|d) value_list()',
             'a', 'El método values() devuelve todos los valores del diccionario', 10),
            
            # Verdadero/Falso (4 ejercicios)
            (leccion_u4_l4_id, 'verdadero_falso', 'Puedes agregar una nueva clave-valor a un diccionario asignando directamente',
             '', 'verdadero', 'Puedes agregar nuevos elementos asignando: diccionario["nueva_clave"] = valor', 10),
            
            (leccion_u4_l4_id, 'verdadero_falso', 'El método pop() requiere especificar la clave del elemento a eliminar',
             '', 'verdadero', 'pop() necesita la clave como argumento: diccionario.pop("clave")', 10),
            
            (leccion_u4_l4_id, 'verdadero_falso', 'El método clear() elimina todos los elementos del diccionario',
             '', 'verdadero', 'clear() elimina todos los elementos, dejando el diccionario vacío', 10),
            
            (leccion_u4_l4_id, 'verdadero_falso', 'Puedes actualizar el valor de una clave existente en un diccionario asignando directamente: diccionario["clave"] = nuevo_valor',
             '', 'verdadero', 'Puedes actualizar valores asignando directamente usando la clave entre corchetes', 10),
            
            # Fill in the blank (2 ejercicios)
            (leccion_u4_l4_id, 'fill_in_blank', 'Completa el código para eliminar una clave y verificar que fue eliminada:<br><code>persona = {"nombre": "Luis", "edad": 30, "telefono": "123456"}<br>metodo = ___<br>getattr(persona, metodo)("telefono")<br>if "telefono" not in persona:<br>    print("Teléfono eliminado correctamente")</code>',
             '', '"pop"', 'El método pop() elimina un elemento usando su clave. Se usa getattr() para llamar al método dinámicamente', 10),
            
            (leccion_u4_l4_id, 'fill_in_blank', 'Completa el código para agregar información adicional al diccionario:<br><code>persona = {"nombre": "Ana", "edad": 25}<br>clave = ___<br>valor = ___<br>persona[clave] = valor<br>persona["pais"] = "España"<br>print(f"{persona[\'nombre\']} vive en {persona[\'ciudad\']}")</code>',
             '', '"ciudad"|"Madrid"', 'Se agregan nuevos elementos asignando directamente con la clave y el valor', 10)
        ]
        
        cursor.executemany('''
            INSERT INTO ejercicios (leccion_id, tipo, pregunta, opciones, respuesta_correcta, explicacion, puntos)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ejercicios_u4_l4)
        
        # Ejercicios para la Lección 1 de Unidad 5: El ciclo for - 10 ejercicios totales (4 opción múltiple + 3 verdadero/falso + 3 fill_in_blank)
        ejercicios_u5_l1 = [
            # Opción múltiple (4 ejercicios)
            (leccion_u5_l1_id, 'opcion_multiple', '¿Qué es un ciclo for en Python?',
             'a) Una función|b) Una estructura que repite código para cada elemento de una secuencia|c) Un operador|d) Una variable',
             'b', 'El ciclo for repite código para cada elemento de una secuencia como una lista', 10),
            
            (leccion_u5_l1_id, 'opcion_multiple', '¿Cuál es la sintaxis correcta para recorrer una lista llamada "frutas"?',
             'a) for frutas:|b) for elemento in frutas:|c) for frutas in elemento:|d) for in frutas:',
             'b', 'La sintaxis correcta es: for variable in lista:', 10),
            
            (leccion_u5_l1_id, 'opcion_multiple', '¿Qué hace el siguiente código: for numero in [1, 2, 3]: print(numero)?',
             'a) Imprime solo el número 1|b) Imprime los números 1, 2 y 3 uno por uno|c) No imprime nada|d) Da error',
             'b', 'El ciclo for recorre cada elemento de la lista e imprime cada número', 10),
            
            (leccion_u5_l1_id, 'opcion_multiple', '¿Puedes usar un ciclo for para recorrer un string?',
             'a) No, solo listas|b) Sí, recorre cada carácter del string|c) Solo si es corto|d) Solo números',
             'b', 'Sí, el ciclo for puede recorrer strings, recorriendo cada carácter', 10),
            
            # Verdadero/Falso (3 ejercicios)
            (leccion_u5_l1_id, 'verdadero_falso', 'El ciclo for puede recorrer listas, strings y otros tipos de secuencias',
             '', 'verdadero', 'El ciclo for puede recorrer cualquier secuencia: listas, strings, tuplas, etc.', 10),
            
            (leccion_u5_l1_id, 'verdadero_falso', 'En un ciclo for, la variable toma el valor de cada elemento de la secuencia',
             '', 'verdadero', 'La variable en el for toma el valor de cada elemento en cada iteración', 10),
            
            (leccion_u5_l1_id, 'verdadero_falso', 'El ciclo for siempre necesita una lista para funcionar',
             '', 'falso', 'El ciclo for puede trabajar con cualquier secuencia iterable, no solo listas', 10),
            
            # Fill in the blank (3 ejercicios)
            (leccion_u5_l1_id, 'fill_in_blank', 'Completa el código para recorrer la lista e imprimir cada elemento con su índice:<br><code>frutas = ["manzana", "banana", "naranja"]<br>indice = 0<br>for fruta in frutas:<br>    print(f"{indice}: {fruta}")<br>    indice = indice + ___</code>',
             '', '1', 'Se suma 1 al índice en cada iteración para contar los elementos', 10),
            
            (leccion_u5_l1_id, 'fill_in_blank', 'Completa el código para contar cuántas letras tiene la palabra:<br><code>palabra = "Python"<br>contador = 0<br>for letra in palabra:<br>    contador = contador + ___<br>print(f"La palabra tiene {contador} letras")</code>',
             '', '1', 'Se suma 1 al contador por cada letra encontrada', 10),
            
            (leccion_u5_l1_id, 'fill_in_blank', 'Completa el código para calcular el promedio de los números:<br><code>numeros = [10, 20, 30, 40]<br>suma = 0<br>cantidad = 0<br>for numero in numeros:<br>    suma = suma + numero<br>    cantidad = cantidad + 1<br>promedio = suma ___ cantidad<br>print(f"El promedio es {promedio}")</code>',
             '', '/', 'Se usa el operador / para dividir la suma entre la cantidad y obtener el promedio', 10)
        ]
        
        cursor.executemany('''
            INSERT INTO ejercicios (leccion_id, tipo, pregunta, opciones, respuesta_correcta, explicacion, puntos)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ejercicios_u5_l1)
        
        # Ejercicios para la Lección 2 de Unidad 5: La función range() - 10 ejercicios totales (4 opción múltiple + 3 verdadero/falso + 3 fill_in_blank)
        ejercicios_u5_l2 = [
            # Opción múltiple (4 ejercicios)
            (leccion_u5_l2_id, 'opcion_multiple', '¿Qué hace la función range(5)?',
             'a) Crea una lista con los números del 0 al 5|b) Genera una secuencia de números del 0 al 4|c) Crea una lista con 5 elementos|d) Genera números aleatorios',
             'b', 'range(5) genera una secuencia del 0 al 4 (5 números empezando desde 0)', 10),
            
            (leccion_u5_l2_id, 'opcion_multiple', '¿Qué números genera range(1, 5)?',
             'a) 1, 2, 3, 4, 5|b) 1, 2, 3, 4|c) 0, 1, 2, 3, 4|d) 5, 4, 3, 2, 1',
             'b', 'range(1, 5) genera números del 1 al 4 (incluye el inicio, excluye el final)', 10),
            
            (leccion_u5_l2_id, 'opcion_multiple', '¿Qué hace range(0, 10, 2)?',
             'a) Genera números del 0 al 10|b) Genera números pares del 0 al 8 (0, 2, 4, 6, 8)|c) Genera números del 0 al 2|d) Genera 10 números',
             'b', 'range(0, 10, 2) genera números del 0 al 8 de 2 en 2: 0, 2, 4, 6, 8', 10),
            
            (leccion_u5_l2_id, 'opcion_multiple', '¿Cómo se usa range() con un ciclo for para repetir código 5 veces?',
             'a) for i in range(5):|b) for range(5):|c) for i in 5:|d) for 5:',
             'a', 'Se usa for i in range(5): para repetir código 5 veces', 10),
            
            # Verdadero/Falso (3 ejercicios)
            (leccion_u5_l2_id, 'verdadero_falso', 'range(5) genera números del 0 al 4',
             '', 'verdadero', 'range(5) genera una secuencia del 0 al 4 (5 números empezando desde 0)', 10),
            
            (leccion_u5_l2_id, 'verdadero_falso', 'range(1, 5) incluye el número 5 en la secuencia',
             '', 'falso', 'range(1, 5) genera números del 1 al 4, excluyendo el 5', 10),
            
            (leccion_u5_l2_id, 'verdadero_falso', 'Puedes usar range() con un paso negativo para contar hacia atrás',
             '', 'verdadero', 'Sí, puedes usar range(10, 0, -1) para contar del 10 al 1', 10),
            
            # Fill in the blank (3 ejercicios)
            (leccion_u5_l2_id, 'fill_in_blank', 'Completa el código para imprimir números del 0 al 4:<br><code>for i in range(___):<br>    print(i)</code>',
             '', '5', 'range(5) genera números del 0 al 4', 10),
            
            (leccion_u5_l2_id, 'fill_in_blank', 'Completa el código para imprimir números del 5 al 10:<br><code>for numero in range(5, ___):<br>    print(numero)</code>',
             '', '11', 'range(5, 11) genera números del 5 al 10 (el segundo parámetro es exclusivo)', 10),
            
            (leccion_u5_l2_id, 'fill_in_blank', 'Completa el código para imprimir números impares del 1 al 9:<br><code>for i in range(1, 10, ___):<br>    print(i)</code>',
             '', '2', 'range(1, 10, 2) genera números impares: 1, 3, 5, 7, 9', 10)
        ]
        
        cursor.executemany('''
            INSERT INTO ejercicios (leccion_id, tipo, pregunta, opciones, respuesta_correcta, explicacion, puntos)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ejercicios_u5_l2)
        
        # Ejercicios para la Lección 3 de Unidad 5: El ciclo while - 10 ejercicios totales (4 opción múltiple + 3 verdadero/falso + 3 fill_in_blank)
        ejercicios_u5_l3 = [
            # Opción múltiple (4 ejercicios)
            (leccion_u5_l3_id, 'opcion_multiple', '¿Qué es un ciclo while en Python?',
             'a) Un ciclo que se ejecuta un número fijo de veces|b) Un ciclo que se ejecuta mientras una condición sea verdadera|c) Un ciclo que solo funciona con listas|d) Una función',
             'b', 'El ciclo while se ejecuta mientras la condición sea verdadera', 10),
            
            (leccion_u5_l3_id, 'opcion_multiple', '¿Cuál es la sintaxis correcta para un ciclo while?',
             'a) while condicion:|b) while (condicion):|c) while condicion do:|d) while condicion {',
             'a', 'La sintaxis correcta es: while condicion: seguido de código con indentación', 10),
            
            (leccion_u5_l3_id, 'opcion_multiple', '¿Qué puede pasar si olvidas actualizar la variable en un ciclo while?',
             'a) El ciclo se ejecuta una vez|b) El ciclo puede ejecutarse infinitamente|c) El ciclo no se ejecuta|d) No pasa nada',
             'b', 'Si no actualizas la condición, el ciclo puede ejecutarse infinitamente (bucle infinito)', 10),
            
            (leccion_u5_l3_id, 'opcion_multiple', '¿Cuándo se detiene un ciclo while?',
             'a) Siempre después de 10 iteraciones|b) Cuando la condición se vuelve falsa|c) Nunca se detiene|d) Solo con break',
             'b', 'El ciclo while se detiene cuando la condición se vuelve falsa', 10),
            
            # Verdadero/Falso (3 ejercicios)
            (leccion_u5_l3_id, 'verdadero_falso', 'El ciclo while se ejecuta mientras la condición sea verdadera',
             '', 'verdadero', 'El ciclo while continúa ejecutándose mientras la condición sea True', 10),
            
            (leccion_u5_l3_id, 'verdadero_falso', 'Un ciclo while puede ejecutarse infinitamente si la condición nunca se vuelve falsa',
             '', 'verdadero', 'Si la condición siempre es verdadera y no se actualiza, el ciclo será infinito', 10),
            
            (leccion_u5_l3_id, 'verdadero_falso', 'El ciclo while siempre necesita una lista para funcionar',
             '', 'falso', 'El ciclo while solo necesita una condición booleana, no una lista', 10),
            
            # Fill in the blank (3 ejercicios)
            (leccion_u5_l3_id, 'fill_in_blank', 'Completa el código para contar desde 0 hasta 4:<br><code>contador = 0<br>while contador < 5:<br>    print(contador)<br>    contador = contador + ___</code>',
             '', '1', 'Se suma 1 al contador en cada iteración para avanzar', 10),
            
            (leccion_u5_l3_id, 'fill_in_blank', 'Completa el código para contar hacia atrás desde 10 hasta 1:<br><code>numero = 10<br>while numero > 0:<br>    print(numero)<br>    numero = numero - ___</code>',
             '', '1', 'Se resta 1 al número en cada iteración para contar hacia atrás', 10),
            
            (leccion_u5_l3_id, 'fill_in_blank', 'Completa el código para repetir hasta que el usuario ingrese "salir":<br><code>entrada = ""<br>while entrada != ___:<br>    entrada = input("Escribe algo: ")<br>    print(f"Escribiste: {entrada}")<br>print("Programa terminado")</code>',
             '', '"salir"', 'Se compara con "salir" para determinar cuándo terminar el ciclo', 10)
        ]
        
        cursor.executemany('''
            INSERT INTO ejercicios (leccion_id, tipo, pregunta, opciones, respuesta_correcta, explicacion, puntos)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ejercicios_u5_l3)
        
        # Ejercicios para la Lección 4 de Unidad 5: break y continue - 10 ejercicios totales (4 opción múltiple + 3 verdadero/falso + 3 fill_in_blank)
        ejercicios_u5_l4 = [
            # Opción múltiple (4 ejercicios)
            (leccion_u5_l4_id, 'opcion_multiple', '¿Qué hace la palabra clave break en un ciclo?',
             'a) Continúa con la siguiente iteración|b) Detiene completamente el ciclo|c) Reinicia el ciclo|d) No hace nada',
             'b', 'break detiene completamente el ciclo y sale de él', 10),
            
            (leccion_u5_l4_id, 'opcion_multiple', '¿Qué hace la palabra clave continue en un ciclo?',
             'a) Detiene el ciclo|b) Salta a la siguiente iteración sin ejecutar el resto del código|c) Reinicia el ciclo|d) Imprime un mensaje',
             'b', 'continue salta a la siguiente iteración sin ejecutar el código restante', 10),
            
            (leccion_u5_l4_id, 'opcion_multiple', '¿En qué tipo de ciclos puedes usar break y continue?',
             'a) Solo en for|b) Solo en while|c) En for y while|d) En ningún ciclo',
             'c', 'break y continue funcionan tanto en ciclos for como while', 10),
            
            (leccion_u5_l4_id, 'opcion_multiple', 'Si tienes un ciclo for y usas break cuando i == 3, ¿qué pasa?',
             'a) El ciclo continúa normalmente|b) El ciclo se detiene completamente cuando i es 3|c) Solo se salta la iteración cuando i es 3|d) El ciclo se reinicia',
             'b', 'break detiene completamente el ciclo cuando se ejecuta', 10),
            
            # Verdadero/Falso (3 ejercicios)
            (leccion_u5_l4_id, 'verdadero_falso', 'break detiene completamente el ciclo y sale de él',
             '', 'verdadero', 'break termina el ciclo inmediatamente y continúa con el código después del ciclo', 10),
            
            (leccion_u5_l4_id, 'verdadero_falso', 'continue salta a la siguiente iteración sin ejecutar el código restante',
             '', 'verdadero', 'continue salta el código restante de la iteración actual y va a la siguiente', 10),
            
            (leccion_u5_l4_id, 'verdadero_falso', 'break y continue solo funcionan en ciclos for',
             '', 'falso', 'break y continue funcionan tanto en ciclos for como while', 10),
            
            # Fill in the blank (3 ejercicios)
            (leccion_u5_l4_id, 'fill_in_blank', 'Completa el código para detener el ciclo cuando encontremos un número mayor que 5:<br><code>numeros = [1, 3, 7, 2, 9]<br>for numero in numeros:<br>    if numero > 5:<br>        print(f"Encontrado {numero}, deteniendo")<br>        ___<br>    print(numero)</code>',
             '', 'break', 'Se usa break para detener completamente el ciclo cuando se encuentra un número mayor que 5', 10),
            
            (leccion_u5_l4_id, 'fill_in_blank', 'Completa el código para imprimir solo números impares (saltar los pares):<br><code>for i in range(10):<br>    if i % 2 == 0:<br>        ___<br>    print(i)</code>',
             '', 'continue', 'Se usa continue para saltar a la siguiente iteración cuando el número es par', 10),
            
            (leccion_u5_l4_id, 'fill_in_blank', 'Completa el código para buscar un valor y detener cuando lo encontremos:<br><code>valores = [10, 20, 30, 40, 50]<br>buscado = 30<br>for valor in valores:<br>    if valor == buscado:<br>        print(f"¡Encontrado {buscado}!")<br>        ___<br>    print(f"Buscando... {valor}")</code>',
             '', 'break', 'Se usa break para detener el ciclo cuando se encuentra el valor buscado', 10)
        ]
        
        cursor.executemany('''
            INSERT INTO ejercicios (leccion_id, tipo, pregunta, opciones, respuesta_correcta, explicacion, puntos)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ejercicios_u5_l4)
    
    # Siempre hacer commit para asegurar que las tablas se guarden
    conn.commit()
    conn.close()
    print("Base de datos inicializada correctamente")

# La función get_db_connection ya está definida arriba

if __name__ == '__main__':
    init_db()