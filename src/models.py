from main import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    rol = db.Column(db.String(20), nullable=False)

class Problem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    dificultad = db.Column(db.String(20), nullable=False)
    categoria = db.Column(db.String(50), nullable=False)

class Solution(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.Text, nullable=False)
    lenguaje = db.Column(db.String(50), nullable=False)
    estado = db.Column(db.String(20), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    problem_id = db.Column(db.Integer, db.ForeignKey("problem.id"))

class TestCase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descripcion = db.Column(db.String(200), nullable=False)
    entrada = db.Column(db.Text, nullable=False)
    salida_esperada = db.Column(db.Text, nullable=False)
    es_publico = db.Column(db.Boolean, default=True)
    problem_id = db.Column(db.Integer, db.ForeignKey("problem.id"))