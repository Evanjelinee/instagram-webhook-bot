import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Переменные окружения
VERIFY_TOKEN = os.environ.get('META_VERIFY_TOKEN', 'my-secret-token-123')
ACCESS_TOKEN = os.environ.get('INSTAGRAM_ACCESS_TOKEN')
IG_USER_ID = '17841431299134110'  # Твой Instagram ID
CODE_WORD = 'курс'  # Кодовое слово для активации
DM_MESSAGE = 'Привет! Спасибо за интерес к курсу. Вот ссылка: [твоя ссылка]'
REPLY_COMMENT = 'Ответила в директ '

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    if mode == 'subscribe' and token == VERIFY_TOKEN:
        return challenge, 200
    return 'Forbidden', 403

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    
    if not data:
        return jsonify({'status': 'no data'}), 200
    
    # Обрабатываем комментарии
    if 'entry' in data:
        for entry in data['entry']:
            if 'messaging' in entry:
                for event in entry['messaging']:
                    if 'message' in event:
                        # Получили сообщение в директ
                        print(f"Message: {event['message']}")
            
            if 'changes' in entry:
                for change in entry['changes']:
                    if change.get('field') == 'comments':
                        comment_data = change.get('value', {})
                        comment = comment_data.get('object', {}).get('comment', '')
                        comment_id = comment_data.get('object', {}).get('id', '')
                        from_user = comment_data.get('from', {})
                        user_id = from_user.get('id', '')
                        
                        print(f"Comment: {comment}")
                        
                        # Проверяем кодовое слово
                        if CODE_WORD.lower() in comment.lower():
                            # Отправляем в директ
                            send_dm(user_id, DM_MESSAGE)
                            # Отвечаем в комментариях
                            reply_to_comment(comment_id, REPLY_COMMENT)
    
    return jsonify({'status': 'received'}), 200

def send_dm(user_id, message):
    """Отправка сообщения в директ"""
    url = f'https://graph.instagram.com/v18.0/{IG_USER_ID}/messages'
    payload = {
        'recipient': {'id': user_id},
        'message': {'text': message},
        'access_token': ACCESS_TOKEN
    }
    try:
        response = requests.post(url, json=payload)
        print(f"DM sent: {response.status_code}")
    except Exception as e:
        print(f"Error sending DM: {e}")

def reply_to_comment(comment_id, message):
    """Ответ на комментарий"""
    url = f'https://graph.instagram.com/v18.0/{comment_id}/replies'
    payload = {
        'message': message,
        'access_token': ACCESS_TOKEN
    }
    try:
        response = requests.post(url, json=payload)
        print(f"Reply sent: {response.status_code}")
    except Exception as e:
        print(f"Error replying: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
