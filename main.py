
import os
import requests
from flask import Flask, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ZAPI_INSTANCE_ID = "3DF189F728F4A0C2E72632C54B267657"
ZAPI_TOKEN = "4ADA364DCC70ABFE1175200B"
ZAPI_CLIENT_TOKEN = "Fa25fe4ed32ff4c1189f0e12a6fbdd93dS"

app = Flask(__name__)
client = OpenAI(api_key=OPENAI_API_KEY)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    print("📦 Payload recebido:", data)

    if data.get("type") != "ReceivedCallback":
        return jsonify({"status": "ignored"}), 200

    phone = data.get("phone")
    text = data.get("text", {}).get("message")
    audio = data.get("audio", {}).get("audioUrl")

    if text:
        resposta = responder_com_ia(text)
        enviar_texto(phone, resposta)
        enviar_audio_boas_vindas(phone)

    return jsonify({"status": "ok"}), 200

def responder_com_ia(mensagem):
    try:
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um atendente educado e prestativo."},
                {"role": "user", "content": mensagem},
            ]
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print("Erro ao gerar resposta da IA:", e)
        return "Desculpe, não consegui gerar uma resposta agora."

def enviar_texto(phone, mensagem):
    url = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_TOKEN}/send-text"
    payload = {"phone": phone, "message": mensagem}
    headers = {"Client-Token": ZAPI_CLIENT_TOKEN}
    response = requests.post(url, json=payload, headers=headers)
    print("📤 Enviado para", phone + ":", mensagem)
    print("📨 Status:", response.status_code)
    print("📨 Resposta:", response.text)

def enviar_audio_boas_vindas(phone):
    audio_url = "https://raw.githubusercontent.com/kelissonvidal/caplux-audios/main/boas_vindas.ogg"
    url = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_TOKEN}/send-audio"
    payload = {"phone": phone, "audio": audio_url}
    headers = {"Client-Token": ZAPI_CLIENT_TOKEN}
    print("🔊 Enviando áudio de boas-vindas...")
    response = requests.post(url, json=payload, headers=headers)
    print("🎙️ Áudio enviado:", audio_url, "→", phone)
    print("📨 Status:", response.status_code)
    print("📨 Resposta:", response.text)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
