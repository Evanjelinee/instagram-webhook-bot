import json
import os

from flask import Flask, request


app = Flask(__name__)
VERIFY_TOKEN = os.environ.get("META_VERIFY_TOKEN", "dev_verify_token")


@app.get("/webhook")
def verify_webhook():
    """Handle Meta's webhook subscription challenge."""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN and challenge:
        return challenge, 200, {"Content-Type": "text/plain"}

    return "Verification failed", 403


@app.post("/webhook")
def receive_webhook():
    """Receive and log Instagram webhook events."""
    payload = request.get_json(silent=True)
    if payload is None:
        return {"error": "Expected a JSON request body"}, 400

    app.logger.info("Received Instagram webhook event:\n%s", json.dumps(payload, indent=2))
    return {"status": "received"}, 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=False)
