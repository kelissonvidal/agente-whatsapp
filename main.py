import os
import time
import requests
import asyncio
from flask import Flask, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
ZAPI_CLIENT_TOKEN = os.getenv("ZAPI_CLIENT_TOKEN")

API_BASE = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_TOKEN}"

HEADERS = {
    "Client-Token": ZAPI_CLIENT_TOKEN
}

# Controle de boas-vindas
usuarios_atendidos = set()

# Repositório de áudios por intenção
audios_por_intencao = {
    "formas de pagamento": "formas_pagamento.ogg",
    "prazo de entrega": "prazo_entrega.ogg",
    "garantia": "garantia.ogg"
}

async def delay_por_bloco(bloco):
    palavras = bloco.split()
    n = len(palavras)
    if n <= 8:
        return 2
    elif n <= 14:
        return 3
    else:
        return 4

def detectar_intencao(texto):
    texto = texto.lower()
    if "forma" in texto and "pagamento" in texto:
        return "formas de pagamento"
    if "prazo" in texto or "entrega" in texto or "frete" in texto:
        return "prazo de entrega"
    if "garantia" in texto or "funcionar" in texto or "confiar" in texto:
        return "garantia"
    return None

def dividir_em_blocos(texto):
    palavras = texto.split()
    blocos = []
    bloco = []
    for palavra in palavras:
        bloco.append(palavra)
        if len(bloco) >= 12 and palavra.endswith("."):
            blocos.append(" ".join(bloco))
            bloco = []
    if bloco:
        blocos.append(" ".join(bloco))
    return blocos

def enviar_audio(telefone, nome_arquivo):
    url = f"{API_BASE}/send-audio"
    payload = {
        "phone": telefone,
        "audio": f"https://raw.githubusercontent.com/kelissonvidal/agente-whatsapp/main/data/{nome_arquivo}"
    }
    response = requests.post(url, headers=HEADERS, json=payload)
    print(f"[ÁUDIO] Enviado: {nome_arquivo} → {telefone}")
    print(f"[Z-API] Status: {response.status_code} | Resposta: {response.text}")

def enviar_texto(telefone, mensagem):
    url = f"{API_BASE}/send-text"
    payload = {
        "phone": telefone,
        "message": mensagem
    }
    response = requests.post(url, headers=HEADERS, json=payload)
    print(f"[TEXTO] Enviado para {telefone}: {mensagem}")
    print(f"[Z-API] Status: {response.status_code} | Resposta: {response.text}")

async def responder_com_blocos(telefone, resposta):
    blocos = dividir_em_blocos(resposta)
    for bloco in blocos:
        await asyncio.sleep(await delay_por_bloco(bloco))
        enviar_texto(telefone, bloco)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    print(f"📦 Payload recebido: {data}")

    tipo = data.get("type")
    telefone = data.get("phone")
    mensagem = data.get("text", {}).get("message", "")
    audio_info = data.get("audio", {})
    audio_url = audio_info.get("audioUrl", "")

    if data.get("fromMe"):
        return jsonify({"status": "ignorado"})

    if tipo == "ReceivedCallback":
        if telefone not in usuarios_atendidos:
            usuarios_atendidos.add(telefone)
            enviar_audio(telefone, "boas_vindas.ogg")
            return jsonify({"status": "boas-vindas"})

        if audio_url:
            try:
                transcricao = transcrever_audio(audio_url)
                print(f"✅ Transcrição: {transcricao}")
                mensagem = transcricao
            except Exception as e:
                print(f"[ERRO] Transcrição falhou: {e}")
                return jsonify({"erro": "transcricao"})

        intencao = detectar_intencao(mensagem)
        if intencao and intencao in audios_por_intencao:
            enviar_audio(telefone, audios_por_intencao[intencao])
        else:
            resposta_ia = gerar_resposta(mensagem)
            asyncio.run(responder_com_blocos(telefone, resposta_ia))

    return jsonify({"status": "recebido"})

def gerar_resposta(mensagem):
    try:
        resposta = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um atendente simpático da Caplux Suplementos, especialista em queda de cabelo. Responda de forma objetiva e natural."},
                {"role": "user", "content": mensagem}
            ]
        )
        return resposta.choices[0].message.content
    except Exception as e:
        print(f"[ERRO IA] {e}")
        return "Desculpe, não consegui entender. Pode repetir?"

def transcrever_audio(audio_url):
    import aiohttp
    import openai
    import tempfile

    async def baixar_arquivo():
        async with aiohttp.ClientSession() as session:
            async with session.get(audio_url) as resp:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as f:
                    f.write(await resp.read())
                    return f.name

    async def transcrever(caminho):
        with open(caminho, "rb") as f:
            transcript = openai.Audio.transcribe("whisper-1", f)
            return transcript["text"]

    caminho_audio = asyncio.run(baixar_arquivo())
    texto = asyncio.run(transcrever(caminho_audio))
    return texto

if __name__ == "__main__":
    app.run(debug=True)
