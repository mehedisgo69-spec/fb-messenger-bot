from flask import Flask, request
import requests
import os
import re

app = Flask(__name__)

PAGE_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}

# ---------------- Language Detection ----------------

def is_bangla(text):
    return any("\u0980" <= c <= "\u09FF" for c in text)

def is_roman_bangla(text):
    keywords = [
        "ami", "tumi", "kemon", "acho", "jabo", "khabo",
        "korbo", "cholo", "ek", "sathe", "valo", "bhalo",
        "ki", "keno", "kothay", "kemon acho"
    ]
    t = text.lower()
    return any(k in t for k in keywords)

# ---------------- English Fix ----------------

def fix_english(text):
    text = text.strip()
    if not text:
        return text

    text = re.sub(r"\s+([?.!,])", r"\1", text)

    text = text[0].upper() + text[1:]

    if text.endswith(("?", "!", ".")):
        return text

    question_words = (
        "how", "what", "why", "where", "when",
        "do", "does", "did", "is", "are", "can", "will"
    )

    if text.lower().startswith(question_words):
        return text + "?"

    return text + "."

# ---------------- Google Translate ----------------

def google_translate(text, target):
    url = "https://translate.googleapis.com/translate_a/single"
    params = {
        "client": "gtx",
        "sl": "auto",
        "tl": target,
        "dt": "t",
        "q": text
    }

    r = requests.get(url, params=params, headers=HEADERS, timeout=10)
    r.raise_for_status()
    data = r.json()

    return "".join(i[0] for i in data[0])

def translate_text(text):
    text = text.strip()
    if not text:
        return ""

    if text.lower() in ["hi", "hello", "hey"]:
        return fix_english(text)

    if is_bangla(text) or is_roman_bangla(text):
        target = "en"
    else:
        target = "bn"

    try:
        translated = google_translate(text, target)
    except Exception as e:
        print("Translation error:", e)
        return "⚠️ Translation error. Try again."

    if target == "en":
        translated = fix_english(translated)

    return translated

# ---------------- Send Message ----------------

def send_message(psid, text):
    url = "https://graph.facebook.com/v18.0/me/messages"
    params = {"access_token": PAGE_TOKEN}
    payload = {
        "recipient": {"id": psid},
        "message": {"text": text}
    }
    requests.post(url, params=params, json=payload, headers=HEADERS)

# ---------------- Webhook ----------------

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if (
            request.args.get("hub.mode") == "subscribe"
            and request.args.get("hub.verify_token") == VERIFY_TOKEN
        ):
            return request.args.get("hub.challenge")
        return "Verification failed", 403

    data = request.get_json()

    if "entry" in data:
        for entry in data["entry"]:
            if "messaging" in entry:
                for event in entry["messaging"]:
                    if "message" in event and "text" in event["message"]:
                        sender = event["sender"]["id"]
                        text = event["message"]["text"]

                        reply = translate_text(text)
                        send_message(sender, reply)

    return "OK"

# ---------------- Health ----------------

@app.route("/")
def home():
    return "FB Bangla-English Translator Bot is running 🚀"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
