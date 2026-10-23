
import os
from flask import Flask, request, jsonify

app = Flask(__name__)

VERIFY_TOKEN = os.environ.get("WEBHOOK_VERIFY_TOKEN", "dev-verify-token")
ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN")

IG_USER_ID = "17841431299134110"
CODE_WORD = "курс"


@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("Webhook verified!")
        return challenge, 200

    return "Forbidden", 403


@app.route("/webhook", methods=["POST"])
def webhook():
    raw_data = request.get_data(as_text=True)
    data = request.get_json(silent=True)

    print("=== WEBHOOK JSON ===")
    print(data)
    print("=== WEBHOOK RAW ===")
    print(raw_data)
    print("====================")

    return jsonify({"status": "received"}), 200


@app.route("/privacy", methods=["GET"])
def privacy():
    return """
    <!DOCTYPE html>
    <html lang="ru">
    <head><meta charset="UTF-8"><title>Privacy Policy</title></head>
    <body>
        <h1>Privacy Policy — Curso Bot</h1>
        <p>Curso Bot processes Instagram usernames, user IDs,
        comment text and comment IDs to operate automated replies.</p>
        <p>Data is used to operate the bot and is not sold.</p>
        <p>For privacy questions, contact: evapolkaad@gmail.com</p>
    </body>
    </html>
    """


@app.route("/data-deletion", methods=["GET"])
def data_deletion():
    return """
    <!DOCTYPE html>
    <html lang="ru">
    <head><meta charset="UTF-8"><title>Data Deletion</title></head>
    <body>
        <h1>Data Deletion — Curso Bot</h1>
        <p>To request deletion of data associated with Curso Bot,
        email evapolkaad@gmail.com and include your Instagram username.</p>
    </body>
    </html>
    """


@app.route("/", methods=["GET"])
def home():
    return "Curso Bot is running!", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
