from __future__ import annotations

import csv
import json
import os
import re
from decimal import Decimal, InvalidOperation
from io import StringIO
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.core.management.base import BaseCommand, CommandError

from menu.management.commands.import_menu_zip import normalize_text
from menu.models import Organization, Product


NAME_KEYS = ("name", "product", "mahsulot", "махсулот", "mahsulot_nomi", "product_name")
PRICE_KEYS = ("price", "narx", "цена", "narxi", "price_per_kg", "kg_price")
USER_AGENT = "Dietologiya-price-updater/1.0"
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"


def parse_price(value) -> Decimal | None:
    cleaned = str(value or "").strip().lower()
    if not cleaned:
        return None
    for token in ("so'm", "som", "sum", "uzs", "сум", "сўм", " "):
        cleaned = cleaned.replace(token, "")
    cleaned = cleaned.replace(",", ".")
    try:
        price = Decimal(cleaned)
    except InvalidOperation:
        return None
    return price if price > 0 else None


def first_present(row: dict, keys: tuple[str, ...]):
    normalized = {normalize_text(key): value for key, value in row.items()}
    for key in keys:
        if normalize_text(key) in normalized:
            return normalized[normalize_text(key)]
    return None


def rows_from_json(payload: str) -> list[dict]:
    data = json.loads(payload)
    if isinstance(data, dict):
        if "products" in data:
            data = data["products"]
        elif "prices" in data:
            data = data["prices"]
        else:
            data = [{"name": name, "price": price} for name, price in data.items()]
    if not isinstance(data, list):
        raise CommandError("JSON source must be a list, object, or contain products/prices list.")
    return [item for item in data if isinstance(item, dict)]


def rows_from_csv(payload: str) -> list[dict]:
    reader = csv.DictReader(StringIO(payload))
    return list(reader)


def price_map_from_payload(payload: str, source_url: str) -> dict[str, Decimal]:
    stripped = payload.lstrip()
    rows = rows_from_json(payload) if stripped.startswith(("{", "[")) else rows_from_csv(payload)
    prices = {}
    for row in rows:
        name = first_present(row, NAME_KEYS)
        price = parse_price(first_present(row, PRICE_KEYS))
        if not name or price is None:
            continue
        prices[normalize_text(name)] = price
    if not prices:
        raise CommandError(f"No product prices found in source: {source_url}")
    return prices


def response_text(payload: dict) -> str:
    if payload.get("output_text"):
        return payload["output_text"]

    parts = []
    for item in payload.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if text:
                parts.append(text)
    return "\n".join(parts)


def extract_json_text(text: str) -> str:
    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    start = min([index for index in (text.find("["), text.find("{")) if index >= 0], default=-1)
    end = max(text.rfind("]"), text.rfind("}"))
    if start >= 0 and end > start:
        return text[start:end + 1]
    return text


def product_names(products) -> list[str]:
    seen = set()
    names = []
    for product in products:
        normalized = normalize_text(product.name)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        names.append(product.name)
    return names


class Command(BaseCommand):
    help = "Update product prices from an internet CSV/JSON source or OpenAI web-search AI."

    def add_arguments(self, parser):
        parser.add_argument("--url", help="Internet CSV/JSON URL with product names and prices.")
        parser.add_argument("--ai-latest", action="store_true", help="Use OpenAI web search to find latest prices.")
        parser.add_argument("--city", default="Tashkent", help="City for AI price search.")
        parser.add_argument("--country", default="UZ", help="Two-letter country code for AI price search.")
        parser.add_argument("--model", default=os.environ.get("OPENAI_PRICE_MODEL", "gpt-5"))
        parser.add_argument("--organization", help="Update only one organization by name.")
        parser.add_argument("--timeout", type=int, default=20)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        products = Product.objects.all()
        if options.get("organization"):
            organization = Organization.objects.filter(name=options["organization"]).first()
            if not organization:
                raise CommandError(f"Organization not found: {options['organization']}")
            products = products.filter(organization=organization)
        products = list(products)

        if bool(options.get("url")) == bool(options.get("ai_latest")):
            raise CommandError("Provide exactly one of --url or --ai-latest.")

        if options.get("url"):
            source_url = options["url"]
            payload = self._fetch(source_url, options["timeout"])
            prices = price_map_from_payload(payload, source_url)
        else:
            prices = self._fetch_ai_latest_prices(products, options)

        updated = 0
        matched = 0
        for product in products:
            price = prices.get(normalize_text(product.name))
            if price is None:
                continue
            matched += 1
            if product.price_per_kg == price:
                continue
            self.stdout.write(f"{product.name}: {product.price_per_kg} -> {price}")
            if not options["dry_run"]:
                product.price_per_kg = price
                product.save(update_fields=["price_per_kg"])
            updated += 1

        mode = "Dry run" if options["dry_run"] else "Updated"
        self.stdout.write(self.style.SUCCESS(
            f"{mode}: {updated}. Matched products: {matched}. Source prices: {len(prices)}"
        ))

    def _fetch(self, source_url: str, timeout: int) -> str:
        if not source_url.startswith(("http://", "https://")):
            raise CommandError("URL must start with http:// or https://")
        request = Request(source_url, headers={"User-Agent": USER_AGENT})
        try:
            with urlopen(request, timeout=timeout) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return response.read().decode(charset)
        except URLError as error:
            raise CommandError(f"Could not fetch price source: {error}") from error

    def _fetch_ai_latest_prices(self, products: list[Product], options) -> dict[str, Decimal]:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise CommandError("OPENAI_API_KEY is required for --ai-latest.")

        names = product_names(products)
        if not names:
            raise CommandError("No products found to update.")

        prompt = (
            "Find the latest available food product prices for Uzbekistan. "
            f"Prefer current market or retail prices in {options['city']}. "
            "Return only valid JSON, no markdown. Format: "
            "[{\"name\":\"same product name from input\",\"price\":12345,\"unit\":\"kg\","
            "\"source\":\"URL or source title\",\"date\":\"YYYY-MM-DD if known\"}]. "
            "Use UZS per kilogram for solid products and UZS per liter for liquids. "
            "If a reliable current price is not found, omit that product. "
            "Input products: " + json.dumps(names, ensure_ascii=False)
        )
        body = {
            "model": options["model"],
            "tools": [
                {
                    "type": "web_search",
                    "user_location": {
                        "type": "approximate",
                        "country": options["country"],
                        "city": options["city"],
                        "timezone": "Asia/Tashkent",
                    },
                }
            ],
            "tool_choice": "auto",
            "input": prompt,
        }
        request = Request(
            OPENAI_RESPONSES_URL,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=options["timeout"]) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            message = error.read().decode("utf-8", errors="replace")
            raise CommandError(f"OpenAI price AI request failed: {message}") from error
        except URLError as error:
            raise CommandError(f"OpenAI price AI request failed: {error}") from error

        text = response_text(payload)
        if not text:
            raise CommandError("OpenAI price AI returned no text.")
        return price_map_from_payload(extract_json_text(text), "OpenAI web-search AI")
