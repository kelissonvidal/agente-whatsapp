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

# Configuração da API da OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY", "sua_nova_chave_aqui")

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

@app.route('/webhook', methods=['POST'])
def receber_mensagem():
    data = request.json
    msg = data.get('text', {}).get('message')
    telefone = data.get('phone')
    is_me = data.get('fromMe', False)

    print(f"📥 Mensagem recebida: {msg} de {telefone}")

    if msg and telefone and not is_me:
        resposta = gerar_resposta(msg)
        enviar_mensagem(telefone, resposta)
        return jsonify({"status": "mensagem enviada"})

    return jsonify({"status": "nada recebido"})

def gerar_resposta(pergunta):
    try:
        resposta = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um atendente simpático da empresa KVP Suplementos. Responda de forma breve, natural e objetiva sobre o suplemento para tratamento capilar."},
                {"role": "user", "content": pergunta}
            ],
            temperature=0.7
        )
        return resposta.choices[0].message.content.strip()
    except Exception as e:
        print("[ERRO IA] Falha ao gerar resposta da OpenAI:", e)
        return "Desculpe, tivemos um problema ao gerar a resposta. Pode repetir a pergunta?"

# Teste imediato (opcional para debug)
if __name__ == "__main__":
    telefone_teste = "5537998278996"
    texto_teste = "🚀 Teste direto com a versão atualizada da OpenAI"
    print("🟢 Executando teste imediato de envio...")
    enviar_mensagem(telefone_teste, texto_teste)
    app.run(host='0.0.0.0', port=10000)
