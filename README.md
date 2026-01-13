# CodeBase

Plataforma educativa en línea basada en Flask para el aprendizaje interactivo con lecciones, ejercicios y evaluaciones.

## Características

- 🎓 Sistema de lecciones estructuradas por unidades
- ✍️ Ejercicios interactivos (opción múltiple, verdadero/falso, rellenar espacios)
- 📊 Seguimiento del progreso del estudiante
- 🔒 Sistema de autenticación seguro
- 👨‍💼 Panel de administración para gestión de contenido
- 📄 Soporte para contenido en PDF
- 🎖️ Generación de certificados
- 💾 Base de datos SQLite

## Tecnologías

- **Backend**: Flask (Python)
- **Frontend**: HTML5, CSS3, JavaScript
- **Base de datos**: SQLite3
- **Despliegue**: Render.com

## Requisitos previos

- Python 3.7+
- pip (gestor de paquetes de Python)
- Git

## Instalación

1. Clonar el repositorio:
```bash
git clone https://github.com/DenisS-h/CodeBase.git
cd CodeBase
```

2. Crear un entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Configurar variables de entorno:
```bash
# Crear archivo .env
cp .env.example .env  # Si existe
# Editar .env con tus valores
```

5. Ejecutar la aplicación:
```bash
python app.py
```

La aplicación estará disponible en `http://localhost:5000`

## Estructura del proyecto

```
CodeBase/
├── app.py                 # Archivo principal de la aplicación
├── database.py            # Configuración de la base de datos
├── models.py              # Modelos de datos
├── email_service.py       # Servicio de envío de emails
├── requirements.txt       # Dependencias del proyecto
├── templates/             # Plantillas HTML
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── leccion.html
│   └── admin/             # Plantillas del panel de administración
├── static/                # Archivos estáticos
│   ├── css/              # Estilos CSS
│   ├── js/               # Scripts JavaScript
│   └── uploads/          # Archivos subidos por usuarios
└── instance/             # Datos de instancia (base de datos)
```

## Uso

### Para estudiantes
1. Registrarse en la plataforma
2. Acceder al dashboard para ver el progreso
3. Completar lecciones y ejercicios
4. Ver calificaciones y certificados

### Para administradores
1. Acceder al panel de administración
2. Gestionar usuarios y contenido
3. Crear ejercicios y subir PDFs
4. Visualizar el progreso de estudiantes

## Licencia

Este proyecto está bajo licencia MIT.

## Autor

Denis S-h

## Contacto

Para preguntas o sugerencias, por favor abre un issue en el repositorio.
