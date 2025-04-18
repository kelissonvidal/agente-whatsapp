from flask import Flask, request
import os
import requests
import openai

app = Flask(__name__)

# Configurações da API Z-API e OpenAI
ZAPI_INSTANCE_ID = "3DF189F728F4A0C2E72632C54B267657"
ZAPI_CLIENT_TOKEN = "Fa25fe4ed32ff4c1189f0e12a6fbdd93dS"
ZAPI_API_URL = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_CLIENT_TOKEN}"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# Caminho corrigido para o áudio de boas-vindas
AUDIO_BOAS_VINDAS = "./data/boas_vindas.ogg"
USERS_RESPONDED = set()

# Envio de mensagens
def send_text(phone, message):
    response = requests.post(f"{ZAPI_API_URL}/send-text", json={"phone": phone, "message": message})
    print("📤 Enviado para", phone + ":", message)
    print("📨 Status:", response.status_code)
    print("📨 Resposta:", response.text)
    return response.status_code

def send_audio(phone, file_path):
    print("📢 Enviando áudio de boas-vindas...")
    with open(file_path, "rb") as audio_file:
        files = {"audio": ("boas_vindas.ogg", audio_file, "audio/ogg; codecs=opus")}
        response = requests.post(f"{ZAPI_API_URL}/send-audio", data={"phone": phone}, files=files)
    print("🎙️ Áudio enviado:", file_path, "→", phone)
    print("📨 Status:", response.status_code)
    print("📨 Resposta:", response.text)
    return response.status_code

# Transcrição e Resposta
def transcrever_audio(audio_url):
    print("🔊 Baixando áudio...")
    audio_response = requests.get(audio_url)
    audio_path = "/tmp/temp_audio.ogg"
    with open(audio_path, "wb") as f:
        f.write(audio_response.content)

    print("🧠 Transcrevendo com Whisper...")
    try:
        with open(audio_path, "rb") as f:
            transcript = openai.audio.transcriptions.create(model="whisper-1", file=f)
        texto = transcript.text.strip()
        print("✅ Transcrição concluída:", texto)
        return texto
    except Exception as e:
        print("❌ Erro ao transcrever:", e)
        return None

def responder_mensagem(phone, mensagem):
    resposta = gerar_resposta_ia(mensagem)
    if resposta:
        blocos = dividir_blocos(resposta)
        for bloco in blocos:
            send_text(phone, bloco)

def gerar_resposta_ia(texto):
    try:
        print("🤖 Solicitando resposta da IA...")
        resposta = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": texto}],
        )
        texto_resposta = resposta.choices[0].message.content.strip()
        print("🤖 Resposta da IA:", texto_resposta)
        return texto_resposta
    except Exception as e:
        print("❌ Erro na resposta da IA:", e)
        return "Desculpe, ocorreu um erro ao gerar a resposta."

def dividir_blocos(texto, palavras_limite=12):
    palavras = texto.split()
    blocos = []
    bloco = []
    contador = 0

    for palavra in palavras:
        bloco.append(palavra)
        contador += 1
        if contador >= palavras_limite and palavra.endswith("."):
            blocos.append(" ".join(bloco))
            bloco = []
            contador = 0

    if bloco:
        blocos.append(" ".join(bloco))

    return blocos

# Webhook
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("📦 Payload recebido:", data)

    if data.get("type") != "ReceivedCallback":
        return "ignorado", 200

    phone = data.get("phone")
    message = data.get("text", {}).get("message")
    audio = data.get("audio", {}).get("audioUrl")

    if not phone:
        return "ignorado", 200

    if phone not in USERS_RESPONDED:
        if os.path.exists(AUDIO_BOAS_VINDAS):
            send_audio(phone, AUDIO_BOAS_VINDAS)
        USERS_RESPONDED.add(phone)

    if audio:
        texto_transcrito = transcrever_audio(audio)
        if texto_transcrito:
            responder_mensagem(phone, texto_transcrito)
    elif message:
        responder_mensagem(phone, message)

    return "ok", 200

if __name__ == "__main__":
    print("🚀 IA Caplux iniciada e aguardando mensagens...")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))