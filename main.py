import os
import requests
import time
from flask import Flask, request
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
ZAPI_CLIENT_TOKEN = os.getenv("ZAPI_CLIENT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

API_BASE = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_TOKEN}"
AUDIO_GITHUB_BASE = "https://raw.githubusercontent.com/kelissonvidal/caplux-audios/main/"

client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)
USERS_RESPONDED = set()

# Quebra mensagens longas em blocos naturais
def quebrar_em_blocos(texto):
    palavras = texto.split()
    blocos = []
    bloco = []

    for palavra in palavras:
        bloco.append(palavra)
        if len(bloco) >= 12 and "." in palavra:
            blocos.append(" ".join(bloco))
            bloco = []

    if bloco:
        blocos.append(" ".join(bloco))

    return blocos

# Define o tempo de "pausa" entre blocos baseado no tamanho
def delay_por_bloco(bloco):
    palavras = len(bloco.split())
    if palavras < 10:
        return 2
    elif palavras < 15:
        return 3
    else:
        return 4

# Envia um áudio hospedado no GitHub
def enviar_audio(telefone, nome_arquivo):
    url = f"{API_BASE}/send-audio"
    headers = {
        "Content-Type": "application/json",
        "Client-Token": ZAPI_CLIENT_TOKEN
    }
    payload = {
        "phone": telefone,
        "audio": AUDIO_GITHUB_BASE + nome_arquivo
    }
    response = requests.post(url, headers=headers, json=payload)
    print(f"[ÁUDIO] Enviado: {nome_arquivo} → {telefone}")
    print(f"[Z-API] Status: {response.status_code} | Resposta: {response.text}")

# Envia mensagem de texto dividida em blocos
def responder_com_blocos(telefone, texto):
    blocos = quebrar_em_blocos(texto)
    for bloco in blocos:
        time.sleep(delay_por_bloco(bloco))
        payload = {
            "phone": telefone,
            "message": bloco
        }
        response = requests.post(f"{API_BASE}/send-text", json=payload)
        print(f"[TEXTO] Enviado para {telefone}: {bloco}")
        print(f"[Z-API] Status: {response.status_code} | Resposta: {response.text}")

# Transcreve o áudio com Whisper
def transcrever_audio(audio_url):
    try:
        audio_data = requests.get(audio_url).content
        with open("temp_audio.ogg", "wb") as f:
            f.write(audio_data)
        with open("temp_audio.ogg", "rb") as f:
            transcription = client.audio.transcriptions.create(model="whisper-1", file=f)
        return transcription.text
    except Exception as e:
        print("❌ Erro na transcrição:", e)
        return None

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("📦 Payload recebido:", data)

    tipo = data.get("type")
    telefone = data.get("phone")
    mensagem_texto = data.get("text", {}).get("message", "")
    url_audio = data.get("audio", {}).get("audioUrl", "")
    enviado_pela_ia = data.get("fromApi", False)

    if enviado_pela_ia or not telefone:
        return "ignorado", 200

    if telefone not in USERS_RESPONDED:
        enviar_audio(telefone, "boas_vindas.ogg")
        USERS_RESPONDED.add(telefone)

    # Se for áudio
    if tipo == "ReceivedCallback" and url_audio:
        transcricao = transcrever_audio(url_audio)
        if transcricao:
            print("✅ Transcrição:", transcricao)
            resposta = gerar_resposta(transcricao)
            responder_com_blocos(telefone, resposta)
        return "áudio processado", 200

    # Se for texto
    if mensagem_texto:
        resposta = gerar_resposta(mensagem_texto)
        responder_com_blocos(telefone, resposta)
        return "mensagem respondida", 200

    return "ok", 200

def gerar_resposta(pergunta):
    resposta = client.chat.completions.create(
        model="gpt-4",
        messages=[{
            "role": "system",
            "content": "Você é um atendente educado que ajuda pessoas interessadas em suplementos para queda de cabelo."
        }, {
            "role": "user",
            "content": pergunta
        }],
        temperature=0.7
    )
    return resposta.choices[0].message.content

if __name__ == "__main__":
    print("🚀 Servidor rodando...")
    app.run(host="0.0.0.0", port=10000)
