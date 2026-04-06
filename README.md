# Diatologitaya

`Diatologitaya` Django asosida qurilgan ovqatlanish va parhez boshqaruv tizimi bo'lib, tashkilotlar uchun kunlik menyu, taom tarkibi, mahsulot qiymati va oziq-ovqat ko'rsatkichlarini markazlashgan tarzda yuritishga xizmat qiladi. Loyiha admin boshqaruvi, tashkilot kabineti, demo ma'lumotlar yaratish va Word eksport kabi amaliy funksiyalarni o'z ichiga oladi.

## Asosiy imkoniyatlar

- Tashkilot, mavsum, parhez, ovqatlanish vaqti, mahsulot, taom va kunlik menyu uchun to'liq ma'lumot modeli
- Taom va menyu kesimida oqsil, yog', uglevod, kaloriya va tannarxni avtomatik hisoblash
- Ikki boshqaruv paneli: global admin panel (`/admin/`) va tashkilotlar uchun alohida kabinet (`/organization-admin/`)
- Tashkilot foydalanuvchisi uchun login, profil sahifasi va eng so'nggi menyuni Word formatda eksport qilish
- Excel fayllar to'plamidan ZIP orqali mahsulotlar, taomlar va menyularni import qilish
- Responsive frontend: Django templates, Bootstrap 5 va maxsus CSS/JS
- Production tayyor konfiguratsiya: WhiteNoise, `gunicorn` va `dj-database-url`

## Texnologiyalar

- Python 3.12+
- Django 4.2
- SQLite lokal muhit uchun, PostgreSQL production uchun
- WhiteNoise statik fayllar uchun
- Jazzmin admin interfeysini chiroyli boshqarish uchun

## Loyiha tuzilmasi

- `Diatologitaya/` - asosiy Django konfiguratsiyasi
- `menu/` - biznes logika, modellar, viewlar, admin va management commandlar
- `static/` - statik fayllar
- `templates/` va `menu/templates/` - foydalanuvchi va admin interfeyslari
- `manage.py` - Django boshqaruv skripti

## Lokal ishga tushirish

1. Virtual environment yarating:

   ```bash
   python -m venv venv
   ```

2. Virtual environment'ni yoqing:

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
   set DJANGO_SECRET_KEY=your-secret-key
   set DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
   ```

5. Migratsiyalarni ishga tushiring:

   ```bash
   python manage.py migrate
   ```

6. Administrator yarating:

   ```bash
   python manage.py createsuperuser
   ```

7. Serverni ishga tushiring:

   ```bash
   python manage.py runserver
   ```

8. Brauzerda quyidagi sahifalarni oching:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/admin/`
- `http://127.0.0.1:8000/organization-admin/`

## Demo ma'lumotlar

Test uchun tayyor demo tashkilot va menyu yozuvlarini yaratish mumkin:

```bash
python manage.py seed_demo_data
```

Ushbu buyruq quyidagilarni yaratadi:

- demo tashkilot
- tashkilot egasi uchun foydalanuvchi
- mahsulotlar va taomlar katalogi
- namunaviy kunlik menyu yozuvlari

## ZIP orqali import

Agar sizda Excel ishchi fayllari ZIP ko'rinishida bo'lsa, ularni tizimga import qilish mumkin:

```bash
python manage.py import_menu_zip --zip-path path\to\menu.zip --organization "Tashkilot nomi" --year 2026
```

Bu buyruq:

- mahsulotlar katalogini yaratadi yoki yangilaydi
- taom tarkibini import qiladi
- kunlik menyu yozuvlarini tashkilot bo'yicha shakllantiradi

## Muhim muhit o'zgaruvchilari

- `DJANGO_SECRET_KEY` - production uchun majburiy maxfiy kalit
- `DJANGO_DEBUG` - `True` yoki `False`
- `DJANGO_ALLOWED_HOSTS` - vergul bilan ajratilgan hostlar ro'yxati
- `DJANGO_CSRF_TRUSTED_ORIGINS` - production domenlari uchun trusted originlar
- `DATABASE_URL` - PostgreSQL yoki boshqa qo'llab-quvvatlanadigan baza ulanishi
- `DJANGO_SQLITE_PATH` - lokal SQLite fayli uchun maxsus yo'l

## Eslatmalar

- Statik fayllar WhiteNoise orqali servis qilinadi, shu sabab `DISABLE_COLLECTSTATIC=1` ishlatmaslik tavsiya etiladi.
- Lokal muhitda baza sukut bo'yicha SQLite bilan ishlaydi.
- Admin interfeysi Jazzmin bilan bezatilgan.
