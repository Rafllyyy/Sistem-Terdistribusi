import os
import time

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

load_dotenv()

# Kunci API dibaca dari file .env supaya tidak ikut tertulis di kode yang di-screenshot.
API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
BATAS_KARAKTER = 1000

app = Flask(__name__)
# Frontend dibuka dari alamat berbeda (port lain atau file langsung), jadi browser butuh izin CORS.
CORS(app)


def galat(pesan, status):
    return jsonify({"error": pesan}), status


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "model": MODEL, "api_key_terisi": bool(API_KEY)})


@app.post("/api/tanya")
def tanya():
    data = request.get_json(silent=True) or {}
    pertanyaan = str(data.get("pertanyaan", "")).strip()

    if not pertanyaan:
        return galat("Pertanyaan masih kosong. Tulis dulu pertanyaannya.", 400)
    if len(pertanyaan) > BATAS_KARAKTER:
        return galat(f"Pertanyaan terlalu panjang. Maksimal {BATAS_KARAKTER} karakter.", 400)
    if not API_KEY:
        return galat("GEMINI_API_KEY belum diisi di file .env pada folder backend.", 500)

    payload = {
        "systemInstruction": {
            "parts": [{"text": "Kamu asisten belajar untuk mahasiswa. Jawab dalam bahasa Indonesia, jelas, maksimal lima kalimat, tanpa format markdown."}]
        },
        "contents": [{"role": "user", "parts": [{"text": pertanyaan}]}],
    }
    headers = {"Content-Type": "application/json", "x-goog-api-key": API_KEY}

    mulai = time.perf_counter()
    try:
        resp = requests.post(GEMINI_URL, json=payload, headers=headers, timeout=30)
    except requests.Timeout:
        return galat("Gemini terlalu lama menjawab. Coba kirim lagi.", 504)
    except requests.RequestException:
        return galat("Backend tidak bisa menghubungi Gemini. Periksa koneksi internet.", 502)
    waktu_ms = round((time.perf_counter() - mulai) * 1000)

    try:
        hasil = resp.json()
    except ValueError:
        return galat("Balasan Gemini tidak bisa dibaca.", 502)

    if resp.status_code != 200:
        pesan = hasil.get("error", {}).get("message", "Gemini menolak permintaan.")
        return galat(f"Gemini menolak permintaan (kode {resp.status_code}): {pesan}", 502)

    try:
        jawaban = hasil["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        return galat("Gemini tidak memberi jawaban untuk pertanyaan ini. Coba ubah kalimatnya.", 502)

    return jsonify({"jawaban": jawaban, "meta": {"model": MODEL, "waktu_gemini_ms": waktu_ms}})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
