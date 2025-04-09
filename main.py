
from flask import Flask, request, jsonify
import requests
import time
import openai
import os

app = Flask(__name__)

# Configurações da API Z-API
INSTANCE_ID = "3DF189F728F4A0C2E72632C54B267657"
TOKEN = "4ADA364DCC70ABFE1175200B"
CLIENT_TOKEN = "F9d86342bfd3d40e3b8a22ca73cfe9877S"
ZAPI_URL = f"https://api.z-api.io/instances/{INSTANCE_ID}/token/{TOKEN}"

# Envia áudio de boas-vindas (arquivo .ogg hospedado no GitHub)
def enviar_audio_boas_vindas(telefone):
    url = f"{ZAPI_URL}/send-audio"
    payload = {
        "phone": telefone,
        "audio": "https://raw.githubusercontent.com/kelissonvidal/agente-whatsapp/main/data/boas_vindas.ogg"
    }
    headers = {
        "Content-Type": "application/json",
        "Client-Token": CLIENT_TOKEN
    }
    requests.post(url, json=payload, headers=headers)

# Envia mensagem de texto
def enviar_mensagem(telefone, mensagem):
    url = f"{ZAPI_URL}/send-text"
    payload = {
        "phone": telefone,
        "message": mensagem
    }
    headers = {
        "Content-Type": "application/json",
        "Client-Token": CLIENT_TOKEN
    }
    requests.post(url, json=payload, headers=headers)

# Transcreve o áudio recebido
def transcrever_audio(url_audio):
    try:
        audio_response = requests.get(url_audio)
        with open("temp_audio.ogg", "wb") as f:
            f.write(audio_response.content)

        with open("temp_audio.ogg", "rb") as audio_file:
            transcript = openai.Audio.transcribe("whisper-1", audio_file)
        os.remove("temp_audio.ogg")
        return transcript["text"]
    except Exception as e:
        print(f"[ERRO TRANSCRIÇÃO] {e}")
        return None

# Gera resposta com base na IA (utiliza conteúdo do GitHub)
def gerar_resposta(pergunta):
    try:
        url_conhecimento = "https://raw.githubusercontent.com/kelissonvidal/agente-whatsapp/main/data/funil_caplux.md"
        base = requests.get(url_conhecimento).text

        resposta = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": base},
                {"role": "user", "content": pergunta}
            ]
        )
        texto = resposta.choices[0].message.content.strip()
        return texto
    except Exception as e:
        print("[ERRO IA]", e)
        return "Desculpe, tivemos um problema ao gerar a resposta. Pode repetir a pergunta?"

# Webhook da Z-API
@app.route("/webhook", methods=["POST"])
def receber_mensagem():
    data = request.json
    telefone = data.get("phone")
    from_me = data.get("fromMe", False)
    msg = data.get("text", {}).get("message")
    msg_type = data.get("type")
    audio_url = data.get("audio", {}).get("url")

    if not telefone or from_me:
        return jsonify({"status": "ignorado"})

    if msg_type == "audio" and audio_url:
        msg = transcrever_audio(audio_url)

    if msg:
        if msg.lower() in ["oi", "olá", "bom dia", "boa tarde", "boa noite"]:
            enviar_audio_boas_vindas(telefone)
            return jsonify({"status": "audio enviado"})

        resposta = gerar_resposta(msg)
        blocos = dividir_mensagem_em_blocos(resposta)
        for bloco in blocos:
            enviar_mensagem(telefone, bloco)
            time.sleep(1.5)

    return jsonify({"status": "mensagem processada"})

def dividir_mensagem_em_blocos(texto, max_palavras=12):
    palavras = texto.split()
    blocos = []
    bloco = []

    for palavra in palavras:
        bloco.append(palavra)
        if len(bloco) >= max_palavras and palavra.endswith((".", "!", "?", "…")):
            blocos.append(" ".join(bloco))
            bloco = []

    if bloco:
        blocos.append(" ".join(bloco))

    return blocos

if __name__ == "__main__":
    app.run(debug=True)
