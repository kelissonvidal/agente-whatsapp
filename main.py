
from flask import Flask, request, jsonify
import requests
import openai
import os
import asyncio
from io import BytesIO
import time
from datetime import datetime

app = Flask(__name__)

# Configurações
ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
ZAPI_CLIENT_TOKEN = os.getenv("ZAPI_CLIENT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

API_BASE = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_TOKEN}"
HEADERS = { "Client-Token": ZAPI_CLIENT_TOKEN }
openai.api_key = OPENAI_API_KEY

GITHUB_REPO = "kelissonvidal/agente-whatsapp"
DEMANDAS_PATH = "data/demandas.txt"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DEMANDAS_PATH}"
GITHUB_HEADERS = { "Authorization": f"Bearer {GITHUB_TOKEN}" }

SESSOES = {}

# Blocos de texto finais após o áudio 9
BLOCOS_FECHAMENTO = [
    "Maravilha! Parabéns pela decisão de transformar de vez um problema capilar em cabelos lindos, saudáveis e fortes.",
    "Agora vou embalar seu Caplux e despachar via correios e volto aqui para te informar o código de rastreio.",
    "Me informe por favor esses dados abaixo:\n- Nome completo.\n- CPF para emitir o boleto.\n- Bairro, Rua e número.\n- Cidade, Estado e Cep.",
    "Obrigado pela confiança."
]

# Enviar mensagem de texto
def enviar_mensagem(telefone, mensagem):
    payload = { "phone": telefone, "message": mensagem }
    requests.post(f"{API_BASE}/send-text", headers=HEADERS, json=payload)

# Enviar áudio por nome de arquivo
def enviar_audio(telefone, nome_arquivo):
    url = f"https://raw.githubusercontent.com/kelissonvidal/agente-whatsapp/main/data/{nome_arquivo}"
    payload = { "phone": telefone, "audio": url }
    requests.post(f"{API_BASE}/send-audio", headers=HEADERS, json=payload)

# Enviar os blocos finais do fechamento com delay
async def enviar_blocos_finais(telefone):
    for bloco in BLOCOS_FECHAMENTO:
        await asyncio.sleep(4)
        enviar_mensagem(telefone, bloco)

# Transcrição de áudio com Whisper
def transcrever_audio(url):
    try:
        resposta = requests.get(url)
        resposta.raise_for_status()
        with BytesIO(resposta.content) as f:
            transcript = openai.audio.transcriptions.create(
                model="whisper-1",
                file=("audio.ogg", f)
            )
        return transcript.text
    except Exception as e:
        print("[Whisper] Erro na transcrição:", e)
        return ""

# Gerar resposta de fallback com IA
def gerar_resposta_ia(mensagem, nome=None):
    prompt = f"Mensagem do cliente: '{mensagem}'. Responda de forma simpática e natural como um atendente humano do produto Caplux, suplemento para queda de cabelo."
    if nome:
        prompt += f" Use o nome {nome} de forma ocasional nas respostas."
    try:
        resposta = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return resposta.choices[0].message.content.strip()
    except Exception as e:
        print("[OpenAI] Erro:", e)
        return "Desculpe, estou com dificuldade para responder isso agora."

# Registrar dúvidas não respondidas no GitHub
def registrar_demanda(telefone, mensagem):
    try:
        dt = datetime.now().strftime("%d/%m/%Y %H:%M")
        entrada = f"🕓 {dt}\n📞 Cliente: {telefone}\n💬 Pergunta: {mensagem}\n⚠️ Status: Fora do escopo / Não encontrado\n---\n"
        # Buscar conteúdo atual
        atual = requests.get(GITHUB_API_URL, headers=GITHUB_HEADERS).json()
        from base64 import b64decode, b64encode
        conteudo = b64decode(atual["content"]).decode() + entrada
        novo = b64encode(conteudo.encode()).decode()
        update_payload = {
            "message": f"Adiciona dúvida do cliente {telefone}",
            "content": novo,
            "sha": atual["sha"]
        }
        r = requests.put(GITHUB_API_URL, headers=GITHUB_HEADERS, json=update_payload)
        print("[GitHub] Demanda registrada:", r.status_code)
    except Exception as e:
        print("[GitHub] Falha ao registrar demanda:", e)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if data.get("type") != "ReceivedCallback" or data.get("fromMe"):
        return jsonify({"status": "ignorado"})

    telefone = data.get("phone")
    mensagem_texto = data.get("text", {}).get("message", "").strip()
    audio_info = data.get("audio")

    sessao = SESSOES.setdefault(telefone, {"etapa": 0, "nome": None, "permite_audio": None, "aguardando_resposta": False})

    def avancar():
        sessao["etapa"] += 1
        sessao["aguardando_resposta"] = False

    etapa = sessao["etapa"]

    # Etapa 0 - Pergunta o nome
    if etapa == 0:
        enviar_mensagem(telefone, "Olá! Seja muito bem-vindo. Qual é o seu nome, por favor?")
        avancar()
        return jsonify({"status": "nome_solicitado"})

    # Etapa 1 - Pergunta se prefere áudio
    if etapa == 1:
        sessao["nome"] = mensagem_texto.split()[0].capitalize() if mensagem_texto else "cliente"
        enviar_mensagem(telefone, f"Obrigado, {sessao['nome']}! Você prefere que eu responda só por texto ou também posso enviar áudios?")
        avancar()
        return jsonify({"status": "preferencia_solicitada"})

    # Etapa 2 - Armazena preferência
    if etapa == 2:
        pref = mensagem_texto.lower()
        sessao["permite_audio"] = not ("texto" in pref and "áudio" not in pref)
        avancar()
        enviar_audio(telefone, "audio_1.ogg")
        sessao["aguardando_resposta"] = True
        return jsonify({"status": "inicio_funil_com_audio_1"})

    # Etapas 3 a 7 (áudios 2 a 6)
    if etapa in [3, 4, 5, 6, 7]:
        if not sessao["aguardando_resposta"]:
            enviar_audio(telefone, f"audio_{etapa - 1}.ogg")
            sessao["aguardando_resposta"] = True
            return jsonify({"status": f"audio_{etapa - 1}_enviado"})
        else:
            avancar()
            return jsonify({"status": "resposta_recebida"})

    # Etapas 8 a 10 (áudios automáticos 6, 7, 8)
    if etapa in [8, 9, 10]:
        enviar_audio(telefone, f"audio_{etapa - 1}.ogg")
        time.sleep(8)
        avancar()
        return jsonify({"status": f"audio_{etapa - 1}_enviado"})

    # Etapa 11 - áudio 9 + blocos finais
    if etapa == 11:
        enviar_audio(telefone, "audio_9.ogg")
        time.sleep(8)
        asyncio.run(enviar_blocos_finais(telefone))
        avancar()
        return jsonify({"status": "final_bloco"})

    # Fallback fora do funil (responder e registrar)
    if mensagem_texto:
        resposta = gerar_resposta_ia(mensagem_texto, sessao.get("nome"))
        enviar_mensagem(telefone, resposta)
        registrar_demanda(telefone, mensagem_texto)
        return jsonify({"status": "fallback_resposta_texto"})

    if audio_info and audio_info.get("audioUrl"):
        url_audio = audio_info["audioUrl"]
        transcricao = transcrever_audio(url_audio)
        if transcricao:
            resposta = gerar_resposta_ia(transcricao, sessao.get("nome"))
            enviar_mensagem(telefone, resposta)
            registrar_demanda(telefone, transcricao)
        return jsonify({"status": "fallback_resposta_audio"})

    return jsonify({"status": "ignorado"})
