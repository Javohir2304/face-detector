"""Kamera (yoki rasm) orqali yuzni tanish va bazadagi odamga necha foiz mosligini ko'rsatish.

  python recognize.py                    # kamera; Q - chiqish, R - bazani qayta yuklash
  python recognize.py --image photo.jpg  # bitta rasm
"""
import argparse
import sys

import cv2

from database import FaceDatabase
from face_engine import FaceEngine

FONT = cv2.FONT_HERSHEY_SIMPLEX
GREEN = (0, 200, 0)
RED = (0, 0, 255)
WHITE = (255, 255, 255)


def ascii_label(text):
    # cv2.putText faqat ASCII chiza oladi: oʻ/gʻ dagi maxsus tutuq belgilarini oddiy ' ga almashtiramiz.
    for char in "ʻʼ‘’`":
        text = text.replace(char, "'")
    return text.encode("ascii", "replace").decode()


def describe(result):
    if result["known"]:
        return f"{result['name']} {result['percent']:.0f}%"
    if result["name"] is None:
        return "Noma'lum"
    return f"Noma'lum ({result['name']}? {result['percent']:.0f}%)"


def annotate(engine, image, names, matrix):
    """Har bir yuzni rasmga chizadi va engine.identify natijasini qaytaradi."""
    results = engine.identify(image, names, matrix)
    for result in results:
        x, y, w, h = result["box"]
        color = GREEN if result["known"] else RED
        label = ascii_label(describe(result))
        (text_w, text_h), _ = cv2.getTextSize(label, FONT, 0.6, 2)
        top = max(y, text_h + 10)
        cv2.rectangle(image, (x, y), (x + w, y + h), color, 2)
        cv2.rectangle(image, (x, top - text_h - 10), (x + text_w + 8, top), color, cv2.FILLED)
        cv2.putText(image, label, (x + 4, top - 6), FONT, 0.6, WHITE, 2)
    return results


def load_known(db):
    names, matrix = db.load_all()
    if not names:
        print("Baza bo'sh — avval add_person.py bilan odam qo'shing.")
    else:
        print(f"Bazada {len(set(names))} ta odam, {len(names)} ta yuz.")
    return names, matrix


def run_image(engine, db, path, save, show):
    image = cv2.imread(path)
    if image is None:
        sys.exit(f"Rasmni o'qib bo'lmadi: {path}")
    results = annotate(engine, image, *load_known(db))
    if not results:
        print("Rasmda yuz topilmadi.")
    for i, result in enumerate(results, 1):
        print(f"  {i}. {describe(result)}")
    if save:
        cv2.imwrite(save, image)
        print(f"Natija saqlandi: {save}")
    if show:
        cv2.imshow("Natija | istalgan tugma - yopish", image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


def run_camera(engine, db, camera_index):
    capture = cv2.VideoCapture(camera_index)
    if not capture.isOpened():
        sys.exit("Kamerani ochib bo'lmadi. macOS'da: System Settings > Privacy & Security > Camera > Terminal'ga ruxsat bering.")
    names, matrix = load_known(db)
    window = "Yuzni tanish | Q - chiqish, R - bazani yangilash"
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        annotate(engine, frame, names, matrix)
        cv2.imshow(window, frame)
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            break
        if key == ord("r"):
            names, matrix = load_known(db)
    capture.release()
    cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description="Yuzni tanish")
    parser.add_argument("--image", help="kamera o'rniga bitta rasmni tekshirish")
    parser.add_argument("--save", metavar="FAYL", help="natijani rasm qilib saqlash (--image bilan)")
    parser.add_argument("--no-show", action="store_true", help="oyna ochmaslik (--image bilan)")
    parser.add_argument("--camera-index", type=int, default=0, help="kamera raqami (standart: 0)")
    args = parser.parse_args()

    engine = FaceEngine()
    db = FaceDatabase()
    if args.image:
        run_image(engine, db, args.image, args.save, not args.no_show)
    else:
        run_camera(engine, db, args.camera_index)


if __name__ == "__main__":
    main()
