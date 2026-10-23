# Instagram Webhook Receiver

A minimal Flask server for Meta's Instagram webhook verification and event
delivery. It does not make Instagram API calls and needs no paid services or API
keys.

## Run it

From the project root:

```bash
python -m pip install -r instagram_webhook/requirements.txt
python instagram_webhook/app.py
```

The server listens on `http://localhost:8000`. To use a different verification
token, set `META_VERIFY_TOKEN` before starting it. For example:

```bash
META_VERIFY_TOKEN=my-local-token python instagram_webhook/app.py
```

Meta's webhook setup must use the same verification token. The default token is
`dev_verify_token`, intended only for local testing.

## Test the routes

In another terminal, test verification:

```bash
curl -i "http://localhost:8000/webhook?hub.mode=subscribe&hub.verify_token=dev_verify_token&hub.challenge=12345"
```

The response body should be `12345`. Send a sample event:

```bash
curl -i -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"object":"instagram","entry":[]}'
```

The server responds with `{"status":"received"}` and logs the JSON event.

## Before production

This starter accepts any valid JSON POST; it does not yet verify Meta's
`X-Hub-Signature-256` signature. Add signature validation before relying on
events sent to a publicly accessible endpoint. Meta also needs a publicly
reachable HTTPS URL; localhost is only for development.
