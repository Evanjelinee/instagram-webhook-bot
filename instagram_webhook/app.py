import os
import json
import random
import urllib.request
import urllib.error
from threading import Lock
from flask import Flask, request, jsonify

app = Flask(__name__)
VERIFY_TOKEN = os.environ.get('WEBHOOK_VERIFY_TOKEN', 'dev-verify-token')
ACCESS_TOKEN = os.environ.get('INSTAGRAM_ACCESS_TOKEN')
IG_USER_ID = '17841431299134110'
NEW_LINK = 'https://t.me/espano_A1/34'
KEYWORDS = {'испанский', 'español', 'espanol', 'ссылка'}
CONFIRMATIONS = {'подписалась', 'подписался', 'готово'}

LINK_INTRO = (
    'Приветствую! 💌\n\n'
    'Я подготовила материалы для самостоятельного изучения испанского языка — от самых основ до продвинутого уровня. 📚\n\n'
    '🇪🇸 Что тебя ждёт:\n'
    '📖 Авторские пособия по испанскому языку\n'
    '🎓 Бесплатный 7-дневный курс для начинающих\n'
    '🧠 Интерактивные карточки для изучения и запоминания слов\n\n'
    '💗 Всё это доступно на моём сайте!\n\n'
    'Чтобы получить ссылку, подпишись на @evangel1na_b и напиши в ответ «Готово», «Подписалась» или «Подписался». 💌'
)
UNKNOWN_REPLY = (
    'Кажется, мы немного запутались\n\n'
    'Чтобы получить доступ к материалам, подпишись на мой аккаунт @evangel1na_b 🇪🇸\n\n'
    'После подписки просто напиши «Готово», «Подписалась» или «Подписался» — '
    'я проверю подписку и сразу отправлю ссылку! 💌'
)
LINK_SUCCESS = f'Спасибо за подписку! 💗\n\nВот обещанная ссылка:\n{NEW_LINK}\n\n¡Nos vemos! 🇪🇸'
LINK_NOT_FOLLOWING = 'Пока не вижу подтверждённой подписки 💗 Подпишись на @evangel1na_b и снова напиши «Готово», «Подписалась» или «Подписался».'
LINK_CHECK_UNAVAILABLE = 'Пока не получилось проверить подписку 🥹 Попробуй написать «Готово», «Подписалась» или «Подписался» немного позже 💗'
COMMENT_REPLIES = [
    'Написала тебе в Direct 💌', 'Уже отправила тебе сообщение 💗',
    'Проверь Direct ✨', 'Лови сообщение в Direct 💌',
    'Загляни в Direct 💗', 'Отправила тебе всё в личку 🫶',
    'Ответила тебе в Direct ✨',
]
FALLBACK_REPLIES = [
    'Не получилось написать тебе 💌 Напиши мне в Direct «Español» 💗',
    'Твой Direct не принял сообщение 🥹 Напиши мне «Español» в личку 💌',
    'Не смогла отправить ссылку 💗 Напиши мне в Direct слово «Español»',
]
# Temporary in-memory state: lost on restart and not shared across workers.
# For reliable production behavior, replace with persistent storage (e.g. PostgreSQL).
pending_users = set()
reminded_users = set()
processed_comments = set()
processed_messages = set()
state_lock = Lock()


def api_request(path, payload):
    if not ACCESS_TOKEN:
        raise RuntimeError('Не задан INSTAGRAM_ACCESS_TOKEN')
    url = f'https://graph.instagram.com/v26.0/{path}'
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode('utf-8'),
        headers={'Authorization': f'Bearer {ACCESS_TOKEN}', 'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        content = response.read().decode('utf-8')
        return json.loads(content) if content else {}


def get_follow_status(user_id):
    """Returns True/False if Meta explicitly reports status; None if unavailable."""
    if not ACCESS_TOKEN:
        return None
    from urllib.parse import urlencode
    query = urlencode({'fields': 'is_user_follow_business', 'access_token': ACCESS_TOKEN})
    url = f'https://graph.instagram.com/v26.0/{user_id}?{query}'
    try:
        req = urllib.request.Request(url, method='GET')
        with urllib.request.urlopen(req, timeout=20) as response:
            data = json.loads(response.read().decode('utf-8'))
        status = data.get('is_user_follow_business')
        return status if isinstance(status, bool) else None
    except (urllib.error.HTTPError, urllib.error.URLError, ValueError) as error:
        print(f'Не удалось проверить подписку: {error}', flush=True)
        return None


def send_direct(user_id, text):
    return api_request(f'{IG_USER_ID}/messages', {
        'recipient': {'id': str(user_id)}, 'message': {'text': text},
    })


def reply_to_comment(comment_id, text):
    return api_request(f'{comment_id}/replies', {'message': text})


def handle_comment(value):
    comment_text = (value.get('text') or '').strip().casefold()
    comment_id = value.get('id')
    author_id = (value.get('from') or {}).get('id')
    if not comment_id or not author_id or str(author_id) == IG_USER_ID:
        return
    if comment_text not in KEYWORDS:
        return
    with state_lock:
        if comment_id in processed_comments:
            return
    message_text = LINK_INTRO
    try:
        api_request(f'{IG_USER_ID}/messages', {
            'recipient': {'comment_id': str(comment_id)},
            'message': {'text': message_text},
        })
    except Exception as error:
        print(f'Не удалось отправить Direct: {error}', flush=True)
        fallback = random.choice(FALLBACK_REPLIES)
        try:
            reply_to_comment(comment_id, fallback)
            with state_lock:
                processed_comments.add(comment_id)
        except Exception as reply_error:
            print(f'Ошибка запасного ответа: {reply_error}', flush=True)
        return
    # Meta may use different scoped IDs for comments and Direct.
    # A confirmation can only be matched when the IDs correspond.
    with state_lock:
        pending_users.add(str(author_id))
        reminded_users.discard(str(author_id))
    try:
        reply_to_comment(comment_id, random.choice(COMMENT_REPLIES))
    except Exception as error:
        print(f'Ошибка публичного ответа: {error}', flush=True)
    with state_lock:
        processed_comments.add(comment_id)
    print(f'Обработан комментарий {comment_id}', flush=True)


def handle_message(event):
    sender_id = (event.get('sender') or {}).get('id')
    message = event.get('message') or {}
    if not sender_id or str(sender_id) == IG_USER_ID or message.get('is_echo'):
        return
    text = (message.get('text') or '').strip().casefold()
    message_id = message.get('mid')
    with state_lock:
        if message_id and message_id in processed_messages:
            return
        pending = str(sender_id) in pending_users
    if text in KEYWORDS:
        send_direct(sender_id, LINK_INTRO)
        with state_lock:
            pending_users.add(str(sender_id))
            reminded_users.discard(str(sender_id))
    elif text in CONFIRMATIONS and pending:
        with state_lock:
            reminded_users.discard(str(sender_id))
        follow_status = get_follow_status(sender_id)
        if follow_status is True:
            send_direct(sender_id, LINK_SUCCESS)
            with state_lock:
                pending_users.discard(str(sender_id))
                reminded_users.discard(str(sender_id))
        elif follow_status is False:
            send_direct(sender_id, LINK_NOT_FOLLOWING)
        else:
            send_direct(sender_id, LINK_CHECK_UNAVAILABLE)
    elif pending and text:
        with state_lock:
            already_reminded = str(sender_id) in reminded_users
        if already_reminded:
            return
        send_direct(sender_id, UNKNOWN_REPLY)
        with state_lock:
            reminded_users.add(str(sender_id))
    else:
        return
    if message_id:
        with state_lock:
            processed_messages.add(message_id)
    print(f'Обработано сообщение от {sender_id}', flush=True)


@app.route('/webhook', methods=['GET'])
def verify_webhook():
    if request.args.get('hub.mode') == 'subscribe' and request.args.get('hub.verify_token') == VERIFY_TOKEN:
        return request.args.get('hub.challenge') or '', 200
    return 'Forbidden', 403


@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(silent=True) or {}
    for entry in data.get('entry', []):
        for change in entry.get('changes', []):
            if change.get('field') == 'comments':
                try:
                    handle_comment(change.get('value') or {})
                except Exception as error:
                    print(f'Ошибка обработки комментария: {error}', flush=True)
        for event in entry.get('messaging', []):
            try:
                handle_message(event)
            except Exception as error:
                print(f'Ошибка обработки Direct: {error}', flush=True)
    return jsonify({'status': 'received'}), 200


@app.route('/privacy', methods=['GET'])
def privacy():
    return '''<h1>Privacy Policy — Curso Bot</h1><p>Processes Instagram usernames, IDs and comments
    to operate automated replies. Data is not sold.</p><p>Contact: evapolkaad@gmail.com</p>'''


@app.route('/data-deletion', methods=['GET'])
def data_deletion():
    return '''<h1>Data Deletion — Curso Bot</h1><p>To request deletion of data, email evapolkaad@gmail.com
    and include your Instagram username.</p>'''


@app.route('/', methods=['GET'])
def home():
    return 'Curso Bot is running!', 200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
