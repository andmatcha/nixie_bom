#!/usr/bin/env python3
"""Fetch Digi-Key product data for agent-friendly BOM workflows.

This tool uses Digi-Key Product Information V4 instead of scraping product
pages. It prints normalized JSON so another agent or script can consume price,
availability, specifications, and datasheet links deterministically.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shlex
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


JsonDict = dict[str, Any]

DEFAULT_SITE = "JP"
DEFAULT_LANGUAGE = "ja"
DEFAULT_CURRENCY = "JPY"
DEFAULT_CACHE_TTL_SECONDS = 24 * 60 * 60
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MAX_RETRIES = 3
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"

PRODUCT_DETAILS_DOC_URL = (
    "https://developer.digikey.com/products/product-information-v4/"
    "productsearch/productdetails"
)


class DigikeyLookupError(Exception):
    """Base class for expected command errors."""


class DigikeyConfigError(DigikeyLookupError):
    """Raised when credentials or command configuration are incomplete."""


class DigikeyApiError(DigikeyLookupError):
    """Raised when Digi-Key returns an HTTP error or malformed response."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_body: Any = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body
        self.headers = headers or {}


class DotenvError(DigikeyLookupError):
    """Raised when a .env file exists but cannot be parsed."""


@dataclass(frozen=True)
class DigikeyConfig:
    client_id: str
    client_secret: str
    account_id: str | None
    environment: str
    site: str
    language: str
    currency: str
    cache_dir: Path
    cache_ttl_seconds: int
    timeout_seconds: int
    max_retries: int
    refresh: bool

    @property
    def api_base_url(self) -> str:
        if self.environment == "sandbox":
            return "https://sandbox-api.digikey.com"
        return "https://api.digikey.com"

    @property
    def token_url(self) -> str:
        return f"{self.api_base_url}/v1/oauth2/token"


class JsonCache:
    def __init__(self, cache_dir: Path, ttl_seconds: int, refresh: bool) -> None:
        self.cache_dir = cache_dir
        self.ttl_seconds = ttl_seconds
        self.refresh = refresh

    def get(self, key: str) -> JsonDict | None:
        if self.refresh or self.ttl_seconds <= 0:
            return None
        path = self._path_for_key(key)
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return None

        cached_at = payload.get("cached_at_epoch")
        if not isinstance(cached_at, (int, float)):
            return None
        if time.time() - cached_at > self.ttl_seconds:
            return None

        data = payload.get("data")
        return data if isinstance(data, dict) else None

    def set(self, key: str, data: JsonDict) -> None:
        if self.ttl_seconds <= 0:
            return
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path = self._path_for_key(key)
        tmp_path = path.with_suffix(".tmp")
        payload = {
            "cached_at": utc_now_iso(),
            "cached_at_epoch": time.time(),
            "data": data,
        }
        with tmp_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(tmp_path, path)

    def _path_for_key(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"


class DigikeyClient:
    def __init__(self, config: DigikeyConfig) -> None:
        self.config = config
        self.cache = JsonCache(
            config.cache_dir,
            config.cache_ttl_seconds,
            config.refresh,
        )
        self._access_token: str | None = None
        self._access_token_expires_at = 0.0

    def product_details(
        self,
        product_number: str,
        *,
        manufacturer_id: str | None = None,
        includes: str | None = None,
    ) -> tuple[JsonDict, bool]:
        cache_key = self._cache_key(
            "productdetails",
            product_number,
            manufacturer_id or "",
            includes or "",
        )
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached, True

        encoded_part = urllib.parse.quote(product_number, safe="")
        path = f"/products/v4/search/{encoded_part}/productdetails"
        query: dict[str, str] = {}
        if manufacturer_id:
            query["manufacturerId"] = manufacturer_id
        if includes:
            query["includes"] = includes

        data = self._get_json(path, query=query)
        self.cache.set(cache_key, data)
        return data, False

    def alternate_packaging(self, product_number: str) -> tuple[JsonDict, bool]:
        cache_key = self._cache_key("alternatepackaging", product_number)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached, True

        encoded_part = urllib.parse.quote(product_number, safe="")
        data = self._get_json(f"/products/v4/search/{encoded_part}/alternatepackaging")
        self.cache.set(cache_key, data)
        return data, False

    def substitutions(
        self,
        product_number: str,
        *,
        includes: str | None = None,
    ) -> tuple[JsonDict, bool]:
        cache_key = self._cache_key("substitutions", product_number, includes or "")
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached, True

        encoded_part = urllib.parse.quote(product_number, safe="")
        query = {"includes": includes} if includes else None
        data = self._get_json(
            f"/products/v4/search/{encoded_part}/substitutions",
            query=query,
        )
        self.cache.set(cache_key, data)
        return data, False

    def recommended_products(
        self,
        product_number: str,
        *,
        limit: int = 10,
        search_option_list: str = "InStock,ExcludeNonStock,RoHSCompliant",
        exclude_marketplace_products: bool = True,
    ) -> tuple[JsonDict, bool]:
        cache_key = self._cache_key(
            "recommendedproducts",
            product_number,
            str(limit),
            search_option_list,
            str(exclude_marketplace_products),
        )
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached, True

        encoded_part = urllib.parse.quote(product_number, safe="")
        query = {
            "limit": str(limit),
            "searchOptionList": search_option_list,
            "excludeMarketPlaceProducts": str(exclude_marketplace_products).lower(),
        }
        data = self._get_json(
            f"/products/v4/search/{encoded_part}/recommendedproducts",
            query=query,
        )
        self.cache.set(cache_key, data)
        return data, False

    def keyword_search(
        self,
        keywords: str,
        *,
        limit: int = 10,
        offset: int = 0,
        minimum_quantity_available: int | None = None,
        search_options: list[str] | None = None,
        sort_field: str = "QuantityAvailable",
        sort_order: str = "Descending",
    ) -> tuple[JsonDict, bool]:
        body: JsonDict = {
            "Keywords": keywords,
            "Limit": limit,
            "Offset": offset,
            "SortOptions": {
                "Field": sort_field,
                "SortOrder": sort_order,
            },
        }
        filter_request: JsonDict = {}
        if minimum_quantity_available is not None:
            filter_request["MinimumQuantityAvailable"] = minimum_quantity_available
        if search_options:
            filter_request["SearchOptions"] = search_options
        if filter_request:
            body["FilterOptionsRequest"] = filter_request

        cache_key = self._cache_key(
            "keyword",
            json.dumps(body, sort_keys=True, ensure_ascii=True),
        )
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached, True

        data = self._post_json("/products/v4/search/keyword", body=body)
        self.cache.set(cache_key, data)
        return data, False

    def _cache_key(self, *parts: str) -> str:
        material = {
            "environment": self.config.environment,
            "site": self.config.site,
            "language": self.config.language,
            "currency": self.config.currency,
            "account_id": self.config.account_id or "",
            "parts": parts,
        }
        encoded = json.dumps(material, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def _get_json(self, path: str, *, query: dict[str, str] | None = None) -> JsonDict:
        url = f"{self.config.api_base_url}{path}"
        if query:
            url = f"{url}?{urllib.parse.urlencode(query)}"
        headers = self._api_headers()
        return self._request_json("GET", url, headers=headers, auth=True)

    def _post_json(self, path: str, *, body: JsonDict) -> JsonDict:
        url = f"{self.config.api_base_url}{path}"
        headers = self._api_headers()
        headers["Content-Type"] = "application/json"
        encoded_body = json.dumps(body).encode("utf-8")
        return self._request_json("POST", url, headers=headers, body=encoded_body, auth=True)

    def _api_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self._get_access_token()}",
            "User-Agent": "nixie-bom-digikey-lookup/1.0",
            "X-DIGIKEY-Client-Id": self.config.client_id,
            "X-DIGIKEY-Locale-Currency": self.config.currency,
            "X-DIGIKEY-Locale-Language": self.config.language,
            "X-DIGIKEY-Locale-Site": self.config.site,
        }
        if self.config.account_id:
            headers["X-DIGIKEY-Account-Id"] = self.config.account_id
        return headers

    def _get_access_token(self) -> str:
        if (
            self._access_token
            and time.time() < self._access_token_expires_at - 30
        ):
            return self._access_token

        form = urllib.parse.urlencode(
            {
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "grant_type": "client_credentials",
            }
        ).encode("utf-8")
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "nixie-bom-digikey-lookup/1.0",
        }
        payload = self._request_json(
            "POST",
            self.config.token_url,
            headers=headers,
            body=form,
            auth=False,
        )
        token = payload.get("access_token")
        if not isinstance(token, str) or not token:
            raise DigikeyApiError("Digi-Key token response did not include access_token")
        expires_in = payload.get("expires_in", 600)
        try:
            expires_in_seconds = int(expires_in)
        except (TypeError, ValueError):
            expires_in_seconds = 600

        self._access_token = token
        self._access_token_expires_at = time.time() + expires_in_seconds
        return token

    def _request_json(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        body: bytes | None = None,
        auth: bool,
    ) -> JsonDict:
        last_error: DigikeyApiError | None = None
        did_refresh_token = False

        for attempt in range(self.config.max_retries + 1):
            request = urllib.request.Request(
                url,
                data=body,
                headers=headers,
                method=method,
            )
            try:
                with urllib.request.urlopen(  # noqa: S310 - endpoint is fixed by config.
                    request,
                    timeout=self.config.timeout_seconds,
                ) as response:
                    raw = response.read().decode("utf-8")
                    parsed = json.loads(raw) if raw else {}
                    if not isinstance(parsed, dict):
                        raise DigikeyApiError("Digi-Key returned non-object JSON")
                    return parsed
            except urllib.error.HTTPError as error:
                response_body = read_error_body(error)
                retry_after = parse_retry_after(error.headers.get("Retry-After"))
                headers_dict = dict(error.headers.items())

                if auth and error.code == 401 and not did_refresh_token:
                    self._access_token = None
                    headers = self._api_headers()
                    did_refresh_token = True
                    continue

                last_error = DigikeyApiError(
                    f"Digi-Key API returned HTTP {error.code}",
                    status_code=error.code,
                    response_body=response_body,
                    headers=headers_dict,
                )
                if error.code in {429, 500, 502, 503, 504} and attempt < self.config.max_retries:
                    time.sleep(retry_after if retry_after is not None else 2**attempt)
                    continue
                raise last_error
            except urllib.error.URLError as error:
                last_error = DigikeyApiError(f"Network error: {error.reason}")
                if attempt < self.config.max_retries:
                    time.sleep(2**attempt)
                    continue
                raise last_error
            except json.JSONDecodeError as error:
                raise DigikeyApiError(f"Digi-Key returned invalid JSON: {error}") from error

        if last_error:
            raise last_error
        raise DigikeyApiError("Digi-Key request failed")


def normalize_product_details(
    raw: JsonDict,
    *,
    query: JsonDict,
    config: DigikeyConfig,
    requested_quantity: int,
    cache_hit: bool,
    include_raw: bool,
) -> JsonDict:
    product = raw.get("Product") or {}
    if not isinstance(product, dict):
        product = {}

    parameters = normalize_parameters(product.get("Parameters"))
    variations = [
        normalize_variation(variation, requested_quantity=requested_quantity)
        for variation in product.get("ProductVariations") or []
        if isinstance(variation, dict)
    ]
    best_offer = choose_best_offer(variations)
    status = named_value(product.get("ProductStatus"), "Status")
    classifications = product.get("Classifications") or {}
    description = product.get("Description") or {}

    output: JsonDict = {
        "ok": True,
        "fetched_at": utc_now_iso(),
        "cache": {
            "hit": cache_hit,
            "ttl_seconds": config.cache_ttl_seconds,
        },
        "query": query,
        "source": source_block(config),
        "product": {
            "manufacturer": normalize_id_name(product.get("Manufacturer")),
            "manufacturer_part_number": product.get("ManufacturerProductNumber"),
            "description": value_or_none(description, "ProductDescription"),
            "detailed_description": value_or_none(description, "DetailedDescription"),
            "category": normalize_category(product.get("Category")),
            "series": normalize_id_name(product.get("Series")),
            "product_url": product.get("ProductUrl"),
            "datasheet_url": product.get("DatasheetUrl"),
            "photo_url": product.get("PhotoUrl"),
            "quantity_available": product.get("QuantityAvailable"),
            "unit_price": product.get("UnitPrice"),
            "status": status,
            "status_flags": {
                "normally_stocking": product.get("NormallyStocking"),
                "discontinued": product.get("Discontinued"),
                "end_of_life": product.get("EndOfLife"),
                "back_order_not_allowed": product.get("BackOrderNotAllowed"),
                "non_cancelable_non_returnable": product.get("Ncnr"),
            },
            "compliance": {
                "rohs_status": value_or_none(classifications, "RohsStatus"),
                "reach_status": value_or_none(classifications, "ReachStatus"),
                "moisture_sensitivity_level": value_or_none(
                    classifications,
                    "MoistureSensitivityLevel",
                ),
                "export_control_class_number": value_or_none(
                    classifications,
                    "ExportControlClassNumber",
                ),
                "htsus_code": value_or_none(classifications, "HtsusCode"),
            },
            "manufacturer_lead_weeks": product.get("ManufacturerLeadWeeks"),
            "manufacturer_public_quantity": product.get("ManufacturerPublicQuantity"),
            "date_last_buy_chance": product.get("DateLastBuyChance"),
            "shipping_info": product.get("ShippingInfo"),
            "other_names": product.get("OtherNames") or [],
            "parameters": parameters,
            "parameter_map": {
                parameter["name"]: parameter["value"]
                for parameter in parameters
                if parameter.get("name") is not None
            },
            "variations": variations,
            "best_offer": best_offer,
        },
        "warnings": build_warnings(product, requested_quantity, best_offer),
    }
    if include_raw:
        output["raw"] = raw
    return output


def normalize_variation(variation: JsonDict, *, requested_quantity: int) -> JsonDict:
    standard_pricing = normalize_price_breaks(variation.get("StandardPricing"))
    my_pricing = normalize_price_breaks(variation.get("MyPricing"))
    min_order_quantity = int_or_none(variation.get("MinimumOrderQuantity")) or 1
    quantity_available = int_or_none(variation.get("QuantityAvailableforPackageType"))

    selected_price = select_price(
        my_pricing if my_pricing else standard_pricing,
        requested_quantity=requested_quantity,
        min_order_quantity=min_order_quantity,
    )
    if selected_price:
        selected_price["pricing_type"] = "my" if my_pricing else "standard"

    return {
        "digikey_product_number": variation.get("DigiKeyProductNumber"),
        "package_type": named_value(variation.get("PackageType"), "Name"),
        "supplier": normalize_id_name(variation.get("Supplier")),
        "quantity_available": quantity_available,
        "minimum_order_quantity": min_order_quantity,
        "standard_package": variation.get("StandardPackage"),
        "max_quantity_for_distribution": variation.get("MaxQuantityForDistribution"),
        "marketplace": variation.get("MarketPlace"),
        "tariff_active": variation.get("TariffActive"),
        "digi_reel_fee": variation.get("DigiReelFee"),
        "standard_pricing": standard_pricing,
        "my_pricing": my_pricing,
        "selected_price": selected_price,
    }


def normalize_parameters(value: Any) -> list[JsonDict]:
    if not isinstance(value, list):
        return []
    parameters: list[JsonDict] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        parameters.append(
            {
                "id": item.get("ParameterId"),
                "name": item.get("ParameterText"),
                "type": item.get("ParameterType"),
                "value_id": item.get("ValueId"),
                "value": item.get("ValueText"),
            }
        )
    return parameters


def normalize_price_breaks(value: Any) -> list[JsonDict]:
    if not isinstance(value, list):
        return []
    breaks: list[JsonDict] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        breaks.append(
            {
                "break_quantity": item.get("BreakQuantity"),
                "unit_price": item.get("UnitPrice"),
                "total_price": item.get("TotalPrice"),
            }
        )
    return sorted(
        breaks,
        key=lambda item: int_or_none(item.get("break_quantity")) or 0,
    )


def select_price(
    price_breaks: list[JsonDict],
    *,
    requested_quantity: int,
    min_order_quantity: int,
) -> JsonDict | None:
    if not price_breaks:
        return None
    purchase_quantity = max(requested_quantity, min_order_quantity, 1)
    eligible = [
        item
        for item in price_breaks
        if (int_or_none(item.get("break_quantity")) or 0) <= purchase_quantity
    ]
    chosen = eligible[-1] if eligible else price_breaks[0]
    unit_price = float_or_none(chosen.get("unit_price"))
    estimated_total = unit_price * purchase_quantity if unit_price is not None else None
    return {
        "requested_quantity": requested_quantity,
        "purchase_quantity": purchase_quantity,
        "break_quantity": chosen.get("break_quantity"),
        "unit_price": unit_price,
        "estimated_total_price": round(estimated_total, 6)
        if estimated_total is not None
        else None,
    }


def choose_best_offer(variations: list[JsonDict]) -> JsonDict | None:
    candidates: list[JsonDict] = []
    for variation in variations:
        selected = variation.get("selected_price")
        if not isinstance(selected, dict):
            continue
        unit_price = float_or_none(selected.get("unit_price"))
        total_price = float_or_none(selected.get("estimated_total_price"))
        if unit_price is None or total_price is None:
            continue
        quantity_available = int_or_none(variation.get("quantity_available"))
        purchase_quantity = int_or_none(selected.get("purchase_quantity")) or 1
        in_stock_enough = quantity_available is None or quantity_available >= purchase_quantity
        candidates.append(
            {
                "digikey_product_number": variation.get("digikey_product_number"),
                "package_type": variation.get("package_type"),
                "supplier": variation.get("supplier"),
                "in_stock_enough": in_stock_enough,
                "quantity_available": quantity_available,
                **selected,
            }
        )
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda item: (
            not bool(item.get("in_stock_enough")),
            float_or_none(item.get("estimated_total_price")) or float("inf"),
            float_or_none(item.get("unit_price")) or float("inf"),
        ),
    )[0]


def build_warnings(
    product: JsonDict,
    requested_quantity: int,
    best_offer: JsonDict | None,
) -> list[str]:
    warnings: list[str] = []
    if product.get("Discontinued"):
        warnings.append("Product is marked discontinued by Digi-Key.")
    if product.get("EndOfLife"):
        warnings.append("Product is marked end-of-life by Digi-Key.")
    if product.get("Ncnr"):
        warnings.append("Product is marked non-cancellable and non-returnable.")
    if product.get("NormallyStocking") is False:
        warnings.append("Product is not normally stocked.")
    if not product.get("DatasheetUrl"):
        warnings.append("No datasheet URL was returned.")
    quantity_available = int_or_none(product.get("QuantityAvailable"))
    if quantity_available is not None and quantity_available < requested_quantity:
        warnings.append(
            "Total available quantity is lower than the requested quantity."
        )
    if best_offer is None:
        warnings.append("No usable pricing break was returned.")
    elif not best_offer.get("in_stock_enough"):
        warnings.append("Best priced variation does not have enough stock.")
    return warnings


def normalize_id_name(value: Any) -> JsonDict | None:
    if not isinstance(value, dict):
        return None
    result = {
        "id": value.get("Id"),
        "name": value.get("Name"),
    }
    return result if result["id"] is not None or result["name"] is not None else None


def normalize_category(value: Any) -> JsonDict | None:
    if not isinstance(value, dict):
        return None
    return {
        "id": value.get("CategoryId"),
        "name": value.get("Name"),
        "parent_id": value.get("ParentId"),
        "product_count": value.get("ProductCount"),
    }


def named_value(value: Any, field_name: str) -> str | None:
    if isinstance(value, dict):
        field = value.get(field_name)
        return str(field) if field is not None else None
    return None


def value_or_none(value: Any, key: str) -> Any:
    return value.get(key) if isinstance(value, dict) else None


def load_dotenv(path: Path = DEFAULT_ENV_FILE, *, override: bool = False) -> bool:
    """Load KEY=VALUE pairs from .env without overriding shell env by default."""
    if not path.exists():
        return False
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise DotenvError(f"Could not read .env file: {path}") from error

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            raise DotenvError(f"Invalid .env line {line_number}: missing '='")

        key, raw_value = line.split("=", 1)
        key = key.strip()
        if not is_valid_env_key(key):
            raise DotenvError(f"Invalid .env line {line_number}: invalid key '{key}'")
        if not override and key in os.environ:
            continue

        os.environ[key] = parse_env_value(raw_value)
    return True


def is_valid_env_key(key: str) -> bool:
    if not key or key[0].isdigit():
        return False
    return all(char.isalnum() or char == "_" for char in key)


def parse_env_value(raw_value: str) -> str:
    value = strip_env_comment(raw_value).strip()
    if not value:
        return ""
    try:
        parsed = shlex.split(value, posix=True)
    except ValueError as error:
        raise DotenvError(f"Invalid quoted value in .env: {error}") from error
    if len(parsed) == 1:
        return parsed[0]
    if len(parsed) == 0:
        return ""
    raise DotenvError("Invalid .env value: use quotes for values containing spaces")


def strip_env_comment(value: str) -> str:
    quote: str | None = None
    escaped = False
    for index, char in enumerate(value):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char in {"'", '"'}:
            if quote == char:
                quote = None
            elif quote is None:
                quote = char
            continue
        if char == "#" and quote is None:
            previous = value[index - 1] if index > 0 else " "
            if previous.isspace():
                return value[:index]
    return value


def process_part(args: argparse.Namespace) -> JsonDict:
    config = config_from_args(args)
    client = DigikeyClient(config)
    raw, cache_hit = client.product_details(
        args.product_number,
        manufacturer_id=args.manufacturer_id,
        includes=args.includes,
    )
    return normalize_product_details(
        raw,
        query={
            "product_number": args.product_number,
            "manufacturer_id": args.manufacturer_id,
            "includes": args.includes,
            "requested_quantity": args.quantity,
        },
        config=config,
        requested_quantity=args.quantity,
        cache_hit=cache_hit,
        include_raw=args.include_raw,
    )


def process_bom(args: argparse.Namespace) -> JsonDict:
    config = config_from_args(args)
    client = DigikeyClient(config)
    csv_path = Path(args.csv_path)
    with csv_path.open("r", encoding=args.encoding, newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    digikey_column = find_column(
        fieldnames,
        [
            "Digi-Key Part Number",
            "DigiKey Part Number",
            "DK Part Number",
            "Digi-Key PN",
            "Digikey PN",
        ],
    )
    manufacturer_part_column = find_column(
        fieldnames,
        [
            "Manufacturer Part Number",
            "Manufacturer PN",
            "MPN",
            "Part Number",
        ],
    )
    quantity_column = find_column(fieldnames, ["Quantity", "Qty"])
    reference_column = find_column(
        fieldnames,
        [
            "Reference Designator",
            "Customer Reference",
            "Designator",
            "RefDes",
        ],
    )

    line_items: list[JsonDict] = []
    total_estimated_price = 0.0
    ok_count = 0

    for line_index, row in enumerate(rows, start=2):
        product_number = first_nonempty(
            row.get(digikey_column) if digikey_column else None,
            row.get(manufacturer_part_column) if manufacturer_part_column else None,
        )
        quantity = parse_quantity(row.get(quantity_column) if quantity_column else None)
        reference = row.get(reference_column) if reference_column else None
        item: JsonDict = {
            "line": line_index,
            "input": {
                "product_number": product_number,
                "quantity": quantity,
                "reference": reference,
                "used_column": digikey_column if row.get(digikey_column or "") else manufacturer_part_column,
            },
        }
        if not product_number:
            item["ok"] = False
            item["error"] = "No Digi-Key or manufacturer part number column value was found."
            line_items.append(item)
            continue

        try:
            raw, cache_hit = client.product_details(product_number)
            normalized = normalize_product_details(
                raw,
                query={
                    "product_number": product_number,
                    "requested_quantity": quantity,
                    "source_csv": str(csv_path),
                    "line": line_index,
                },
                config=config,
                requested_quantity=quantity,
                cache_hit=cache_hit,
                include_raw=args.include_raw,
            )
            product = normalized["product"]
            best_offer = product.get("best_offer") or {}
            estimated = float_or_none(best_offer.get("estimated_total_price"))
            if estimated is not None:
                total_estimated_price += estimated
            item.update(
                {
                    "ok": True,
                    "cache": normalized["cache"],
                    "product": product,
                    "warnings": normalized["warnings"],
                }
            )
            ok_count += 1
        except DigikeyLookupError as error:
            item["ok"] = False
            item["error"] = error_to_json(error)
        line_items.append(item)

    result: JsonDict = {
        "ok": all(item.get("ok") for item in line_items),
        "fetched_at": utc_now_iso(),
        "source": source_block(config),
        "input": {
            "csv_path": str(csv_path),
            "encoding": args.encoding,
            "rows": len(rows),
            "columns": {
                "digikey_part_number": digikey_column,
                "manufacturer_part_number": manufacturer_part_column,
                "quantity": quantity_column,
                "reference": reference_column,
            },
        },
        "summary": {
            "ok_count": ok_count,
            "error_count": len(line_items) - ok_count,
            "estimated_total_price": round(total_estimated_price, 6),
            "currency": config.currency,
        },
        "line_items": line_items,
    }
    return result


def config_from_args(args: argparse.Namespace) -> DigikeyConfig:
    client_id = args.client_id or getenv_first("DIGIKEY_CLIENT_ID", "CLIENT_ID")
    client_secret = args.client_secret or getenv_first(
        "DIGIKEY_CLIENT_SECRET",
        "CLIENT_SECRET",
    )
    account_id = args.account_id or getenv_first("DIGIKEY_ACCOUNT_ID", "ACCOUNT_ID")
    if not client_id or not client_secret:
        raise DigikeyConfigError(
            "DIGIKEY_CLIENT_ID/DIGIKEY_CLIENT_SECRET or CLIENT_ID/CLIENT_SECRET are required."
        )
    environment = (
        args.environment
        or getenv_first("DIGIKEY_ENV", "DIGIKEY_ENVIRONMENT")
        or "production"
    ).lower()
    if environment not in {"production", "sandbox"}:
        raise DigikeyConfigError("--environment must be production or sandbox.")
    return DigikeyConfig(
        client_id=client_id,
        client_secret=client_secret,
        account_id=account_id,
        environment=environment,
        site=(args.site or os.getenv("DIGIKEY_SITE") or DEFAULT_SITE).upper(),
        language=(args.language or os.getenv("DIGIKEY_LANGUAGE") or DEFAULT_LANGUAGE),
        currency=(args.currency or os.getenv("DIGIKEY_CURRENCY") or DEFAULT_CURRENCY).upper(),
        cache_dir=Path(args.cache_dir or os.getenv("DIGIKEY_CACHE_DIR") or ".cache/digikey"),
        cache_ttl_seconds=args.cache_ttl_seconds,
        timeout_seconds=args.timeout,
        max_retries=args.max_retries,
        refresh=args.refresh,
    )


def getenv_first(*keys: str) -> str | None:
    for key in keys:
        value = os.getenv(key)
        if value:
            return value
    return None


def source_block(config: DigikeyConfig) -> JsonDict:
    return {
        "provider": "Digi-Key",
        "api": "Product Information V4",
        "environment": config.environment,
        "endpoint": "/products/v4/search/{productNumber}/productdetails",
        "documentation": PRODUCT_DETAILS_DOC_URL,
        "site": config.site,
        "language": config.language,
        "currency": config.currency,
    }


def find_column(fieldnames: Iterable[str], candidates: Iterable[str]) -> str | None:
    normalized = {normalize_column_name(name): name for name in fieldnames}
    for candidate in candidates:
        match = normalized.get(normalize_column_name(candidate))
        if match:
            return match
    return None


def normalize_column_name(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def first_nonempty(*values: str | None) -> str | None:
    for value in values:
        if value and value.strip():
            return value.strip()
    return None


def parse_quantity(value: str | None) -> int:
    if value is None or not str(value).strip():
        return 1
    try:
        quantity = int(float(str(value).strip()))
    except ValueError:
        return 1
    return max(quantity, 1)


def int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_retry_after(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return max(int(value), 0)
    except ValueError:
        return None


def read_error_body(error: urllib.error.HTTPError) -> Any:
    raw = error.read().decode("utf-8", errors="replace")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def error_to_json(error: BaseException) -> JsonDict:
    if isinstance(error, DigikeyApiError):
        return {
            "type": error.__class__.__name__,
            "message": str(error),
            "status_code": error.status_code,
            "response_body": error.response_body,
            "headers": {
                key: value
                for key, value in error.headers.items()
                if key.lower().startswith("x-")
                or key.lower() in {"retry-after", "content-type"}
            },
        }
    return {
        "type": error.__class__.__name__,
        "message": str(error),
    }


def build_error_response(error: BaseException) -> JsonDict:
    hints = [
        "Create a Digi-Key developer application subscribed to Product Information V4.",
        "Set DIGIKEY_CLIENT_ID and DIGIKEY_CLIENT_SECRET in the environment.",
        "For two-legged OAuth, set DIGIKEY_ACCOUNT_ID if your application requires it.",
        "Use --environment sandbox only with sandbox credentials.",
    ]
    return {
        "ok": False,
        "fetched_at": utc_now_iso(),
        "error": error_to_json(error),
        "hints": hints,
    }


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--client-id", help="Defaults to DIGIKEY_CLIENT_ID.")
    parser.add_argument("--client-secret", help="Defaults to DIGIKEY_CLIENT_SECRET.")
    parser.add_argument("--account-id", help="Defaults to DIGIKEY_ACCOUNT_ID.")
    parser.add_argument(
        "--environment",
        choices=["production", "sandbox"],
        default=None,
    )
    parser.add_argument("--site")
    parser.add_argument(
        "--language",
    )
    parser.add_argument(
        "--currency",
    )
    parser.add_argument(
        "--cache-dir",
    )
    parser.add_argument(
        "--cache-ttl-seconds",
        type=int,
        default=int(os.getenv("DIGIKEY_CACHE_TTL_SECONDS", DEFAULT_CACHE_TTL_SECONDS)),
    )
    parser.add_argument("--refresh", action="store_true", help="Ignore response cache.")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES)
    parser.add_argument("--include-raw", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("-o", "--output", help="Write JSON to this file instead of stdout.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch Digi-Key price, stock, specs, and datasheet URLs as JSON.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    part_parser = subparsers.add_parser("part", help="Fetch one product number.")
    add_common_arguments(part_parser)
    part_parser.add_argument("product_number")
    part_parser.add_argument("--manufacturer-id")
    part_parser.add_argument("--includes")
    part_parser.add_argument("--quantity", type=int, default=1)
    part_parser.set_defaults(handler=process_part)

    bom_parser = subparsers.add_parser("bom", help="Fetch all product numbers in a CSV BOM.")
    add_common_arguments(bom_parser)
    bom_parser.add_argument("csv_path")
    bom_parser.add_argument("--encoding", default="utf-8-sig")
    bom_parser.set_defaults(handler=process_bom)
    return parser


def emit_json(payload: JsonDict, *, pretty: bool, output: str | None) -> None:
    text = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2 if pretty else None,
        separators=None if pretty else (",", ":"),
    )
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(f"{text}\n", encoding="utf-8")
    else:
        print(text)


def main(argv: list[str] | None = None) -> int:
    command_args = sys.argv[1:] if argv is None else argv
    try:
        load_dotenv()
    except DigikeyLookupError as error:
        emit_json(
            build_error_response(error),
            pretty="--pretty" in command_args,
            output=None,
        )
        return 2
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        payload = args.handler(args)
        exit_code = 0 if payload.get("ok") else 2
    except DigikeyLookupError as error:
        payload = build_error_response(error)
        exit_code = 2
    except (OSError, ValueError) as error:
        payload = build_error_response(error)
        exit_code = 2

    emit_json(payload, pretty=args.pretty, output=args.output)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
