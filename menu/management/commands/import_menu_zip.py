from __future__ import annotations

import re
import tempfile
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zipfile import ZipFile

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from menu.models import Dish, DishIngredient, MealTime, MenuDay, MenuEntry, Organization, Product, Season
from menu.xlsx_utils import XlsxWorkbook


MONTHS = {
    "январ": 1,
    "феврал": 2,
    "март": 3,
    "апрел": 4,
    "май": 5,
    "июн": 6,
    "июл": 7,
    "август": 8,
    "сентябр": 9,
    "октябр": 10,
    "ноябр": 11,
    "декабр": 12,
}

LIQUID_PRODUCT_HINTS = ("сут", "чой", "сув", "кислота", "вино", "соус", "қаймоқ", "qaymoq")
PRICE_ROW_HINTS = ("нархи", "нарх", "цена", "цен", "1 килограм")
PRODUCT_HEADER_HINTS = (
    "махсулотлар номи",
    "махсулотлар тури",
    "махсулотлар турлари",
    "маҳсулотлар номи",
    "маҳсулотлар тури",
    "маҳсулотлар турлари",
    "product",
)
MEAL_SLOT_KEYWORDS = {
    "1-нону": "first_breakfast",
    "2-нону": "second_breakfast",
    "туш": "lunch",
    "обед": "lunch",
    "толма": "buffet",
    "полд": "buffet",
    "буфет": "buffet",
    "кеч": "dinner",
    "ужин": "dinner",
}


def parse_decimal(value: str) -> Decimal | None:
    cleaned = (value or "").strip().replace(",", ".")
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def normalize_text(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"^\d+[\.\)]\s*", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" .")


def is_meaningful_product_name(value: str) -> bool:
    normalized = normalize_text(value)
    return bool(normalized and re.search(r"[a-zа-яёқғҳў]", normalized))


def build_product_columns(sheet, code_row: int, primary_name_row: int, secondary_name_row: int, start_col: int = 4):
    columns = []
    for col in range(start_col, sheet.max_col + 1):
        code = sheet.get(code_row, col)
        name = sheet.get(secondary_name_row, col) or sheet.get(primary_name_row, col)
        if not is_meaningful_product_name(name):
            continue
        columns.append({"col": col, "code": code, "name": name})
    return columns


def find_row_with_any(sheet, hints, max_row: int | None = None) -> int | None:
    max_row = min(max_row or sheet.max_row, sheet.max_row)
    for row in range(1, max_row + 1):
        row_text = " ".join(sheet.get(row, col) for col in range(1, min(sheet.max_col, 8) + 1))
        normalized = normalize_text(row_text)
        if any(hint in normalized for hint in hints):
            return row
    return None


def find_product_header_rows(sheet, price_row: int | None = None) -> tuple[int, int, int]:
    search_until = max(1, (price_row or 12) - 1)
    product_row = find_row_with_any(sheet, PRODUCT_HEADER_HINTS, search_until) or 3
    if product_row + 1 <= sheet.max_row:
        return product_row, product_row + 1, product_row + 2
    return product_row, product_row, product_row


def product_price_map_from_sheet(sheet, header_sheet=None) -> dict[str, Decimal]:
    price_row = find_row_with_any(sheet, PRICE_ROW_HINTS, 15)
    if not price_row:
        return {}

    source_sheet = header_sheet or sheet
    code_row, primary_name_row, secondary_name_row = find_product_header_rows(
        source_sheet,
        price_row if source_sheet is sheet else None,
    )
    product_columns = build_product_columns(source_sheet, code_row, primary_name_row, secondary_name_row)
    prices = {}
    for column in product_columns:
        price = parse_decimal(sheet.get(price_row, column["col"]))
        if price is None or price <= 0:
            continue
        prices[normalize_text(column["name"])] = price
    return prices


def collect_workbook_prices(workbook: XlsxWorkbook) -> dict[str, Decimal]:
    prices = {}
    sheets = {sheet_name: workbook.read_sheet(sheet_name) for sheet_name in workbook.sheet_targets}
    preferred_names = ("цены", "нарх", "раскладка", "ум")
    sheet_names = sorted(
        workbook.sheet_targets,
        key=lambda name: 0 if any(token in normalize_text(name) for token in preferred_names) else 1,
    )
    for sheet_name in sheet_names:
        sheet = sheets[sheet_name]
        sheet_prices = product_price_map_from_sheet(sheet)
        if not sheet_prices:
            for header_sheet in sheets.values():
                if header_sheet is sheet:
                    continue
                sheet_prices = product_price_map_from_sheet(sheet, header_sheet)
                if sheet_prices:
                    break
        prices.update(sheet_prices)
    return prices


def infer_unit(name: str) -> str:
    lowered = normalize_text(name)
    return Product.Unit.MILLILITER if any(token in lowered for token in LIQUID_PRODUCT_HINTS) else Product.Unit.GRAM


def parse_start_date(file_name: str, year: int) -> date:
    match = re.search(r"(\d{1,2})-(\d{1,2})\s+([А-Яа-яЁё]+)", file_name)
    if not match:
        return date(year, 1, 1)
    day = int(match.group(1))
    month = MONTHS.get(match.group(3).lower(), 1)
    return date(year, month, day)


class Command(BaseCommand):
    help = "Import products, dishes, and menu days from the provided zip workbook set."

    def add_arguments(self, parser):
        parser.add_argument("--zip-path")
        parser.add_argument("--folder-path")
        parser.add_argument("--organization", required=True)
        parser.add_argument("--year", type=int, default=2026)

    @transaction.atomic
    def handle(self, *args, **options):
        organization, _ = Organization.objects.get_or_create(name=options["organization"])
        self._ensure_mealtimes()

        with tempfile.TemporaryDirectory() as temp_dir:
            extracted = self._extract_workbooks(options, Path(temp_dir))
            master_path = next((path for path in extracted if "барча" in path.name.lower()), None)
            menu_path = next((path for path in extracted if "лактозсиз" in path.name.lower()), None)
            if not master_path:
                raise CommandError("Master workbook not found. File name should include 'барча'.")

            workbook_prices = self._collect_prices_from_files(extracted)
            product_lookup = self._import_master_workbook(master_path, organization, workbook_prices)
            if menu_path:
                self._import_menu_workbook(menu_path, organization, product_lookup, options["year"])
            updated_count = self._update_existing_product_prices(organization, workbook_prices)

        self.stdout.write(self.style.SUCCESS(
            f"Imported workbook data for {organization.name}. Prices updated: {updated_count}"
        ))

    def _extract_workbooks(self, options, temp_dir: Path) -> list[Path]:
        zip_path = Path(options["zip_path"]) if options.get("zip_path") else None
        folder_path = Path(options["folder_path"]) if options.get("folder_path") else None
        if bool(zip_path) == bool(folder_path):
            raise CommandError("Provide exactly one of --zip-path or --folder-path.")
        if zip_path:
            if not zip_path.exists():
                raise CommandError(f"Zip file not found: {zip_path}")
            with ZipFile(zip_path) as archive:
                archive.extractall(temp_dir)
            root = temp_dir
        else:
            if not folder_path.exists():
                raise CommandError(f"Folder not found: {folder_path}")
            root = folder_path

        xlsx_files = sorted(path for path in root.glob("*.xlsx") if not path.name.startswith("~$"))
        xls_files = sorted(path for path in root.glob("*.xls") if not path.name.startswith("~$"))
        for path in xls_files:
            self.stdout.write(self.style.WARNING(f"Skipped old .xls workbook, save as .xlsx to import: {path.name}"))
        if not xlsx_files:
            raise CommandError("No .xlsx workbooks found.")
        return xlsx_files

    def _collect_prices_from_files(self, workbook_paths: list[Path]) -> dict[str, Decimal]:
        prices = {}
        for workbook_path in workbook_paths:
            workbook = XlsxWorkbook(workbook_path)
            file_prices = collect_workbook_prices(workbook)
            prices.update(file_prices)
            if file_prices:
                self.stdout.write(f"Prices found in {workbook_path.name}: {len(file_prices)}")
        return prices

    def _update_existing_product_prices(self, organization: Organization, prices: dict[str, Decimal]) -> int:
        updated_count = 0
        for product in Product.objects.filter(organization=organization):
            price = prices.get(normalize_text(product.name))
            if price is None or product.price_per_kg == price:
                continue
            product.price_per_kg = price
            product.save(update_fields=["price_per_kg"])
            updated_count += 1
        return updated_count

    def _ensure_mealtimes(self):
        items = [
            ("first_breakfast", "1-nonushta", 1),
            ("second_breakfast", "2-nonushta", 2),
            ("lunch", "Tushlik", 3),
            ("buffet", "Bufet mahsulotlari", 4),
            ("dinner", "Kechki ovqat", 5),
        ]
        for slot, title, order in items:
            MealTime.objects.update_or_create(slot=slot, defaults={"title": title, "order": order})

    def _import_master_workbook(self, workbook_path: Path, organization: Organization, workbook_prices: dict[str, Decimal]):
        workbook = XlsxWorkbook(workbook_path)
        nutrition_sheet = workbook.read_sheet("раскладка")
        dish_sheet = workbook.read_sheet("все")

        product_columns = build_product_columns(nutrition_sheet, 3, 4, 5)
        protein_row = find_row_with_any(nutrition_sheet, ("оқсил", "оксил", "белок"), 15) or 7
        fat_row = find_row_with_any(nutrition_sheet, ("ёғ", "ег", "жир"), 15) or 8
        carbs_row = find_row_with_any(nutrition_sheet, ("углевод",), 15) or 9
        calories_row = find_row_with_any(nutrition_sheet, ("каллория", "калория", "энергетик", "э.қ"), 15) or 10
        products_by_col = {}
        products_by_name = {}

        for column in product_columns:
            name = column["name"]
            normalized_name = normalize_text(name)
            price = workbook_prices.get(normalized_name)
            if price is None:
                price = product_price_map_from_sheet(nutrition_sheet).get(normalized_name, Decimal("0"))
            product, _ = Product.objects.update_or_create(
                organization=organization,
                name=name,
                defaults={
                    "unit": infer_unit(name),
                    "protein": parse_decimal(nutrition_sheet.get(protein_row, column["col"])) or Decimal("0"),
                    "fat": parse_decimal(nutrition_sheet.get(fat_row, column["col"])) or Decimal("0"),
                    "carbs": parse_decimal(nutrition_sheet.get(carbs_row, column["col"])) or Decimal("0"),
                    "calories": int(parse_decimal(nutrition_sheet.get(calories_row, column["col"])) or 0),
                    "price_per_kg": price or Decimal("0"),
                },
            )
            products_by_col[column["col"]] = product
            products_by_name[normalize_text(product.name)] = product

        for row in range(7, dish_sheet.max_row + 1):
            dish_name = dish_sheet.get(row, 2)
            portion = dish_sheet.get(row, 3)
            if not dish_name or not portion:
                continue

            dish, _ = Dish.objects.update_or_create(
                organization=organization,
                name=dish_name,
                defaults={"description": f"Import: {workbook_path.name}"},
            )
            DishIngredient.objects.filter(dish=dish).delete()
            has_ingredients = False
            for col, product in products_by_col.items():
                amount = parse_decimal(dish_sheet.get(row, col))
                if not amount or amount <= 0:
                    continue
                grams = int(amount.quantize(Decimal("1")))
                DishIngredient.objects.create(dish=dish, product=product, grams=grams)
                has_ingredients = True
            if not has_ingredients:
                continue
            products_by_name[normalize_text(dish.name)] = dish

        self.stdout.write(f"Products imported: {len(products_by_col)}")
        self.stdout.write(f"Dishes in catalog: {Dish.objects.filter(organization=organization).count()}")
        return products_by_name

    def _import_menu_workbook(self, workbook_path: Path, organization: Organization, product_lookup, year: int):
        workbook = XlsxWorkbook(workbook_path)
        start_date = parse_start_date(workbook_path.name.lower(), year)
        numbered_sheets = sorted(
            [name for name in workbook.sheet_targets if name.isdigit()],
            key=lambda value: int(value),
        )

        for sheet_name in numbered_sheets:
            sheet = workbook.read_sheet(sheet_name)
            product_columns = build_product_columns(sheet, 2, 3, 4)
            products_by_col = {}
            for column in product_columns:
                normalized = normalize_text(column["name"])
                product = Product.objects.filter(organization=organization, name=column["name"]).first()
                if not product:
                    product = Product.objects.filter(organization=organization, name__icontains=column["name"]).first()
                if not product:
                    product, _ = Product.objects.get_or_create(
                        organization=organization,
                        name=column["name"],
                        defaults={"unit": infer_unit(column["name"])},
                    )
                products_by_col[column["col"]] = product

            day_index = int(sheet_name) - 1
            menu_date = start_date.fromordinal(start_date.toordinal() + day_index)
            season_name = self._season_name(menu_date.month)
            season, _ = Season.objects.get_or_create(name=season_name, year=menu_date.year)
            menu_day, _ = MenuDay.objects.update_or_create(
                organization=organization,
                date=menu_date,
                defaults={"season": season, "people_count": 1},
            )
            MenuEntry.objects.filter(menu_day=menu_day).delete()

            current_slot = None
            people_count = menu_day.people_count
            for row in range(10, sheet.max_row + 1):
                title = sheet.get(row, 1)
                if not title:
                    continue

                slot = self._resolve_meal_slot(title)
                if slot:
                    current_slot = slot
                    people_count = int(parse_decimal(sheet.get(row, 2)) or people_count or 1)
                    continue

                if title == "0" or not current_slot:
                    continue

                portion = sheet.get(row, 3)
                if not portion:
                    continue

                dish = Dish.objects.filter(
                    organization=organization,
                    name__iexact=title,
                ).first()
                if not dish:
                    dish = Dish.objects.filter(
                        organization=organization,
                        name__icontains=title,
                    ).first()
                if not dish:
                    dish, _ = Dish.objects.update_or_create(
                        organization=organization,
                        name=title,
                        defaults={"description": f"Import: {workbook_path.name}"},
                    )

                ingredient_values = []
                for col, product in products_by_col.items():
                    amount = parse_decimal(sheet.get(row, col))
                    if not amount or amount <= 0:
                        continue
                    ingredient_values.append((product, int(amount.quantize(Decimal('1')))))

                if ingredient_values:
                    DishIngredient.objects.filter(dish=dish).delete()
                    for product, grams in ingredient_values:
                        DishIngredient.objects.create(dish=dish, product=product, grams=grams)

                MenuEntry.objects.create(
                    menu_day=menu_day,
                    mealtime=MealTime.objects.get(slot=current_slot),
                    dish=dish,
                    portions=max(people_count, 1),
                )

            menu_day.people_count = max(people_count, 1)
            menu_day.save(update_fields=["people_count"])

        self.stdout.write(f"Menu days imported: {MenuDay.objects.filter(organization=organization).count()}")

    def _resolve_meal_slot(self, value: str) -> str | None:
        normalized = normalize_text(value)
        for keyword, slot in MEAL_SLOT_KEYWORDS.items():
            if keyword in normalized:
                return slot
        return None

    def _season_name(self, month: int) -> str:
        if month in {12, 1, 2}:
            return Season.SeasonName.WINTER
        if month in {3, 4, 5}:
            return Season.SeasonName.SPRING
        if month in {6, 7, 8}:
            return Season.SeasonName.SUMMER
        return Season.SeasonName.AUTUMN
