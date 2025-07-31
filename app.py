from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
import random
import json
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
client = None
db = None
records_collection = None

if MONGO_URI:
    try:
        from pymongo import MongoClient
        client = MongoClient(MONGO_URI)
        db = client['buscaminas_db']
        records_collection = db['records']
    except Exception as e:
        print(f"Error conectando a MongoDB: {e}")
        records_collection = None
else:
    records_collection = None

app = Flask(__name__)
app.secret_key = "buscaminas_secret_key"
socketio = SocketIO(app, cors_allowed_origins="*")

salas = {}
jugadores = {}

NIVELES = [
    ("Fácil", 8, 8, 10),
    ("Medio", 16, 16, 40),
    ("Difícil", 16, 30, 99)
]

def crear_tablero(filas, columnas, minas):
    if filas < 5 or columnas < 5 or minas < 1 or minas >= filas * columnas:
        raise ValueError("Parámetros inválidos para el tablero.")
    tablero = [[0 for _ in range(columnas)] for _ in range(filas)]
    todas_pos = [(f, c) for f in range(filas) for c in range(columnas)]
    bombas = set()
    max_adyacentes = 5  # Máximo de minas adyacentes permitidas por celda
    intentos = 0
    random.shuffle(todas_pos)
    for f, c in todas_pos:
        if len(bombas) >= minas:
            break
        # Simula colocar la mina y verifica adyacentes
        adyacentes = [(i, j) for i in range(max(0, f-1), min(filas, f+2))
                              for j in range(max(0, c-1), min(columnas, c+2))
                              if not (i == f and j == c)]
        excede = False
        for i, j in adyacentes:
            count = 0
            for ii in range(max(0, i-1), min(filas, i+2)):
                for jj in range(max(0, j-1), min(columnas, j+2)):
                    if (ii, jj) in bombas or (ii == f and jj == c):
                        count += 1
            if count > max_adyacentes:
                excede = True
                break
        if not excede:
            bombas.add((f, c))
        intentos += 1
        if intentos > filas * columnas * 2:
            break  # Evita bucles infinitos
    # Si faltan minas, colócalas aleatoriamente sin restricción
    restantes = minas - len(bombas)
    if restantes > 0:
        libres = [pos for pos in todas_pos if pos not in bombas]
        bombas.update(random.sample(libres, restantes))
    for f, c in bombas:
        tablero[f][c] = -1
    for f in range(filas):
        for c in range(columnas):
            if tablero[f][c] == -1:
                continue
            count = 0
            for i in range(max(0, f-1), min(filas, f+2)):
                for j in range(max(0, c-1), min(columnas, c+2)):
                    if tablero[i][j] == -1:
                        count += 1
            tablero[f][c] = count
    return tablero



@app.route("/")
def inicio():
    try:
        records = session.get('records', {})
        return render_template("inicio.html", records=records)
    except Exception as e:
        print(f"[ERROR inicio] {str(e)}")
        return f"Error al cargar la página de inicio: {str(e)}", 500

@app.route("/multijugador")
def multijugador():
    return render_template("multijugador.html")

@app.route("/sala/<sala_id>")
def sala(sala_id):
    if sala_id not in salas:
        return redirect(url_for('multijugador'))
    return render_template("sala.html", sala_id=sala_id)

@app.route("/jugar", methods=["POST"])
def jugar():
    try:
        nivel = request.form.get("nivel")
        modo = request.form.get("modo", "clasico")
        if nivel == "facil":
            nombre, filas, columnas, minas = NIVELES[0]
            tiempo_limite = 60
        elif nivel == "medio":
            nombre, filas, columnas, minas = NIVELES[1]
            tiempo_limite = 120
        elif nivel == "dificil":
            nombre, filas, columnas, minas = NIVELES[2]
            tiempo_limite = 240
        elif nivel == "personalizado":
            try:
                filas = int(request.form.get("filas", 10))
                columnas = int(request.form.get("columnas", 10))
                minas = int(request.form.get("minas", 10))
                nombre = "Personalizado"
                if filas < 5: filas = 5
                if columnas < 5: columnas = 5
                if minas < 1: minas = 1
                if minas > filas * columnas - 1:
                    minas = filas * columnas - 1
                # Tiempo proporcional: 60s para 8x8, 120s para 16x16, 240s para 16x30
                base = filas * columnas
                if base <= 64:
                    tiempo_limite = 60
                elif base <= 256:
                    tiempo_limite = 120
                else:
                    tiempo_limite = 240
            except Exception:
                filas, columnas, minas = 10, 10, 10
                nombre = "Personalizado"
                tiempo_limite = 90
        else:
            nombre, filas, columnas, minas = NIVELES[0]
            tiempo_limite = 60
        tablero = crear_tablero(filas, columnas, minas)
        session['tablero'] = json.dumps(tablero)
        session['filas'] = filas
        session['columnas'] = columnas
        session['minas'] = minas
        session['descubierto'] = json.dumps([[False for _ in range(columnas)] for _ in range(filas)])
        session['bandera'] = json.dumps([[False for _ in range(columnas)] for _ in range(filas)])
        session['juego_terminado'] = False
        session['nivel_actual'] = nombre
        return render_template("index.html", filas=filas, columnas=columnas, nivel=nombre, minas=minas, modo=modo, tiempo_limite=tiempo_limite)
    except Exception as e:
        print(f"[ERROR jugar] {str(e)}")
        return f"Error al iniciar el juego: {str(e)}", 500

@app.route("/jugar", methods=["GET"])
def jugar_get():
    return redirect(url_for('inicio'))

@app.route("/tutorial", methods=["GET", "POST"])
def tutorial():
    if request.method == "GET":
        return redirect(url_for('inicio'))
    return render_template("tutorial.html")

@app.route("/accion", methods=["POST"])
def accion():
    try:
        data = request.json
        f = data.get('fila')
        c = data.get('columna')
        tipo = data.get('tipo')
        modo = session.get('modo', 'clasico')
        if f is None or c is None or tipo not in ["descubrir", "bandera"]:
            return jsonify({'error': 'Datos inválidos'}), 400
        tablero = json.loads(session.get('tablero', '[]'))
        filas = session.get('filas')
        columnas = session.get('columnas')
        minas = session.get('minas')
        descubierto = json.loads(session.get('descubierto', '[]'))
        bandera = json.loads(session.get('bandera', '[]'))
        juego_terminado = session.get('juego_terminado', False)
        resultado = {"fin": False, "ganaste": False}
        if not tablero or filas is None or columnas is None or minas is None:
            return jsonify({'error': 'Sesión inválida'}), 400
        if juego_terminado:
            resultado["fin"] = True
            return jsonify(resultado)
        if tipo == "descubrir":
            if bandera[f][c]:
                bandera[f][c] = False
            if descubierto[f][c]:
                return jsonify(resultado)
            if tablero[f][c] == -1:
                descubierto[f][c] = True
                resultado["fin"] = True
                resultado["perdiste"] = True
                session['juego_terminado'] = True
            else:
                revelar(tablero, descubierto, f, c)
        elif tipo == "bandera":
            if not descubierto[f][c]:
                # Modo experto: perder si marcas bandera en celda sin mina
                if modo == 'experto' and not bandera[f][c] and tablero[f][c] != -1:
                    resultado["fin"] = True
                    resultado["perdiste"] = True
                    resultado["bandera_incorrecta"] = True
                    session['juego_terminado'] = True
                else:
                    bandera[f][c] = not bandera[f][c]
        sin_minas = 0
        for i in range(filas):
            for j in range(columnas):
                if not descubierto[i][j] and tablero[i][j] != -1:
                    sin_minas += 1
        if sin_minas == 0:
            resultado["fin"] = True
            resultado["ganaste"] = True
            session['juego_terminado'] = True
        session['descubierto'] = json.dumps(descubierto)
        session['bandera'] = json.dumps(bandera)
        resultado["descubierto"] = descubierto
        resultado["bandera"] = bandera
        resultado["tablero"] = tablero if resultado["fin"] else [[tablero[i][j] if descubierto[i][j] else "" for j in range(columnas)] for i in range(filas)]
        return jsonify(resultado)
    except Exception as e:
        print(f"[ERROR accion] {str(e)}")
        return jsonify({'error': f'Error en la acción: {str(e)}'}), 500

@app.route("/record", methods=["POST"])
def record():
    try:
        data = request.get_json()
        nivel = data.get('nivel', 'Desconocido')
        records = session.get('records', {})
        if nivel not in records:
            records[nivel] = 0
        records[nivel] += 1
        session['records'] = records
        return jsonify({'ok': True, 'records': records})
    except Exception as e:
        print(f"[ERROR record] {str(e)}")
        return jsonify({'error': f'Error al guardar el récord: {str(e)}'}), 500

@app.route("/api/record", methods=["POST"])
def guardar_record():
    data = request.get_json()
    nombre = data.get("nombre", "Anónimo")
    tiempo = data.get("tiempo")
    nivel = data.get("nivel", "Desconocido")
    uuid = data.get("uuid")
    if tiempo is None or uuid is None:
        return jsonify({"error": "Tiempo y uuid requeridos"}), 400
    record = {
        "nombre": nombre,
        "tiempo": tiempo,
        "nivel": nivel,
        "uuid": uuid,
        "fecha": datetime.utcnow()
    }
    # Elimina cualquier récord anterior del mismo usuario y nivel
    if records_collection is not None:
        records_collection.delete_many({"uuid": uuid, "nivel": nivel})
        result = records_collection.insert_one(record)
        return jsonify({"ok": True, "id": str(result.inserted_id)})
    else:
        print("MongoDB no disponible, no se puede guardar el récord.")
        return jsonify({"ok": True, "message": "MongoDB no disponible, récord no guardado."})

def formatear_tiempo(segundos):
    """Convierte segundos a formato MM:SS"""
    if isinstance(segundos, (int, float)):
        minutos = int(segundos // 60)
        segs = int(segundos % 60)
        return f"{minutos:02d}:{segs:02d}"
    return str(segundos)

@app.route("/api/ranking", methods=["GET"])
def ranking_global():
    try:
        nivel = request.args.get("nivel", None)
        filtro = {"nivel": nivel} if nivel else {}
        
        # Top 10 mejores tiempos
        if records_collection is not None:
            try:
                records = list(records_collection.find(filtro).sort("tiempo", 1).limit(10))
                
                # Convertir ObjectId y fecha a string, formatear tiempo
                for r in records:
                    r["id"] = str(r.pop("_id"))
                    r["fecha"] = r["fecha"].strftime("%Y-%m-%d %H:%M") if "fecha" in r else ""
                    r["tiempo"] = formatear_tiempo(r["tiempo"])
                
                return jsonify({"records": records})
            except Exception as e:
                print(f"[ERROR] Error al obtener ranking de MongoDB: {e}")
                return jsonify({"records": []})
        else:
            return jsonify({"records": []})
    except Exception as e:
        print(f"[ERROR] Error general en ranking_global: {e}")
        return jsonify({"records": []})



def revelar(tablero, descubierto, f, c):
    if descubierto[f][c]:
        return
    filas = len(tablero)
    columnas = len(tablero[0])
    queue = [(f, c)]
    while queue:
        x, y = queue.pop()
        if not (0 <= x < filas and 0 <= y < columnas):
            continue
        if descubierto[x][y]:
            continue
        descubierto[x][y] = True
        if tablero[x][y] == 0:
            for i in range(x-1, x+2):
                for j in range(y-1, y+2):
                    if 0 <= i < filas and 0 <= j < columnas and not descubierto[i][j]:
                        queue.append((i, j))

@app.errorhandler(404)
def page_not_found(e):
    return redirect(url_for('inicio'))

# Eventos de Socket.IO para multijugador
@socketio.on('connect')
def handle_connect():
    print(f"Cliente conectado: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    session_id = request.sid
    if session_id in jugadores:
        jugador = jugadores[session_id]
        sala_id = jugador['sala_id']
        if sala_id in salas:
            # Guardar información del jugador que se desconecta
            jugador_desconectado = jugador['nombre']
            
            # Remover jugador de la sala
            salas[sala_id]['jugadores'].pop(session_id, None)
            
            if len(salas[sala_id]['jugadores']) == 0:
                # Si no quedan jugadores, eliminar la sala
                del salas[sala_id]
            else:
                # Actualizar lista de jugadores para turnos (remover jugador desconectado)
                if session_id in salas[sala_id]['jugadores_lista']:
                    indice_desconectado = salas[sala_id]['jugadores_lista'].index(session_id)
                    salas[sala_id]['jugadores_lista'].remove(session_id)
                    
                    # CORRECCIÓN: Ajustar turno actual correctamente
                    if len(salas[sala_id]['jugadores_lista']) > 0:
                        # Si el jugador que se fue era el actual, pasar al siguiente
                        if salas[sala_id]['turno_actual'] == indice_desconectado:
                            # El turno se mantiene en la misma posición, pero ahora apunta al siguiente jugador
                            salas[sala_id]['turno_actual'] = salas[sala_id]['turno_actual'] % len(salas[sala_id]['jugadores_lista'])
                        # Si el jugador que se fue estaba antes del turno actual, ajustar índice
                        elif salas[sala_id]['turno_actual'] > indice_desconectado:
                            salas[sala_id]['turno_actual'] -= 1
                    else:
                        # Si no quedan jugadores en la lista, resetear turno
                        salas[sala_id]['turno_actual'] = 0
                
                print(f"[DEBUG] Desconexión: {jugador_desconectado} salió. turno_actual: {salas[sala_id]['turno_actual']}, jugadores_lista: {salas[sala_id]['jugadores_lista']}")
                
                # Notificar a los jugadores restantes
                emit('jugador_salio', {'jugador': jugador_desconectado}, room=sala_id)
                emit('actualizar_jugadores', {
                    'jugadores': list(salas[sala_id]['jugadores'].values())
                }, room=sala_id)
        
        del jugadores[session_id]

@socketio.on('crear_sala')
def handle_crear_sala(data):
    sala_id = str(random.randint(1000, 9999))
    nivel = data.get('nivel', 'facil')
    
    if nivel == 'facil':
        filas, columnas, minas = 8, 8, 10
    elif nivel == 'medio':
        filas, columnas, minas = 16, 16, 40
    else:
        filas, columnas, minas = 16, 30, 99
    
    tablero = crear_tablero(filas, columnas, minas)
    colores = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#feca57', '#ff9ff3']
    
    salas[sala_id] = {
        'tablero': tablero,
        'descubierto': [[False for _ in range(columnas)] for _ in range(filas)],
        'bandera': [[False for _ in range(columnas)] for _ in range(filas)],
        'jugadores': {},
        'estado': 'esperando',
        'filas': filas,
        'columnas': columnas,
        'minas': minas,
        'creador': None,
        'turno_actual': 0,
        'jugadores_lista': []
    }
    
    emit('sala_creada', {'sala_id': sala_id})

@socketio.on('unirse_sala')
def handle_unirse_sala(data):
    sala_id = data['sala_id']
    nombre = data['nombre']
    uuid_jugador = data.get('uuid', None)
    
    if sala_id not in salas:
        emit('error', {'mensaje': 'Sala no encontrada'})
        return
    
    session_id = request.sid
    colores = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#feca57', '#ff9ff3']
    color = colores[len(salas[sala_id]['jugadores']) % len(colores)]
    
    if not uuid_jugador:
        import uuid
        uuid_jugador = str(uuid.uuid4())
    
    jugadores[session_id] = {
        'nombre': nombre,
        'sala_id': sala_id,
        'color': color,
        'uuid': uuid_jugador
    }
    
    if len(salas[sala_id]['jugadores']) == 0:
        salas[sala_id]['creador'] = session_id
    
    salas[sala_id]['jugadores'][session_id] = {
        'nombre': nombre,
        'color': color,
        'es_creador': salas[sala_id]['creador'] == session_id,
        'uuid': uuid_jugador
    }
    
    if session_id not in salas[sala_id]['jugadores_lista']:
        salas[sala_id]['jugadores_lista'].append(session_id)
    
    num_jugadores_antes = len(salas[sala_id]['jugadores']) - 1
    
    if num_jugadores_antes == 0:
        pass
    elif num_jugadores_antes == 1:
        salas[sala_id]['turno_actual'] = random.randint(0, 1)
        jugador_inicial = salas[sala_id]['jugadores_lista'][salas[sala_id]['turno_actual']]
        jugador_inicial_nombre = salas[sala_id]['jugadores'][jugador_inicial]['nombre']
        jugador_inicial_uuid = salas[sala_id]['jugadores'][jugador_inicial]['uuid']
        
        emit('turno_asignado', {
            'jugador_actual': jugador_inicial_nombre,
            'uuid_actual': jugador_inicial_uuid,
            'turno_actual': salas[sala_id]['turno_actual']
        }, room=sala_id)
    
    join_room(sala_id)
    emit('jugador_unido', {
        'jugador': nombre,
        'color': color,
        'jugadores': list(salas[sala_id]['jugadores'].values()),
        'uuid': uuid_jugador
    }, room=sala_id)
    
    emit('actualizar_jugadores', {
        'jugadores': list(salas[sala_id]['jugadores'].values())
    }, room=sala_id)
    
    emit('unirse_exitoso', {
        'sala_id': sala_id,
        'nombre': nombre,
        'uuid': uuid_jugador
    })

@socketio.on('accion_multijugador')
def handle_accion_multijugador(data):
    session_id = request.sid
    if session_id not in jugadores:
        return
    
    jugador = jugadores[session_id]
    sala_id = jugador['sala_id']
    
    if sala_id not in salas:
        return
    
    sala = salas[sala_id]
    
    if len(sala['jugadores_lista']) > 0 and sala['turno_actual'] < len(sala['jugadores_lista']):
        jugador_actual = sala['jugadores_lista'][sala['turno_actual']]
        
        if session_id != jugador_actual:
            emit('error_turno', {
                'mensaje': 'No es tu turno. Espera a que el otro jugador termine.',
                'jugador_actual': sala['jugadores'][jugador_actual]['nombre'],
                'uuid_actual': sala['jugadores'][jugador_actual]['uuid']
            })
            return
    else:
        return
    
    f = data['fila']
    c = data['columna']
    tipo = data['tipo']
    
    if tipo == 'descubrir':
        if sala['descubierto'][f][c]:
            return
        
        if sala['tablero'][f][c] == -1:
            sala['descubierto'][f][c] = True
            sala['estado'] = 'perdido'
            emit('mina_encontrada', {
                'fila': f, 'columna': c,
                'jugador': jugador['nombre'],
                'uuid_jugador': jugador['uuid'],
                'estado': 'perdido'
            }, room=sala_id)
        else:
            revelar(sala['tablero'], sala['descubierto'], f, c)
            celdas_descubiertas = sum(sum(sala['descubierto'], []))
            
            celdas_nuevas = 0
            for i in range(sala['filas']):
                for j in range(sala['columnas']):
                    if sala['descubierto'][i][j]:
                        celdas_nuevas += 1
            
            if len(sala['jugadores_lista']) > 0:
                sala['turno_actual'] = (sala['turno_actual'] + 1) % len(sala['jugadores_lista'])
                siguiente_jugador = sala['jugadores_lista'][sala['turno_actual']]
                
                for session_id_jugador in sala['jugadores_lista']:
                    jugador_actual = sala['jugadores'][session_id_jugador]
                    es_tu_turno = jugador_actual['uuid'] == sala['jugadores'][siguiente_jugador]['uuid']
                    
                    emit('celda_descubierta', {
                        'fila': f, 'columna': c,
                        'jugador': jugador['nombre'],
                        'uuid_jugador': jugador['uuid'],
                        'descubierto': sala['descubierto'],
                        'celdas_descubiertas': celdas_descubiertas,
                        'celdas_nuevas': celdas_nuevas,
                        'siguiente_jugador': sala['jugadores'][siguiente_jugador]['nombre'],
                        'uuid_siguiente': sala['jugadores'][siguiente_jugador]['uuid'],
                        'es_tu_turno': es_tu_turno
                    }, room=session_id_jugador)
    
    elif tipo == 'bandera':
        if not sala['descubierto'][f][c]:
            sala['bandera'][f][c] = not sala['bandera'][f][c]
            
            if len(sala['jugadores_lista']) > 0:
                sala['turno_actual'] = (sala['turno_actual'] + 1) % len(sala['jugadores_lista'])
                siguiente_jugador = sala['jugadores_lista'][sala['turno_actual']]
                
                for session_id_jugador in sala['jugadores_lista']:
                    jugador_actual = sala['jugadores'][session_id_jugador]
                    es_tu_turno = jugador_actual['uuid'] == sala['jugadores'][siguiente_jugador]['uuid']
                    
                    emit('bandera_marcada', {
                        'fila': f, 'columna': c,
                        'jugador': jugador['nombre'],
                        'uuid_jugador': jugador['uuid'],
                        'marcada': sala['bandera'][f][c],
                        'siguiente_jugador': sala['jugadores'][siguiente_jugador]['nombre'],
                        'uuid_siguiente': sala['jugadores'][siguiente_jugador]['uuid'],
                        'es_tu_turno': es_tu_turno
                    }, room=session_id_jugador)

@socketio.on('solicitar_tablero')
def handle_solicitar_tablero():
    session_id = request.sid
    
    if session_id not in jugadores:
        return
    
    jugador = jugadores[session_id]
    sala_id = jugador['sala_id']
    
    if sala_id not in salas:
        return
    
    sala = salas[sala_id]
    
    jugador_actual = None
    es_tu_turno = False
    uuid_actual = None
    
    if len(sala['jugadores_lista']) > 0 and sala['turno_actual'] < len(sala['jugadores_lista']):
        jugador_actual = sala['jugadores_lista'][sala['turno_actual']]
        uuid_actual = sala['jugadores'][jugador_actual]['uuid'] if jugador_actual else None
        es_tu_turno = jugador['uuid'] == uuid_actual
    
    emit('datos_tablero', {
        'tablero': sala['tablero'],
        'descubierto': sala['descubierto'],
        'bandera': sala['bandera'],
        'filas': sala['filas'],
        'columnas': sala['columnas'],
        'minas': sala['minas'],
        'es_tu_turno': es_tu_turno,
        'jugador_actual': sala['jugadores'][jugador_actual]['nombre'] if jugador_actual else None,
        'uuid_actual': uuid_actual,
        'mi_uuid': jugador['uuid']
    })

@socketio.on('mensaje_chat')
def handle_mensaje_chat(data):
    session_id = request.sid
    if session_id not in jugadores:
        return
    
    jugador = jugadores[session_id]
    sala_id = jugador['sala_id']
    
    if sala_id not in salas:
        return
    
    emit('mensaje_chat', {
        'jugador': jugador['nombre'],
        'mensaje': data['mensaje']
    }, room=sala_id)

@socketio.on('reiniciar_juego')
def handle_reiniciar_juego():
    session_id = request.sid
    if session_id not in jugadores:
        return
    
    jugador = jugadores[session_id]
    sala_id = jugador['sala_id']
    
    if sala_id not in salas:
        return
    
    if not salas[sala_id]['jugadores'][session_id]['es_creador']:
        return
    
    sala = salas[sala_id]
    tablero = crear_tablero(sala['filas'], sala['columnas'], sala['minas'])
    
    salas[sala_id]['tablero'] = tablero
    salas[sala_id]['descubierto'] = [[False for _ in range(sala['columnas'])] for _ in range(sala['filas'])]
    salas[sala_id]['bandera'] = [[False for _ in range(sala['columnas'])] for _ in range(sala['filas'])]
    salas[sala_id]['estado'] = 'esperando'
    salas[sala_id]['turno_actual'] = 0
    
    emit('juego_reiniciado', {
        'tablero': tablero,
        'descubierto': salas[sala_id]['descubierto'],
        'bandera': salas[sala_id]['bandera']
    }, room=sala_id)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, debug=False)
