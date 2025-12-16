from flask import Flask, request
import requests
import os
import re

app = Flask(__name__)

PAGE_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")

# ------------------ Language Helpers ------------------

def is_bangla(text):
    return any("\u0980" <= c <= "\u09FF" for c in text)

def is_roman_bangla(text):
    keywords = [
        "ami", "tumi", "kemon", "acho", "jabo", "khabo",
        "korbo", "cholo", "ek", "sathe", "valo", "bhalo"
    ]
    t = text.lower()
    return any(k in t for k in keywords)

# ------------------ English Formatter ------------------

def fix_english(text):
    text = text.strip()
    if not text:
        return text

    greetings = ["hi", "hello", "hey", "thanks", "ok"]
    if text.lower() in greetings:
        return text.capitalize() + "."

    question_words = [
        "how", "what", "why", "where", "when",
        "do", "does", "did", "is", "are", "can", "will"
    ]

    is_question = any(
        text.lower().startswith(q + " ") or text.lower() == q
        for q in question_words
    )

    text = re.sub(r"\s+([?.!,])", r"\1", text)
    text = text[0].upper() + text[1:]

    if text.endswith(("?", "!", ".")):
        return text

    return text + ("?" if is_question else ".")

# ------------------ Translator ------------------

def translate_text(text):
    text = text.strip()
    if not text:
        return ""

    # Greeting direct reply
    if text.lower() in ["hi", "hello", "hey"]:
        return fix_english(text)

    # Decide target language
    if is_bangla(text) or is_roman_bangla(text):
        target = "en"
    else:
        target = "bn"

    try:
        res = requests.post(
            "https://libretranslate.de/translate",
            json={
                "q": text,
                "source": "auto",
                "target": target,
                "format": "text"
            },
            timeout=10
        )
        translated = res.json()["translatedText"]
    except:
        return "Translation failed."

    if target == "en":
        translated = fix_english(translated)

    return translated

# ------------------ Facebook ------------------

def send_message(psid, text):
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_TOKEN}"
    payload = {
        "recipient": {"id": psid},
        "message": {"text": text}
    }
    requests.post(url, json=payload)

# ------------------ Webhook ------------------

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if (
            request.args.get("hub.mode") == "subscribe"
            and request.args.get("hub.verify_token") == VERIFY_TOKEN
        ):
            return request.args.get("hub.challenge")
        return "Verification failed"

    data = request.get_json()

    for entry in data.get("entry", []):
        for event in entry.get("messaging", []):
            if "message" in event and "text" in event["message"]:
                sender = event["sender"]["id"]
                text = event["message"]["text"]

                reply = translate_text(text)
                send_message(sender, reply)

    return "OK"

# ------------------ Home ------------------

@app.route("/")
def home():
    return "FB Translator Bot is running 🚀"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
