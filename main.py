
from flask import Flask, request, jsonify
import requests
import openai
import time
import os
import asyncio
from urllib.parse import quote
from io import BytesIO

app = Flask(__name__)

# Variáveis de ambiente
ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
ZAPI_CLIENT_TOKEN = os.getenv("ZAPI_CLIENT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY

API_BASE = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_TOKEN}"

HEADERS = {
    "Client-Token": ZAPI_CLIENT_TOKEN
}

AUDIO_MAP = {
    "boas_vindas": "boas_vindas.ogg",
    "formas_pagamento": "formas_pagamento.ogg",
    "prazo_entrega": "prazo_entrega.ogg",
    "garantia": "garantia.ogg",
}

AUDIO_URL_BASE = "https://raw.githubusercontent.com/kelissonvidal/agente-whatsapp/main/data/"

# Intent keywords
INTENTS = {
    "formas_pagamento": ["forma de pagamento", "pagamento", "parcelar", "cartão", "pix", "boleto"],
    "prazo_entrega": ["prazo", "entrega", "quando chega", "demora", "frete"],
    "garantia": ["garantia", "se não funcionar", "dinheiro de volta", "e se não der certo"]
}


def detectar_intencao(mensagem):
    mensagem = mensagem.lower()
    for chave, palavras in INTENTS.items():
        if any(p in mensagem for p in palavras):
            return chave
    return None


def dividir_em_blocos(texto, max_palavras=12):
    palavras = texto.split()
    blocos = []
    bloco = []

    for palavra in palavras:
        bloco.append(palavra)
        if len(bloco) >= max_palavras:
            blocos.append(" ".join(bloco))
            bloco = []

    if bloco:
        blocos.append(" ".join(bloco))

    return blocos


def delay_por_bloco(bloco):
    palavras = len(bloco.split())
    return max(2, min(5, palavras * 0.25))


def enviar_mensagem(telefone, mensagem):
    payload = {
        "phone": telefone,
        "message": mensagem
    }
    response = requests.post(f"{API_BASE}/send-text", headers=HEADERS, json=payload)
    print(f"[TEXTO] Enviado para {telefone}: {mensagem}")
    print("[Z-API] Status:", response.status_code, "| Resposta:", response.text)


def enviar_audio(telefone, nome_arquivo):
    url_audio = f"{AUDIO_URL_BASE}{nome_arquivo}"
    payload = {
        "audio": url_audio,
        "phone": telefone
    }
    response = requests.post(f"{API_BASE}/send-audio", headers=HEADERS, json=payload)
    print(f"[ÁUDIO] Enviado: {nome_arquivo} → {telefone}")
    print("[Z-API] Status:", response.status_code, "| Resposta:", response.text)


async def responder_com_blocos(telefone, resposta):
    blocos = dividir_em_blocos(resposta)
    for bloco in blocos:
        await asyncio.sleep(delay_por_bloco(bloco))
        enviar_mensagem(telefone, bloco)


def transcrever_audio(url):
    try:
        resposta = requests.get(url)
        resposta.raise_for_status()
        with BytesIO(resposta.content) as f:
            transcript = openai.audio.transcriptions.create(
                model="whisper-1",
                file=f
            )
        return transcript.text
    except Exception as e:
        print("[ERRO] Transcrição falhou:", e)
        return ""


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if data.get("type") != "ReceivedCallback":
        return jsonify({"status": "ignorado"})

    if data.get("fromMe"):
        return jsonify({"status": "ignorado"})

    telefone = data.get("phone")
    mensagem_texto = data.get("text", {}).get("message")
    audio_info = data.get("audio")

    if mensagem_texto:
        if "oi" in mensagem_texto.lower() or "olá" in mensagem_texto.lower():
            enviar_audio(telefone, AUDIO_MAP["boas_vindas"])
            asyncio.run(responder_com_blocos(telefone, "Olá, como posso ajudá-lo hoje? Você está interessado em suplementos para queda de cabelo?"))
            return jsonify({"status": "ok"})

        intencao = detectar_intencao(mensagem_texto)
        if intencao:
            enviar_audio(telefone, AUDIO_MAP[intencao])
        asyncio.run(responder_com_blocos(telefone, gerar_resposta_ia(mensagem_texto)))
        return jsonify({"status": "ok"})

    if audio_info and audio_info.get("audioUrl"):
        url_audio = audio_info["audioUrl"]
        texto_transcrito = transcrever_audio(url_audio)
        print("✅ Transcrição:", texto_transcrito)

        if texto_transcrito:
            intencao = detectar_intencao(texto_transcrito)
            if intencao:
                enviar_audio(telefone, AUDIO_MAP[intencao])
            resposta_ia = gerar_resposta_ia(texto_transcrito)
            asyncio.run(responder_com_blocos(telefone, resposta_ia))
        return jsonify({"status": "ok"})

    return jsonify({"status": "ignorado"})


def gerar_resposta_ia(mensagem):
    prompt = f"Mensagem do cliente: '{mensagem}'. Responda de forma breve, simpática e natural como se fosse um atendente humano."
    try:
        resposta = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return resposta.choices[0].message.content.strip()
    except Exception as e:
        print("[ERRO] Falha ao gerar resposta da IA:", e)
        return "Desculpe, algo deu errado ao tentar responder."

if __name__ == "__main__":
    app.run(debug=True)
