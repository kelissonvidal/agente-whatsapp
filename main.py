# Código base corrigido com lógica de avanço e suporte para texto.

# Trecho principal corrigido (trechos substituíveis)

if etapa in [3, 4, 5, 6, 7]:
    if not sessao["aguardando_resposta"]:
        if sessao["permite_audio"]:
            enviar_audio(telefone, f"audio_{etapa - 1}.ogg")
        else:
            enviar_mensagem(telefone, f"(Texto alternativo ao áudio {etapa - 1})")
        sessao["aguardando_resposta"] = True
        return jsonify({"status": f"etapa_{etapa}_pergunta_enviada"})
    else:
        # Cliente respondeu (texto ou áudio), avançar
        avancar()
        return jsonify({"status": f"etapa_{etapa}_resposta_recebida"})

if mensagem_texto:
    if sessao["aguardando_resposta"] and etapa in [3, 4, 5, 6, 7]:
        avancar()
        return jsonify({"status": "etapa_avancada_com_texto"})
    resposta = gerar_resposta_ia(mensagem_texto, sessao.get("nome"))
    enviar_mensagem(telefone, resposta)
    registrar_demanda(telefone, mensagem_texto)
    return jsonify({"status": "fallback_resposta_texto"})

if audio_info and audio_info.get("audioUrl"):
    url_audio = audio_info["audioUrl"]
    transcricao = transcrever_audio(url_audio)
    if transcricao:
        if sessao["aguardando_resposta"] and etapa in [3, 4, 5, 6, 7]:
            avancar()
            return jsonify({"status": "etapa_avancada_com_audio"})
        resposta = gerar_resposta_ia(transcricao, sessao.get("nome"))
        enviar_mensagem(telefone, resposta)
        registrar_demanda(telefone, transcricao)
    return jsonify({"status": "fallback_resposta_audio"})
