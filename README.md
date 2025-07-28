# Buscaminas Web

Una aplicación web del clásico juego Buscaminas desarrollada con Flask.

## Características

- Tres niveles de dificultad: Fácil, Medio y Difícil
- Modo personalizado para configurar tablero
- Dos modos de juego: Clásico y Experto
- Sistema de récords (opcional con MongoDB)
- Interfaz responsive y moderna

## Despliegue en Vercel

### Configuración de Variables de Entorno

Para que la aplicación funcione completamente, configura las siguientes variables de entorno en el dashboard de Vercel:

1. Ve a tu proyecto en [Vercel Dashboard](https://vercel.com/dashboard)
2. Selecciona tu proyecto `buscaminas-flask`
3. Ve a la pestaña "Settings" → "Environment Variables"
4. Agrega las siguientes variables:

```
MONGO_URI=mongodb+srv://usuario:contraseña@cluster.mongodb.net/buscaminas_db
```

**Nota**: Si no configuras `MONGO_URI`, la aplicación funcionará sin la funcionalidad de récords globales.

### Despliegue

1. Conecta tu repositorio de GitHub a Vercel
2. Vercel detectará automáticamente que es una aplicación Python/Flask
3. El archivo `vercel.json` ya está configurado correctamente
4. Haz push de los cambios y Vercel desplegará automáticamente

## Desarrollo Local

1. Clona el repositorio
2. Instala las dependencias: `pip install -r requirements.txt`
3. Crea un archivo `.env` con las variables de entorno
4. Ejecuta: `python app.py`
5. Abre http://localhost:5000

## Estructura del Proyecto

```
buscaminas_web/
├── app.py              # Aplicación principal Flask
├── requirements.txt    # Dependencias Python
├── vercel.json        # Configuración de Vercel
├── static/            # Archivos estáticos (CSS, imágenes)
└── templates/         # Plantillas HTML
```

## Solución de Problemas

Si encuentras errores 500 en Vercel:

1. Verifica que todas las dependencias estén en `requirements.txt`
2. Asegúrate de que las variables de entorno estén configuradas
3. Revisa los logs en el dashboard de Vercel
4. La aplicación funcionará sin MongoDB, pero sin récords globales 