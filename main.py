from flask import Flask, request
import requests
import os

app = Flask(__name__)

# ================= CONFIG =================
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = "mytoken"
# =========================================


@app.route("/", methods=["GET"])
def home():
    return "Messenger Translator Bot is running ✅", 200


# ---------- WEBHOOK VERIFY ----------
@app.route("/webhook", methods=["GET"])
def verify():
    token_sent = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if token_sent == VERIFY_TOKEN:
        return challenge
    return "Invalid verification token", 403


# ---------- WEBHOOK RECEIVE ----------
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for event in entry.get("messaging", []):
                if "message" in event and "text" in event["message"]:
                    sender_id = event["sender"]["id"]
                    text = event["message"]["text"]

                    reply_text = translate_auto(text)
                    send_message(sender_id, reply_text)

    return "ok", 200


# ---------- TRANSLATION LOGIC ----------
def translate_auto(text):
    try:
        original_text = text.strip()

        # ----- Step 1: Detect Roman Bangla -----
        roman_bangla_keywords = [
            "ami", "tumi", "apni", "kemon", "acho", "achen",
            "ki", "korcho", "korchen", "valo", "bhalo",
            "thik", "achhi", "achi"
        ]

        is_roman_bangla = any(
            word in original_text.lower()
            for word in roman_bangla_keywords
        )

        # ----- Step 2: Roman Bangla → Bangla -----
        if is_roman_bangla:
            try:
                rb_url = "https://inputtools.google.com/request"
                rb_payload = {
                    "text": original_text,
                    "itc": "bn-t-i0-und",
                    "num": 1
                }
                rb_res = requests.post(rb_url, json=rb_payload, timeout=10)
                original_text = rb_res.json()[1][0][1][0]
            except:
                pass

        # ----- Step 3: Detect Bangla or English -----
        is_bangla = any("\u0980" <= c <= "\u09FF" for c in original_text)
        target_lang = "en" if is_bangla else "bn"

        # ----- Step 4: Sentence-based Translation -----
        lt_url = "https://libretranslate.de/translate"
        payload = {
            "q": original_text,
            "source": "auto",
            "target": target_lang,
            "format": "text"
        }

        response = requests.post(lt_url, json=payload, timeout=15)
        translated = response.json()["translatedText"]

        # ----- Step 5: Capitalization Fix -----
        if translated and translated[0].isalpha():
            translated = translated[0].upper() + translated[1:]

        return translated

    except Exception:
        return "Translation failed. Please try again."


# ---------- SEND MESSAGE ----------
def send_message(recipient_id, text):
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    requests.post(url, json=payload)


# ---------- START ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
