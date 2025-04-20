
import os
import time
import requests
import asyncio
from flask import Flask, request, jsonify
from openai import OpenAI
from urllib.parse import quote

app = Flask(__name__)

# Variáveis de ambiente
INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
TOKEN = os.getenv("ZAPI_TOKEN")
CLIENT_TOKEN = os.getenv("ZAPI_CLIENT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
API_BASE = f"https://api.z-api.io/instances/{INSTANCE_ID}/token/{TOKEN}"

# Novo cliente OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# Áudios inteligentes: nome do arquivo => intenções relacionadas
AUDIO_MAP = {
    "boas_vindas.ogg": ["oi", "olá", "bom dia", "boa tarde", "boa noite"],
    "formas_pagamento.ogg": ["formas de pagamento", "como posso pagar", "aceita pix", "pagamento"],
    "prazo_entrega.ogg": ["prazo", "entrega", "tempo de entrega", "chegar", "frete"],
    "garantia.ogg": ["garantia", "seguro", "funcionar", "não der certo", "caso não funcione"]
}

# URL base dos áudios
AUDIO_BASE_URL = "https://raw.githubusercontent.com/kelissonvidal/agente-whatsapp/main/data"

# Controle de mensagens recentes para travar loops
mensagens_enviadas = set()

def detectar_intencao(texto):
    texto = texto.lower()
    for arquivo, padroes in AUDIO_MAP.items():
        if any(p in texto for p in padroes):
            return arquivo
    return None

def dividir_em_blocos(texto, limite=12):
    palavras = texto.split()
    blocos = []
    bloco = []

    for palavra in palavras:
        bloco.append(palavra)
        if len(bloco) >= limite and palavra.endswith((".", "!", "?")):
            blocos.append(" ".join(bloco))
            bloco = []

    if bloco:
        blocos.append(" ".join(bloco))

    return blocos

def calcular_delay(bloco):
    palavras = len(bloco.split())
    if palavras < 10:
        return 2
    elif palavras < 15:
        return 3
    return 4

async def responder_com_blocos(telefone, resposta):
    blocos = dividir_em_blocos(resposta)
    for bloco in blocos:
        if bloco in mensagens_enviadas:
            continue
        mensagens_enviadas.add(bloco)

        payload = {
            "phone": telefone,
            "message": bloco
        }
        headers = {"Client-Token": CLIENT_TOKEN}
        response = requests.post(f"{API_BASE}/send-text", headers=headers, json=payload)

        print(f"[TEXTO] Enviado para {telefone}: {bloco}")
        print("[Z-API] Status:", response.status_code, "| Resposta:", response.text)

        await asyncio.sleep(calcular_delay(bloco))

def enviar_audio(telefone, nome_arquivo):
    url = f"{AUDIO_BASE_URL}/{quote(nome_arquivo)}"
    payload = {
        "phone": telefone,
        "audio": url
    }
    headers = {"Client-Token": CLIENT_TOKEN}
    response = requests.post(f"{API_BASE}/send-audio", headers=headers, json=payload)

    print(f"[ÁUDIO] Enviado: {nome_arquivo} → {telefone}")
    print("[Z-API] Status:", response.status_code, "| Resposta:", response.text)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    print("📦 Payload recebido:", data)

    if data.get("type") != "ReceivedCallback" or data.get("fromMe"):
        return jsonify({"status": "ignorado"})

    telefone = data.get("phone")
    mensagem = data.get("text", {}).get("message", "")
    audio = data.get("audio", {})

    # IA deve responder apenas se não estiver em loop
    if mensagem and not data.get("fromApi"):
        if mensagem.lower().strip() in mensagens_enviadas:
            return jsonify({"status": "loop evitado"})

        intencao_audio = detectar_intencao(mensagem)
        if intencao_audio:
            enviar_audio(telefone, intencao_audio)
        else:
            asyncio.run(responder_com_blocos(telefone, gerar_resposta_ia(mensagem)))

    if audio and not data.get("fromApi"):
        url_audio = audio.get("audioUrl")
        transcricao = transcrever_audio(url_audio)
        if transcricao:
            print("✅ Transcrição:", transcricao)
            intencao_audio = detectar_intencao(transcricao)
            if intencao_audio:
                enviar_audio(telefone, intencao_audio)
            else:
                asyncio.run(responder_com_blocos(telefone, gerar_resposta_ia(transcricao)))

    return jsonify({"status": "ok"})

def transcrever_audio(audio_url):
    try:
        with client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_url,
            response_format="text",
            language="pt"
        ) as response:
            return response.text
    except Exception as e:
        print("Erro ao transcrever áudio:", e)
        return None

def gerar_resposta_ia(texto_usuario):
    try:
        resposta = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Você é um atendente comercial da empresa Caplux Suplementos. Responda de forma humanizada, simpática, sem repetir a mesma pergunta. Seja direto, como um atendente real."},
                {"role": "user", "content": texto_usuario}
            ]
        )
        return resposta.choices[0].message.content.strip()
    except Exception as e:
        print("Erro ao gerar resposta da IA:", e)
        return "Desculpe, não consegui entender sua pergunta."

if __name__ == "__main__":
    app.run(port=10000)
