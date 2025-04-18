
from flask import Flask, request
import requests
import openai
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
INSTANCE_ID = os.getenv("INSTANCE_ID")
INSTANCE_TOKEN = os.getenv("INSTANCE_TOKEN")
CLIENT_TOKEN = os.getenv("CLIENT_TOKEN")

openai.api_key = OPENAI_API_KEY

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("📦 Payload recebido:", data)

    if data.get("type") == "ReceivedCallback":
        phone = data.get("phone")
        message = data.get("text", {}).get("message")
        audio_data = data.get("audio")

        if audio_data:
            audio_url = audio_data.get("audioUrl")
            if audio_url:
                print("🔊 Baixando áudio...")
                try:
                    audio_response = requests.get(audio_url)
                    audio_path = "/tmp/audio.ogg"
                    with open(audio_path, "wb") as f:
                        f.write(audio_response.content)
                    print("🧠 Transcrevendo com Whisper...")
                    transcript = transcribe_audio(audio_path)
                    print("📝 Texto transcrito:", transcript)
                    resposta = responder(transcript)
                    enviar_texto(phone, resposta)
                except Exception as e:
                    print("❌ Erro ao transcrever:", e)
        elif message:
            resposta = responder(message)
            enviar_texto(phone, resposta)
            enviar_audio_boas_vindas(phone)

    return "OK", 200

def responder(pergunta):
    print("🧠 Solicitando resposta da IA...")
    try:
        resposta = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um atendente educado e prestativo da Caplux Suplementos."},
                {"role": "user", "content": pergunta}
            ]
        )
        texto = resposta.choices[0].message.content
        print("🤖 Resposta da IA:", texto)
        return texto
    except Exception as e:
        print("Erro ao gerar resposta da IA:", e)
        return "Desculpe, houve um erro ao tentar responder."

def enviar_texto(phone, message):
    url = f"https://api.z-api.io/instances/{INSTANCE_ID}/token/{INSTANCE_TOKEN}/send-text"
    headers = {
        "Client-Token": CLIENT_TOKEN
    }
    payload = {
        "phone": phone,
        "message": message
    }
    response = requests.post(url, json=payload, headers=headers)
    print("📨 Enviado para", phone + ":", message)
    print("📨 Status:", response.status_code)
    print("📨 Resposta:", response.text)

def enviar_audio_boas_vindas(phone):
    print("📢 Enviando áudio de boas-vindas...")
    audio_url = "https://raw.githubusercontent.com/kelissonvidal/caplux-audios/main/boas_vindas.ogg"
    url = f"https://api.z-api.io/instances/{INSTANCE_ID}/token/{INSTANCE_TOKEN}/send-audio"
    headers = {
        "Client-Token": CLIENT_TOKEN
    }
    payload = {
        "phone": phone,
        "audio": audio_url
    }
    response = requests.post(url, json=payload, headers=headers)
    print("🎙️ Áudio enviado:", audio_url, "→", phone)
    print("📨 Status:", response.status_code)
    print("📨 Resposta:", response.text)

def transcribe_audio(audio_path):
    with open(audio_path, "rb") as f:
        transcript = openai.audio.transcriptions.create(
            file=f,
            model="whisper-1"
        )
    return transcript.text

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
