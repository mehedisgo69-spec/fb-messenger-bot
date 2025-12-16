from flask import Flask, request
import requests
import os

app = Flask(__name__)

def translate_auto(text):
    original_text = text.strip()

    try:
        # ---------- Detect Bangla ----------
        is_bangla = any("\u0980" <= c <= "\u09FF" for c in original_text)
        target = "en" if is_bangla else "bn"

        # ---------- Try LibreTranslate first ----------
        try:
            lt_url = "https://libretranslate.de/translate"
            payload = {
                "q": original_text,
                "source": "auto",
                "target": target,
                "format": "text"
            }
            res = requests.post(lt_url, json=payload, timeout=7)
            translated = res.json()["translatedText"]

        except:
            # ---------- Google Fallback ----------
            google_url = "https://translate.googleapis.com/translate_a/single"
            params = {
                "client": "gtx",
                "sl": "auto",
                "tl": target,
                "dt": "t",
                "q": original_text
            }
            r = requests.get(google_url, params=params, timeout=7)
            translated = "".join(
                part[0] for part in r.json()[0]
            )

        # ---------- Capital Fix ----------
        if translated and translated[0].isalpha():
            translated = translated[0].upper() + translated[1:]

        return translated

    except Exception:
        return "Sorry, translation service is temporarily busy."
