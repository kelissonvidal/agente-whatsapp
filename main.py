from flask import Flask, request, jsonify
import requests
import openai
import os
import time
import threading
from io import BytesIO
from datetime import datetime
from base64 import b64decode, b64encode

app = Flask(__name__)

# Configurações de ambiente
ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
ZAPI_CLIENT_TOKEN = os.getenv("ZAPI_CLIENT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

API_BASE = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_TOKEN}"
HEADERS = {"Client-Token": ZAPI_CLIENT_TOKEN}
openai.api_key = OPENAI_API_KEY
GITHUB_HEADERS = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
GITHUB_REPO = "kelissonvidal/agente-whatsapp"
DEMANDAS_PATH = "data/demandas.txt"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DEMANDAS_PATH}"

# Sessões de atendimento
SESSOES = {}

# Blocos de texto para fechamento da venda
BLOCOS_FECHAMENTO = [
    "Maravilha! Parabéns pela decisão de transformar de vez um problema capilar em cabelos lindos, saudáveis e fortes.",
    "Agora vou embalar seu Caplux e despachar via correios e volto aqui para te informar o código de rastreio.",
    "Me informe por favor esses dados abaixo:\n- Nome completo.\n- CPF para emitir o boleto.\n- Bairro, Rua e número.\n- Cidade, Estado e Cep.",
    "Obrigado pela confiança."
]

def enviar_mensagem(telefone, mensagem):
    payload = {"phone": telefone, "message": mensagem}
    requests.post(f"{API_BASE}/send-text", headers=HEADERS, json=payload)

def enviar_audio(telefone, nome_arquivo):
    url = f"https://raw.githubusercontent.com/kelissonvidal/agente-whatsapp/main/data/{nome_arquivo}"
    payload = {"phone": telefone, "audio": url}
    requests.post(f"{API_BASE}/send-audio", headers=HEADERS, json=payload)

def enviar_blocos_finais(telefone):
    for bloco in BLOCOS_FECHAMENTO:
        time.sleep(4)
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
    prompt = (
        f"Cliente disse: \"{mensagem}\".\n"
        "Responda de forma educada e mantenha o contexto sobre o suplemento Caplux para queda de cabelo. "
        "Se for uma pergunta fora do assunto, esclareça brevemente e retorne o cliente para o fluxo de atendimento. "
        "Se for uma resposta adequada para a etapa atual, apenas avance normalmente."
    )
    if nome:
        prompt += f" Use o nome {nome} de forma natural na conversa."
    
    try:
        resposta = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return resposta.choices[0].message.content.strip()
    except Exception as e:
        print("[OpenAI] Erro ao gerar resposta IA:", e)
        return "Desculpe, estou com dificuldade para interpretar sua resposta agora."

def registrar_demanda(telefone, mensagem):
    try:
        dt = datetime.now().strftime("%d/%m/%Y %H:%M")
        entrada = f"🕓 {dt}\n📞 Cliente: {telefone}\n💬 Pergunta: {mensagem}\n⚠️ Status: Fora do escopo\n---\n"
        atual = requests.get(GITHUB_API_URL, headers=GITHUB_HEADERS).json()
        conteudo = b64decode(atual["content"]).decode() + entrada
        novo = b64encode(conteudo.encode()).decode()
        update_payload = {"message": f"Demanda {telefone}", "content": novo, "sha": atual["sha"]}
        requests.put(GITHUB_API_URL, headers=GITHUB_HEADERS, json=update_payload)
    except Exception as e:
        print("[GitHub] Falha ao registrar demanda:", e)
def enviar_fluxo_automatico(telefone, permite_audio):
    try:
        for etapa_auto in [6, 7, 8]:
            if permite_audio:
                enviar_audio(telefone, f"audio_{etapa_auto}.ogg")
            else:
                enviar_mensagem(telefone, get_texto_alternativo(etapa_auto))
            time.sleep(8)

        # Após o áudio 8, envia o áudio 9
        if permite_audio:
            enviar_audio(telefone, "audio_9.ogg")
        else:
            enviar_mensagem(telefone, get_texto_alternativo(9))

        # Após o áudio 9, envia os blocos de fechamento
        enviar_blocos_finais(telefone)

    except Exception as e:
        print("[Fluxo Automático] Erro:", e)

def get_texto_alternativo(etapa):
    textos = {
        1: "Gostaria de saber sua idade, por favor?",
        2: "Você já fez algum tratamento específico para o cabelo?",
        3: "Há quanto tempo você percebe essas mudanças no seu cabelo?",
        4: "Você costuma se alimentar bem e com regularidade?",
        5: "Você está pronto para começar sua transformação capilar agora mesmo?",
        6: "O Caplux é formulado com nutrientes potentes que vão revitalizar seu couro cabeludo.",
        7: "Clientes relatam resultados surpreendentes em poucas semanas.",
        8: "Você estará dando o primeiro passo para recuperar sua autoestima!",
        9: "Para finalizarmos, preciso confirmar seus dados de envio."
    }
    return textos.get(etapa, "(Mensagem não encontrada)")
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    if data.get("type") != "ReceivedCallback" or data.get("fromMe"):
        return jsonify({"status": "ignorado"})

    telefone = data.get("phone")
    mensagem = data.get("text", {}).get("message", "").strip()
    audio = data.get("audio", {}).get("audioUrl")

    # Se não existe sessão ou finalizou, recomeça
    if telefone not in SESSOES or SESSOES[telefone].get("estado") == "finalizado":
        SESSOES[telefone] = {"estado": "inicio", "nome": None, "permite_audio": None, "etapa": 1}
        enviar_mensagem(telefone, "Olá! Seja muito bem-vindo. Qual é o seu nome, por favor?")
        SESSOES[telefone]["estado"] = "aguardando_nome"
        return jsonify({"status": "fluxo_iniciado"})

    sessao = SESSOES[telefone]
    estado = sessao["estado"]

    if estado == "aguardando_nome" and mensagem:
        sessao["nome"] = mensagem.split()[0].capitalize()
        enviar_mensagem(telefone, f"Obrigado, {sessao['nome']}! Você prefere que eu responda só por texto ou também posso enviar áudios?")
        sessao["estado"] = "aguardando_preferencia"
        return jsonify({"status": "perguntou_preferencia"})

    if estado == "aguardando_preferencia" and mensagem:
        sessao["permite_audio"] = not ("texto" in mensagem.lower() and "áudio" not in mensagem.lower())
        sessao["estado"] = "etapa_funil"
        etapa = sessao["etapa"]
        if sessao["permite_audio"]:
            enviar_audio(telefone, f"audio_{etapa}.ogg")
        else:
            enviar_mensagem(telefone, get_texto_alternativo(etapa))
        sessao["estado"] = f"aguardando_resposta_{etapa}"
        return jsonify({"status": f"enviou_audio_{etapa}"})

    for etapa in range(1, 6):
        if estado == f"aguardando_resposta_{etapa}":
            resposta_cliente = mensagem if mensagem else None
            if audio:
                resposta_cliente = transcrever_audio(audio)

            if resposta_cliente:
                # Verificar se resposta é coerente (implementação pode ser melhorada depois)
                sessao["etapa"] += 1
                proxima = sessao["etapa"]
                if proxima <= 5:
                    if sessao["permite_audio"]:
                        enviar_audio(telefone, f"audio_{proxima}.ogg")
                    else:
                        enviar_mensagem(telefone, get_texto_alternativo(proxima))
                    sessao["estado"] = f"aguardando_resposta_{proxima}"
                elif proxima == 6:
                    # Inicia o envio automático dos áudios 6,7,8,9
                    threading.Thread(target=enviar_fluxo_automatico, args=(telefone, sessao["permite_audio"])).start()
                    sessao["estado"] = "aguardando_resposta_9"
                return jsonify({"status": f"etapa_{etapa}_respondida"})

    if estado == "aguardando_resposta_9":
        resposta_cliente = mensagem if mensagem else None
        if audio:
            resposta_cliente = transcrever_audio(audio)

        if resposta_cliente:
            enviar_mensagem(telefone, "Perfeito, pedido confirmado! Obrigado pela confiança. 🚀")
            sessao["estado"] = "finalizado"
            return jsonify({"status": "fechamento_finalizado"})

    if mensagem:
        resposta = gerar_resposta_ia(mensagem, sessao.get("nome"))
        enviar_mensagem(telefone, resposta)
        registrar_demanda(telefone, mensagem)
        return jsonify({"status": "fallback_texto"})

    if audio:
        texto = transcrever_audio(audio)
        if texto:
            resposta = gerar_resposta_ia(texto, sessao.get("nome"))
            enviar_mensagem(telefone, resposta)
            registrar_demanda(telefone, texto)
        return jsonify({"status": "fallback_audio"})

    return jsonify({"status": "sem_acao"})
