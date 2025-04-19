import os
import requests
from flask import Flask, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
ZAPI_CLIENT_TOKEN = os.getenv("ZAPI_CLIENT_TOKEN")
ZAPI_BASE_URL = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}"

HEADERS = {
    "Client-Token": ZAPI_CLIENT_TOKEN
}

AUDIO_LINKS = {
    "boas_vindas": "https://raw.githubusercontent.com/kelissonvidal/caplux-audios/main/boas_vindas.ogg",
    "formas_pagamento": "https://raw.githubusercontent.com/kelissonvidal/caplux-audios/main/formas_pagamento.ogg",
    "garantia": "https://raw.githubusercontent.com/kelissonvidal/caplux-audios/main/garantia.ogg",
    "prazo_entrega": "https://raw.githubusercontent.com/kelissonvidal/caplux-audios/main/prazo_entrega.ogg",
}

def enviar_audio_para_whatsapp(phone, audio_url):
    url = f"{ZAPI_BASE_URL}/audio/send-from-url"
    payload = {
        "phone": phone,
        "audio": audio_url
    }
    response = requests.post(url, json=payload, headers=HEADERS)
    return response

def enviar_mensagem_para_whatsapp(phone, mensagem):
    url = f"{ZAPI_BASE_URL}/send-text"
    payload = {
        "phone": phone,
        "message": mensagem
    }
    response = requests.post(url, json=payload, headers=HEADERS)
    return response

@app.route("/webhook", methods=["POST"])
def webhook():
    payload = request.get_json()

    if payload.get("type") == "ReceivedCallback" and not payload.get("fromApi", False):
        phone = payload.get("phone")
        message = payload.get("text", {}).get("message", "").lower()

        if message:
            if "forma de pagamento" in message or "formas de pagamento" in message:
                enviar_audio_para_whatsapp(phone, AUDIO_LINKS["formas_pagamento"])
            elif "garantia" in message:
                enviar_audio_para_whatsapp(phone, AUDIO_LINKS["garantia"])
            elif "prazo" in message or "entrega" in message:
                enviar_audio_para_whatsapp(phone, AUDIO_LINKS["prazo_entrega"])
            else:
                resposta = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Você é um atendente simpático e prestativo."},
                        {"role": "user", "content": message}
                    ]
                )
                texto_ia = resposta.choices[0].message.content.strip()
                enviar_mensagem_para_whatsapp(phone, texto_ia)

            enviar_audio_para_whatsapp(phone, AUDIO_LINKS["boas_vindas"])

    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)