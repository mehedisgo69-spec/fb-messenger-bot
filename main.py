from flask import Flask, request
import requests
import os
import re

app = Flask(__name__)

PAGE_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")


# ------------------ Helpers ------------------

def is_bangla(text):
    return any("\u0980" <= c <= "\u09FF" for c in text)


def is_roman_bangla(text):
    keywords = [
        "ami", "tumi", "kemon", "acho", "bhalo", "nai", "কি", "কি?"
    ]
    t = text.lower()
    return any(k in t for k in keywords)


def fix_english(text):
    text = text.strip()
    if not text:
        return text

    # Remove extra spaces before punctuation
    text = re.sub(r"\s+([?.!,])", r"\1", text)

    # Split sentences by punctuation
    sentences = re.split(r'([?.!])', text)

    fixed = ""
    for i in range(0, len(sentences) - 1, 2):
        sentence = sentences[i].strip()
        punct = sentences[i + 1]

        if sentence:
            sentence = sentence[0].upper() + sentence[1:]
            fixed += sentence + punct + " "

    # Handle last sentence if no punctuation
    if len(sentences) % 2 != 0:
        last = sentences[-1].strip()
        if last:
            fixed += last[0].upper() + last[1:] + "."

    return fixed.strip()


def translate_text(text):
    text = text.strip()
    if not text:
        return ""

    # Decide target language
    if is_bangla(text):
        target = "en"
    elif is_roman_bangla(text):
        target = "en"
    else:
        target = "bn"

    # -------- Try LibreTranslate --------
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
        # -------- Google fallback --------
        try:
            res = requests.get(
                "https://translate.googleapis.com/translate_a/single",
                params={
                    "client": "gtx",
                    "sl": "auto",
                    "tl": target,
                    "dt": "t",
                    "q": text
                },
                timeout=10
            )
            translated = "".join(
                part[0] for part in res.json()[0]
            )
        except:
            return "Translation failed. Please try again."

    if target == "en":
        translated = fix_english(translated)

    return translated


# ------------------ Webhook ------------------

@app.route("/webhook", methods=["GET"])
def verify():
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if token == VERIFY_TOKEN:
        return challenge
    return "Invalid token", 403


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    for entry in data.get("entry", []):
        for event in entry.get("messaging", []):
            if "message" in event and "text" in event["message"]:
                sender_id = event["sender"]["id"]
                text = event["message"]["text"]

                reply = translate_text(text)
                send_message(sender_id, reply)

    return "ok", 200


def send_message(psid, text):
    url = "https://graph.facebook.com/v18.0/me/messages"
    payload = {
        "recipient": {"id": psid},
        "message": {"text": text}
    }
    params = {"access_token": PAGE_TOKEN}

    requests.post(url, params=params, json=payload, timeout=10)


# ------------------ Health Check ------------------

@app.route("/")
def home():
    return "Messenger Translator Bot is running 🚀"
