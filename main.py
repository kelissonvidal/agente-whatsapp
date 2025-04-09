
import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()

    # Verifica se é a primeira mensagem do cliente
    user_message = data.get('text', {}).get('body', '').lower()
    sender = data.get('from')

    if user_message in ['oi', 'olá', 'bom dia', 'boa tarde', 'boa noite']:
        try:
            audio_path = './data/boas_vindas.ogg'
            if not os.path.exists(audio_path):
                print('[ERRO] Arquivo de áudio não encontrado.')
                return jsonify({'status': 'erro', 'motivo': 'áudio não encontrado'}), 500

            with open(audio_path, 'rb') as audio:
                response = requests.post(
                    url='https://api.z-api.io/instances/YOUR_INSTANCE_ID/token/YOUR_TOKEN/send-audio',
                    files={'audio': ('boas_vindas.ogg', audio, 'audio/ogg')},
                    data={'phone': sender}
                )

            print(f"[INFO] Enviado áudio de boas-vindas para {sender}")
            return jsonify({'status': 'enviado'}), 200

        except Exception as e:
            print(f"[ERRO] Falha ao enviar áudio: {e}")
            return jsonify({'status': 'erro', 'motivo': str(e)}), 500

    return jsonify({'status': 'ignorado'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
