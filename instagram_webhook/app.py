
import os
import json
import urllib.request
import urllib.error
from flask import Flask, request, jsonify

app = Flask(__name__)

VERIFY_TOKEN = os.environ.get("WEBHOOK_VERIFY_TOKEN", "dev-verify-token")
ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
IG_USER_ID = "17841431299134110"

# Можно изменить текст сообщения
DM_MESSAGE = (
    "¡Hola! 💌 Gracias por tu interés en mi curso de español. "
    "Aquí puedes conocer los cursos y sus precios: https://t.me/espano_A1"
)
COMMENT_REPLY = "Написала тебе в Direct 💌"

# Защита от повторной обработки в пределах работы приложения
processed_comments = set()


def api_post(path, payload):
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
        return json.loads(response.read().decode("utf-8"))


@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200

    return "Forbidden", 403


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True) or {}

    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") != "comments":
                continue

            value = change.get("value", {})
            comment_text = (value.get("text") or "").strip()
            comment_id = value.get("id")
            author_id = (value.get("from") or {}).get("id")

            if not comment_id or not author_id:
                continue

            # Не отвечаем на собственные комментарии
            if str(author_id) == IG_USER_ID:
                continue

            # Срабатывает на «Курс», «курс», «КУРС»
            if comment_text.casefold() != "курс":
                continue

            if comment_id in processed_comments:
                continue

            try:
                # Личный ответ именно на комментарий
                api_post(
                    f"{IG_USER_ID}/messages",
                    {
                        "recipient": {"comment_id": comment_id},
                        "message": {"text": DM_MESSAGE},
                    },
                )

                # Публичный ответ под комментарием
                api_post(
                    f"{comment_id}/replies",
                    {"message": COMMENT_REPLY},
                )

                processed_comments.add(comment_id)
                print(f"Успешно обработан комментарий {comment_id}", flush=True)

            except urllib.error.HTTPError as error:
                details = error.read().decode("utf-8", errors="replace")
                print(
                    f"Ошибка Meta API: HTTP {error.code}: {details}",
                    flush=True,
                )
            except Exception as error:
                print(f"Ошибка обработки: {error}", flush=True)

    return jsonify({"status": "received"}), 200


@app.route("/privacy", methods=["GET"])
def privacy():
    return """
    <h1>Privacy Policy — Curso Bot</h1>
    <p>Processes Instagram usernames, IDs and comments to operate
    automated replies. Data is not sold.</p>
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
