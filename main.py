
import os
import requests
import time
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

def dividir_blocos(texto, limite=12):
    palavras = texto.split()
    blocos = []
    bloco_atual = []

    for palavra in palavras:
        bloco_atual.append(palavra)
        if len(bloco_atual) >= limite and palavra.endswith((".", "!", "?")):
            blocos.append(" ".join(bloco_atual))
            bloco_atual = []

    if bloco_atual:
        blocos.append(" ".join(bloco_atual))

    return blocos

def delay_por_bloco(bloco):
    palavras = len(bloco.split())
    if palavras <= 8:
        return 2
    elif palavras <= 12:
        return 3
    else:
        return 4

def responder_com_blocos(numero, resposta):
    blocos = dividir_blocos(resposta)
    for bloco in blocos:
        enviar_texto(numero, bloco)
        time.sleep(delay_por_bloco(bloco))

def transcrever_audio(url_audio):
    response = requests.get(url_audio)
    with open("/tmp/audio.ogg", "wb") as f:
        f.write(response.content)
    with open("/tmp/audio.ogg", "rb") as audio_file:
        transcript = openai.audio.transcriptions.create(model="whisper-1", file=audio_file)
    return transcript.text

def gerar_resposta(pergunta):
    resposta = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Você é um atendente cordial da empresa Caplux Suplementos, especializada em produtos para queda de cabelo."},
            {"role": "user", "content": pergunta}
        ]
    )
    return resposta.choices[0].message.content.strip()

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Payload inválido"}), 400

    tipo = data.get("type")
    telefone = data.get("phone")

    if data.get("fromMe"):
        return jsonify({"status": "ignorado"}), 200

    if tipo == "ReceivedCallback":
        if "audio" in data:
            try:
                url_audio = data["audio"]["audioUrl"]
                texto = transcrever_audio(url_audio)
                resposta = gerar_resposta(texto)
                responder_com_blocos(telefone, resposta)
            except Exception as e:
                print("Erro ao transcrever ou responder:", e)
        elif "text" in data:
            msg = data["text"]["message"]
            if msg.lower() in ["oi", "olá", "bom dia", "boa tarde", "boa noite"]:
                enviar_audio(telefone, URL_AUDIO)
            resposta = gerar_resposta(msg)
            responder_com_blocos(telefone, resposta)

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
