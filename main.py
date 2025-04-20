import os
import time
import requests
import asyncio
from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)

API_BASE = "https://api.z-api.io/instances/" + os.getenv("ZAPI_INSTANCE_ID")
HEADERS = {
    "Authorization": os.getenv("ZAPI_CLIENT_TOKEN"),
    "Content-Type": "application/json"
}
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AUDIO_REPO_URL = "https://raw.githubusercontent.com/kelissonvidal/agente-whatsapp/main/data/"
INTENCOES_AUDIO = {
    "prazo de entrega": "prazo_entrega.ogg",
    "formas de pagamento": "formas_pagamento.ogg",
    "garantia": "garantia.ogg"
}

async def delay_por_bloco(bloco):
    palavras = len(bloco.split())
    if palavras <= 8:
        await asyncio.sleep(2)
    elif palavras <= 12:
        await asyncio.sleep(3)
    else:
        await asyncio.sleep(4)

def enviar_audio(numero, nome_arquivo):
    audio_url = AUDIO_REPO_URL + nome_arquivo
    payload = {"phone": numero, "audio": audio_url}
    try:
        r = requests.post(f"{API_BASE}/send-audio", headers=HEADERS, json=payload)
        print(f"[AUDIO] Enviado: {nome_arquivo} → {numero}")
        print(f"[Z-API] Status: {r.status_code} | Resposta: {r.text}")
    except Exception as e:
        print(f"[ERRO] Falha ao enviar áudio: {e}")

def responder_texto(numero, texto):
    payload = {"phone": numero, "message": texto}
    r = requests.post(f"{API_BASE}/send-text", headers=HEADERS, json=payload)
    print(f"[TEXTO] Enviado para {numero}: {texto}")
    print(f"[Z-API] Status: {r.status_code} | Resposta: {r.text}")

async def responder_com_blocos(numero, resposta):
    blocos = resposta.split(". ")
    for bloco in blocos:
        if bloco.strip():
            responder_texto(numero, bloco.strip())
            await delay_por_bloco(bloco)

def detectar_audio_inteligente(texto):
    texto = texto.lower()
    for chave, nome_arquivo in INTENCOES_AUDIO.items():
        if chave in texto:
            return nome_arquivo
    return None

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    if not data or "type" not in data or data["type"] != "ReceivedCallback":
        return jsonify({"status": "ignored"}), 200

    if data.get("fromApi"):
        return jsonify({"status": "ignored - fromApi"}), 200

    telefone = data.get("phone")
    texto = data.get("text", {}).get("message", "").lower()

    if texto:
        nome_audio = detectar_audio_inteligente(texto)
        if nome_audio:
            enviar_audio(telefone, nome_audio)
        else:
            resposta = "Olá, como posso ajudá-lo hoje? Você está interessado em suplementos para queda de cabelo?"
            asyncio.run(responder_com_blocos(telefone, resposta))

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)