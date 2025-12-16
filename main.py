from flask import Flask, request
import requests
import os

app = Flask(__name__)

PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")

def translate(text):
    url = "https://libretranslate.com/translate"
    data = {
        "q": text,
        "source": "auto",
        "target": "en",
        "format": "text"
    }
    r = requests.post(url, data=data).json()
    return r["translatedText"]

def send_message(sender_id, message):
    url = f"https://graph.facebook.com/v17.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": sender_id},
        "message": {"text": message}
    }
    requests.post(url, json=payload)

@app.route("/", methods=["GET"])
def verify():
    if request.args.get("hub.verify_token") == "mytoken":
        return request.args.get("hub.challenge")
    return "Wrong token"

@app.route("/", methods=["POST"])
def webhook():
    data = request.json
    sender_id = data["entry"][0]["messaging"][0]["sender"]["id"]
    text = data["entry"][0]["messaging"][0]["message"]["text"]
    translated = translate(text)
    send_message(sender_id, translated)
    return "ok"

if __name__ == "__main__":
    app.run()
