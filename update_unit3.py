import sqlite3
import os

DATABASE_PATH = os.path.join('instance', 'aprendizaje.db')

def update_unit3_content():
    print(f"Conectando a {DATABASE_PATH}...")
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        # 1. Asegurar que la Unidad 3 existe
        print("Verificando Unidad 3...")
        cursor.execute("SELECT id FROM unidades WHERE numero = 3")
        unit_result = cursor.fetchone()
        
        if not unit_result:
            print("Creando Unidad 3...")
            cursor.execute('''
                INSERT INTO unidades (numero, titulo, descripcion, orden)
                VALUES (3, 'Operadores y condicionales', 'Aquí aprenderás a hacer que tu programa tome decisiones. Usarás símbolos matemáticos para comparar datos y crearás reglas para que el código haga cosas distintas según el caso', 3)
            ''')
            unit_id = cursor.lastrowid
        else:
            unit_id = unit_result[0]
            print(f"Unidad 3 existe con ID: {unit_id}")

        # 2. Definir Lecciones de la Unidad 3
        lessons_data = [
            {
                'orden': 1,
                'titulo': 'Operadores aritméticos (suma, resta, multiplicación, división)',
                'descripcion': 'Usa los operadores +, -, *, / y otros para realizar cálculos matemáticos',
                'puntos': 80,
                'theory': '''
                <h3>🔢 Matemáticas en Python</h3>
                <p>Python funciona como una calculadora superpoderosa. Puedes usar los símbolos matemáticos básicos que ya conoces:</p>
                <ul>
                    <li><code>+</code> para suma</li>
                    <li><code>-</code> para resta</li>
                    <li><code>*</code> para multiplicación (usa el asterisco)</li>
                    <li><code>/</code> para división (usa la barra inclinada)</li>
                </ul>
                <p>Pero también tiene algunos poderes especiales:</p>
                <ul>
                    <li><code>//</code> <strong>División entera:</strong> Divide y descarta los decimales (ej: <code>7 // 2</code> da <code>3</code>).</li>
                    <li><code>%</code> <strong>Módulo:</strong> Te da el <em>resto</em> de una división (ej: <code>7 % 3</code> da <code>1</code>). ¡Muy útil para saber si un número es par o impar!</li>
                    <li><code>**</code> <strong>Potencia:</strong> Eleva un número a otro (ej: <code>2 ** 3</code> es 2 al cubo, que da <code>8</code>).</li>
                </ul>
                <h3>Ejemplos:</h3>
                <pre>
print(10 + 5)   # Salida: 15
print(10 - 2)   # Salida: 8
print(3 * 4)    # Salida: 12
print(10 / 2)   # Salida: 5.0 (siempre decimal)
print(10 // 3)  # Salida: 3 (sin decimales)
print(10 % 3)   # Salida: 1 (el resto)
print(2 ** 3)   # Salida: 8 (2*2*2)</pre>
                ''',
                'exercises': [
                    ('opcion_multiple', '¿Qué operador se usa para la exponenciación (elevar a una potencia)?',
                     'a) ^|b) **|c) pow()|d) exp()', 'b', 'El operador ** se usa para exponenciación. Por ejemplo: 2 ** 3 = 8', 10),
                    ('fill_in_blank', 'Completa el código para sumar dos números y mostrar el resultado:<br><code>a = 5<br>b = 3<br><br>suma = a ___ b<br>print(___)</code>',
                     '', '+|suma', 'El operador + se usa para sumar dos números y luego se muestra el resultado con print()', 10),
                    ('verdadero_falso', 'El operador // puede usarse solo con números enteros',
                     '', 'falso', 'El operador // puede usarse con cualquier número. Si divides 7.5 // 2, el resultado es 3.0 (float)', 10)
                ]
            },
            {
                'orden': 2,
                'titulo': 'Comparaciones (mayor que, menor que, igual a)',
                'descripcion': 'Compara valores usando operadores como >, <, ==, != para tomar decisiones',
                'puntos': 90,
                'theory': '''
                <h3>⚖️ Comparando valores</h3>
                <p>A menudo necesitamos saber si un número es mayor que otro, o si dos textos son iguales. Para esto usamos los <strong>operadores de comparación</strong>. ¡Siempre responden con <code>True</code> (Verdadero) o <code>False</code> (Falso)!</p>
                <ul>
                    <li><code>==</code> <strong>Igual a:</strong> ¿Son estos dos valores idénticos? (Ojo: usa dos signos igual, uno solo es para asignar variables).</li>
                    <li><code>!=</code> <strong>Diferente de:</strong> ¿Son distintos?</li>
                    <li><code>></code> <strong>Mayor que</strong></li>
                    <li><code><</code> <strong>Menor que</strong></li>
                    <li><code>>=</code> <strong>Mayor o igual que</strong></li>
                    <li><code><=</code> <strong>Menor o igual que</strong></li>
                </ul>
                <h3>Ejemplos:</h3>
                <pre>
edad = 18
print(edad >= 18)   # Salida: True
print(edad == 20)   # Salida: False
print(edad != 10)   # Salida: True

nombre = "Ana"
print(nombre == "ana") # Salida: False (¡Las mayúsculas importan!)</pre>
                ''',
                'exercises': [
                    ('opcion_multiple', '¿Qué operador se usa para verificar si dos valores son iguales?',
                     'a) =|b) ==|c) ===|d) equals()', 'b', 'El operador == verifica si dos valores son iguales. El operador = se usa para asignación', 10),
                     ('verdadero_falso', 'La expresión 5 > 10 devuelve True',
                     '', 'falso', 'La expresión 5 > 10 es falsa porque 5 no es mayor que 10. Devuelve False', 10),
                    ('fill_in_blank', 'Completa el código para verificar si dos números son iguales:<br><code>a = 10<br>b = 10<br><br>if a ___ b:<br>    print("Los números son iguales")</code>',
                     '', '==', 'El operador == verifica si dos valores son iguales', 10)
                ]
            },
            {
                'orden': 3,
                'titulo': 'La estructura if y else: Tomando decisiones',
                'descripcion': 'Crea programas que tomen decisiones usando las estructuras if y else',
                'puntos': 100,
                'theory': '''
                <h3>🤔 Tomando decisiones con If / Else</h3>
                <p>Hasta ahora nuestro código siempre seguía una línea recta. ¡Con <code>if</code> (si) y <code>else</code> (si no), podemos crear caminos!</p>
                <p>La estructura básica es:</p>
                <pre>
if condicion:
    # Código que se ejecuta si es VERDAD
    # ¡Nota la indentación (sangría)!
else:
    # Código que se ejecuta si es FALSO</pre>
                <p>🛑 <strong>¡Importante!</strong> En Python, los espacios en blanco al principio de la línea (indentación) son obligatorios. Indican qué código pertenece al bloque <code>if</code> o <code>else</code>.</p>
                <h3>Ejemplo:</h3>
                <pre>
edad = 15

if edad >= 18:
    print("Eres mayor de edad")
    print("Puedes votar")
else:
    print("Eres menor de edad")
    print("Aún no puedes votar")
    
print("Este mensaje se imprime siempre") # Está fuera del if/else</pre>
                ''',
                'exercises': [
                    ('opcion_multiple', '¿Qué símbolo se usa para indicar el bloque de código dentro de un if en Python?',
                     'a) Llaves { }|b) Paréntesis ( )|c) Indentación (espacios o tabs)|d) Corchetes [ ]', 'c', 'En Python, la indentación (espacios o tabs) indica el bloque de código que pertenece al if', 10),
                    ('verdadero_falso', 'El bloque else siempre se ejecuta cuando la condición del if es falsa',
                     '', 'verdadero', 'El bloque else se ejecuta siempre que la condición del if sea False', 10),
                    ('fill_in_blank', 'Completa el código:<br><code>nota = 8<br>___ nota >= 6:<br>    print("Aprobado")<br>___:<br>    print("Reprobado")</code>',
                     '', 'if|else', 'Se usa if para la condición principal y else para el caso contrario', 10)
                ]
            },
            {
                'orden': 4,
                'titulo': 'Condiciones múltiples: elif, and, or',
                'descripcion': 'Maneja múltiples condiciones usando elif y combina condiciones con and y or',
                'puntos': 110,
                'theory': '''
                <h3>🔀 Múltiples Caminos</h3>
                <p>¿Qué pasa si tienes más de dos opciones? Usamos <code>elif</code> (abreviatura de "else if").</p>
                <pre>
color = "rojo"

if color == "verde":
    print("Avanzar")
elif color == "amarillo":
    print("Precaución")
elif color == "rojo":
    print("Detenerse")
else:
    print("Color desconocido")</pre>
                <h3>🤝 Conectores Lógicos</h3>
                <p>A veces necesitas verificar dos cosas a la vez. Para eso usamos:</p>
                <ul>
                    <li><code>and</code> (y): Ambas condiciones deben ser Verdad. (Ej: Tener dinero Y tener tiempo).</li>
                    <li><code>or</code> (o): Basta con que UNA sea Verdad. (Ej: Es sábado O es domingo).</li>
                    <li><code>not</code> (no): Invierte el valor (True se vuelve False y viceversa).</li>
                </ul>
                <pre>
if tiene_entrada and es_mayor_edad:
    print("Puede entrar al club")
    
if dia == "Sabado" or dia == "Domingo":
    print("Es fin de semana")</pre>
                ''',
                'exercises': [
                     ('opcion_multiple', '¿Qué palabra clave se usa para agregar condiciones adicionales después de un if?',
                     'a) else if|b) elif|c) elseif|d) and if', 'b', 'La palabra clave elif se usa para agregar condiciones adicionales', 10),
                    ('verdadero_falso', 'El operador and devuelve True solo si ambas condiciones son verdaderas',
                     '', 'verdadero', 'Correcto, ambas partes deben ser ciertas', 10),
                    ('fill_in_blank', 'Completa el código:<br><code>edad = 20<br>dinero = True<br>if edad >= 18 ___ dinero:<br>    print("Puedes comprar")</code>',
                     '', 'and', 'Necesitas ser mayor de edad Y tener dinero', 10)
                ]
            }
        ]

        # 3. Procesar cada lección
        for lesson_data in lessons_data:
            print(f"Procesando lección: {lesson_data['titulo']}")
            
            # Buscar si la lección ya existe
            cursor.execute('''
                SELECT id FROM lecciones 
                WHERE unidad_id = ? AND orden = ?
            ''', (unit_id, lesson_data['orden']))
            
            lesson_result = cursor.fetchone()
            
            if lesson_result:
                lemma_id = lesson_result[0]
                # Actualizar datos de la lección
                cursor.execute('''
                    UPDATE lecciones 
                    SET titulo = ?, descripcion = ?, puntos_requeridos = ?
                    WHERE id = ?
                ''', (lesson_data['titulo'], lesson_data['descripcion'], lesson_data['puntos'], lemma_id))
                
                # Eliminar ejercicios existentes para evitar duplicados y reordenar
                cursor.execute("DELETE FROM ejercicios WHERE leccion_id = ?", (lemma_id,))
                print(f"  Ejercicios antiguos eliminados para lección ID {lemma_id}")
            else:
                # Insertar nueva lección
                cursor.execute('''
                    INSERT INTO lecciones (unidad_id, titulo, descripcion, puntos_requeridos, orden)
                    VALUES (?, ?, ?, ?, ?)
                ''', (unit_id, lesson_data['titulo'], lesson_data['descripcion'], lesson_data['puntos'], lesson_data['orden']))
                lemma_id = cursor.lastrowid
                print(f"  Nueva lección creada con ID {lemma_id}")

            # 4. Insertar Teoría como primer ejercicio
            cursor.execute('''
                INSERT INTO ejercicios (leccion_id, tipo, pregunta, opciones, respuesta_correcta, explicacion, puntos)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (lemma_id, 'teoria', lesson_data['theory'], None, 'OK', 'Conceptos clave aprendidos', 0))
            print("  Teoría insertada")

            # 5. Insertar Ejercicios prácticos
            for ex in lesson_data['exercises']:
                tipo, preg, opc, resp, expl, pts = ex
                cursor.execute('''
                    INSERT INTO ejercicios (leccion_id, tipo, pregunta, opciones, respuesta_correcta, explicacion, puntos)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (lemma_id, tipo, preg, opc, resp, expl, pts))
            print(f"  {len(lesson_data['exercises'])} ejercicios prácticos insertados")

        conn.commit()
        print("\n¡Actualización completada exitosamente!")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error durante la actualización: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    update_unit3_content()
