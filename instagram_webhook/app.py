
import os
import json
import urllib.request
import urllib.error
import urllib.parse
from flask import Flask, request, jsonify

app = Flask(__name__)

VERIFY_TOKEN = os.environ.get("WEBHOOK_VERIFY_TOKEN", "dev-verify-token")
ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
IG_USER_ID = "17841431299134110"

INSTAGRAM_URL = "https://www.instagram.com/evangel1na_b/"
TELEGRAM_URL = "https://t.me/espano_A1"

START_MESSAGE = (
    "Привет! 💌 Чтобы получить курс, подпишись на наш Instagram: "
    + INSTAGRAM_URL
    + "\n\nЗатем ответь на это сообщение словом ПОДПИСАЛАСЬ/ПОДПИСАЛСЯ — "
    "я проверю подписку и пришлю ссылку на курс 💗"
)

COMMENT_REPLY = "Написала тебе в Direct 💌"

processed_comments = set()


def api_request(path, payload=None, params=None):
    if not ACCESS_TOKEN:
        raise RuntimeError("Не задан INSTAGRAM_ACCESS_TOKEN")

    url = f"https://graph.instagram.com/v26.0/{path}"

    if params:
        url += "?" + urllib.parse.urlencode(params)

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=body, headers=headers, method="POST"
        )
    else:
        req = urllib.request.Request(url, headers=headers, method="GET")

    with urllib.request.urlopen(req, timeout=20) as response:
        result = response.read().decode("utf-8")
        return json.loads(result) if result else {}


def send_dm(user_id, message):
    return api_request(
        f"{IG_USER_ID}/messages",
        {
            "recipient": {"id": str(user_id)},
            "message": {"text": message},
        },
    )


def check_follow(user_id):
    profile = api_request(
        str(user_id),
        params={
            "fields": "is_user_follow_business,username"
        },
    )

    return profile.get("is_user_follow_business")


def handle_comment(value):
    comment_text = (value.get("text") or "").strip()
    comment_id = value.get("id")
    author_id = (value.get("from") or {}).get("id")

    if not comment_id or not author_id:
        return

    if str(author_id) == IG_USER_ID:
        return

    if comment_text.casefold() != "espanol":
        return

    if comment_id in processed_comments:
        return

    api_request(
        f"{IG_USER_ID}/messages",
        {
            "recipient": {"comment_id": str(comment_id)},
            "message": {"text": START_MESSAGE},
        },
    )

    try:
        api_request(
            f"{comment_id}/replies",
            {"message": COMMENT_REPLY},
        )
    except Exception as error:
        print(f"Ошибка публичного ответа: {error}", flush=True)

    processed_comments.add(comment_id)
    print(f"Обработан комментарий {comment_id}", flush=True)


def handle_message(event):
    sender_id = (event.get("sender") or {}).get("id")
    message = event.get("message") or {}
    text = (message.get("text") or "").strip().casefold()

    if not sender_id or not text:
        return

    if str(sender_id) == IG_USER_ID:
        return

    if text not in ("подписалась", "подписался", "готово"):
        return

    try:
        is_following = check_follow(sender_id)

        if is_following is True:
            send_dm(
                sender_id,
                "Ура! 💗 Подписка подтверждена!\n\n"
                f"Вот ссылка на курс: {TELEGRAM_URL}",
            )
        elif is_following is False:
            send_dm(
                sender_id,
                "Пока не вижу подписку 😔\n"
                "Подпишись на @evangel1na_b и напиши "
                "«ПОДПИСАЛАСЬ» ещё раз 💌",
            )
        else:
            send_dm(
                sender_id,
                "Не получилось проверить подписку сейчас 😔 "
                "Попробуй немного позже.",
            )

    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        print(f"Ошибка проверки подписки: HTTP {error.code}: {details}",
              flush=True)
        try:
            send_dm(
                sender_id,
                "Не удалось проверить подписку сейчас 😔 "
                "Попробуй немного позже.",
            )
        except Exception as send_error:
            print(f"Ошибка отправки сообщения: {send_error}", flush=True)

    except Exception as error:
        print(f"Ошибка обработки сообщения: {error}", flush=True)


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
                if change.get("field") == "comments":
                    try:
                        handle_comment(change.get("value") or {})
                    except urllib.error.HTTPError as error:
                        details = error.read().decode(
                            "utf-8", errors="replace"
                        )
                        print(
                            f"Ошибка Meta API: HTTP {error.code}: {details}",
                            flush=True,
                        )
                    except Exception as error:
                        print(f"Ошибка комментария: {error}", flush=True)

            for event in entry.get("messaging", []):
                try:
                    handle_message(event)
                except Exception as error:
                    print(f"Ошибка Direct: {error}", flush=True)

    except Exception as error:
        print(f"Ошибка webhook: {error}", flush=True)

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
