import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

VERIFY_TOKEN = os.environ.get('WEBHOOK_VERIFY_TOKEN', 'dev-verify-token')
ACCESS_TOKEN = os.environ.get('INSTAGRAM_ACCESS_TOKEN')
IG_USER_ID = '17841431299134110'
CODE_WORD = 'курс'

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    if mode == 'subscribe' and token == VERIFY_TOKEN:
        print(f"Webhook verified! Challenge: {challenge}")
        return challenge, 200
    return 'Forbidden', 403

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print(f"\n{'='*50}")
    print(f"ПОЛУЧЕНЫ ДАННЫЕ ОТ META:")
    print(f"{'='*50}")
    print(f"Весь запрос: {data}")
    print(f"{'='*50}\n")
    
    if not data:
        return jsonify({'status': 'no data'}), 200
    
    # Обрабатываем комментарии
    if 'entry' in data:
        for entry in data['entry']:
            print(f"Entry: {entry}")
            
            if 'changes' in entry:
                for change in entry['changes']:
                    print(f"Change: {change}")
                    print(f"Field: {change.get('field')}")
                    
                    if change.get('field') == 'comments':
                        value = change.get('value', {})
                        print(f"Comment value: {value}")
                        
                        # Проверяем разные форматы данных
                        if 'comment' in value:
                            comment_text = value['comment'].get('text', '')
                            comment_id = value['comment'].get('id', '')
                            from_user = value['comment'].get('from', {})
                            user_id = from_user.get('id', '')
                            
                            print(f"\nКОММЕНТАРИЙ НАЙДЕН!")
                            print(f"Текст: {comment_text}")
                            print(f"ID: {comment_id}")
                            print(f"Пользователь: {user_id}\n")
                            
                            if CODE_WORD.lower() in comment_text.lower():
                                print(f"Кодовое слово '{CODE_WORD}' найдено! Отправляю ответ...")
                                # send_dm(user_id, "Привет! Спасибо за интерес к курсу.")
                                # reply_to_comment(comment_id, "Ответила в директ 💌")
    
    return jsonify({'status': 'received'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
@app.route("/privacy")
def privacy():
    return """
    <h1>Privacy Policy — Curso Bot</h1>
    <p>Curso Bot processes Instagram usernames, user IDs, comment text
    and comment IDs to respond to comments and send requested messages.</p>
    <p>Data is used only to operate the bot and is not sold.
    Webhook logs may temporarily contain event data.</p>
    <p>For privacy questions or data deletion requests, contact:
    evapolkaad@gmail.com</p>
    """

@app.route("/data-deletion")
def data_deletion():
    return """
    <h1>Data Deletion — Curso Bot</h1>
    <p>To request deletion of data associated with Curso Bot,
    email evapolkaad@gmail.com and include your Instagram username.</p>
    <p>We will review the request and delete data under our control
    unless retention is legally required.</p>
    """
