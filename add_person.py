"""Bazaga odam qo'shish: rasm(lar)dan, papkadan yoki kameradan.

  python add_person.py --name "Ali Valiyev" --image ali1.jpg ali2.jpg
  python add_person.py --name "Ali Valiyev" --camera
  python add_person.py --folder people/       # people/<ism>/*.jpg
  python add_person.py --list
  python add_person.py --delete "Ali Valiyev"
"""
import argparse
import sys
from pathlib import Path

import cv2

from database import FaceDatabase
from face_engine import FaceEngine

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
# Bundan tor yuzlarda (piksel) vektor ishonchsiz bo'ladi.
MIN_FACE_WIDTH = 80
FONT = cv2.FONT_HERSHEY_SIMPLEX


def largest_face(faces):
    return max(faces, key=lambda face: face[2] * face[3])


def enroll(engine, db, name, image, source):
    """Rasmdagi eng katta yuzni bazaga qo'shadi: (qo'shildimi, izohlar)."""
    if image is None:
        return False, ["rasmni o'qib bo'lmadi"]
    faces = engine.detect(image)
    if not faces:
        return False, ["yuz topilmadi"]
    face = largest_face(faces)
    notes = []
    if len(faces) > 1:
        notes.append(f"{len(faces)} ta yuz bor, eng kattasi olindi")
    if face[2] < MIN_FACE_WIDTH:
        notes.append(f"yuz juda kichik ({int(face[2])}px), aniqlik past bo'lishi mumkin")
    db.add_embedding(name, engine.embed(image, face), source=source)
    return True, notes


def add_from_images(engine, db, name, paths):
    added = 0
    for path in paths:
        ok, notes = enroll(engine, db, name, cv2.imread(str(path)), str(path))
        added += ok
        print(f"  {'+' if ok else 'x'} {path}" + (f": {'; '.join(notes)}" if notes else ""))
    return added


def add_from_folder(engine, db, folder):
    """Har bir ichki papka nomi — odamning ismi, ichidagi rasmlar — uning yuzlari."""
    total = 0
    for person_dir in sorted(p for p in Path(folder).iterdir() if p.is_dir()):
        images = sorted(p for p in person_dir.iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS)
        print(f"{person_dir.name}:")
        total += add_from_images(engine, db, person_dir.name, images)
    return total


def add_from_camera(engine, db, name, shots, camera_index):
    capture = cv2.VideoCapture(camera_index)
    if not capture.isOpened():
        sys.exit("Kamerani ochib bo'lmadi. macOS'da: System Settings > Privacy & Security > Camera > Terminal'ga ruxsat bering.")
    window = "Yuz qo'shish | SPACE - suratga olish, Q - tugatish"
    added = 0
    while added < shots:
        ok, frame = capture.read()
        if not ok:
            break
        faces = engine.detect(frame)
        preview = frame.copy()
        color = (0, 200, 0) if len(faces) == 1 else (0, 0, 255)
        for face in faces:
            x, y, w, h = face[:4].astype(int)
            cv2.rectangle(preview, (x, y), (x + w, y + h), color, 2)
        hint = "SPACE - suratga olish" if len(faces) == 1 else "Kadrda bitta yuz bo'lishi kerak"
        cv2.putText(preview, f"{added}/{shots}  {hint}", (10, 30), FONT, 0.8, color, 2)
        cv2.imshow(window, preview)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            break
        if key == ord(" ") and len(faces) == 1:
            db.add_embedding(name, engine.embed(frame, faces[0]), source="camera")
            added += 1
            print(f"  + {added}-surat saqlandi")
    capture.release()
    cv2.destroyAllWindows()
    return added


def main():
    parser = argparse.ArgumentParser(description="Bazaga odam qo'shish")
    parser.add_argument("--name", help="odamning ismi")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--image", nargs="+", help="bir yoki bir nechta rasm fayli")
    source.add_argument("--camera", action="store_true", help="kameradan suratga olish")
    source.add_argument("--folder", help="papka: har bir ichki papka nomi = ism")
    source.add_argument("--list", action="store_true", help="bazadagi odamlar ro'yxati")
    source.add_argument("--delete", metavar="ISM", help="odamni bazadan o'chirish")
    parser.add_argument("--shots", type=int, default=5, help="kameradan nechta surat olish (standart: 5)")
    parser.add_argument("--camera-index", type=int, default=0, help="kamera raqami (standart: 0)")
    args = parser.parse_args()

    db = FaceDatabase()
    if args.list:
        people = db.list_people()
        if not people:
            print("Baza bo'sh.")
        for name, count in people:
            print(f"  {name}  ({count} ta yuz)")
        return
    if args.delete:
        print("O'chirildi." if db.delete_person(args.delete) else "Bunday odam topilmadi.")
        return
    if args.folder:
        print(f"Jami {add_from_folder(FaceEngine(), db, args.folder)} ta yuz qo'shildi.")
        return
    if not args.name or not (args.image or args.camera):
        parser.error("--name bilan birga --image yoki --camera kerak")

    engine = FaceEngine()
    if args.image:
        added = add_from_images(engine, db, args.name, args.image)
    else:
        added = add_from_camera(engine, db, args.name, args.shots, args.camera_index)
    print(f"{args.name}: {added} ta yuz qo'shildi.")


if __name__ == "__main__":
    main()
