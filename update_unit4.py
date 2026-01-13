import sqlite3
import os

DATABASE_PATH = os.path.join('instance', 'aprendizaje.db')

def update_unit4_content():
    print(f"Conectando a {DATABASE_PATH}...")
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        # 1. Asegurar que la Unidad 4 existe
        print("Verificando Unidad 4...")
        cursor.execute("SELECT id FROM unidades WHERE numero = 4")
        unit_result = cursor.fetchone()
        
        if not unit_result:
            print("Creando Unidad 4...")
            cursor.execute('''
                INSERT INTO unidades (numero, titulo, descripcion, orden)
                VALUES (4, 'Listas y diccionarios', 'En lugar de tener datos sueltos, aprenderás a agruparlos. Verás cómo manejar colecciones de elementos de forma ordenada y cómo usar etiquetas para encontrar información rápidamente', 4)
            ''')
            unit_id = cursor.lastrowid
        else:
            unit_id = unit_result[0]
            print(f"Unidad 4 existe con ID: {unit_id}")

        # 2. Definir Lecciones de la Unidad 4
        lessons_data = [
            {
                'orden': 1,
                'titulo': 'Listas: Guardando múltiples datos',
                'descripcion': 'Aprende a crear listas para guardar varios elementos en una sola variable',
                'puntos': 120,
                'theory': '''
                <h3>📋 ¿Qué es una Lista?</h3>
                <p>Imagina que tienes una mochila. En lugar de llevar tus libros en las manos, los metes todos en la mochila. ¡Una <strong>lista</strong> es como esa mochila!</p>
                <p>Te permite guardar muchos valores en una sola variable, ordenados uno tras otro.</p>
                <h3>Sintaxis</h3>
                <p>Las listas se crean usando corchetes <code>[]</code> y separando los elementos con comas.</p>
                <pre>
# Una lista de números
numeros = [1, 2, 3, 4, 5]

# Una lista de textos
frutas = ["Manzana", "Banana", "Cereza"]

# ¡Puedes mezclar tipos!
mezcla = [10, "Hola", True]</pre>
                <h3>Accediendo a los datos</h3>
                <p>Cada elemento tiene una posición (índice). <strong>¡Cuidado!</strong> En programación, empezamos a contar desde <strong>0</strong>.</p>
                <pre>
frutas = ["Manzana", "Banana", "Cereza"]
# Índices:    0          1         2

print(frutas[0])  # Salida: "Manzana"
print(frutas[1])  # Salida: "Banana"</pre>
                ''',
                'exercises': [
                    ('opcion_multiple', '¿Con qué símbolo se crean las listas en Python?',
                     'a) Paréntesis ()|b) Llaves {}|c) Corchetes []|d) Comillas ""', 'c', 'Las listas se definen usando corchetes []', 10),
                    ('fill_in_blank', 'Si lista = ["A", "B", "C"], ¿qué imprime lista[1]?<br><code>lista = ["A", "B", "C"]<br>print(lista[1])</code>',
                     '', 'B', 'El índice 1 es el segundo elemento, ya que empezamos a contar desde 0', 10),
                    ('verdadero_falso', 'El primer elemento de una lista siempre tiene el índice 1',
                     '', 'falso', 'El primer elemento siempre tiene el índice 0', 10)
                ]
            },
            {
                'orden': 2,
                'titulo': 'Métodos de listas: Agregando y quitando',
                'descripcion': 'Aprende a modificar tus listas usando métodos como append, remove y len',
                'puntos': 130,
                'theory': '''
                <h3>🛠️ Modificando Listas</h3>
                <p>Las listas son dinámicas: ¡pueden crecer y encogerse! Python nos da herramientas (métodos) para trabajar con ellas.</p>
                <ul>
                    <li><code>append(valor)</code>: Agrega un elemento al <strong>final</strong> de la lista.</li>
                    <li><code>insert(posicion, valor)</code>: Agrega un elemento en una posición específica.</li>
                    <li><code>remove(valor)</code>: Busca y elimina la primera aparición de ese valor.</li>
                    <li><code>pop(posicion)</code>: Elimina el elemento en esa posición (si no pones nada, elimina el último).</li>
                    <li><code>len(lista)</code>: Nos dice <strong>cuántos</strong> elementos tiene la lista.</li>
                </ul>
                <h3>Ejemplos:</h3>
                <pre>
colores = ["Rojo", "Verde"]

# Agregar
colores.append("Azul")  
# Ahora es ["Rojo", "Verde", "Azul"]

# Eliminar
colores.remove("Rojo")
# Ahora es ["Verde", "Azul"]

# Contar
cantidad = len(colores) # 2</pre>
                ''',
                'exercises': [
                    ('opcion_multiple', '¿Qué método agrega un elemento al final de la lista?',
                     'a) add()|b) push()|c) append()|d) insert()', 'c', 'El método append() agrega elementos al final', 10),
                     ('verdadero_falso', 'len() devuelve el último elemento de la lista',
                     '', 'falso', 'len() devuelve la cantidad total de elementos (longitud) de la lista', 10),
                    ('fill_in_blank', 'Completa el código para agregar "Perro" a la lista:<br><code>animales = ["Gato"]<br>animales.___("Perro")</code>',
                     '', 'append', 'Usamos append para agregar elementos', 10)
                ]
            },
            {
                'orden': 3,
                'titulo': 'Diccionarios: Etiquetas para tus datos',
                'descripcion': 'Usa diccionarios para guardar información asociada clave-valor',
                'puntos': 140,
                'theory': '''
                <h3>📖 ¿Qué es un Diccionario?</h3>
                <p>Imagina un diccionario real: buscas una palabra (clave) y encuentras su definición (valor). ¡En Python es igual!</p>
                <p>Los diccionarios guardan pares de <strong>Clave: Valor</strong>. Son perfectos para guardar información estructurada, como el perfil de un usuario.</p>
                <h3>Sintaxis</h3>
                <p>Usamos llaves <code>{}</code> y separamos la clave del valor con dos puntos <code>:</code>.</p>
                <pre>
usuario = {
    "nombre": "Ana",
    "edad": 25,
    "es_estudiante": True
}

# Acceder a datos usando la clave (NO índices)
print(usuario["nombre"])  # Salida: "Ana"
print(usuario["edad"])    # Salida: 25</pre>
                <p>💡 A diferencia de las listas, ¡el orden no importa tanto, importan las claves!</p>
                ''',
                'exercises': [
                    ('opcion_multiple', '¿Qué símbolo se usa para definir un diccionario?',
                     'a) []|b) ()|c) {}|d) <>', 'c', 'Los diccionarios usan llaves {}', 10),
                    ('verdadero_falso', 'En un diccionario accedemos a los valores usando su índice numérico (0, 1, 2...)',
                     '', 'falso', 'En los diccionarios accedemos a los valores usando sus Claves (Keys)', 10),
                    ('fill_in_blank', 'Completa para obtener el valor de "color":<br><code>auto = {"color": "rojo"}<br>print(auto[___])</code>',
                     '', '"color"|\'color\'', 'Debes usar la clave exacta entre comillas', 10)
                ]
            },
            {
                'orden': 4,
                'titulo': 'Tuplas y Sets: Colecciones especiales',
                'descripcion': 'Conoce las tuplas (inmutables) y los sets (sin duplicados)',
                'puntos': 150,
                'theory': '''
                <h3>🔒 Tuplas: Las listas intocables</h3>
                <p>Las <strong>Tuplas</strong> son como listas, pero <strong>inmutables</strong>. Una vez creadas, ¡no se pueden cambiar! (no puedes agregar, quitar ni modificar elementos).</p>
                <p>Se usan paréntesis <code>()</code>.</p>
                <pre>
coordenadas = (10, 20)
# coordenadas[0] = 15  <- ¡Esto daría ERROR!
</pre>
                <h3>✨ Sets: Sin repetidos</h3>
                <p>Los <strong>Sets</strong> (conjuntos) son colecciones desordenadas que <strong>no permiten duplicados</strong>. ¡Son útiles para eliminar repetidos!</p>
                <p>Se usan llaves <code>{}</code> como los diccionarios, pero sin los dos puntos.</p>
                <pre>
numeros = {1, 2, 2, 3, 3, 3}
print(numeros)  # Salida: {1, 2, 3} ¡Magia!
</pre>
                ''',
                'exercises': [
                     ('opcion_multiple', '¿Cuál es la principal diferencia entre una lista y una tupla?',
                     'a) Las tuplas son más lentas|b) Las tuplas son inmutables (no cambian)|c) Las listas no guardan texto|d) No hay diferencia', 'b', 'Las tuplas son inmutables, no se pueden modificar después de creadas', 10),
                    ('verdadero_falso', 'Un Set (conjunto) puede tener el mismo valor repetido varias veces',
                     '', 'falso', 'Los Sets eliminan automáticamente los valores duplicados', 10),
                    ('fill_in_blank', 'Completa para crear una tupla:<br><code>puntos = _10, 20_</code>',
                     '', '(|)', 'Las tuplas se definen con paréntesis ()', 10)
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
            ''', (lemma_id, 'teoria', lesson_data['theory'], None, 'OK', 'Conceptos aprendidos', 0))
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
    update_unit4_content()
