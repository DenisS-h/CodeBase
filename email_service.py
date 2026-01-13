"""
Módulo de servicio de correo electrónico para CodeBase
Maneja el envío de correos usando Flask-Mail y SMTP
"""

from flask_mail import Mail, Message
from flask import render_template
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

mail = None

def init_mail(app):
    """
    Inicializar Flask-Mail con la aplicación Flask
    """
    global mail
    
    # Configuración de Flask-Mail desde variables de entorno
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True') == 'True'
    app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'False') == 'True'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    
    # Configurar remitente por defecto con nombre "CodeBase"
    default_sender = os.getenv('MAIL_DEFAULT_SENDER')
    if not default_sender and app.config['MAIL_USERNAME']:
        default_sender = f"CodeBase <{app.config['MAIL_USERNAME']}>"
    
    app.config['MAIL_DEFAULT_SENDER'] = default_sender
    
    mail = Mail(app)
    return mail

def enviar_email_bienvenida(nombre, email):
    """
    Enviar correo de bienvenida a un nuevo usuario
    
    Args:
        nombre (str): Nombre del usuario
        email (str): Dirección de correo electrónico del usuario
    
    Returns:
        bool: True si el correo se envió exitosamente, False en caso contrario
    """
    try:
        # Obtener email de envío para asegurar formato "CodeBase <email>"
        sender_email = os.getenv('MAIL_USERNAME')
        sender = f"CodeBase <{sender_email}>" if sender_email else None

        # Crear el mensaje
        msg = Message(
            subject='¡Bienvenido a CodeBase! 🎉',
            sender=sender,
            recipients=[email]
        )
        
        # Renderizar el template HTML
        msg.html = render_template('emails/bienvenida.html', nombre=nombre)
        
        # Versión de texto plano como fallback
        msg.body = f"""
¡Hola {nombre}!

Bienvenido a CodeBase, tu plataforma de aprendizaje de programación.

Estamos emocionados de tenerte con nosotros. CodeBase te ayudará a aprender Python
de manera interactiva y divertida, con ejercicios prácticos y un sistema de 
progreso que te mantendrá motivado.

¿Qué puedes hacer ahora?
- Explora las lecciones disponibles
- Completa ejercicios interactivos
- Gana puntos y mantén tu racha de aprendizaje

¡Comienza tu viaje de programación hoy mismo!

Saludos,
El equipo de CodeBase
        """
        
        # Enviar el correo
        mail.send(msg)
        return True
        
    except Exception as e:
        # Registrar el error (en producción, usar un logger apropiado)
        print(f"❌ ERROR CRÍTICO al enviar email de bienvenida a {email}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def debug_email_config():
    """Imprime la configuración actual de email para depuración"""
    print("--- DEPURACIÓN DE CONFIGURACIÓN DE EMAIL ---")
    print(f"MAIL_SERVER: {os.getenv('MAIL_SERVER')}")
    print(f"MAIL_PORT: {os.getenv('MAIL_PORT')}")
    print(f"MAIL_USE_TLS: {os.getenv('MAIL_USE_TLS')}")
    print(f"MAIL_USERNAME: {os.getenv('MAIL_USERNAME')}")
    # No imprimir contraseña real
    has_pwd = bool(os.getenv('MAIL_PASSWORD'))
    print(f"MAIL_PASSWORD configurado: {'SÍ' if has_pwd else 'NO'}")
    print("------------------------------------------")


def enviar_email_recuperacion(nombre, email, password_temporal):
    """
    Enviar correo de recuperación de contraseña con contraseña temporal
    
    Args:
        nombre (str): Nombre del usuario
        email (str): Dirección de correo electrónico
        password_temporal (str): Nueva contraseña temporal generada
    
    Returns:
        bool: True si el correo se envió exitosamente, False en caso contrario
    """
    try:
        # Obtener email de envío para asegurar formato "CodeBase <email>"
        sender_email = os.getenv('MAIL_USERNAME')
        sender = f"CodeBase <{sender_email}>" if sender_email else None
        
        # Crear el mensaje
        msg = Message(
            subject='Recuperación de Contraseña - CodeBase',
            sender=sender,
            recipients=[email]
        )
        
        # Renderizar el template HTML
        # Nota: Asegurar que existe este template
        msg.html = render_template('emails/recuperacion.html', 
                                 nombre=nombre, 
                                 password_temporal=password_temporal)
        
        # Versión de texto plano como fallback
        msg.body = f"""
¡Hola {nombre}!

Hemos recibido una solicitud para restablecer tu contraseña en CodeBase.

Tu nueva contraseña temporal es: {password_temporal}

Por favor, inicia sesión con esta contraseña y cámbiala inmediatamente desde tu perfil 
o contactando al administrador.

Si no solicitaste este cambio, por favor contacta al soporte inmediatamente.

Saludos,
El equipo de CodeBase
        """
        
        # Enviar el correo
        mail.send(msg)
        return True
        
    except Exception as e:
        print(f"❌ ERROR CRÍTICO al enviar email de recuperación a {email}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
