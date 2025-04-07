
from flask import Flask, request, jsonify
import requests
import openai
import os

app = Flask(__name__)

# Configurações da Z-API
INSTANCE_ID = "3DF189F728F4A0C2E72632C54B267657"
TOKEN = "4ADA364DCC70ABFE1175200B"
CLIENT_TOKEN = "F9d86342bfd3d40e3b8a22ca73cfe9877S"
API_URL = f"https://api.z-api.io/instances/{INSTANCE_ID}/token/{TOKEN}/send-text"

# API Key da OpenAI (usando variável de ambiente)
openai.api_key = os.environ.get("OPENAI_API_KEY")

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
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "Você é um atendente da KVP Suplementos, prestando atendimento humanizado sobre um suplemento para tratamento capilar. Seja educado, direto e útil."
                },
                {
                    "role": "user",
                    "content": pergunta
                }
            ],
            max_tokens=300,
            temperature=0.7
        )
        resposta = response['choices'][0]['message']['content']
        return resposta.strip()
    except Exception as e:
        print(f"Erro ao gerar resposta IA: {e}")
        return "Desculpe, tivemos um problema ao gerar a resposta. Pode repetir a pergunta?"

@app.route('/webhook', methods=['POST'])
def receber_mensagem():
    data = request.json
    msg = data.get('text', {}).get('message')
    telefone = data.get('phone')
    enviado_por_mim = data.get('fromMe', False)

    if msg and telefone and not enviado_por_mim:
        resposta = gerar_resposta_ia(msg)
        enviar_mensagem(telefone, resposta)
        return jsonify({"status": "mensagem enviada"})
    return jsonify({"status": "nada recebido"})

if __name__ == "__main__":
    telefone_teste = "5537998278996"
    texto_teste = "Olá! Gostaria de saber como funciona o suplemento para queda de cabelo."
    print("🟢 Executando teste imediato de envio com IA...")
    enviar_mensagem(telefone_teste, gerar_resposta_ia(texto_teste))
    app.run(host='0.0.0.0', port=81)
