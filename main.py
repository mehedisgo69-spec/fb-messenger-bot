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

def small_word_translate(text):
    t = text.lower().strip()

    mapping = {
        "hi": "হাই",
        "hello": "হ্যালো",
        "hey": "হেই",
        "bye": "বিদায়",
        "thanks": "ধন্যবাদ",
        "thank you": "ধন্যবাদ",
        "ok": "ঠিক আছে",
        "okay": "ঠিক আছে",
        "yes": "হ্যাঁ",
        "no": "না"
    }

    return mapping.get(t)

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

    # 🔹 Small words first (Hi, Hello, etc.)
    small = small_word_translate(text)
    if small:
        return small

    # Decide target language
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

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    for entry in data.get("entry", []):
        for msg in entry.get("messaging", []):

            psid = msg["sender"]["id"]

            # ---------- Get Started ----------
            if "postback" in msg:
                payload = msg["postback"].get("payload")

                if payload == "GET_STARTED":
                    welcome_text = (
                        "স্বাগতম! 👋😊\n\n"
                        "বাংলা বা ইংরেজিতে লিখুন,\n"
                        "আমি স্বয়ংক্রিয়ভাবে অনুবাদ করে দেবো। 🌍\n\n"
                        "উদাহরণ:\n"
                        "• কেমন আছো?\n"
                        "• How are you?\n\n"
                        "Help লিখলে ব্যবহার জানতে পারবেন।"
                    )
                    send_message(psid, welcome_text)

                return "ok", 200

            # ---------- Text Message ----------
            if "message" in msg and "text" in msg["message"]:
                text = msg["message"]["text"].strip()
                text_lower = text.lower()

                # ----- Help command -----
                if text_lower == "help":
                    help_text = (
                        "🆘 সাহায্য\n\n"
                        "আপনি যেকোনো ভাষায় লিখতে পারেন:\n"
                        "• বাংলা\n"
                        "• English\n"
                        "• Roman Bangla\n\n"
                        "আমি স্বয়ংক্রিয়ভাবে অনুবাদ করে দেবো।\n\n"
                        "উদাহরণ:\n"
                        "কেমন আছো?\n"
                        "How are you?\n"
                        "Tumi kemon acho?"
                    )
                    send_message(psid, help_text)
                    return "ok", 200

                # ----- About command -----
                if text_lower == "about":
                    about_text = (
                        "ℹ️ About\n\n"
                        "আমি একটি বাংলা ↔ ইংরেজি অনুবাদক বট।\n"
                        "বাংলা, ইংরেজি ও Roman Bangla বুঝতে পারি।\n\n"
                        "উদ্দেশ্য:\n"
                        "সহজ ও দ্রুত অনুবাদ। ⚡"
                    )
                    send_message(psid, about_text)
                    return "ok", 200

                # ----- Normal translation (small words included) -----
                translated = translate_text(text)
                send_message(psid, translated)

    return "ok", 200


# ---------------- Health ----------------

@app.route("/")
def home():
    return "FB Bangla-English Translator Bot is running 🚀"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
