
import os
import requests
from flask import Flask, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
ZAPI_CLIENT_TOKEN = os.getenv("ZAPI_CLIENT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)

URL_AUDIO = "https://raw.githubusercontent.com/kelissonvidal/caplux-audios/main/boas_vindas.ogg"

def enviar_audio(numero, link_audio):
    url = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_TOKEN}/send-audio"
    headers = {"Client-Token": ZAPI_CLIENT_TOKEN}
    payload = {"phone": numero, "audio": link_audio}
    response = requests.post(url, json=payload, headers=headers)
    return response.status_code, response.json()

def enviar_texto(numero, mensagem):
    url = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_TOKEN}/send-text"
    headers = {"Client-Token": ZAPI_CLIENT_TOKEN}
    payload = {"phone": numero, "message": mensagem}
    response = requests.post(url, json=payload, headers=headers)
    return response.status_code, response.json()

def transcrever_audio(url_audio):
    response = requests.get(url_audio)
    with open("/tmp/audio.ogg", "wb") as f:
        f.write(response.content)
    with open("/tmp/audio.ogg", "rb") as audio_file:
        transcript = openai.audio.transcriptions.create(model="whisper-1", file=audio_file)
    return transcript.text

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Payload inválido"}), 400

    tipo = data.get("type")
    telefone = data.get("phone")

    # Ignorar mensagens enviadas pela própria IA
    if data.get("fromMe"):
        return jsonify({"status": "ignorado"}), 200

    if tipo == "ReceivedCallback":
        if "audio" in data:
            try:
                url_audio = data["audio"]["audioUrl"]
                texto = transcrever_audio(url_audio)
                resposta = f"Você disse: {texto}"
                enviar_texto(telefone, resposta)
            except Exception as e:
                print("Erro ao transcrever:", e)
        elif "text" in data:
            msg = data["text"]["message"]
            if msg.lower() in ["oi", "olá", "bom dia", "boa tarde", "boa noite"]:
                enviar_audio(telefone, URL_AUDIO)
            resposta = "Olá! Como posso te ajudar hoje?"
            enviar_texto(telefone, resposta)

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
