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

# Configuração da OpenAI
openai.api_key = os.environ.get("OPENAI_API_KEY")

# Links dos arquivos (substitua pelo seu repositório real futuramente)
GITHUB_BASE = "https://raw.githubusercontent.com/kelissonvidal/agente-whatsapp/main/"

URL_CONTEXTO = GITHUB_BASE + "contexto.txt"
URL_INSTRUCOES = GITHUB_BASE + "instrucoes.txt"

ultimo_contato = {}
nomes_clientes = {}

def carregar_arquivo(url):
    try:
        r = requests.get(url)
        r.raise_for_status()
        return r.text.strip()
    except Exception as e:
        print(f"Erro ao carregar {url}: {e}")
        return ""

def saudacao_por_horario():
    hora = datetime.now().hour
    if 5 <= hora < 12:
        return "Bom dia! ☀️"
    elif 12 <= hora < 18:
        return "Boa tarde! 🌤️"
    else:
        return "Boa noite! 🌙"

def enviar_mensagem(telefone, texto):
    payload = {"phone": telefone, "message": texto}
    headers = {"Content-Type": "application/json", "Client-Token": CLIENT_TOKEN}
    print(f"📨 Enviando para {telefone}: {texto}")
    resposta = requests.post(API_URL, json=payload, headers=headers)
    print(f"🔄 Status: {resposta.status_code}")
    print(f"📬 Conteúdo: {resposta.text}")

def gerar_resposta(msg, nome_cliente):
    contexto = carregar_arquivo(URL_CONTEXTO)
    instrucoes = carregar_arquivo(URL_INSTRUCOES)
    system_prompt = f"{contexto}

{instrucoes}

Cliente: {nome_cliente}"

    try:
        resposta = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": msg}
            ],
            temperature=0.7
        )
        return resposta.choices[0].message.content.strip()
    except Exception as e:
        print("[ERRO IA]", e)
        return "Tivemos um problema ao responder. Pode tentar novamente?"

@app.route("/webhook", methods=["POST"])
def receber_mensagem():
    data = request.json
    telefone = data.get("phone")
    msg = data.get("text", {}).get("message")
    from_me = data.get("fromMe", False)

    if not telefone or not msg or from_me:
        return jsonify({"status": "ignorado"})

    print(f"📥 Mensagem de {telefone}: {msg}")

    agora = time.time()
    saudou = telefone in ultimo_contato and agora - ultimo_contato[telefone] < 300

    if telefone not in nomes_clientes:
        if not saudou:
            enviar_mensagem(telefone, saudacao_por_horario())
            time.sleep(1.5)
        enviar_mensagem(telefone, "Oi! Qual o seu nome, por favor?")
        ultimo_contato[telefone] = agora
        nomes_clientes[telefone] = None
        return jsonify({"status": "pedindo nome"})

    if nomes_clientes[telefone] is None:
        nomes_clientes[telefone] = msg.strip().split()[0].capitalize()
        enviar_mensagem(telefone, f"Prazer, {nomes_clientes[telefone]}! Como posso te ajudar hoje?")
        return jsonify({"status": "nome salvo"})

    nome_cliente = nomes_clientes[telefone]
    resposta = gerar_resposta(msg, nome_cliente)
    for frase in resposta.split('.'):
        frase = frase.strip()
        if frase:
            enviar_mensagem(telefone, frase + '.')
            time.sleep(random.uniform(1.5, 2.3))

    return jsonify({"status": "mensagem enviada"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)