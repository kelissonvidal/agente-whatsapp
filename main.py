
import os
import openai
import requests
from flask import Flask, request, jsonify
import aiohttp
import asyncio
import time
import re

app = Flask(__name__)

# Variáveis de ambiente
ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
ZAPI_CLIENT_TOKEN = os.getenv("ZAPI_CLIENT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY

# Configurações
ZAPI_URL = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_TOKEN}"
PASTA_AUDIOS = "./data"
USERS_RESPONDED = set()
ULTIMAS_INTERACOES = {}

# ========== FUNÇÕES UTILITÁRIAS ==========

def dividir_texto_em_blocos(texto, limite=12):
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

def delay_por_bloco(bloco):
    qtde_palavras = len(bloco.split())
    if qtde_palavras <= 8:
        return 2
    elif qtde_palavras <= 14:
        return 3
    else:
        return 4

def normalizar(texto):
    return re.sub(r"[^\w\s]", "", texto.lower())

def nome_arquivo_audio_para(texto):
    texto_normalizado = normalizar(texto)
    palavras = texto_normalizado.split()
    return "_".join(palavras[:4]) + ".ogg"

# ========== FUNÇÕES PRINCIPAIS ==========

async def enviar_audio_zapi(phone, nome_arquivo):
    caminho = os.path.join(PASTA_AUDIOS, nome_arquivo)
    if not os.path.exists(caminho):
        print(f"❌ Áudio não encontrado: {nome_arquivo}")
        return

    url = f"{ZAPI_URL}/send-audio"
    headers = {"Client-Token": ZAPI_CLIENT_TOKEN}
    data = {"phone": phone, "filename": nome_arquivo}
    files = {"audio": (nome_arquivo, open(caminho, "rb"), "audio/ogg")}

    try:
        response = requests.post(url, headers=headers, data=data, files=files)
        print(f"🎙️ Áudio enviado: {nome_arquivo} → {phone}")
        print(f"📨 Status: {response.status_code}")
        print(f"📨 Resposta: {response.text}")
    except Exception as e:
        print("Erro ao enviar áudio:", e)

def enviar_texto_zapi(phone, mensagem):
    url = f"{ZAPI_URL}/send-text"
    headers = {"Content-Type": "application/json", "Client-Token": ZAPI_CLIENT_TOKEN}
    payload = {"phone": phone, "message": mensagem}
    response = requests.post(url, headers=headers, json=payload)
    print(f"📤 Enviado para {phone}: {mensagem}")
    print(f"📨 Status: {response.status_code}")
    print(f"📨 Resposta: {response.text}")

def responder_com_blocos(phone, resposta):
    blocos = dividir_texto_em_blocos(resposta)
    for bloco in blocos:
        delay = delay_por_bloco(bloco)
        time.sleep(delay)
        enviar_texto_zapi(phone, bloco)

async def processar_audio(phone, audio_url):
    try:
        print("🔊 Baixando áudio...")
        async with aiohttp.ClientSession() as session:
            async with session.get(audio_url) as resp:
                if resp.status != 200:
                    raise Exception(f"Erro ao baixar áudio: {resp.status}")
                audio_bytes = await resp.read()

        print("🧠 Transcrevendo com Whisper...")
        response = openai.audio.transcriptions.create(
            model="whisper-1",
            file=("audio.ogg", audio_bytes, "audio/ogg")
        )
        transcricao = response.text.strip()
        print("✅ Transcrição:", transcricao)

        if not transcricao:
            enviar_texto_zapi(phone, "Desculpe, não consegui entender o áudio.")
            return

        resposta_ia = gerar_resposta(transcricao)
        print("🤖 Resposta da IA:", resposta_ia)

        nome_arquivo = nome_arquivo_audio_para(resposta_ia)
        caminho = os.path.join(PASTA_AUDIOS, nome_arquivo)
        if os.path.exists(caminho):
            await enviar_audio_zapi(phone, nome_arquivo)
        else:
            responder_com_blocos(phone, resposta_ia)

    except Exception as e:
        print("❌ Erro ao processar:", e)

# ========== ROTEAMENTO ==========

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("📦 Payload recebido:", data)

    phone = data.get("phone")
    if not phone:
        return "ok", 200

    if data.get("type") != "ReceivedCallback":
        return "ok", 200

    if phone in USERS_RESPONDED:
        return "ok", 200

    USERS_RESPONDED.add(phone)

    # Resposta inicial
    if phone not in ULTIMAS_INTERACOES:
        asyncio.run(enviar_audio_zapi(phone, "boas_vindas.ogg"))
        ULTIMAS_INTERACOES[phone] = time.time()
        return "ok", 200

    # Caso seja texto
    texto = data.get("text", {}).get("message")
    if texto:
        resposta_ia = gerar_resposta(texto)
        print("🤖 Resposta da IA:", resposta_ia)

        nome_arquivo = nome_arquivo_audio_para(resposta_ia)
        caminho = os.path.join(PASTA_AUDIOS, nome_arquivo)
        if os.path.exists(caminho):
            asyncio.run(enviar_audio_zapi(phone, nome_arquivo))
        else:
            responder_com_blocos(phone, resposta_ia)

        ULTIMAS_INTERACOES[phone] = time.time()
        return "ok", 200

    # Caso seja áudio
    audio_url = data.get("audio", {}).get("audioUrl")
    if audio_url:
        asyncio.run(processar_audio(phone, audio_url))
        ULTIMAS_INTERACOES[phone] = time.time()
        return "ok", 200

    return "ok", 200

# ========== FUNÇÃO DE RESPOSTA ==========

def gerar_resposta(pergunta):
    try:
        resposta = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "Você é um atendente especialista em produtos para queda de cabelo. Responda com clareza e empatia, como se estivesse falando por áudio ou digitando em um chat humanizado. Seja breve e direto."
                },
                {"role": "user", "content": pergunta}
            ]
        )
        return resposta.choices[0].message.content.strip()
    except Exception as e:
        print("Erro ao gerar resposta:", e)
        return "Desculpe, estou com dificuldades para responder agora."

# ========== EXECUÇÃO ==========
if __name__ == "__main__":
    print("✅ Servidor iniciado")
    app.run(host="0.0.0.0", port=10000)
