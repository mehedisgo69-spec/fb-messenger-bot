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
        "ami", "tumi", "kemon", "acho", "bhalo", "nai",
        "ki", "keno", "kothay", "jabo", "cholo"
    ]
    t = text.lower()
    return any(k in t for k in keywords)

def fix_english(text):
    text = text.strip()
    if not text:
        return text

    # remove space before punctuation
    text = re.sub(r"\s+([?.!,])", r"\1", text)

    sentences = re.split(r'([?.!])', text)
    fixed = ""

    for i in range(0, len(sentences) - 1, 2):
        s = sentences[i].strip()
        p = sentences[i + 1]
        if s:
            fixed += s[0].upper() + s[1:] + p + " "

    if len(sentences) % 2 != 0:
        last = sentences[-1].strip()
        if last:
            fixed += last[0].upper() + last[1:] + "."

    return fixed.strip()

# ------------------ Translation ------------------

def translate_text(text):
    text = text.strip()
    if not text:
        return ""

    # Decide target language
    if is_bangla(text) or is_roman_bangla(text):
        target = "en"
    else:
        target = "bn"

    try:
        # LibreTranslate
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

    except Exception as e:
        print("LibreTranslate failed:", e)
        try:
            # Google fallback
            params = {
                "client": "gtx",
                "sl": "auto",
                "tl": target,
                "dt": "t",
                "q": text
            }
            g = requests.get(
                "https://translate.googleapis.com/translate_a/single",
                params=params,
                timeout=10
            )
            translated = "".join(
                part[0] for part in g.json()[0] if part[0]
            )
        except Exception as e:
            print("Google fallback failed:", e)
            return text

    if target == "en":
        return fix_english(translated)
    else:
        return translated

# ------------------ Messenger ------------------

def send_message(psid, text):
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_TOKEN}"
    payload = {
        "recipient": {"id": psid},
        "message": {"text": text}
    }
    requests.post(url, json=payload)

@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "Invalid token", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    for entry in data.get("entry", []):
        for msg in entry.get("messaging", []):
            if "message" in msg and "text" in msg["message"]:
                psid = msg["sender"]["id"]
                text = msg["message"]["text"]

                translated = translate_text(text)
                send_message(psid, translated)

    return "ok", 200

@app.route("/")
def home():
    return "FB Messenger Translator Bot is running 🚀"
