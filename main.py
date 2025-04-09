
import os
import json
import requests
from flask import Flask, request
from datetime import datetime
from urllib.parse import quote

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
        files = {"audio": ("boas_vindas.ogg", audio_file, "audio/ogg; codecs=opus")}
        data = {"phone": phone}
        response = requests.post(url, data=data, files=files)
    return response.status_code, response.text

# Função para enviar texto
def send_text(phone, message):
    url = f"{API_URL}/send-text"
    payload = {"phone": phone, "message": message}
    response = requests.post(url, json=payload)
    return response.status_code, response.text

# Webhook
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    message = data.get("text", {}).get("message")
    phone = data.get("phone")

    if not phone:
        return "ignored", 200

    if phone not in USERS_RESPONDED:
        try:
            send_audio(phone)
            USERS_RESPONDED.add(phone)
            return "audio sent", 200
        except Exception as e:
            print("[ERRO] Falha ao enviar áudio:", e)
            return "audio error", 500

    if message:
        resposta = f"Recebi sua mensagem: {message}"
        send_text(phone, resposta)

    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
