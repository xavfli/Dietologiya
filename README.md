# Dietologiya

`Dietologiya` - Django asosida qurilgan ovqatlanish va parhez boshqaruv platformasi. Loyiha tashkilotlar uchun kunlik menyu, taom tarkibi, mahsulot sarfi, oziq qiymati va xarajatlarni markazlashgan tarzda yuritishga yordam beradi.

## Imkoniyatlar

- Tashkilot, mavsum, parhez, ovqatlanish vaqti, mahsulot, taom va kunlik menyu modellarini boshqarish
- Taom va menyu bo'yicha oqsil, yog', uglevod, kaloriya va tannarxni avtomatik hisoblash
- Global admin panel: default `/secure-admin/`
- Tashkilot kabineti: `/organization-admin/`
- Tashkilot foydalanuvchilari uchun login va profil sahifasi
- Word formatida xarajat hisobotlarini yuklab olish
- Demo ma'lumotlarni `seed_demo_data` buyrug'i bilan yaratish
- ZIP orqali menyu ma'lumotlarini import qilish
- Yangiliklar sahifasi: `/news/`
- 400, 403, 404 va 500 xatolari uchun maxsus sahifalar
- Responsive frontend va global UI effektlar

## Word Hisobotlar

Profil sahifasida ikki xil Word eksport mavjud:

- `Bir kunlik xarajatlar` - oxirgi menyu kuni bo'yicha mahsulot miqdori va jami narxni chiqaradi.
- `Barcha xarajatlar` - tashkilotdagi barcha menyu kunlarini jamlaydi. Agar tizimga 1 oylik menyu kiritilgan bo'lsa, 1 oylik umumiy mahsulot sarfi va xarajat Word faylga tushadi.

URL manzillar:

- `/profile/export-word/`
- `/profile/export-all-word/`

## Texnologiyalar

- Python 3.12+
- Django 4.2
- SQLite lokal muhit uchun
- PostgreSQL production uchun
- WhiteNoise
- Jazzmin

## Loyiha Tuzilmasi

- `Diatologitaya/` - Django konfiguratsiyasi
- `menu/` - modellar, viewlar, admin, URL va management commandlar
- `menu/templates/` - foydalanuvchi sahifalari
- `static/` - CSS, JavaScript, rasm va ikonlar
- `manage.py` - Django boshqaruv fayli

## Lokal Ishga Tushirish

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

4. Muhit o'zgaruvchilarini sozlang:

```bash
set DJANGO_DEBUG=True
set DJANGO_SECRET_KEY=change-me
set DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,dietologiya.local
```

5. Migratsiyalarni ishga tushiring:

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
- `http://127.0.0.1:8000/secure-admin/`
- `http://127.0.0.1:8000/organization-admin/`

## Demo Ma'lumotlar

Demo tashkilot, foydalanuvchi, mahsulot, taom va menyu yozuvlarini yaratish:

```bash
python manage.py seed_demo_data
```

Demo login ma'lumotlari:

- Tashkilot: `Sog'lom Avlod MTT`
- Login: `soglom_avlod`
- Parol: `OrgDemo2026!`

## ZIP Orqali Import

Excel fayllar to'plamini ZIP orqali import qilish:

```bash
python manage.py import_menu_zip --zip-path path\to\menu.zip --organization "Tashkilot nomi" --year 2026
```

Papka ichidagi `.xlsx` fayllardan import qilish:

```bash
python manage.py import_menu_zip --folder-path path\to\folder --organization "Tashkilot nomi" --year 2026
```

## Internetdan Narx Yangilash

Mahsulot narxlarini internetdagi CSV yoki JSON manbadan avtomatik yangilash:

```bash
python manage.py update_product_prices --url "https://example.com/prices.csv" --organization "Tashkilot nomi"
```

CSV ustunlari uchun `mahsulot,narx` yoki `name,price` ishlatiladi:

```csv
mahsulot,narx
Guruch,14313
Kartoshka,5000
```

JSON ham qo'llab-quvvatlanadi:

```json
[
  {"name": "Guruch", "price": 14313},
  {"name": "Kartoshka", "price": 5000}
]
```

Avval bazani o'zgartirmasdan tekshirish uchun:

```bash
python manage.py update_product_prices --url "https://example.com/prices.csv" --dry-run
```

Oxirgi narxlarni AI orqali internetdan qidirib yangilash uchun `OPENAI_API_KEY` sozlanadi:

```bash
set OPENAI_API_KEY=sk-...
python manage.py update_product_prices --ai-latest --city "Tashkent" --organization "Tashkilot nomi"
```

AI rejimini avval bazani o'zgartirmasdan tekshirish:

```bash
python manage.py update_product_prices --ai-latest --city "Tashkent" --dry-run
```

Modelni almashtirish kerak bo'lsa:

```bash
python manage.py update_product_prices --ai-latest --model gpt-5 --city "Tashkent"
```

## Renderga Deploy Qilish

1. Render dashboardda `New` -> `Postgres` tanlang va database yarating.
2. Yaratilgan database ichidan `Internal Database URL` qiymatini nusxalang.
3. `New` -> `Web Service` tanlang.
4. GitHub repository sifatida `xavfli/Dietologiya` ni ulang.
5. Sozlamalarni kiriting:

- Runtime: `Python 3`
- Branch: `main`
- Build Command: `./build.sh`
- Start Command: `gunicorn Diatologitaya.wsgi --log-file -`

6. Environment variables bo'limiga qo'shing:

- `DATABASE_URL` - Render Postgres `Internal Database URL`
- `DJANGO_SECRET_KEY` - xavfsiz secret key
- `DJANGO_DEBUG` - `False`
- `DJANGO_ADMIN_PATH` - admin panel manzili, masalan `secure-admin/`
- `DJANGO_SUPERUSER_USERNAME` - admin login
- `DJANGO_SUPERUSER_PASSWORD` - admin parol
- `DJANGO_SUPERUSER_EMAIL` - admin email, ixtiyoriy
- `PYTHON_VERSION` - `3.12`
- `WEB_CONCURRENCY` - `4`

Render `RENDER_EXTERNAL_HOSTNAME` qiymatini avtomatik beradi. Shu sabab `.onrender.com` domen `ALLOWED_HOSTS` va `CSRF_TRUSTED_ORIGINS` ro'yxatiga avtomatik qo'shiladi.
`DATABASE_URL` qiymati to'liq bo'lishi kerak, masalan `postgresql://...` bilan boshlanadi.
`DATABASE_URL` noto'g'ri kiritilsa, loyiha build paytida yiqilmaslik uchun SQLite fallback ishlatadi, lekin production uchun Render Postgres `Internal Database URL` qiymatini to'g'ri qo'yish shart.
`<Postgres Internal Database URL>` yoki `<Generate qilingan secret>` kabi placeholder matnlarni qoldirmang; ularning o'rniga haqiqiy qiymat yozing.
Static fayllar Render build paytida WhiteNoise orqali compressed holatda yig'iladi. Vendor JavaScript ichidagi yo'q `.map` havolalar buildni yiqitmasligi uchun manifest talab qilmaydigan compressed storage ishlatiladi.

### Renderda Admin Yaratish

Build jarayonida `python manage.py ensure_superuser` ishga tushadi. Bu command adminni faqat quyidagi env o'zgaruvchilar berilganda yaratadi:

- `DJANGO_SUPERUSER_USERNAME`
- `DJANGO_SUPERUSER_PASSWORD`
- `DJANGO_SUPERUSER_EMAIL` ixtiyoriy

Kodda default login yoki default parol yo'q. Agar env qiymatlar berilmasa, admin yaratish o'tkazib yuboriladi.
Admin mavjud bo'lsa, qayta yaratilmaydi. Parolni majburan yangilash kerak bo'lsa, vaqtincha `DJANGO_SUPERUSER_UPDATE_PASSWORD=True` qo'shib deploy qiling, keyin uni olib tashlang.

## Xato Sahifalari

Production rejimida quyidagi xatolar maxsus sahifa orqali ko'rsatiladi:

- `400` - noto'g'ri so'rov
- `403` - ruxsat yo'q
- `404` - sahifa topilmadi
- `500` - server xatosi

## Muhim ENV O'zgaruvchilar

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DATABASE_URL`
- `DJANGO_SQLITE_PATH`
- `DJANGO_ADMIN_PATH`
- `DJANGO_SUPERUSER_USERNAME`
- `DJANGO_SUPERUSER_PASSWORD`
- `DJANGO_SUPERUSER_EMAIL`
- `PYTHON_VERSION`

## Tekshirish

O'zgarishlardan keyin Django tekshiruvini ishga tushiring:

```bash
python manage.py check
```

## Eslatma

- Lokal muhitda SQLite ishlatiladi.
- Production uchun PostgreSQL tavsiya etiladi.
- Admin panel UI ichida alohida reklama qilinmaydi, kerak bo'lsa `/secure-admin/` orqali ochiladi. Render'da bu manzilni `DJANGO_ADMIN_PATH` orqali o'zgartirish mumkin.
