#!/usr/bin/env python3
"""Reusable helpers for Digi-Key-backed BOM reports."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Iterable

import digikey_lookup


JsonDict = dict[str, Any]
JPY = Decimal("0.01")

DIGIKEY_PART_COLUMNS = [
    "Digi-Key Part Number",
    "DigiKey Part Number",
    "DK Part Number",
    "Digi-Key PN",
    "Digikey PN",
]
MANUFACTURER_PART_COLUMNS = [
    "Manufacturer Part Number",
    "Manufacturer PN",
    "MPN",
    "Part Number",
]
QUANTITY_COLUMNS = ["Quantity", "Qty"]
REFERENCE_COLUMNS = [
    "Reference Designator",
    "Customer Reference",
    "Designator",
    "RefDes",
]


@dataclass(frozen=True)
class BomColumns:
    digikey_part_number: str | None
    manufacturer_part_number: str | None
    quantity: str | None
    reference: str | None


@dataclass(frozen=True)
class BomLine:
    line_number: int
    row: dict[str, str]
    product_number: str | None
    quantity: int
    reference: str | None
    used_column: str | None


def read_bom(path: Path, *, encoding: str = "utf-8-sig") -> tuple[list[BomLine], BomColumns]:
    with path.open("r", encoding=encoding, newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    columns = BomColumns(
        digikey_part_number=digikey_lookup.find_column(fieldnames, DIGIKEY_PART_COLUMNS),
        manufacturer_part_number=digikey_lookup.find_column(fieldnames, MANUFACTURER_PART_COLUMNS),
        quantity=digikey_lookup.find_column(fieldnames, QUANTITY_COLUMNS),
        reference=digikey_lookup.find_column(fieldnames, REFERENCE_COLUMNS),
    )

    lines: list[BomLine] = []
    for index, row in enumerate(rows, start=2):
        digikey_value = row.get(columns.digikey_part_number or "") if columns.digikey_part_number else None
        manufacturer_value = (
            row.get(columns.manufacturer_part_number or "")
            if columns.manufacturer_part_number
            else None
        )
        product_number = digikey_lookup.first_nonempty(digikey_value, manufacturer_value)
        used_column = columns.digikey_part_number if digikey_value else columns.manufacturer_part_number
        lines.append(
            BomLine(
                line_number=index,
                row=row,
                product_number=product_number,
                quantity=digikey_lookup.parse_quantity(row.get(columns.quantity or "")),
                reference=row.get(columns.reference or "") if columns.reference else None,
                used_column=used_column,
            )
        )
    return lines, columns


def fetch_bom(
    client: digikey_lookup.DigikeyClient,
    bom_path: Path,
    *,
    config: digikey_lookup.DigikeyConfig,
    encoding: str = "utf-8-sig",
    include_raw: bool = False,
) -> JsonDict:
    lines, columns = read_bom(bom_path, encoding=encoding)
    line_items: list[JsonDict] = []
    total = Decimal("0.00")
    ok_count = 0

    for line in lines:
        item: JsonDict = {
            "line": line.line_number,
            "input": {
                "product_number": line.product_number,
                "quantity": line.quantity,
                "reference": line.reference,
                "used_column": line.used_column,
            },
            "source_row": line.row,
        }
        if not line.product_number:
            item["ok"] = False
            item["error"] = "No Digi-Key or manufacturer part number column value was found."
            line_items.append(item)
            continue

        try:
            raw, cache_hit = client.product_details(line.product_number)
            normalized = digikey_lookup.normalize_product_details(
                raw,
                query={
                    "product_number": line.product_number,
                    "requested_quantity": line.quantity,
                    "source_csv": str(bom_path),
                    "line": line.line_number,
                },
                config=config,
                requested_quantity=line.quantity,
                cache_hit=cache_hit,
                include_raw=include_raw,
            )
            product = normalized["product"]
            best_offer = product.get("best_offer") or {}
            total += decimal_money(best_offer.get("estimated_total_price"))
            item.update(
                {
                    "ok": True,
                    "cache": normalized["cache"],
                    "product": product,
                    "availability": evaluate_availability(product, line.quantity),
                    "warnings": normalized["warnings"],
                }
            )
            ok_count += 1
        except digikey_lookup.DigikeyLookupError as error:
            item["ok"] = False
            item["error"] = digikey_lookup.error_to_json(error)
        line_items.append(item)

    return {
        "ok": all(item.get("ok") for item in line_items),
        "fetched_at": digikey_lookup.utc_now_iso(),
        "source": digikey_lookup.source_block(config),
        "input": {
            "csv_path": str(bom_path),
            "encoding": encoding,
            "rows": len(lines),
            "columns": {
                "digikey_part_number": columns.digikey_part_number,
                "manufacturer_part_number": columns.manufacturer_part_number,
                "quantity": columns.quantity,
                "reference": columns.reference,
            },
        },
        "summary": {
            "ok_count": ok_count,
            "error_count": len(line_items) - ok_count,
            "estimated_total_price": float(total),
            "currency": config.currency,
        },
        "line_items": line_items,
    }


def evaluate_availability(product: JsonDict, requested_quantity: int) -> JsonDict:
    best_offer = product.get("best_offer") or {}
    status_flags = product.get("status_flags") or {}
    status = product.get("status") or ""
    quantity_available = digikey_lookup.int_or_none(product.get("quantity_available"))
    purchase_quantity = digikey_lookup.int_or_none(best_offer.get("purchase_quantity")) or requested_quantity
    selected_variation = find_selected_variation(product)
    marketplace = bool(selected_variation.get("marketplace")) if selected_variation else False

    active = is_active_product(product)
    in_stock = quantity_available is not None and quantity_available >= purchase_quantity
    selected_in_stock = bool(best_offer.get("in_stock_enough"))
    immediate = active and in_stock and selected_in_stock and not marketplace

    reasons: list[str] = []
    if not active:
        reasons.append(f"status is {status or 'unknown'}")
    if status_flags.get("discontinued"):
        reasons.append("discontinued")
    if status_flags.get("end_of_life"):
        reasons.append("end of life")
    if not in_stock:
        reasons.append("insufficient total stock")
    if not selected_in_stock:
        reasons.append("selected package has insufficient stock")
    if marketplace:
        reasons.append("marketplace product")

    return {
        "active": active,
        "in_stock": in_stock,
        "immediate": immediate,
        "status": status,
        "quantity_available": quantity_available,
        "purchase_quantity": purchase_quantity,
        "selected_package_in_stock": selected_in_stock,
        "marketplace": marketplace,
        "reasons": reasons,
    }


def is_active_product(product: JsonDict) -> bool:
    flags = product.get("status_flags") or {}
    if flags.get("discontinued") or flags.get("end_of_life"):
        return False
    status = str(product.get("status") or "").strip().lower()
    active_words = {"active", "アクティブ"}
    return status in active_words


def find_selected_variation(product: JsonDict) -> JsonDict | None:
    best = product.get("best_offer") or {}
    selected_number = best.get("digikey_product_number")
    for variation in product.get("variations") or []:
        if variation.get("digikey_product_number") == selected_number:
            return variation
    return None


def price_rows(lookup: JsonDict) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in lookup.get("line_items", []):
        row = item.get("source_row") or {}
        product = item.get("product") or {}
        availability = item.get("availability") or {}
        best = product.get("best_offer") or {}
        rows.append(
            {
                "Line": item.get("line"),
                "Reference Designator": row.get("Reference Designator", item.get("input", {}).get("reference") or ""),
                "Quantity": item.get("input", {}).get("quantity", ""),
                "Purchase Quantity": best.get("purchase_quantity", ""),
                "Digi-Key Part Number": row.get("Digi-Key Part Number", item.get("input", {}).get("product_number") or ""),
                "Manufacturer": (product.get("manufacturer") or {}).get("name") or row.get("Manufacturer", ""),
                "Manufacturer Part Number": product.get("manufacturer_part_number") or row.get("Manufacturer Part Number", ""),
                "Description": row.get("Description", product.get("description") or ""),
                "Package": row.get("Package", ""),
                "Status": product.get("status", ""),
                "Active": bool_text(availability.get("active")),
                "Immediate": bool_text(availability.get("immediate")),
                "Quantity Available": availability.get("quantity_available", ""),
                "Package Type": best.get("package_type", ""),
                "Unit Price JPY": money(best.get("unit_price")),
                "Line Total JPY": money(best.get("estimated_total_price")),
                "Pricing Type": best.get("pricing_type", ""),
                "Product URL": product.get("product_url", ""),
                "Datasheet URL": product.get("datasheet_url", ""),
                "Notes": row.get("Notes", ""),
                "Warnings": "; ".join(item.get("warnings") or []),
                "Availability Reasons": "; ".join(availability.get("reasons") or []),
            }
        )
    return rows


def availability_rows(lookup: JsonDict) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in lookup.get("line_items", []):
        row = item.get("source_row") or {}
        product = item.get("product") or {}
        best = product.get("best_offer") or {}
        availability = item.get("availability") or {}
        rows.append(
            {
                "Line": item.get("line"),
                "Reference Designator": row.get("Reference Designator", item.get("input", {}).get("reference") or ""),
                "Quantity": item.get("input", {}).get("quantity", ""),
                "Purchase Quantity": availability.get("purchase_quantity", ""),
                "Digi-Key Part Number": row.get("Digi-Key Part Number", item.get("input", {}).get("product_number") or ""),
                "Manufacturer Part Number": product.get("manufacturer_part_number") or row.get("Manufacturer Part Number", ""),
                "Status": availability.get("status", ""),
                "Active": bool_text(availability.get("active")),
                "In Stock": bool_text(availability.get("in_stock")),
                "Immediate": bool_text(availability.get("immediate")),
                "Quantity Available": availability.get("quantity_available", ""),
                "Selected Package In Stock": bool_text(availability.get("selected_package_in_stock")),
                "Marketplace": bool_text(availability.get("marketplace")),
                "Unit Price JPY": money(best.get("unit_price")),
                "Line Total JPY": money(best.get("estimated_total_price")),
                "Product URL": product.get("product_url", ""),
                "Reasons": "; ".join(availability.get("reasons") or []),
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def total_from_price_rows(rows: Iterable[dict[str, Any]]) -> Decimal:
    total = Decimal("0.00")
    for row in rows:
        total += decimal_money(row.get("Line Total JPY"))
    return total


def summarize_by_note_group(rows: Iterable[dict[str, Any]]) -> dict[str, Decimal]:
    groups: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    for row in rows:
        notes = str(row.get("Notes") or "")
        group = notes.split(":", 1)[0].strip() if ":" in notes else "Unspecified"
        groups[group] += decimal_money(row.get("Line Total JPY"))
    return dict(groups)


def write_price_summary(path: Path, lookup: JsonDict, rows: list[dict[str, Any]], csv_path: Path) -> None:
    total = total_from_price_rows(rows)
    status_counts: dict[str, int] = defaultdict(int)
    for row in rows:
        status_counts[str(row.get("Status") or "Unknown")] += 1

    group_lines = "\n".join(
        f"| {group} | {amount:,.2f} |"
        for group, amount in sorted(summarize_by_note_group(rows).items())
    )
    status_lines = "\n".join(
        f"- {status}: {count} 明細" for status, count in sorted(status_counts.items())
    )
    warning_lines = "\n".join(
        f"| {row['Reference Designator']} | {row['Manufacturer Part Number']} | {row['Warnings'] or row['Availability Reasons']} |"
        for row in rows
        if row.get("Warnings") or row.get("Availability Reasons")
    )
    if not warning_lines:
        warning_lines = "| なし | なし | なし |"

    fetched = format_jst(lookup.get("fetched_at"))
    text = f"""# 部品代集計

Digi-Key Product Information V4 API を使用し、`{lookup.get('input', {}).get('csv_path')}` の全明細について価格を取得した。

## 集計結果

| 項目 | 値 |
| --- | ---: |
| 対象明細数 | {len(rows)} |
| 取得成功 | {lookup.get('summary', {}).get('ok_count')} |
| 取得失敗 | {lookup.get('summary', {}).get('error_count')} |
| 合計部品代 | {total:,.2f} JPY |

価格取得日時: {fetched}  
出力 CSV: `{csv_path}`

## 区分別小計

| 区分 | 小計 JPY |
| --- | ---: |
{group_lines}

## ステータス内訳

{status_lines}

## 注意事項

- 合計は Digi-Key API が返した商品単価を基にした部品代であり、送料、税、手数料は含まない。
- IN-12 ニキシー管本体および INS-1 本体は、現在の BOM に含まれていないため集計対象外である。
- `Purchase Quantity` は最小注文数量を考慮した購入数量であり、BOM 上の `Quantity` と異なる場合がある。
- `Immediate` が `no` の明細は、別途 `tools/digikey_bom_availability.py` の出力を確認する。

## 在庫・警告

| Reference Designator | Manufacturer Part Number | 警告 |
| --- | --- | --- |
{warning_lines}
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_availability_summary(path: Path, lookup: JsonDict, rows: list[dict[str, Any]], csv_path: Path) -> None:
    all_ok = all(row.get("Immediate") == "yes" for row in rows)
    problem_rows = [row for row in rows if row.get("Immediate") != "yes"]
    problem_lines = "\n".join(
        f"| {row['Reference Designator']} | {row['Manufacturer Part Number']} | {row['Status']} | {row['Quantity Available']} | {row['Reasons']} |"
        for row in problem_rows
    )
    if not problem_lines:
        problem_lines = "| なし | なし | なし | なし | なし |"

    text = f"""# Digi-Key 可用性チェック

`{lookup.get('input', {}).get('csv_path')}` の各明細について、Digi-Key 上でアクティブ、在庫あり、即時入手可能かを確認した。

| 項目 | 値 |
| --- | ---: |
| 対象明細数 | {len(rows)} |
| 即時入手可能 | {len(rows) - len(problem_rows)} |
| 要確認 | {len(problem_rows)} |
| 判定 | {'OK' if all_ok else 'NG'} |

確認日時: {format_jst(lookup.get('fetched_at'))}  
出力 CSV: `{csv_path}`

## 要確認明細

| Reference Designator | Manufacturer Part Number | Status | Quantity Available | 理由 |
| --- | --- | --- | ---: | --- |
{problem_lines}
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def decimal_money(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0.00")
    return Decimal(str(value)).quantize(JPY, rounding=ROUND_HALF_UP)


def money(value: Any) -> str:
    if value is None or value == "":
        return ""
    return f"{decimal_money(value):.2f}"


def bool_text(value: Any) -> str:
    return "yes" if bool(value) else "no"


def format_jst(value: str | None) -> str:
    if not value:
        return ""
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    jst = timezone(timedelta(hours=9))
    return timestamp.astimezone(jst).strftime("%Y-%m-%d %H:%M:%S JST")


def load_config_from_args(args: argparse.Namespace) -> digikey_lookup.DigikeyConfig:
    digikey_lookup.load_dotenv()
    return digikey_lookup.config_from_args(args)


def add_bom_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--client-id", help="Defaults to DIGIKEY_CLIENT_ID or CLIENT_ID.")
    parser.add_argument(
        "--client-secret",
        help="Defaults to DIGIKEY_CLIENT_SECRET or CLIENT_SECRET.",
    )
    parser.add_argument(
        "--account-id",
        help="Defaults to DIGIKEY_ACCOUNT_ID or ACCOUNT_ID.",
    )
    parser.add_argument("--environment", choices=["production", "sandbox"])
    parser.add_argument("--site")
    parser.add_argument("--language")
    parser.add_argument("--currency")
    parser.add_argument("--cache-dir")
    parser.add_argument(
        "--cache-ttl-seconds",
        type=int,
        default=digikey_lookup.DEFAULT_CACHE_TTL_SECONDS,
    )
    parser.add_argument("--refresh", action="store_true", help="Ignore response cache.")
    parser.add_argument("--timeout", type=int, default=digikey_lookup.DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--max-retries", type=int, default=digikey_lookup.DEFAULT_MAX_RETRIES)
    parser.add_argument("--include-raw", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument(
        "--bom",
        default="bom/nixie_clock_integrated_digikey_bom.csv",
        help="Input Digi-Key BOM CSV.",
    )
    parser.add_argument("--encoding", default="utf-8-sig")
