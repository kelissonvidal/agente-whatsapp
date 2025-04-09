
import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Dados fixos
API_URL = "https://api.z-api.io/instances/3DF189F728F4A0C2E72632C54B267657/token/4ADA364DCC70ABFE1175200B"
PHONE_PROFILE_NAME = "Caplux Suplementos"
AUDIO_FILE_PATH = "./data/boas_vindas.ogg"
USERS_RESPONDED = set()

# Função para enviar áudio nativo
def send_audio(phone):
    url = f"{API_URL}/send-audio"
    with open(AUDIO_FILE_PATH, "rb") as audio_file:
        files = {"audio": ("boas_vindas.ogg", audio_file, "audio/ogg")}
        data = {"phone": phone}
        response = requests.post(url, data=data, files=files)
    return response.status_code, response.text

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if not data:
        return jsonify({"status": "no data"}), 400

    phone = data.get("phone")
    message = data.get("message")
    if not phone or not message:
        return jsonify({"status": "invalid payload"}), 400

    # Se for a primeira interação com esse número
    if phone not in USERS_RESPONDED:
        USERS_RESPONDED.add(phone)
        status_code, response_text = send_audio(phone)
        return jsonify({
            "status": "audio enviado",
            "code": status_code,
            "response": response_text
        })

    return jsonify({"status": "mensagem recebida"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
