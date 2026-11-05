
import os
import json
import random
import urllib.request
import urllib.error
from flask import Flask, request, jsonify

app = Flask(__name__)

VERIFY_TOKEN = os.environ.get("WEBHOOK_VERIFY_TOKEN", "dev-verify-token")
ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
IG_USER_ID = "17841431299134110"

TELEGRAM_URL = "https://t.me/espano_A1"

# Кодовые слова для комментариев и Direct
KEYWORDS = {"испанский", "español", "espanol"}

DM_MESSAGE = (
    "Привет! 💌 Спасибо за интерес к испанскому 🇪🇸\n\n"
    "Вот ссылка на ресурс:\n"
    f"{TELEGRAM_URL}\n\n"
    "Надеюсь, будет полезно 💗"
)

COMMENT_REPLIES = [
    "Написала тебе в Direct 💌",
    "Уже отправила тебе сообщение 💗",
    "Проверь Direct ✨",
    "Лови сообщение в Direct 💌",
    "Загляни в Direct 💗",
    "Отправила тебе всё в личку 🫶",
    "Ответила тебе в Direct ✨",
]

FALLBACK_REPLIES = [
    "Не получилось написать тебе 💌 Напиши мне в Direct «Español» 💗",
    "Твой Direct не принял сообщение 🥹 Напиши мне «Español» в личку 💌",
    "Не смогла отправить ссылку 💗 Напиши мне в Direct слово «Español»",
]

processed_comments = set()
processed_messages = set()


def api_request(path, payload):
    if not ACCESS_TOKEN:
        raise RuntimeError("Не задан INSTAGRAM_ACCESS_TOKEN")

    url = f"https://graph.instagram.com/v26.0/{path}"

    body = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=20) as response:
        result = response.read().decode("utf-8")
        return json.loads(result) if result else {}


def send_direct(user_id):
    return api_request(
        f"{IG_USER_ID}/messages",
        {
            "recipient": {"id": str(user_id)},
            "message": {"text": DM_MESSAGE},
        },
    )


def reply_to_comment(comment_id, text):
    return api_request(
        f"{comment_id}/replies",
        {"message": text},
    )


def handle_comment(value):
    comment_text = (value.get("text") or "").strip().casefold()
    comment_id = value.get("id")
    author_id = (value.get("from") or {}).get("id")

    if not comment_id or not author_id:
        return

    if str(author_id) == IG_USER_ID:
        return

    if comment_text not in KEYWORDS:
        return

    if comment_id in processed_comments:
        return

    # Сначала пытаемся отправить ссылку в Direct
    try:
        api_request(
            f"{IG_USER_ID}/messages",
            {
                "recipient": {"comment_id": str(comment_id)},
                "message": {"text": DM_MESSAGE},
            },
        )

    except Exception as error:
        print(
            f"Не удалось отправить Direct: {error}",
            flush=True,
        )

        # Если Direct не отправился — просим написать нам
        try:
            reply_to_comment(
                comment_id,
                random.choice(FALLBACK_REPLIES),
            )
            processed_comments.add(comment_id)

        except Exception as reply_error:
            print(
                f"Ошибка запасного ответа: {reply_error}",
                flush=True,
            )

        return

    # Если Direct отправился успешно
    try:
        reply_to_comment(
            comment_id,
            random.choice(COMMENT_REPLIES),
        )
    except Exception as error:
        print(
            f"Ошибка публичного ответа: {error}",
            flush=True,
        )

    processed_comments.add(comment_id)

    print(
        f"Обработан комментарий {comment_id}",
        flush=True,
    )


def handle_message(event):
    sender_id = (event.get("sender") or {}).get("id")
    message = event.get("message") or {}

    if not sender_id or str(sender_id) == IG_USER_ID:
        return

    # Не отвечаем на собственные исходящие сообщения
    if message.get("is_echo"):
        return

    text = (message.get("text") or "").strip().casefold()
    message_id = message.get("mid")

    if text not in KEYWORDS:
        return

    if message_id and message_id in processed_messages:
        return

    send_direct(sender_id)

    if message_id:
        processed_messages.add(message_id)

    print(
        f"Ссылка отправлена пользователю {sender_id}",
        flush=True,
    )


@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge or "", 200

    return "Forbidden", 403


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True) or {}

    for entry in data.get("entry", []):

        # Комментарии
        for change in entry.get("changes", []):
            if change.get("field") != "comments":
                continue

            try:
                handle_comment(change.get("value") or {})

            except Exception as error:
                print(
                    f"Ошибка обработки комментария: {error}",
                    flush=True,
                )

        # Входящие сообщения Direct
        for event in entry.get("messaging", []):
            try:
                handle_message(event)

            except Exception as error:
                print(
                    f"Ошибка обработки Direct: {error}",
                    flush=True,
                )

    return jsonify({"status": "received"}), 200


@app.route("/privacy", methods=["GET"])
def privacy():
    return """
    <h1>Privacy Policy — Curso Bot</h1>
    <p>Processes Instagram usernames, IDs and comments
    to operate automated replies. Data is not sold.</p>
    <p>Contact: evapolkaad@gmail.com</p>
    """


@app.route("/data-deletion", methods=["GET"])
def data_deletion():
    return """
    <h1>Data Deletion — Curso Bot</h1>
    <p>To request deletion of data, email evapolkaad@gmail.com
    and include your Instagram username.</p>
    """


@app.route("/", methods=["GET"])
def home():
    return "Curso Bot is running!", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
