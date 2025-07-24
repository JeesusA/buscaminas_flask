from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import random
import json

app = Flask(__name__)
app.secret_key = "buscaminas_secret_key"

# Niveles predefinidos: (nombre, filas, columnas, minas)
NIVELES = [
    ("Fácil", 8, 8, 10),
    ("Medio", 16, 16, 40),
    ("Difícil", 16, 30, 99)
]

def crear_tablero(filas, columnas, minas):
    if filas < 5 or columnas < 5 or minas < 1 or minas >= filas * columnas:
        raise ValueError("Parámetros inválidos para el tablero.")
    tablero = [[0 for _ in range(columnas)] for _ in range(filas)]
    # Generar todas las posiciones posibles
    todas_pos = [(f, c) for f in range(filas) for c in range(columnas)]
    bombas = set(random.sample(todas_pos, minas))
    for f, c in bombas:
        tablero[f][c] = -1
    for f in range(filas):
        for c in range(columnas):
            if tablero[f][c] == -1:
                continue
            # Contar minas alrededor
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

@app.route("/tutorial")
def tutorial():
    return render_template("tutorial.html")

@app.route("/accion", methods=["POST"])
def accion():
    try:
        data = request.json
        f = data.get('fila')
        c = data.get('columna')
        tipo = data.get('tipo')
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
            # Si hay bandera, quitarla y descubrir la celda normalmente
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

if __name__ == "__main__":
    app.run(debug=True)
