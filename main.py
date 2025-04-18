
from flask import Flask, request
import requests
import openai
import os
import asyncio

app = Flask(__name__)

# Configurações
INSTANCE_ID = "3DF189F728F4A0C2E72632C54B267657"
TOKEN = "4ADA364DCC70ABFE1175200B"
CLIENT_TOKEN = "Fa25fe4ed32ff4c1189f0e12a6fbdd93dS"

API_URL = f"https://api.z-api.io/instances/{INSTANCE_ID}/token/{TOKEN}"
AUDIO_BOAS_VINDAS = "./audios/boas_vindas.ogg"
openai.api_key = os.environ.get("OPENAI_API_KEY")


openai.api_key = OPENAI_API_KEY
USERS_RESPONDED = set()

# Envio de áudio inicial
def send_welcome_audio(phone):
    url = f"{API_URL}/send-audio"
    headers = {
        "Client-Token": CLIENT_TOKEN
    }
    data = {
        "phone": phone
    }
    files = {
        "audio": ("boas_vindas.ogg", open(AUDIO_BOAS_VINDAS, "rb"), "audio/ogg")
    }
    response = requests.post(url, headers=headers, data=data, files=files)
    print("📢 Enviando áudio de boas-vindas...")
    print("🎙️ Áudio enviado:", AUDIO_BOAS_VINDAS, "→", phone)
    print("📨 Status:", response.status_code)
    print("📨 Resposta:", response.text)

# Envio de mensagem de texto
def send_text(phone, message):
    url = f"{API_URL}/send-text"
    payload = {"phone": phone, "message": message}
    response = requests.post(url, json=payload)
    print("📤 Enviado para", phone + ":", message)
    print("📨 Status:", response.status_code)
    print("📨 Resposta:", response.text)

# Transcrição
def transcrever_audio(audio_url):
    print("🔊 Baixando áudio...")
    resposta = requests.get(audio_url)
    with open("temp_audio.ogg", "wb") as f:
        f.write(resposta.content)

    print("🧠 Transcrevendo com Whisper...")
    with open("temp_audio.ogg", "rb") as audio_file:
        transcript = openai.audio.transcriptions.create(
            file=audio_file,
            model="whisper-1"
        )
    return transcript.text

# IA com divisão de texto
async def responder_em_blocos(phone, resposta):
    palavras = resposta.split()
    blocos = []
    bloco = []

    for palavra in palavras:
        bloco.append(palavra)
        if len(bloco) >= 12 and "." in palavra:
            blocos.append(" ".join(bloco))
            bloco = []

    if bloco:
        blocos.append(" ".join(bloco))

    for bloco in blocos:
        send_text(phone, bloco)
        atraso = min(max(len(bloco.split()) * 0.25, 2), 5)
        await asyncio.sleep(atraso)

# Webhook
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("📦 Payload recebido:", data)

    phone = data.get("phone")
    tipo = data.get("type")
    from_me = data.get("fromMe")
    audio_url = data.get("audio", {}).get("audioUrl")

    if not phone or from_me:
        return "ignored", 200

    # Enviar áudio de boas-vindas apenas uma vez
    if phone not in USERS_RESPONDED:
        try:
            send_welcome_audio(phone)
            USERS_RESPONDED.add(phone)
            return "audio sent", 200
        except Exception as e:
            print("[ERRO] Falha ao enviar áudio:", e)
            return "audio error", 500

    # Se for áudio recebido, transcreve e responde com IA
    if tipo == "ReceivedCallback" and audio_url:
        try:
            transcricao = transcrever_audio(audio_url)
            print("✅ Transcrição:", transcricao)

            resposta = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Você é um atendente da Caplux Suplementos, responda de forma simpática e humanizada."},
                    {"role": "user", "content": transcricao}
                ]
            ).choices[0].message.content

            print("🤖 Resposta da IA:", resposta)
            asyncio.run(responder_em_blocos(phone, resposta))
        except Exception as e:
            print("❌ Erro ao processar:", e)
    return "ok", 200

if __name__ == "__main__":
    print("🚀 Servidor rodando na porta 5000...")
    app.run(host="0.0.0.0", port=5000)
