
from flask import Flask, request, jsonify
import requests
import openai
import os
import asyncio
from io import BytesIO
import time

app = Flask(__name__)

# Variáveis de ambiente
ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
ZAPI_CLIENT_TOKEN = os.getenv("ZAPI_CLIENT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

API_BASE = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_TOKEN}"
HEADERS = { "Client-Token": ZAPI_CLIENT_TOKEN }

# Sessão por número
SESSOES = {}

# Mapear blocos de texto do final
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

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if data.get("type") != "ReceivedCallback" or data.get("fromMe"):
        return jsonify({"status": "ignorado"})

    telefone = data.get("phone")
    mensagem = data.get("text", {}).get("message", "").strip()
    sessao = SESSOES.setdefault(telefone, {"etapa": 1, "aguardando_resposta": False})

    etapa = sessao["etapa"]

    if etapa == 1 and not sessao["aguardando_resposta"]:
        enviar_audio(telefone, "audio_1.ogg")
        sessao["aguardando_resposta"] = True
        return jsonify({"status": "etapa_1_enviada"})

    if etapa in [2, 3, 4, 5] and not sessao["aguardando_resposta"]:
        enviar_audio(telefone, f"audio_{etapa}.ogg")
        sessao["aguardando_resposta"] = True
        return jsonify({"status": f"audio_{etapa}_enviado"})

    if etapa in [1, 2, 3, 4, 5] and sessao["aguardando_resposta"]:
        sessao["etapa"] += 1
        sessao["aguardando_resposta"] = False
        return jsonify({"status": "resposta_recebida_etapa_" + str(etapa)})

    if etapa in [6, 7, 8]:
        enviar_audio(telefone, f"audio_{etapa}.ogg")
        time.sleep(8)
        sessao["etapa"] += 1
        return jsonify({"status": f"audio_{etapa}_automático_enviado"})

    if etapa == 9:
        enviar_audio(telefone, "audio_9.ogg")
        time.sleep(8)
        asyncio.run(enviar_blocos_finais(telefone))
        sessao["etapa"] += 1
        return jsonify({"status": "audio_9_e_blocos_finais_enviados"})

    return jsonify({"status": "finalizado"})

    if mensagem_texto:
        if sessao["aguardando_resposta"] and etapa in [3, 4, 5, 6, 7]:
            sessao["aguardando_resposta"] = False
            avancar()
            return jsonify({"status": f"etapa_{etapa}_avancada_com_texto"})
        resposta = gerar_resposta_ia(mensagem_texto, sessao.get("nome"))
        enviar_mensagem(telefone, resposta)
        registrar_demanda(telefone, mensagem_texto)
        return jsonify({"status": "fallback_resposta_texto"})

    if audio_info and audio_info.get("audioUrl"):
        url_audio = audio_info["audioUrl"]
        transcricao = transcrever_audio(url_audio)
        if transcricao:
            if sessao["aguardando_resposta"] and etapa in [3, 4, 5, 6, 7]:
                sessao["aguardando_resposta"] = False
                avancar()
                return jsonify({"status": f"etapa_{etapa}_avancada_com_audio"})
            resposta = gerar_resposta_ia(transcricao, sessao.get("nome"))
            enviar_mensagem(telefone, resposta)
            registrar_demanda(telefone, transcricao)
        return jsonify({"status": "fallback_resposta_audio"})

    return jsonify({"status": "ignorado"})

    telefone = data.get("phone")
    mensagem = data.get("text", {}).get("message", "").strip()
    sessao = SESSOES.setdefault(telefone, {"etapa": 1, "aguardando_resposta": False})

    etapa = sessao["etapa"]

    if etapa == 1 and not sessao["aguardando_resposta"]:
        enviar_audio(telefone, "audio_1.ogg")
        sessao["aguardando_resposta"] = True
        return jsonify({"status": "etapa_1_enviada"})

    if etapa in [2, 3, 4, 5] and not sessao["aguardando_resposta"]:
        enviar_audio(telefone, f"audio_{etapa}.ogg")
        sessao["aguardando_resposta"] = True
        return jsonify({"status": f"audio_{etapa}_enviado"})

    if etapa in [1, 2, 3, 4, 5] and sessao["aguardando_resposta"]:
        sessao["etapa"] += 1
        sessao["aguardando_resposta"] = False
        return jsonify({"status": "resposta_recebida_etapa_" + str(etapa)})

    if etapa in [6, 7, 8]:
        enviar_audio(telefone, f"audio_{etapa}.ogg")
        time.sleep(8)
        sessao["etapa"] += 1
        return jsonify({"status": f"audio_{etapa}_automático_enviado"})

    if etapa == 9:
        enviar_audio(telefone, "audio_9.ogg")
        time.sleep(8)
        asyncio.run(enviar_blocos_finais(telefone))
        sessao["etapa"] += 1
        return jsonify({"status": "audio_9_e_blocos_finais_enviados"})

    return jsonify({"status": "finalizado"})
