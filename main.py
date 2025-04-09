import os
import time
import random
import requests
from flask import Flask, request, jsonify
from datetime import datetime
from openai import OpenAI
from urllib.parse import quote

app = Flask(__name__)

# Configurações da API Z-API
ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID", "3DF189F728F4A0C2E72632C54B267657")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN", "4ADA364DCC70ABFE1175200B")
ZAPI_CLIENT_TOKEN = os.getenv("ZAPI_CLIENT_TOKEN", "F9d86342bfd3d40e3b8a22ca73cfe9877S")
ZAPI_URL = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_TOKEN}/send-text"

# Controle de mensagens recebidas para envio de boas-vindas uma única vez
usuarios_ja_saudados = set()

# Cliente OpenAI
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

# Arquivo com conteúdo do funil
def carregar_contexto():
    try:
        url = "https://raw.githubusercontent.com/kelissonvidal/agente-whatsapp/main/data/funil_caplux.md"
        response = requests.get(url)
        response.raise_for_status()
        return response.text.strip()
    except Exception as e:
        print("[ERRO CONTEXTO]", e)
        return ""

contexto_geral = carregar_contexto()

# Função de geração de resposta
def gerar_resposta(pergunta):
    try:
        resposta = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um atendente de vendas simpático, humano e natural da empresa Caplux Suplementos. Use o conteúdo fornecido como base para conversar com clientes via WhatsApp. Evite respostas longas, e responda com linguagem informal e amigável."},
                {"role": "user", "content": f"{contexto_geral}\n\nPergunta do cliente: {pergunta}"}
            ],
            temperature=0.7,
        )
        return resposta.choices[0].message.content.strip()
    except Exception as e:
        print("[ERRO IA]", e)
        return "Desculpe, tivemos um problema ao gerar a resposta. Pode repetir a pergunta?"

# Função de envio de mensagem via Z-API
def enviar_mensagem(numero, mensagem):
    payload = {
        "phone": numero,
        "message": mensagem
    }
    headers = {
        "Content-Type": "application/json",
        "Client-Token": ZAPI_CLIENT_TOKEN
    }
    response = requests.post(ZAPI_URL, json=payload, headers=headers)
    print("Status da resposta:", response.status_code)
    print("Conteúdo da resposta:", response.text)

# Função de envio de áudio via link do GitHub
def enviar_audio(numero):
    url_ogg = "https://raw.githubusercontent.com/kelissonvidal/agente-whatsapp/main/data/boas_vindas.ogg"
    payload = {
        "phone": numero,
        "audio": url_ogg
    }
    headers = {
        "Content-Type": "application/json",
        "Client-Token": ZAPI_CLIENT_TOKEN
    }
    response = requests.post(
        f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_TOKEN}/send-audio",
        json=payload,
        headers=headers
    )
    print("Áudio enviado:", response.status_code, response.text)

# Webhook de recebimento
@app.route('/webhook', methods=['POST'])
def receber_mensagem():
    data = request.json
    msg = data.get('text', {}).get('message')
    telefone = data.get('phone')
    from_me = data.get('fromMe', False)

    if not msg or not telefone or from_me:
        return jsonify({"status": "ignorado"})

    print("📨 Mensagem recebida:", msg, "de", telefone)

    # Verifica se é a primeira mensagem
    if telefone not in usuarios_ja_saudados:
        usuarios_ja_saudados.add(telefone)
        enviar_audio(telefone)
        time.sleep(1)

    resposta = gerar_resposta(msg)
    partes = dividir_resposta(resposta)

    for parte in partes:
        enviar_mensagem(telefone, parte)
        time.sleep(random.uniform(1.2, 2.2))

    return jsonify({"status": "mensagem enviada"})

def dividir_resposta(texto):
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

@app.route('/')
def index():
    return 'Agente WhatsApp ativo!'

if __name__ == '__main__':
    app.run(port=10000, debug=True)