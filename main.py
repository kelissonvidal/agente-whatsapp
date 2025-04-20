import os
import requests
import asyncio
import openai
from flask import Flask, request, jsonify

ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
ZAPI_CLIENT_TOKEN = os.getenv("ZAPI_CLIENT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

API_BASE = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_TOKEN}"
openai.api_key = OPENAI_API_KEY

AUDIO_DE_BOAS_VINDAS = "boas_vindas.ogg"
AUDIOS_PATH = "./audios"

app = Flask(__name__)

USUARIOS_RESPONDIDOS = set()

def quebrar_em_blocos(texto):
    palavras = texto.split()
    blocos, bloco = [], []
    for palavra in palavras:
        bloco.append(palavra)
        if len(bloco) >= 12 and palavra.endswith('.'):
            blocos.append(' '.join(bloco))
            bloco = []
    if bloco:
        blocos.append(' '.join(bloco))
    return blocos

def delay_por_bloco(bloco):
    palavras = len(bloco.split())
    if palavras <= 8:
        return 2
    elif palavras >= 14:
        return 4
    return 3

async def responder_com_blocos(telefone, texto):
    blocos = quebrar_em_blocos(texto)[:3]
    for bloco in blocos:
        await asyncio.sleep(delay_por_bloco(bloco))
        payload = {"phone": telefone, "message": bloco}
        headers = {
            "Content-Type": "application/json",
            "Client-Token": ZAPI_CLIENT_TOKEN
        }
        try:
            response = requests.post(f"{API_BASE}/send-text", headers=headers, json=payload)
            print(f"[TEXTO] Enviado para {telefone}: {bloco}")
            print(f"[Z-API] Status: {response.status_code} | Resposta: {response.text}")
        except Exception as e:
            print(f"[ERRO] Falha ao enviar bloco: {e}")

def enviar_audio(telefone, nome_arquivo):
    caminho = f"{AUDIOS_PATH}/{nome_arquivo}"
    if not os.path.isfile(caminho):
        print(f"[ERRO] Áudio não encontrado: {caminho}")
        return
    try:
        with open(caminho, "rb") as f:
            files = {'audio': f}
            response = requests.post(
                f"{API_BASE}/send-audio",
                headers={"Client-Token": ZAPI_CLIENT_TOKEN},
                data={"phone": telefone},
                files=files
            )
        print(f"[ÁUDIO] Enviado: {nome_arquivo} → {telefone}")
        print(f"[Z-API] Status: {response.status_code} | Resposta: {response.text}")
    except Exception as e:
        print(f"[ERRO] Falha ao enviar áudio: {e}")

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    print("📦 Payload recebido:", data)

    tipo = data.get("type")
    telefone = data.get("phone")
    de_mim = data.get("fromMe", False)
    texto_recebido = data.get("text", {}).get("message")
    audio = data.get("audio", {}).get("audioUrl")

    if not telefone or de_mim:
        return jsonify({"status": "ignorado"}), 200

    if telefone not in USUARIOS_RESPONDIDOS:
        enviar_audio(telefone, AUDIO_DE_BOAS_VINDAS)
        responder_com_blocos(telefone, "Olá, como posso ajudá-lo hoje? Você está interessado em suplementos para queda de cabelo?")
        USUARIOS_RESPONDIDOS.add(telefone)
        return jsonify({"status": "boas-vindas enviada"}), 200

    if tipo == "ReceivedCallback" and audio:
        try:
            print("🔊 Baixando áudio...")
            resposta = requests.get(audio)
            with open("audio_recebido.ogg", "wb") as f:
                f.write(resposta.content)

            print("🧠 Transcrevendo com Whisper...")
            with open("audio_recebido.ogg", "rb") as f:
                transcricao = openai.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    response_format="text"
                )
            print("✅ Transcrição:", transcricao)

            resposta_ia = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Você é um atendente comercial da Caplux Suplementos."},
                    {"role": "user", "content": transcricao}
                ]
            ).choices[0].message.content

            asyncio.run(responder_com_blocos(telefone, resposta_ia))

        except Exception as e:
            print("❌ Erro ao transcrever ou responder:", str(e))
            return jsonify({"status": "erro"}), 500

    if texto_recebido:
        try:
            resposta_ia = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Você é um atendente comercial da Caplux Suplementos."},
                    {"role": "user", "content": texto_recebido}
                ]
            ).choices[0].message.content
            asyncio.run(responder_com_blocos(telefone, resposta_ia))
        except Exception as e:
            print("❌ Erro ao responder texto:", str(e))
            return jsonify({"status": "erro"}), 500

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(debug=True, port=10000)
