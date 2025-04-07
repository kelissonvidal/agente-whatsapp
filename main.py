from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Endpoint padrão da Z-API
API_URL = "https://api.z-api.io/send-message"

# Token correto da aba "Segurança" no painel da instância
CLIENT_TOKEN = "F9d86342bfd3d40e3b8a22ca73cfe9877S"

# Função para enviar mensagem via Z-API
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

# Teste automático direto no topo do código
telefone_teste = "553734490005"  # Número do WhatsApp Business conectado à instância
texto_teste = "🚀 Teste direto com o token da aba Segurança da Z-API"
print("🟢 Executando teste imediato de envio...")
enviar_mensagem(telefone_teste, texto_teste)

# Endpoint de Webhook (opcional)
@app.route('/webhook', methods=['POST'])
def receber_mensagem():
    data = request.json
    msg = data.get('message')
    telefone = data.get('phone')

    if msg and telefone:
        resposta = gerar_resposta(msg)
        enviar_mensagem(telefone, resposta)
        return jsonify({"status": "mensagem enviada"})
    return jsonify({"status": "nada recebido"})

def gerar_resposta(msg):
    msg = msg.lower()
    if "oi" in msg or "olá" in msg:
        return "Olá! Aqui é da KVP Suplementos. Como posso te ajudar com o tratamento capilar?"
    elif "preço" in msg or "comprar" in msg:
        return "O suplemento custa R$97. Aqui está o link com desconto: https://linkpagamento.com"
    else:
        return "Estou aqui pra tirar suas dúvidas! Deseja saber como funciona o suplemento ou ver resultados reais?"

# Executa localmente (ignorado pelo Render)
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=81)
