# Face Detector — yuz orqali odamni tanish

Bazaga odamning rasmi va ismini qo'shasiz. Kamera yuzni ko'rganda uni bazadagi odamlar bilan solishtiradi va ekranda **ism + necha foiz mosligini** ko'rsatadi.

- Yuzni aniqlash: **YuNet** (OpenCV Zoo)
- Yuzni tanish: **SFace** — har bir yuz 128 ta sondan iborat vektorga aylantiriladi
- Baza: **SQLite** (`data/faces.db`). Rasmlarning o'zi emas, faqat yuz vektorlari saqlanadi.

## O'rnatish

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Modellar `models/` papkasida turibdi. Agar yo'q bo'lsa, ularni yuklab oling:

```bash
mkdir -p models
curl -L -o models/face_detection_yunet_2023mar.onnx https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx
curl -L -o models/face_recognition_sface_2021dec.onnx https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx
```

macOS'da kameradan foydalanish uchun: **System Settings → Privacy & Security → Camera** bo'limida Terminal (yoki VS Code)ga ruxsat bering.

## Veb-interfeys (eng oson yo'l)

```bash
.venv/bin/python app.py
```

Brauzerda **http://localhost:8000** ni oching (brauzer kamera ruxsatini so'raydi):

- **Chapda** — jonli kamera: har bir yuz ramkaga olinadi, ustida ism va foiz chiqadi; pastda har bir yuz uchun foiz chizig'i.
- **Odam qo'shish** — ismni yozing, «Kameradan olish» (bir necha marta bosing) yoki «Rasm tanlash», keyin «Saqlash».
- **Bazadagi odamlar** — ismni bossangiz, shu odamga yana rasm qo'shish mumkin; «O'chirish» — bazadan olib tashlash.
- **Rasm bilan tekshirish** — kamera o'rniga fayldan rasm tekshirish.

Boshqa port kerak bo'lsa: `.venv/bin/python app.py --port 8080`.

| API | Vazifasi |
|---|---|
| `GET /api/people` | odamlar ro'yxati |
| `POST /api/people` | `name` + `images` (bir nechta fayl) — odam qo'shish |
| `DELETE /api/people/<ism>` | odamni o'chirish |
| `POST /api/recognize` | `image` — yuzlar, ismlar va foizlar (JSON) |

## Buyruq qatori (CLI)

### Odam qo'shish

```bash
# Rasmlardan (bir nechta rasm bo'lsa, aniqlik oshadi)
.venv/bin/python add_person.py --name "Ali Valiyev" --image ali1.jpg ali2.jpg

# Kameradan: SPACE — suratga olish (5 marta), Q — tugatish
.venv/bin/python add_person.py --name "Ali Valiyev" --camera

# Butun papkadan: people/Ali Valiyev/*.jpg, people/Vali/*.jpg ...
.venv/bin/python add_person.py --folder people/

.venv/bin/python add_person.py --list                 # ro'yxat
.venv/bin/python add_person.py --delete "Ali Valiyev" # o'chirish
```

### Tanish

```bash
# Kamera: Q — chiqish, R — bazani qayta yuklash (yangi odam qo'shganingizdan keyin)
.venv/bin/python recognize.py

# Bitta rasmni tekshirish
.venv/bin/python recognize.py --image test.jpg --save natija.jpg
```

Ekranda:
- 🟩 **yashil** `Ali Valiyev 87%` — tanildi
- 🟥 **qizil** `Noma'lum (Ali Valiyev? 32%)` — eng yaqin odam shu, lekin mos kelmadi

## Foiz qanday hisoblanadi

SFace ikki yuz vektori orasidagi **cosine o'xshashlik**ni beradi (taxminan -1 dan 1 gacha). U foizga quyidagicha aylantiriladi (`face_engine.py`):

| cosine | foiz | ma'nosi |
|---|---|---|
| ≤ 0 | 0% | butunlay boshqa odam |
| 0.363 | 50% | chegara: bundan yuqorisi — "shu odam" |
| ≥ 0.75 | 100% | juda kuchli moslik |

Bu foiz **ehtimollik emas**, o'qish oson bo'lishi uchun qilingan shkala. Chegarani `MATCH_THRESHOLD` orqali o'zgartirish mumkin: oshirsangiz, xato tanish kamayadi, lekin haqiqiy odamni tanimay qolishi ko'payadi.

## Aniqlikni oshirish

- Har bir odamdan **3–5 ta** turli rasm qo'shing: har xil burchak, yorug'lik, ko'zoynakli/ko'zoynaksiz.
- Yuz rasmda kamida ~80 piksel kenglikda bo'lsin (kichik bo'lsa, `add_person.py` ogohlantiradi).
- Kamera oldida yuz yaxshi yoritilgan bo'lsin.

## Maxfiylik

Yuz ma'lumotlari — shaxsiy biometrik ma'lumot. Bazaga faqat rozilik bergan odamlarni qo'shing. `data/` papkasini boshqalarga yubormang (`.gitignore`'ga kiritilgan).
