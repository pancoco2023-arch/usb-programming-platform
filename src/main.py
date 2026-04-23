"""
Archivo principal del backend del sistema.
API básica para la plataforma de práctica de programación.
"""

from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        "mensaje": "API de la plataforma de práctica de programación"
    })

@app.route('/problemas')
def listar_problemas():
    problemas = [
        {"id": 1, "titulo": "Suma de dos números", "dificultad": "Fácil"},
        {"id": 2, "titulo": "Palíndromo", "dificultad": "Media"}
    ]
    return jsonify(problemas)

@app.route('/enviar-solucion', methods=['POST'])
def enviar_solucion():
    data = request.json
    return jsonify({
        "mensaje": "Solución recibida correctamente",
        "codigo": data.get("codigo"),
        "lenguaje": data.get("lenguaje")
    })

@app.route('/test')
def test():
    return jsonify({
        "mensaje": "Endpoint de prueba funcionando"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
