
from flask import Flask, request
import os
import requests
import openai
import aiohttp
import asyncio
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

# Ambiente
ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
ZAPI_CLIENT_TOKEN = os.getenv("ZAPI_CLIENT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# Configurações
API_URL = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_TOKEN}"
PASTA_AUDIOS = "https://raw.githubusercontent.com/kelissonvidal/caplux-audios/main/"
USERS_RESPONDED = set()
executor = ThreadPoolExecutor()

# === UTILITÁRIOS ===

def dividir_em_blocos(texto, tamanho_minimo=12):
    palavras = texto.split()
    blocos = []
    bloco = []

    for palavra in palavras:
        bloco.append(palavra)
        if len(bloco) >= tamanho_minimo and any(p in palavra for p in [".", "!", "?"]):
            blocos.append(" ".join(bloco))
            bloco = []

    if bloco:
        blocos.append(" ".join(bloco))

    return blocos

def delay_por_bloco(bloco):
    palavras = bloco.split()
    qtd = len(palavras)

    if qtd <= 8:
        return 2
    elif qtd <= 12:
        return 3
    elif qtd <= 18:
        return 4
    else:
        return 5

async def delay_seguro(segundos):
    await asyncio.sleep(segundos)

def send_text(phone, message):
    url = f"{API_URL}/send-text"
    headers = {
        "Content-Type": "application/json",
        "Client-Token": ZAPI_CLIENT_TOKEN
    }
    payload = {
        "phone": phone,
        "message": message
    }
    response = requests.post(url, headers=headers, json=payload)
    print(f"📤 Enviado para {phone}: {message}")
    print("📨 Status:", response.status_code)
    print("📨 Resposta:", response.text)

def send_audio(phone, nome_arquivo):
    url = f"{API_URL}/send-audio"
    headers = {
        "Content-Type": "application/json",
        "Client-Token": ZAPI_CLIENT_TOKEN
    }
    payload = {
        "phone": phone,
        "audio": f"{PASTA_AUDIOS}{nome_arquivo}"
    }
    response = requests.post(url, headers=headers, json=payload)
    print(f"🎙️ Áudio enviado: {nome_arquivo} → {phone}")
    print("📨 Status:", response.status_code)
    print("📨 Resposta:", response.text)

def responder_com_blocos(phone, resposta):
    blocos = dividir_em_blocos(resposta)
    loop = asyncio.new_event_loop()

    async def enviar_blocos():
        for bloco in blocos:
            delay = delay_por_bloco(bloco)
            await delay_seguro(delay)
            send_text(phone, bloco)

    loop.run_in_executor(executor, loop.run_until_complete, enviar_blocos())

# === FLUXO PRINCIPAL ===

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("📦 Payload recebido:", data)

    if data.get("type") != "ReceivedCallback":
        return "ignored", 200

    phone = data.get("phone")
    if not phone:
        return "ignored", 200

    # Envia boas-vindas se for primeira interação
    if phone not in USERS_RESPONDED:
        print("📢 Enviando áudio de boas-vindas...")
        send_audio(phone, "boas_vindas.ogg")
        USERS_RESPONDED.add(phone)

    # Se vier texto
    if "text" in data:
        message = data["text"].get("message", "")
        if message:
            resposta = gerar_resposta_ia(message)
            responder_com_blocos(phone, resposta)

    # Se vier áudio
    elif "audio" in data:
        audio_url = data["audio"].get("audioUrl")
        if audio_url:
            try:
                print("🔊 Baixando áudio...")
                caminho = baixar_audio(audio_url)
                print("🧠 Transcrevendo com Whisper...")
                transcricao = transcrever_whisper(caminho)
                print("✅ Transcrição:", transcricao)
                resposta = gerar_resposta_ia(transcricao)
                responder_com_blocos(phone, resposta)
            except Exception as e:
                print("❌ Erro ao transcrever:", e)

    return "ok", 200

# === INTEGRAÇÃO COM OPENAI ===

def gerar_resposta_ia(texto):
    client = openai.OpenAI(api_key=OPENAI_API_KEY)

    resposta = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Você é um atendente simpático da empresa Caplux Suplementos, especializada em queda de cabelo."},
            {"role": "user", "content": texto}
        ]
    )
    return resposta.choices[0].message.content.strip()

def baixar_audio(url):
    nome_arquivo = "temp_audio.ogg"
    resposta = requests.get(url)
    with open(nome_arquivo, "wb") as f:
        f.write(resposta.content)
    return nome_arquivo

def transcrever_whisper(caminho_ogg):
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    with open(caminho_ogg, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
    return transcription.text.strip()

# === EXECUÇÃO LOCAL ===
if __name__ == "__main__":
    print("✅ Servidor Caplux iniciado localmente...")
    app.run(host="0.0.0.0", port=10000)
