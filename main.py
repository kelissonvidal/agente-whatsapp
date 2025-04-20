
import os
import time
import requests
import asyncio
import json
from flask import Flask, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
ZAPI_CLIENT_TOKEN = os.getenv("ZAPI_CLIENT_TOKEN")
API_BASE = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}"

headers = {
    "Content-Type": "application/json",
    "client-token": ZAPI_CLIENT_TOKEN
}

audios_especiais = {
    "formas de pagamento": "formas_pagamento.ogg",
    "prazo de entrega": "prazo_entrega.ogg",
    "garantia": "garantia.ogg"
}

mensagens_enviadas = set()

def dividir_em_blocos(mensagem, palavras_por_bloco=12):
    palavras = mensagem.split()
    blocos = []
    bloco = []
    for palavra in palavras:
        bloco.append(palavra)
        if len(bloco) >= palavras_por_bloco and palavra.endswith("."):
            blocos.append(" ".join(bloco))
            bloco = []
    if bloco:
        blocos.append(" ".join(bloco))
    return blocos

def delay_por_bloco(texto):
    palavras = texto.split()
    tamanho = len(palavras)
    if tamanho <= 8:
        return 2
    elif tamanho <= 14:
        return 3
    else:
        return 4

async def responder_com_blocos(telefone, mensagem):
    blocos = dividir_em_blocos(mensagem)
    for bloco in blocos:
        payload = {"phone": telefone, "message": bloco}
        try:
            response = requests.post(f"{API_BASE}/send-text", headers=headers, json=payload)
            print(f"[TEXTO] Enviado para {telefone}: {bloco}")
            print(f"[Z-API] Status: {response.status_code} | Resposta: {response.text}")
        except Exception as e:
            print("Erro ao enviar texto:", e)
        await asyncio.sleep(delay_por_bloco(bloco))

def enviar_audio(telefone, nome_arquivo):
    url_audio = f"https://raw.githubusercontent.com/kelissonvidal/agente-whatsapp/main/data/{nome_arquivo}"
    payload = {
        "phone": telefone,
        "audio": url_audio
    }
    try:
        response = requests.post(f"{API_BASE}/send-audio", headers=headers, json=payload)
        print(f"[ÁUDIO] Enviado: {nome_arquivo} → {telefone}")
        print(f"[Z-API] Status: {response.status_code} | Resposta: {response.text}")
    except Exception as e:
        print("Erro ao enviar áudio:", e)

def identificar_audio_especial(texto):
    texto_lower = texto.lower()
    for chave, arquivo in audios_especiais.items():
        if chave in texto_lower:
            return arquivo
    return None

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    print("Payload recebido:", data)

    if data.get("fromApi"):
        return jsonify({"message": "Ignorado (fromApi)"}), 200

    telefone = data.get("phone")
    mensagem_id = data.get("messageId")

    if mensagem_id in mensagens_enviadas:
        return jsonify({"message": "Mensagem já processada"}), 200
    mensagens_enviadas.add(mensagem_id)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    if "text" in data:
        mensagem = data["text"]["message"]
        if mensagem.lower() == "olá":
            enviar_audio(telefone, "boas_vindas.ogg")
        audio_especial = identificar_audio_especial(mensagem)
        if audio_especial:
            enviar_audio(telefone, audio_especial)
        resposta = gerar_resposta_ia(mensagem)
        loop.run_until_complete(responder_com_blocos(telefone, resposta))

    elif "audio" in data:
        audio_url = data["audio"]["audioUrl"]
        try:
            resposta = transcrever_audio(audio_url)
            print("✅ Transcrição:", resposta)
            audio_especial = identificar_audio_especial(resposta)
            if audio_especial:
                enviar_audio(telefone, audio_espec...
            resposta_ia = gerar_resposta_ia(resposta)
            loop.run_until_complete(responder_com_blocos(telefone, resposta_ia))
        except Exception as e:
            print("Erro na transcrição:", e)

    return jsonify({"message": "OK"}), 200

def gerar_resposta_ia(prompt_usuario):
    resposta = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Você é um atendente da Caplux Suplementos. Atenda de forma humanizada, natural e prestativa."},
            {"role": "user", "content": prompt_usuario}
        ]
    )
    return resposta.choices[0].message.content

def transcrever_audio(url):
    resposta = openai.audio.transcriptions.create(
        model="whisper-1",
        file=(url, "audio.ogg")
    )
    return resposta.text

@app.route("/", methods=["GET"])
def home():
    return "Servidor Caplux Ativo"

if __name__ == "__main__":
    app.run(port=10000)
