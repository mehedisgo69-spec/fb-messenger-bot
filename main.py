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
        "ami", "tumi", "kemon", "acho", "bhalo", "nai", "কি", "কিভাবে"
    ]
    t = text.lower()
    return any(k in t for k in keywords)

def roman_to_bangla(text):
    try:
        res = requests.post(
            "https://libretranslate.de/translate",
            json={
                "q": text,
                "source": "auto",
                "target": "bn",
                "format": "text"
            },
            timeout=7
        )
        return res.json()["translatedText"]
    except:
        return text

def is_question(text):
    text = text.lower()

    question_words_bn = [
        "কি", "কেন", "কেমন", "কোথায়", "কখন", "কিভাবে", "তুমি", "আপনি"
    ]

    question_words_en = [
        "do you", "are you", "have you", "is it",
        "can you", "will you", "what", "why", "how"
    ]

    if "?" in text:
        return True

    for w in question_words_bn:
        if w in text:
            return True

    for w in question_words_en:
        if w in text:
            return True

    return False
    

def fix_english(text, original_text=""):
    text = text.strip()
    if not text:
        return text

    question = is_question(original_text)

    # Remove extra spaces before punctuation
    text = re.sub(r"\s+([?.!,])", r"\1", text)

    # Capitalize first letter
    text = text[0].upper() + text[1:]

    # Remove ending punctuation
    text = re.sub(r"[.?!]+$", "", text)

    # Add correct punctuation
    if question:
        text += "?"
    else:
        text += "."

    return text


def translate_text(text):
    original_text = text.strip()
    if not original_text:
        return ""

    # Roman Bangla → Bangla
    if is_roman_bangla(original_text) and not is_bangla(original_text):
        text = roman_to_bangla(original_text)
    else:
        text = original_text

    # Decide target language
    target = "en" if is_bangla(text) else "bn"

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

    # Fix English punctuation & capitalization
    if target == "en":
        translated = fix_english(translated, original_text)

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
