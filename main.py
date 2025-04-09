
from flask import Flask, request, jsonify
import requests
import os
import time

app = Flask(__name__)

ZAPI_URL = "https://api.z-api.io/instances/YOUR_INSTANCE_ID/token/YOUR_INSTANCE_TOKEN"
CLIENT_TOKEN = "YOUR_CLIENT_TOKEN"

# Variável para armazenar se o áudio já foi enviado para cada cliente
clientes_com_audio_enviado = {}

def enviar_audio_boas_vindas(telefone):
    caminho_audio = "boas_vindas.ogg"
    if not os.path.exists(caminho_audio):
        print("[ERRO] Arquivo de áudio não encontrado.")
        return

    url = f"{ZAPI_URL}/send-audio"
    with open(caminho_audio, 'rb') as audio_file:
        files = {'audio': audio_file}
        data = {'phone': telefone}
        headers = {'Client-Token': CLIENT_TOKEN}
        response = requests.post(url, data=data, files=files, headers=headers)
        print("Enviando áudio de boas-vindas:", response.text)

def enviar_mensagem(telefone, mensagem):
    url = f"{ZAPI_URL}/send-text"
    headers = {
        "Content-Type": "application/json",
        "Client-Token": CLIENT_TOKEN
    }
    payload = {
        "phone": telefone,
        "message": mensagem
    }
    response = requests.post(url, headers=headers, json=payload)
    print("Status da resposta:", response.status_code)
    print("Conteúdo da resposta:", response.text)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    telefone = data.get("phone")
    mensagem_texto = data.get("text", {}).get("message")
    mensagem_audio = data.get("audio", {}).get("url")
    from_me = data.get("fromMe", True)

    if telefone and not from_me:
        if telefone not in clientes_com_audio_enviado:
            enviar_audio_boas_vindas(telefone)
            clientes_com_audio_enviado[telefone] = True
            return jsonify({"status": "áudio enviado"})

        if mensagem_texto:
            resposta = gerar_resposta(mensagem_texto)
            enviar_mensagem(telefone, resposta)
            return jsonify({"status": "mensagem enviada"})

        elif mensagem_audio:
            resposta = "Recebi seu áudio! Me dá só um instante que já te respondo direitinho, tá bom?"
            enviar_mensagem(telefone, resposta)
            return jsonify({"status": "áudio recebido"})

    return jsonify({"status": "nada processado"})

def gerar_resposta(mensagem):
    return "Me dá só um segundinho que já vou te responder direitinho, tá?"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
