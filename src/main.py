from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres:diegopdiddy23@localhost:4420/usb_programming_platform"
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
            return redirect(url_for("home"))

        return render_template("login.html", error="Credenciales incorrectas")

    return render_template("login.html")


@app.route("/logout")
def logout():
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

    codigo = request.form.get("codigo")
    lenguaje = request.form.get("lenguaje", "python")

    if codigo and "return" in codigo:
        estado = "Accepted"
        mensaje = "Tu solución fue aceptada."
    else:
        estado = "Wrong Answer"
        mensaje = "Tu solución no pasó los casos de prueba."

    nueva_solucion = Solution(
        codigo=codigo,
        lenguaje=lenguaje,
        estado=estado,
        user_id=session["user_id"],
        problem_id=problem_id
    )

    db.session.add(nueva_solucion)
    db.session.commit()

    return render_template("resultado.html", mensaje=mensaje)


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


@app.route("/admin/problems/new", methods=["GET", "POST"])
def crear_problema():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("user_role") != "admin":
        return render_template(
            "resultado.html",
            mensaje="No tienes permisos para crear problemas."
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

        return render_template(
            "resultado.html",
            mensaje="Problema creado correctamente con su caso de prueba."
        )

    return render_template("admin_problem_form.html")


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

        casos = [
            TestCase(
                descripcion="Caso básico de Two Sum",
                entrada="nums = [2,7,11,15], target = 9",
                salida_esperada="[0,1]",
                es_publico=True,
                problem_id=two_sum.id
            ),
            TestCase(
                descripcion="Palabra palíndroma",
                entrada='s = "A man, a plan, a canal: Panama"',
                salida_esperada="true",
                es_publico=True,
                problem_id=palindrome.id
            ),
            TestCase(
                descripcion="Subarreglo máximo",
                entrada="nums = [-2,1,-3,4,-1,2,1,-5,4]",
                salida_esperada="6",
                es_publico=True,
                problem_id=maximum.id
            )
        ]

        db.session.add_all(casos)

    db.session.commit()


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_data()

    app.run(debug=True)