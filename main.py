
# main.py atualizado com controle estável de avanço de etapas.
# Trecho corrigido: resposta por texto ou áudio avança apenas se etapa aguarda resposta

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
