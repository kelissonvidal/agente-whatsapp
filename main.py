
from flask import Flask, request, jsonify
import requests
import openai
import os
import time
import random
from datetime import datetime

app = Flask(__name__)

# Configurações da Z-API
INSTANCE_ID = "3DF189F728F4A0C2E72632C54B267657"
TOKEN = "4ADA364DCC70ABFE1175200B"
CLIENT_TOKEN = "F9d86342bfd3d40e3b8a22ca73cfe9877S"
API_URL = f"https://api.z-api.io/instances/{INSTANCE_ID}/token/{TOKEN}/send-text"

# API da OpenAI
openai.api_key = os.environ.get("OPENAI_API_KEY")

def saudacao_por_horario():
    hora = datetime.now().hour
    if 5 <= hora < 12:
        return "Bom dia! ☀️"
    elif 12 <= hora < 18:
        return "Boa tarde! ☀️"
    else:
        return "Boa noite! 🌙"

introducoes_possiveis = [
    "Opa, deixa eu te responder certinho…",
    "Boa pergunta! Me dá só um instante…",
    "Ah, já te explico… rapidinho…",
    "Claro! Só um segundinho e te explico tudo.",
    "Vou te responder já já, beleza?"
]

def enviar_mensagem(telefone, texto):
    payload = {
        "phone": telefone,
        "message": texto
    }
    headers = {
        "Content-Type": "application/json",
        "Client-Token": CLIENT_TOKEN
    }
    print(f"📨 Enviando para {telefone}: {texto}")
    resposta = requests.post(API_URL, json=payload, headers=headers)
    print(f"🔄 Status da resposta: {resposta.status_code}")
    print(f"📬 Conteúdo da resposta: {resposta.text}")

def gerar_resposta_ia(pergunta):
    try:
        resposta = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Você é um atendente comercial experiente e simpático da empresa KVP Suplementos. "
                        "Seu papel é atender leads que vieram de anúncios no Facebook, tirar dúvidas com clareza, "
                        "ser amigável e humano, apresentar os benefícios do suplemento para tratamento capilar, "
                        "recomendar produtos de forma natural e oferecer o link de pagamento somente quando o cliente "
                        "estiver pronto para comprar. Responda com um tom acolhedor, como se fosse uma conversa real no WhatsApp. "
                        "Evite linguagem robótica ou respostas automáticas genéricas. Aja como uma pessoa real, com empatia e foco na conversão."
                    )
                },
                {
                    "role": "user",
                    "content": pergunta
                }
            ],
            temperature=0.7
        )
        return resposta.choices[0].message.content.strip()
    except Exception as e:
        print("[ERRO IA] Falha ao gerar resposta da OpenAI:", e)
        return "Desculpe, tivemos um problema ao gerar a resposta. Pode repetir a pergunta?"

@app.route('/webhook', methods=['POST'])
def receber_mensagem():
    data = request.json
    msg = data.get('text', {}).get('message')
    telefone = data.get('phone')
    enviado_por_mim = data.get('fromMe', False)

    if msg and telefone and not enviado_por_mim:
        print(f"📥 Mensagem recebida: {msg} de {telefone}")
        resposta = gerar_resposta_ia(msg)

        # Saudação com base no horário
        saudacao = saudacao_por_horario()
        enviar_mensagem(telefone, saudacao)
        time.sleep(1.8)

        # Introdução aleatória
        intro = random.choice(introducoes_possiveis)
        enviar_mensagem(telefone, intro)
        time.sleep(2.2)

        # Envio segmentado com pausa
        if len(resposta) > 300:
            partes = [resposta[i:i+300] for i in range(0, len(resposta), 300)]
            for parte in partes:
                enviar_mensagem(telefone, parte.strip())
                time.sleep(2)
        else:
            enviar_mensagem(telefone, resposta)

        return jsonify({"status": "mensagem enviada"})

    return jsonify({"status": "nada recebido"})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
