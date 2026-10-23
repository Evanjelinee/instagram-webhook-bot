
import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

VERIFY_TOKEN = os.environ.get(
    "WEBHOOK_VERIFY_TOKEN",
    "dev-verify-token"
)
ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN")

IG_USER_ID = "17841431299134110"
CODE_WORD = "курс"


# Проверка Webhook от Meta
@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("Webhook verified!")
        return challenge, 200

    return "Forbidden", 403


# Получение событий Instagram
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True)

    print("\n=== ПОЛУЧЕНЫ ДАННЫЕ ОТ META ===")
    print(data)
    print("================================\n")

    if not data:
        return jsonify({"status": "no data"}), 200

    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") != "comments":
                continue

            value = change.get("value", {})
            comment = value.get("comment", {})

            comment_text = comment.get("text", "")
            comment_id = comment.get("id", "")
            from_user = comment.get("from", {})
            user_id = from_user.get("id", "")

            print("Комментарий:", comment_text)
            print("ID комментария:", comment_id)
            print("ID пользователя:", user_id)

            if CODE_WORD.lower() in comment_text.lower():
                print(f"Найдено кодовое слово: {CODE_WORD}")

                # Отправка DM и ответ на комментарий
                # пока не включены — сначала проверим получение событий

    return jsonify({"status": "received"}), 200


# Политика конфиденциальности
@app.route("/privacy", methods=["GET"])
def privacy():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head><meta charset="UTF-8"><title>Privacy Policy</title></head>
    <body>
        <h1>Privacy Policy — Curso Bot</h1>
        <p>Curso Bot processes Instagram usernames, user IDs,
        comment text and comment IDs to operate automated replies.</p>
        <p>Data is used to operate the bot and is not sold.
        Webhook logs may temporarily contain event data.</p>
        <p>For privacy questions, contact: evapolkaad@gmail.com</p>
    </body>
    </html>
    """


# Инструкция по удалению данных
@app.route("/data-deletion", methods=["GET"])
def data_deletion():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head><meta charset="UTF-8"><title>Data Deletion</title></head>
    <body>
        <h1>Data Deletion — Curso Bot</h1>
        <p>To request deletion of data associated with Curso Bot,
        email evapolkaad@gmail.com and include your Instagram username.</p>
        <p>We will review the request and delete data under our control,
        unless retention is legally required.</p>
    </body>
    </html>
    """


# Главная страница для проверки работы сервиса
@app.route("/", methods=["GET"])
def home():
    return "Curso Bot is running!", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
