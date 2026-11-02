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

# Сообщение, которое сразу приходит человеку в Direct
DM_MESSAGE = (
    "Привет! 💌 Спасибо за интерес к испанскому 🇪🇸\n\n"
    "Вот ссылка на ресурс:\n"
    f"{TELEGRAM_URL}\n\n"
    "Надеюсь, будет полезно 💗"
)

# Бот будет случайно выбирать один из этих ответов
COMMENT_REPLIES = [
    "Написала тебе в Direct 💌",
    "Уже отправила тебе сообщение 💗",
    "Проверь Direct ✨",
    "Лови сообщение в Direct 💌",
    "Загляни в Direct 💗",
    "Отправила тебе всё в личку 🫶",
    "Сообщение уже у тебя в Direct 💌",
    "Ответила тебе в Direct ✨",
]

# Защита от повторной обработки одного комментария
processed_comments = set()


def api_request(path, payload=None):
    if not ACCESS_TOKEN:
        raise RuntimeError("Не задан INSTAGRAM_ACCESS_TOKEN")

    url = f"https://graph.instagram.com/v26.0/{path}"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    if payload is not None:
        body = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=body,
            headers=headers,
            method="POST",
        )
    else:
        req = urllib.request.Request(
            url,
            headers=headers,
            method="GET",
        )

    with urllib.request.urlopen(req, timeout=20) as response:
        result = response.read().decode("utf-8")
        return json.loads(result) if result else {}


def handle_comment(value):
    comment_text = (value.get("text") or "").strip()
    comment_id = value.get("id")
    author_id = (value.get("from") or {}).get("id")

    if not comment_id or not author_id:
        return

    # Не отвечаем сами себе
    if str(author_id) == IG_USER_ID:
        return

    # Кодовое слово
    if comment_text.casefold() != "espanol":
        return

    # Не обрабатываем один комментарий несколько раз
    if comment_id in processed_comments:
        return

    # 1. Сразу отправляем сообщение в Direct
    api_request(
        f"{IG_USER_ID}/messages",
        {
            "recipient": {
                "comment_id": str(comment_id)
            },
            "message": {
                "text": DM_MESSAGE
            },
        },
    )

    # 2. Оставляем случайный публичный ответ под комментарием
    try:
        random_reply = random.choice(COMMENT_REPLIES)

        api_request(
            f"{comment_id}/replies",
            {
                "message": random_reply
            },
        )

    except Exception as error:
        print(
            f"Ошибка публичного ответа: {error}",
            flush=True,
        )

    processed_comments.add(comment_id)

    print(
        f"Успешно обработан комментарий {comment_id}",
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

    try:
        for entry in data.get("entry", []):

            for change in entry.get("changes", []):

                if change.get("field") != "comments":
                    continue

                try:
                    handle_comment(
                        change.get("value") or {}
                    )

                except urllib.error.HTTPError as error:
                    details = error.read().decode(
                        "utf-8",
                        errors="replace",
                    )

                    print(
                        f"Ошибка Meta API: "
                        f"HTTP {error.code}: {details}",
                        flush=True,
                    )

                except Exception as error:
                    print(
                        f"Ошибка комментария: {error}",
                        flush=True,
                    )

    except Exception as error:
        print(
            f"Ошибка webhook: {error}",
            flush=True,
        )

    return jsonify({"status": "received"}), 200


@app.route("/privacy", methods=["GET"])
def privacy():
    return """
    <h1>Privacy Policy — Curso Bot</h1>
    <p>
    Processes Instagram usernames, IDs and comments
    to operate automated replies.
    Data is not sold.
    </p>
    <p>Contact: evapolkaad@gmail.com</p>
    """


@app.route("/data-deletion", methods=["GET"])
def data_deletion():
    return """
    <h1>Data Deletion — Curso Bot</h1>
    <p>
    To request deletion of data,
    email evapolkaad@gmail.com
    and include your Instagram username.
    </p>
    """


@app.route("/", methods=["GET"])
def home():
    return "Curso Bot is running!", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
    )
