from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Variáveis da instância
INSTANCE_ID = "3DF189F728F4A0C2E72632C54B267657"
TOKEN = "4ADA364DCC70ABFE1175200B"
API_URL = f"https://api.z-api.io/instances/{INSTANCE_ID}/token/{TOKEN}/send-text"

# Client-Token da aba "Segurança"
CLIENT_TOKEN = "F9d86342bfd3d40e3b8a22ca73cfe9877S"

# Função para envio da mensagem
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

# Teste direto
telefone_teste = "553734490005"
texto_teste = "🚀 Teste direto com configuração corrigida!"
print("🟢 Executando teste imediato de envio...")
enviar_mensagem(telefone_teste, texto_teste)

# Webhook de recebimento
@app.route('/webhook', methods=['POST'])
def receber_mensagem():
    try:
        data = request.get_json(force=True)
        print(f"📥 Webhook recebido: {data}")
    except Exception as e:
        print(f"❌ Erro ao processar JSON: {e}")
        print(f"📦 Conteúdo bruto: {request.data}")
    return jsonify({"status": "ok"})

def gerar_resposta(msg):
    msg = msg.lower()
    if "oi" in msg or "olá" in msg:
        return "Olá! Aqui é da KVP Suplementos. Como posso te ajudar com o tratamento capilar?"
    elif "preço" in msg or "comprar" in msg:
        return "O suplemento custa R$97. Aqui está o link com desconto: https://linkpagamento.com"
    else:
        return "Estou aqui pra tirar suas dúvidas! Deseja saber como funciona o suplemento ou ver resultados reais?"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=81)
