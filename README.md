# Dietologiya

`Dietologiya` Django asosida qurilgan ovqatlanish va parhez boshqaruv platformasi. Tizim tashkilotlar uchun kunlik menyu, taom tarkibi, mahsulot qiymati va oziq ko'rsatkichlarini markazlashgan tarzda yuritishga xizmat qiladi.

## Asosiy imkoniyatlar

- Tashkilot, mavsum, parhez, ovqatlanish vaqti, mahsulot, taom va kunlik menyu uchun to'liq model
- Taom va menyu bo'yicha oqsil, yog', uglevod, kaloriya va tannarxni avtomatik hisoblash
- Ikki boshqaruv qismi:
  - Global admin (`/admin/`) - faqat maxsus link orqali
  - Tashkilot kabineti (`/organization-admin/`)
- Tashkilot foydalanuvchilari uchun login/profil sahifasi va Word eksport
  - `Bir kunlik xarajatlar` - eng so'nggi menyu kuni bo'yicha mahsulot va narx hisoboti
  - `Barcha xarajatlar` - tashkilotdagi barcha menyu kunlari bo'yicha umumiy mahsulot va xarajat hisoboti
- Demo ma'lumotlarni bir buyruq bilan yaratish (`seed_demo_data`)
- `Yangiliklar` sahifasi (`/news/`)
- 400, 403, 404 va 500 xatolari uchun foydalanuvchiga tushunarli sahifalar
- Responsive frontend (Django templates + Bootstrap + custom CSS/JS)
- Global UI effektlar: reveal-on-scroll, hover/tilt, ripple, yumshoq animatsiyalar

## Texnologiyalar

- Python 3.12+
- Django 4.2
- SQLite (lokal), PostgreSQL (production)
- WhiteNoise
- Jazzmin

## Loyiha tuzilmasi

- `Diatologitaya/` - Django konfiguratsiyasi (`settings.py`, `urls.py`, `wsgi.py`)
- `menu/` - modellar, viewlar, admin, management commandlar
- `menu/templates/` - foydalanuvchi interfeysi sahifalari
- `static/` - CSS, JS, rasm va ikonlar
- `manage.py` - boshqaruv skripti

## Lokal ishga tushirish (Windows)

1. Virtual muhit yarating:

```bash
python -m venv venv
```

2. Virtual muhitni yoqing:

```bash
venv\Scripts\activate
```

3. Kutubxonalarni o'rnating:

```bash
pip install -r requirements.txt
```

4. Muhit o'zgaruvchilari (minimal):

```bash
set DJANGO_DEBUG=True
set DJANGO_SECRET_KEY=change-me
set DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,dietologiya.local
```

5. Migratsiyalar:

```bash
python manage.py migrate
```

6. Superuser yarating:

```bash
python manage.py createsuperuser
```

7. Serverni ishga tushiring:

```bash
python manage.py runserver
```

8. Brauzerda oching:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/news/`
- `http://127.0.0.1:8000/admin/` (maxsus link)
- `http://127.0.0.1:8000/organization-admin/`

## Word eksport

Profil sahifasida tashkilot foydalanuvchisi uchun ikki xil Word hisobot bor:

- `Bir kunlik xarajatlar` (`/profile/export-word/`) - oxirgi menyu kuni uchun mahsulot miqdori va jami narxni chiqaradi.
- `Barcha xarajatlar` (`/profile/export-all-word/`) - tashkilotdagi barcha menyu kunlarini jamlaydi. Masalan, tizimga 1 oylik menyu kiritilgan bo'lsa, 1 oylik umumiy mahsulot sarfi va xarajat Word faylga tushadi.

## Xato sahifalari

Production rejimida quyidagi xatolar maxsus sahifa orqali ko'rsatiladi:

- `400` - noto'g'ri so'rov
- `403` - ruxsat yo'q
- `404` - sahifa topilmadi
- `500` - server xatosi

## Demo ma'lumotlar

```bash
python manage.py seed_demo_data
```

Buyruq natijasi:

- demo tashkilot: `Sog'lom Avlod MTT`
- login: `soglom_avlod`
- parol: `OrgDemo2026!`
- mahsulot, taom va menyu yozuvlari

## ZIP orqali import

```bash
python manage.py import_menu_zip --zip-path path\to\menu.zip --organization "Tashkilot nomi" --year 2026
```

## Muhim ENV o'zgaruvchilar

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DATABASE_URL`
- `DJANGO_SQLITE_PATH`

## Eslatma

- Admin tugmasi UI'da ko'rsatilmaydi, admin faqat `/admin/` manzili orqali ochiladi.
- Lokalda SQLite ishlatiladi; production uchun PostgreSQL tavsiya etiladi.
- O'zgarishlarni tekshirish uchun `python manage.py check` ishlating.
