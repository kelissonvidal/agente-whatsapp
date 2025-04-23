
from flask import Flask, request, jsonify
import requests
import openai
import os
import asyncio
from io import BytesIO
import time
from datetime import datetime
from base64 import b64decode, b64encode

app = Flask(__name__)

ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
ZAPI_CLIENT_TOKEN = os.getenv("ZAPI_CLIENT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

API_BASE = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_TOKEN}"
HEADERS = { "Client-Token": ZAPI_CLIENT_TOKEN }
openai.api_key = OPENAI_API_KEY
GITHUB_HEADERS = { "Authorization": f"Bearer {GITHUB_TOKEN}" }
GITHUB_REPO = "kelissonvidal/agente-whatsapp"
DEMANDAS_PATH = "data/demandas.txt"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DEMANDAS_PATH}"

SESSOES = {}
BLOCOS_FECHAMENTO = [
    "Maravilha! Parabéns pela decisão de transformar de vez um problema capilar em cabelos lindos, saudáveis e fortes.",
    "Agora vou embalar seu Caplux e despachar via correios e volto aqui para te informar o código de rastreio.",
    "Me informe por favor esses dados abaixo:\n- Nome completo.\n- CPF para emitir o boleto.\n- Bairro, Rua e número.\n- Cidade, Estado e Cep.",
    "Obrigado pela confiança."
]

def enviar_mensagem(telefone, mensagem):
    payload = { "phone": telefone, "message": mensagem }
    requests.post(f"{API_BASE}/send-text", headers=HEADERS, json=payload)

def enviar_audio(telefone, nome_arquivo):
    url = f"https://raw.githubusercontent.com/kelissonvidal/agente-whatsapp/main/data/{nome_arquivo}"
    payload = { "phone": telefone, "audio": url }
    requests.post(f"{API_BASE}/send-audio", headers=HEADERS, json=payload)

async def enviar_blocos_finais(telefone):
    for bloco in BLOCOS_FECHAMENTO:
        await asyncio.sleep(4)
        enviar_mensagem(telefone, bloco)

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

def registrar_demanda(telefone, mensagem):
    try:
        dt = datetime.now().strftime("%d/%m/%Y %H:%M")
        entrada = f"🕓 {dt}\n📞 Cliente: {telefone}\n💬 Pergunta: {mensagem}\n⚠️ Status: Fora do escopo / Não encontrado\n---\n"
        atual = requests.get(GITHUB_API_URL, headers=GITHUB_HEADERS).json()
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
    sessao = SESSOES.setdefault(telefone, {"etapa": 0, "nome": None, "permite_audio": None, "aguardando_resposta": False, "audio_enviado": False})

    def avancar():
        sessao["etapa"] += 1
        sessao["aguardando_resposta"] = False
        sessao["audio_enviado"] = False

    etapa = sessao["etapa"]

    if etapa == 0:
        enviar_mensagem(telefone, "Olá! Seja muito bem-vindo. Qual é o seu nome, por favor?")
        avancar()
        return jsonify({"status": "nome_solicitado"})

    if etapa == 1:
        sessao["nome"] = mensagem_texto.split()[0].capitalize() if mensagem_texto else "cliente"
        enviar_mensagem(telefone, f"Obrigado, {sessao['nome']}! Você prefere que eu responda só por texto ou também posso enviar áudios?")
        avancar()
        return jsonify({"status": "preferencia_solicitada"})

    if etapa == 2:
        pref = mensagem_texto.lower()
        sessao["permite_audio"] = not ("texto" in pref and "áudio" not in pref)
        avancar()
        return jsonify({"status": "preferencia_registrada"})

    if etapa in [3, 4, 5, 6, 7]:
        if not sessao["audio_enviado"]:
            nome_audio = f"audio_{etapa - 2}.ogg"
            if sessao["permite_audio"]:
                enviar_audio(telefone, nome_audio)
            else:
                enviar_mensagem(telefone, f"(Texto alternativo ao {nome_audio})")
            sessao["aguardando_resposta"] = True
            sessao["audio_enviado"] = True
            return jsonify({"status": f"{nome_audio} enviado"})

    if etapa in [8, 9, 10]:
        if not sessao["audio_enviado"]:
            nome_audio = f"audio_{etapa - 2}.ogg"
            if sessao["permite_audio"]:
                enviar_audio(telefone, nome_audio)
            else:
                enviar_mensagem(telefone, f"(Texto alternativo ao {nome_audio})")
            sessao["audio_enviado"] = True
            time.sleep(8)
            avancar()
            return jsonify({"status": f"{nome_audio} enviado automaticamente"})

    if etapa == 11:
        if not sessao["audio_enviado"]:
            if sessao["permite_audio"]:
                enviar_audio(telefone, "audio_9.ogg")
            else:
                enviar_mensagem(telefone, "(Texto alternativo ao áudio 9)")
            sessao["audio_enviado"] = True
            time.sleep(8)
            asyncio.run(enviar_blocos_finais(telefone))
            avancar()
            return jsonify({"status": "fechamento_completo"})

    if mensagem_texto:
        if sessao["aguardando_resposta"] and etapa in [3, 4, 5, 6, 7]:
            avancar()
            return jsonify({"status": f"etapa_{etapa}_avancada_com_texto"})
        resposta = gerar_resposta_ia(mensagem_texto, sessao.get("nome"))
        enviar_mensagem(telefone, resposta)
        registrar_demanda(telefone, mensagem_texto)
        return jsonify({"status": "fallback_texto"})

    if audio_info and audio_info.get("audioUrl"):
        url_audio = audio_info["audioUrl"]
        transcricao = transcrever_audio(url_audio)
        if transcricao:
            if sessao["aguardando_resposta"] and etapa in [3, 4, 5, 6, 7]:
                avancar()
                return jsonify({"status": f"etapa_{etapa}_avancada_com_audio"})
            resposta = gerar_resposta_ia(transcricao, sessao.get("nome"))
            enviar_mensagem(telefone, resposta)
            registrar_demanda(telefone, transcricao)
        return jsonify({"status": "fallback_audio"})

    return jsonify({"status": "ignorado"})
