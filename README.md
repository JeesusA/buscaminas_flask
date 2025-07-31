# 🧨 Buscaminas Web

Una aplicación web del clásico juego Buscaminas desarrollada con Flask y Socket.IO para multijugador en tiempo real.

## 🎮 Características

- **Tres niveles de dificultad**: Fácil, Medio y Difícil
- **Modo personalizado** para configurar tablero
- **Dos modos de juego**: Clásico y Experto
- **Multijugador cooperativo** en tiempo real
- **Sistema de récords** (opcional con MongoDB)
- **Interfaz responsive** y moderna
- **Chat en tiempo real** para multijugador

## 🚀 Despliegue en Railway

### Configuración de Variables de Entorno

Para que la aplicación funcione completamente, configura las siguientes variables de entorno en Railway:

1. Ve a tu proyecto en [Railway Dashboard](https://railway.app/dashboard)
2. Selecciona tu proyecto `buscaminas-web`
3. Ve a la pestaña "Variables"
4. Agrega las siguientes variables:

```
MONGO_URI=mongodb+srv://usuario:contraseña@cluster.mongodb.net/buscaminas_db
```

**Nota**: Si no configuras `MONGO_URI`, la aplicación funcionará sin la funcionalidad de récords globales.

### Despliegue

1. Conecta tu repositorio de GitHub a Railway
2. Railway detectará automáticamente que es una aplicación Python/Flask
3. Los archivos `Procfile` y `runtime.txt` ya están configurados
4. Haz push de los cambios y Railway desplegará automáticamente

## 💻 Desarrollo Local

1. Clona el repositorio
2. Instala las dependencias: `pip install -r requirements.txt`
3. Crea un archivo `.env` con las variables de entorno
4. Ejecuta: `python app.py`
5. Abre http://localhost:5000

## 📁 Estructura del Proyecto

```
buscaminas_web/
├── app.py              # Aplicación principal Flask + Socket.IO
├── requirements.txt    # Dependencias Python
├── Procfile           # Configuración para Railway
├── runtime.txt        # Versión de Python
├── static/            # Archivos estáticos (CSS, imágenes, GIFs)
└── templates/         # Plantillas HTML
    ├── index.html     # Juego principal
    ├── inicio.html    # Menú principal
    ├── multijugador.html # Lobby multijugador
    ├── sala.html      # Sala de juego multijugador
    └── tutorial.html  # Tutorial del juego
```

## 🎯 Modos de Juego

### Juego Individual
- **Clásico**: Juego tradicional de buscaminas
- **Experto**: Solo 1 error permitido
- **Contrarreloj**: Tiempo limitado para completar

### Multijugador Cooperativo
- **Mínimo 2 jugadores** para comenzar
- **Turnos rotativos** entre jugadores
- **Victoria/derrota compartida**
- **Chat en tiempo real**

## 🔧 Solución de Problemas

Si encuentras errores en Railway:

1. Verifica que todas las dependencias estén en `requirements.txt`
2. Asegúrate de que las variables de entorno estén configuradas
3. Revisa los logs en el dashboard de Railway
4. La aplicación funcionará sin MongoDB, pero sin récords globales

## 🌟 Tecnologías

- **Backend**: Flask, Socket.IO, Python
- **Frontend**: HTML5, CSS3, JavaScript
- **Base de datos**: MongoDB (opcional)
- **Deploy**: Railway 