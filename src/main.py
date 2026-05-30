from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import sys
import subprocess
import tempfile
import os
import json

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:diegopdiddy23@localhost:4420/usb_programming_platform"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = "clave_secreta"

db = SQLAlchemy(app)


class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    rol = db.Column(db.String(20), nullable=False, default="estudiante")


class Problem(db.Model):
    __tablename__ = "problem"

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    dificultad = db.Column(db.String(20), nullable=False)
    categoria = db.Column(db.String(50), nullable=False)


class Solution(db.Model):
    __tablename__ = "solution"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.Text, nullable=False)
    lenguaje = db.Column(db.String(50), nullable=False)
    estado = db.Column(db.String(20), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    problem_id = db.Column(db.Integer, db.ForeignKey("problem.id"))


class TestCase(db.Model):
    __tablename__ = "test_case"

    id = db.Column(db.Integer, primary_key=True)
    descripcion = db.Column(db.String(200), nullable=False)
    entrada = db.Column(db.Text, nullable=False)
    salida_esperada = db.Column(db.Text, nullable=False)
    es_publico = db.Column(db.Boolean, default=True)
    problem_id = db.Column(db.Integer, db.ForeignKey("problem.id"))


class ActivityLog(db.Model):
    __tablename__ = "activity_log"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    tipo_evento = db.Column(db.String(80), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    fecha_hora = db.Column(db.DateTime, default=datetime.utcnow)


PLANTILLAS_PROHIBIDAS = [
    "escribe tu solución aquí",
    "escribe tu solucion aqui",
    "return nums",
    "system.out.println(\"resultado\")",
    "return 0;"
]


def registrar_evento(tipo_evento, descripcion, user_id=None):
    evento = ActivityLog(
        user_id=user_id,
        tipo_evento=tipo_evento,
        descripcion=descripcion
    )

    db.session.add(evento)
    db.session.commit()


def normalizar_codigo(codigo):
    if not codigo:
        return ""

    codigo = codigo.replace("\r\n", "\n").replace("\r", "\n")
    lineas = [linea.strip() for linea in codigo.strip().split("\n") if linea.strip()]
    return "\n".join(lineas)


def contiene_plantilla(codigo):
    codigo_normalizado = normalizar_codigo(codigo).lower()

    for fragmento in PLANTILLAS_PROHIBIDAS:
        if fragmento in codigo_normalizado:
            return True

    return False


def codigo_corresponde_lenguaje(codigo, lenguaje):
    codigo_normalizado = normalizar_codigo(codigo).lower()

    if lenguaje == "python":
        if "#include" in codigo_normalizado:
            return False
        if "using namespace" in codigo_normalizado:
            return False
        if "public class" in codigo_normalizado:
            return False
        if "system.out.println" in codigo_normalizado:
            return False
        if "int main" in codigo_normalizado:
            return False
        if "def " not in codigo_normalizado:
            return False
        return True

    if lenguaje == "java":
        if "def " in codigo_normalizado:
            return False
        if "#include" in codigo_normalizado:
            return False
        if "using namespace" in codigo_normalizado:
            return False
        if "public class" not in codigo_normalizado and "class " not in codigo_normalizado:
            return False
        if "{" not in codigo_normalizado or "}" not in codigo_normalizado:
            return False
        if ";" not in codigo_normalizado:
            return False
        return True

    if lenguaje == "cpp":
        if "def " in codigo_normalizado:
            return False
        if "public class" in codigo_normalizado:
            return False
        if "system.out.println" in codigo_normalizado:
            return False
        if "#include" not in codigo_normalizado:
            return False
        if "int main" not in codigo_normalizado:
            return False
        if ";" not in codigo_normalizado:
            return False
        return True

    return False


def obtener_pruebas_python(problema):
    titulo = problema.titulo.lower()

    if "two sum" in titulo:
        return {
            "funcion": "two_sum",
            "casos": [
                {"args": [[2, 7, 11, 15], 9], "esperado": [0, 1]},
                {"args": [[3, 2, 4], 6], "esperado": [1, 2]}
            ]
        }

    if "valid palindrome" in titulo:
        return {
            "funcion": "is_palindrome",
            "casos": [
                {"args": ["A man, a plan, a canal: Panama"], "esperado": True},
                {"args": ["race a car"], "esperado": False}
            ]
        }

    if "maximum subarray" in titulo:
        return {
            "funcion": "max_sub_array",
            "casos": [
                {"args": [[-2, 1, -3, 4, -1, 2, 1, -5, 4]], "esperado": 6},
                {"args": [[1]], "esperado": 1}
            ]
        }

    return None


def ejecutar_python_con_pruebas(codigo, problema):
    pruebas = obtener_pruebas_python(problema)

    if pruebas is None:
        return None, "No hay pruebas automáticas configuradas para este problema."

    script = f"""
import json

{codigo}

funcion = globals().get({json.dumps(pruebas["funcion"])})

if not callable(funcion):
    print(json.dumps({{"ok": False, "error": "No se encontró la función requerida."}}))
    raise SystemExit()

casos = {json.dumps(pruebas["casos"], ensure_ascii=False)}

for caso in casos:
    resultado = funcion(*caso["args"])

    if resultado != caso["esperado"]:
        print(json.dumps({{
            "ok": False,
            "error": "La solución no coincide con la salida esperada."
        }}))
        raise SystemExit()

print(json.dumps({{"ok": True, "error": ""}}))
"""

    ruta_temporal = None

    try:
        archivo = tempfile.NamedTemporaryFile(delete=False, suffix=".py", mode="w", encoding="utf-8")
        ruta_temporal = archivo.name
        archivo.write(script)
        archivo.close()

        proceso = subprocess.run(
            [sys.executable, ruta_temporal],
            capture_output=True,
            text=True,
            timeout=3
        )

        salida = proceso.stdout.strip().splitlines()

        if not salida:
            return False, "El código no generó una respuesta válida."

        resultado = json.loads(salida[-1])

        if resultado["ok"]:
            return True, ""

        return False, resultado["error"]

    except subprocess.TimeoutExpired:
        return False, "La solución superó el tiempo máximo de ejecución."

    except Exception:
        return False, "La solución tiene un error de compilación o ejecución."

    finally:
        if ruta_temporal and os.path.exists(ruta_temporal):
            os.remove(ruta_temporal)


def validar_codigo_simulado(codigo, lenguaje):
    codigo_normalizado = normalizar_codigo(codigo).lower()

    if codigo_normalizado == "":
        return False

    if contiene_plantilla(codigo):
        return False

    if not codigo_corresponde_lenguaje(codigo, lenguaje):
        return False

    if len(codigo_normalizado) < 60:
        return False

    if lenguaje == "java":
        tiene_return = "return" in codigo_normalizado
        tiene_logica = "for" in codigo_normalizado or "if" in codigo_normalizado or "while" in codigo_normalizado
        return tiene_return and tiene_logica

    if lenguaje == "cpp":
        tiene_salida_o_return = "cout" in codigo_normalizado or "return" in codigo_normalizado
        tiene_logica = "for" in codigo_normalizado or "if" in codigo_normalizado or "while" in codigo_normalizado
        return tiene_salida_o_return and tiene_logica

    return False


@app.route("/")
def index():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        usuario = User.query.filter_by(email=email, password=password).first()

        if usuario:
            session["user_id"] = usuario.id
            session["user_name"] = usuario.nombre
            session["user_role"] = usuario.rol

            registrar_evento(
                "Inicio de sesión",
                f"El usuario {usuario.email} inició sesión correctamente.",
                usuario.id
            )

            return redirect(url_for("home"))

        return render_template("login.html", error="Credenciales incorrectas")

    return render_template("login.html")


@app.route("/logout")
def logout():
    if "user_id" in session:
        registrar_evento(
            "Cierre de sesión",
            f"El usuario {session.get('user_name')} cerró sesión.",
            session.get("user_id")
        )

    session.clear()
    return redirect(url_for("login"))


@app.route("/home")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    total_problemas = Problem.query.count()
    soluciones = Solution.query.filter_by(user_id=user_id).all()
    resueltos = sum(1 for s in soluciones if s.estado == "Accepted")
    intentados = len(set(s.problem_id for s in soluciones))

    return render_template(
        "home.html",
        nombre=session.get("user_name"),
        rol=session.get("user_role"),
        total=total_problemas,
        resueltos=resueltos,
        intentados=intentados
    )


@app.route("/problems")
def problems():
    if "user_id" not in session:
        return redirect(url_for("login"))

    dificultad = request.args.get("dificultad")

    if dificultad:
        lista = Problem.query.filter_by(dificultad=dificultad).all()
    else:
        lista = Problem.query.all()

    soluciones = Solution.query.filter_by(user_id=session["user_id"]).all()

    estados = {}
    for s in soluciones:
        estados[s.problem_id] = s.estado

    return render_template(
        "problems.html",
        problemas=lista,
        estados=estados,
        rol=session.get("user_role")
    )


@app.route("/problem/<int:problem_id>")
def problem_detail(problem_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    problema = Problem.query.get_or_404(problem_id)
    casos = TestCase.query.filter_by(problem_id=problem_id, es_publico=True).all()

    return render_template("problem_detail.html", problema=problema, casos=casos)


@app.route("/enviar-solucion/<int:problem_id>", methods=["POST"])
def enviar_solucion(problem_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    problema = Problem.query.get_or_404(problem_id)
    codigo = request.form.get("codigo")
    lenguaje = request.form.get("lenguaje", "python")

    if not codigo or normalizar_codigo(codigo) == "":
        estado = "Wrong Answer"
        mensaje = "No se puede enviar una solución vacía."
        tipo = "error"

    elif contiene_plantilla(codigo):
        estado = "Wrong Answer"
        mensaje = "No se puede enviar una solución basada únicamente en la plantilla."
        tipo = "error"

    elif not codigo_corresponde_lenguaje(codigo, lenguaje):
        estado = "Wrong Answer"
        mensaje = "El código no corresponde al lenguaje seleccionado."
        tipo = "error"

    elif lenguaje == "python":
        resultado, detalle = ejecutar_python_con_pruebas(codigo, problema)

        if resultado is True:
            estado = "Accepted"
            mensaje = "Tu solución fue aceptada."
            tipo = "success"
        elif resultado is False:
            estado = "Wrong Answer"
            mensaje = detalle
            tipo = "error"
        else:
            if validar_codigo_simulado(codigo, lenguaje):
                estado = "Accepted"
                mensaje = "Tu solución fue aceptada mediante validación básica."
                tipo = "success"
            else:
                estado = "Wrong Answer"
                mensaje = "Tu solución no pasó los criterios básicos de validación."
                tipo = "error"

    else:
        if validar_codigo_simulado(codigo, lenguaje):
            estado = "Accepted"
            mensaje = "Tu solución fue aceptada mediante validación básica."
            tipo = "success"
        else:
            estado = "Wrong Answer"
            mensaje = "Tu solución no pasó los criterios básicos de validación."
            tipo = "error"

    nueva_solucion = Solution(
        codigo=codigo,
        lenguaje=lenguaje,
        estado=estado,
        user_id=session["user_id"],
        problem_id=problem_id
    )

    db.session.add(nueva_solucion)
    db.session.commit()

    registrar_evento(
        "Envío de solución",
        f"Se envió una solución en {lenguaje} para el problema con id {problem_id}. Estado: {estado}.",
        session["user_id"]
    )

    return render_template("resultado.html", mensaje=mensaje, tipo=tipo)


@app.route("/admin/problems/new", methods=["GET", "POST"])
def crear_problema():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("user_role") != "admin":
        return render_template(
            "resultado.html",
            mensaje="No tienes permisos para crear problemas.",
            tipo="error"
        )

    if request.method == "POST":
        titulo = request.form.get("titulo")
        descripcion = request.form.get("descripcion")
        dificultad = request.form.get("dificultad")
        categoria = request.form.get("categoria")
        caso_descripcion = request.form.get("caso_descripcion")
        entrada = request.form.get("entrada")
        salida_esperada = request.form.get("salida_esperada")
        es_publico = request.form.get("es_publico") == "on"

        nuevo_problema = Problem(
            titulo=titulo,
            descripcion=descripcion,
            dificultad=dificultad,
            categoria=categoria
        )

        db.session.add(nuevo_problema)
        db.session.commit()

        nuevo_caso = TestCase(
            descripcion=caso_descripcion,
            entrada=entrada,
            salida_esperada=salida_esperada,
            es_publico=es_publico,
            problem_id=nuevo_problema.id
        )

        db.session.add(nuevo_caso)
        db.session.commit()

        registrar_evento(
            "Creación de problema",
            f"El administrador creó el problema '{titulo}' con un caso de prueba asociado.",
            session["user_id"]
        )

        return render_template(
            "resultado.html",
            mensaje="Problema creado correctamente con su caso de prueba.",
            tipo="success"
        )

    return render_template("admin_problem_form.html")


@app.route("/admin/activity-log")
def historial_sistema():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("user_role") != "admin":
        return render_template(
            "resultado.html",
            mensaje="No tienes permisos para ver el historial del sistema.",
            tipo="error"
        )

    tipo_evento = request.args.get("tipo_evento")
    usuario = request.args.get("usuario")
    fecha = request.args.get("fecha")

    consulta = ActivityLog.query

    if tipo_evento:
        consulta = consulta.filter(ActivityLog.tipo_evento.ilike(f"%{tipo_evento}%"))

    if usuario:
        usuarios_filtrados = User.query.filter(User.email.ilike(f"%{usuario}%")).all()
        ids = [u.id for u in usuarios_filtrados]

        if ids:
            consulta = consulta.filter(ActivityLog.user_id.in_(ids))
        else:
            consulta = consulta.filter(ActivityLog.user_id == -1)

    if fecha:
        consulta = consulta.filter(db.func.date(ActivityLog.fecha_hora) == fecha)

    eventos = consulta.order_by(ActivityLog.fecha_hora.desc()).all()
    usuarios = {u.id: u for u in User.query.all()}

    return render_template("activity_log.html", eventos=eventos, usuarios=usuarios)


@app.route("/api/problems")
def api_problems():
    problemas = Problem.query.all()

    data = [
        {
            "id": p.id,
            "titulo": p.titulo,
            "descripcion": p.descripcion,
            "dificultad": p.dificultad,
            "categoria": p.categoria
        }
        for p in problemas
    ]

    return jsonify(data)


@app.route("/test")
def test():
    return jsonify({"mensaje": "Backend funcionando correctamente"})


def seed_data():
    usuario_admin = User.query.filter_by(email="admin@usb.edu.co").first()

    if usuario_admin:
        usuario_admin.rol = "admin"
        usuario_admin.nombre = "Administrador Demo"
        usuario_admin.password = "1234"
    else:
        usuario_admin = User(
            nombre="Administrador Demo",
            email="admin@usb.edu.co",
            password="1234",
            rol="admin"
        )
        db.session.add(usuario_admin)

    if Problem.query.count() == 0:
        problemas = [
            Problem(
                titulo="Two Sum",
                descripcion="Dado un arreglo de números enteros nums y un número target, retorna los índices de los dos números que suman target.",
                dificultad="Fácil",
                categoria="Arrays"
            ),
            Problem(
                titulo="Valid Palindrome",
                descripcion="Dada una cadena de texto, determina si es un palíndromo ignorando espacios, mayúsculas y signos.",
                dificultad="Fácil",
                categoria="Strings"
            ),
            Problem(
                titulo="Maximum Subarray",
                descripcion="Dado un arreglo de enteros, encuentra la suma máxima de un subarreglo continuo.",
                dificultad="Media",
                categoria="Programación dinámica"
            )
        ]

        db.session.add_all(problemas)
        db.session.commit()

    if TestCase.query.count() == 0:
        two_sum = Problem.query.filter_by(titulo="Two Sum").first()
        palindrome = Problem.query.filter_by(titulo="Valid Palindrome").first()
        maximum = Problem.query.filter_by(titulo="Maximum Subarray").first()

        casos = []

        if two_sum:
            casos.append(
                TestCase(
                    descripcion="Caso básico de Two Sum",
                    entrada="nums = [2,7,11,15], target = 9",
                    salida_esperada="[0,1]",
                    es_publico=True,
                    problem_id=two_sum.id
                )
            )

        if palindrome:
            casos.append(
                TestCase(
                    descripcion="Palabra palíndroma",
                    entrada='s = "A man, a plan, a canal: Panama"',
                    salida_esperada="true",
                    es_publico=True,
                    problem_id=palindrome.id
                )
            )

        if maximum:
            casos.append(
                TestCase(
                    descripcion="Subarreglo máximo",
                    entrada="nums = [-2,1,-3,4,-1,2,1,-5,4]",
                    salida_esperada="6",
                    es_publico=True,
                    problem_id=maximum.id
                )
            )

        db.session.add_all(casos)

    db.session.commit()


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_data()

    app.run(debug=True)