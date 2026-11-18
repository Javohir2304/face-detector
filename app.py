"""Veb-interfeys: brauzer kamerasi orqali yuzni tanish va bazaga odam qo'shish.

  .venv/bin/python app.py      ->  http://localhost:8000
"""
import argparse
import threading

import cv2
import numpy as np
from flask import Flask, jsonify, render_template, request

from add_person import enroll
from database import FaceDatabase
from face_engine import FaceEngine

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

engine = FaceEngine()
# OpenCV modellari bir vaqtda bir nechta oqimdan chaqirishga mo'ljallanmagan.
engine_lock = threading.Lock()
# Bazadagi vektorlar har kadrda qayta o'qilmasligi uchun kesh; baza o'zgarganda tozalanadi.
_known_faces = None


def known_faces():
    global _known_faces
    if _known_faces is None:
        _known_faces = FaceDatabase().load_all()
    return _known_faces


def forget_known_faces():
    global _known_faces
    _known_faces = None


def read_image(upload):
    data = np.frombuffer(upload.read(), dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR) if data.size else None


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/people")
def list_people():
    return jsonify([{"name": name, "faces": count} for name, count in FaceDatabase().list_people()])


@app.post("/api/people")
def add_person():
    name = request.form.get("name", "").strip()
    uploads = request.files.getlist("images")
    if not name or not uploads:
        return jsonify(error="Ism va kamida bitta rasm kerak"), 400
    if len(name) > 100:
        return jsonify(error="Ism juda uzun"), 400

    db = FaceDatabase()
    report = []
    with engine_lock:
        for upload in uploads:
            ok, notes = enroll(engine, db, name, read_image(upload), upload.filename)
            report.append({"file": upload.filename, "ok": ok, "notes": notes})
        forget_known_faces()
    return jsonify(added=sum(item["ok"] for item in report), report=report)


@app.delete("/api/people/<path:name>")
def delete_person(name):
    if not FaceDatabase().delete_person(name):
        return jsonify(error="Bunday odam topilmadi"), 404
    with engine_lock:
        forget_known_faces()
    return jsonify(ok=True)


@app.post("/api/recognize")
def recognize():
    upload = request.files.get("image")
    image = read_image(upload) if upload else None
    if image is None:
        return jsonify(error="Rasmni o'qib bo'lmadi"), 400
    with engine_lock:
        names, matrix = known_faces()
        faces = engine.identify(image, names, matrix)
    return jsonify(faces=faces, width=image.shape[1], height=image.shape[0], people=len(set(names)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Yuzni tanish — veb-interfeys")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    print(f"Brauzerda oching: http://localhost:{args.port}")
    app.run(host="127.0.0.1", port=args.port)
