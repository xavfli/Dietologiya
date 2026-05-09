from __future__ import annotations

import json
import os
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.core.files.uploadedfile import UploadedFile
from django.utils import timezone

from .models import (
    AISuggestion,
    Dish,
    ImportJob,
    MenuAlert,
    MenuDay,
    Organization,
    PriceHistory,
    Product,
    TelegramSubscription,
)


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/{method}"


def get_user_organization(user):
    if hasattr(user, "managed_organization"):
        return user.managed_organization
    membership = getattr(user, "organization_membership", None)
    return membership.organization if membership else None


def record_product_price(
    product: Product,
    new_price: Decimal,
    source_type: str,
    source_label: str = "",
    confidence: int = 100,
) -> bool:
    if product.price_per_kg == new_price:
        return False
    old_price = product.price_per_kg
    product.price_per_kg = new_price
    product.save(update_fields=["price_per_kg"])
    if not product.organization:
        return True
    PriceHistory.objects.create(
        product=product,
        organization=product.organization,
        old_price=old_price,
        new_price=new_price,
        source_type=source_type,
        source_label=source_label,
        confidence=confidence,
        effective_date=timezone.localdate(),
    )
    return True


def build_menu_alerts(organization: Organization) -> int:
    MenuAlert.objects.filter(organization=organization, is_resolved=False).delete()
    created = 0
    for menu_day in MenuDay.objects.filter(organization=organization).prefetch_related(
        "entries__dish__ingredients__product"
    ):
        has_lactose = False
        if menu_day.diet and "laktos" in menu_day.diet.title.lower():
            for entry in menu_day.entries.all():
                for ingredient in entry.dish.ingredients.all():
                    product_name = ingredient.product.name.lower()
                    if any(token in product_name for token in ("sut", "qatiq", "pishloq", "tvorog", "қаймоқ")):
                        has_lactose = True
                        break
                if has_lactose:
                    break
        if has_lactose:
            MenuAlert.objects.create(
                organization=organization,
                menu_day=menu_day,
                severity=MenuAlert.Severity.DANGER,
                title="Laktosiz menyuda sut mahsuloti bor",
                message=f"{menu_day.date:%d.%m.%Y} menyusida laktosiz parhezga mos kelmasligi mumkin bo'lgan mahsulot topildi.",
            )
            created += 1

        per_person = menu_day.per_person_cost
        if per_person > Decimal("50000"):
            MenuAlert.objects.create(
                organization=organization,
                menu_day=menu_day,
                severity=MenuAlert.Severity.WARNING,
                title="Kishi boshiga xarajat yuqori",
                message=f"{menu_day.date:%d.%m.%Y} kuni kishi boshiga xarajat {per_person:.0f} so'm.",
            )
            created += 1
    return created


def product_requirement_summary(organization: Organization) -> list[dict]:
    totals: dict[str, dict] = {}
    menu_days = MenuDay.objects.filter(organization=organization).prefetch_related("entries__dish__ingredients__product")
    for day in menu_days:
        for entry in day.entries.all():
            for ingredient in entry.dish.ingredients.all():
                bucket = totals.setdefault(
                    ingredient.product.name,
                    {"name": ingredient.product.name, "quantity": Decimal("0"), "unit": ingredient.product.unit, "cost": Decimal("0")},
                )
                quantity = Decimal(ingredient.grams) * Decimal(entry.portions)
                bucket["quantity"] += quantity
                bucket["cost"] += ingredient.cost_amount * Decimal(entry.portions)
    rows = []
    for item in sorted(totals.values(), key=lambda value: value["cost"], reverse=True):
        quantity_kg = (item["quantity"] / Decimal("1000")).quantize(Decimal("0.001"))
        rows.append({**item, "quantity_kg": quantity_kg})
    return rows


def monthly_cost_chart(organization: Organization) -> list[dict]:
    buckets: dict[str, Decimal] = {}
    for day in MenuDay.objects.filter(organization=organization).order_by("date"):
        month_key = day.date.strftime("%Y-%m")
        buckets[month_key] = buckets.get(month_key, Decimal("0")) + day.total_cost
    if not buckets:
        return []
    total_cost = sum(buckets.values(), Decimal("0")) or Decimal("1")
    colors = ["#2ebc13", "#0f5132", "#ff6b00", "#198754", "#0d6efd", "#ffc107", "#dc3545"]
    offset = Decimal("0")
    rows = []
    for index, (label, cost) in enumerate(buckets.items()):
        percent = (cost / total_cost) * Decimal("100")
        rows.append(
            {
                "label": label,
                "cost": cost,
                "percent": int(percent),
                "dash": float(percent),
                "dash_gap": float(Decimal("100") - percent),
                "dash_offset": float(-offset),
                "color": colors[index % len(colors)],
            }
        )
        offset += percent
    return rows


def monthly_cost_total(organization: Organization) -> Decimal:
    total = Decimal("0")
    for day in MenuDay.objects.filter(organization=organization):
        total += day.total_cost
    return total


def top_cost_products(organization: Organization, limit: int = 8) -> list[dict]:
    return product_requirement_summary(organization)[:limit]


def generate_ai_menu_suggestion(organization: Organization, prompt: str) -> AISuggestion:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None

    dishes = list(Dish.objects.filter(organization=organization).values_list("name", flat=True)[:80])
    products = list(Product.objects.filter(organization=organization).values_list("name", flat=True)[:120])
    body = {
        "model": os.environ.get("OPENAI_MENU_MODEL", "gpt-5"),
        "input": (
            "Tashkilot uchun amaliy menyu tavsiyasi tuz. Mavjud taom va mahsulotlarga tayan. "
            "Javobni o'zbek tilida qisqa jadval va ogohlantirishlar bilan ber.\n"
            f"So'rov: {prompt}\n"
            f"Taomlar: {json.dumps(dishes, ensure_ascii=False)}\n"
            f"Mahsulotlar: {json.dumps(products, ensure_ascii=False)}"
        ),
    }
    request = Request(
        OPENAI_RESPONSES_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=45) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError) as error:
        return AISuggestion.objects.create(organization=organization, prompt=prompt, response=f"AI xatosi: {error}")

    text = payload.get("output_text") or ""
    if not text:
        parts = []
        for item in payload.get("output", []):
            for content in item.get("content", []):
                if content.get("text"):
                    parts.append(content["text"])
        text = "\n".join(parts) or "AI javobi bo'sh qaytdi."
    return AISuggestion.objects.create(organization=organization, prompt=prompt, response=text)


def telegram_api_call(method: str, payload: dict | None = None) -> dict:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return {"ok": False, "description": "TELEGRAM_BOT_TOKEN sozlanmagan."}
    body = json.dumps(payload or {}).encode("utf-8")
    request = Request(
        TELEGRAM_API_URL.format(token=token, method=method),
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        return {"ok": False, "description": error.read().decode("utf-8", errors="replace")}
    except URLError as error:
        return {"ok": False, "description": str(error)}


def send_telegram_chat_message(chat_id: str, text: str) -> bool:
    payload = telegram_api_call("sendMessage", {"chat_id": chat_id, "text": text})
    return bool(payload.get("ok"))


def send_telegram_message(subscription: TelegramSubscription, text: str) -> bool:
    if not subscription.is_active:
        return False
    return send_telegram_chat_message(subscription.chat_id, text)


def create_upload_job(organization: Organization, uploaded_file: UploadedFile, summary: str) -> ImportJob:
    return ImportJob.objects.create(
        organization=organization,
        job_type=ImportJob.JobType.EXCEL,
        status=ImportJob.Status.SUCCESS,
        source=uploaded_file.name,
        summary=summary,
        completed_at=timezone.now(),
    )
