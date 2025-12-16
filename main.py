from flask import Flask, request
import requests
import os

app = Flask(__name__)

VERIFY_TOKEN = "mytoken"
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")

@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "wrong token"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    sender = data["entry"][0]["messaging"][0]["sender"]["id"]
    text = data["entry"][0]["messaging"][0]["message"]["text"]

    translated = translate(text)
    send_message(sender, translated)

    return "ok"

def translate(text):
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": "auto",
            "tl": "en",
            "dt": "t",
            "q": text
        }

        r = requests.get(url, params=params).json()
        result = r[0][0][0]

        try:
            text.encode("ascii")
            params["tl"] = "bn"
            r = requests.get(url, params=params).json()
            result = r[0][0][0]
        except:
            pass

        return result
    except:
        return "translation error"

def send_message(sender_id, message):
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": sender_id},
        "message": {"text": message}
    }
    requests.post(url, json=payload)

@app.route("/")
def home():
    return "Bot running"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
