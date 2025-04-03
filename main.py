from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

API_URL = "https://v2.z-api.io/instances/3DF189F728F4A0C2E72632C54B267657/token/4ADA364DCC70ABFE1175200B/send-text"

# EXECUTA DIRETO NO CARREGAMENTO DO APP (mesmo no Render)
telefone_teste = "5537998278996"
texto_teste = "🚀 Teste direto no topo do main.py"
print("🟢 Executando teste imediato de envio...")
enviar_mensagem(telefone_teste, texto_teste)

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

def enviar_mensagem(telefone, texto):
    payload = {
        "phone": telefone,
        "message": texto
    }
    headers = {'Content-Type': 'application/json'}

    print(f"📨 Enviando para {telefone}: {texto}")

    resposta = requests.post(API_URL, json=payload, headers=headers)


    print(f"🔄 Status da resposta: {resposta.status_code}")
    print(f"📬 Conteúdo da resposta: {resposta.text}")

    # ESSA LINHA INICIA O SERVIDOR
    # Teste direto de envio (executa no carregamento do app na Render)
    telefone_teste = "5537998278996"
    texto_teste = "🚀 Teste disparado assim que o app sobe (sem depender do __main__)"
    enviar_mensagem(telefone_teste, texto_teste)

    # Iniciar o servidor Flask (somente se rodar localmente)
    if __name__ == "__main__":
        app.run(host='0.0.0.0', port=81)


