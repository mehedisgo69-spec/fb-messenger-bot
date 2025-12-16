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


def fix_english(text):
    text = text.strip()
    if not text:
        return text

    # remove space before punctuation
    text = re.sub(r"\s+([?.!,])", r"\1", text)

    # split sentences
    parts = re.split(r'([?.!])', text)

    fixed = ""
    for i in range(0, len(parts) - 1, 2):
        sentence = parts[i].strip()
        punct = parts[i + 1]

        if sentence:
            sentence = sentence[0].upper() + sentence[1:]

        fixed += sentence + punct + " "

    fixed = fixed.strip()

    # if no punctuation at end
    if fixed and fixed[-1] not in ".?!":
        fixed += "."

    return fixed


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
