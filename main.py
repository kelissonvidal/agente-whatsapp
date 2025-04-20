
import requests
import json
from flask import Flask, request
import os

app = Flask(__name__)

ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
ZAPI_CLIENT_TOKEN = os.getenv("ZAPI_CLIENT_TOKEN")

@app.route("/")
def home():
    return "API online"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    telefone = data.get("phone", "")
    texto = data.get("text", {}).get("message", "")
    if texto:
        enviar_texto(telefone, "Olá, como posso te ajudar?")
    return "OK", 200

def enviar_texto(telefone, mensagem):
    url = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_TOKEN}/send-text"
    headers = {
        "Client-Token": ZAPI_CLIENT_TOKEN
    }
    payload = {
        "phone": telefone,
        "message": mensagem
    }
    requests.post(url, headers=headers, json=payload)

if __name__ == "__main__":
    app.run(port=10000)
