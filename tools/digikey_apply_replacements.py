#!/usr/bin/env python3
"""Apply and verify selected Digi-Key replacements to a BOM CSV."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import digikey_bom_common as bom_common
import digikey_lookup


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    bom_common.add_bom_common_arguments(parser)
    parser.add_argument(
        "--replacements",
        default="bom/nixie_clock_digikey_replacements.csv",
        help="Replacement mapping CSV.",
    )
    parser.add_argument(
        "--output-bom",
        default="bom/nixie_clock_integrated_digikey_bom_active.csv",
        help="Output BOM with replacements applied.",
    )
    parser.add_argument(
        "--report-md",
        default="docs/digikey_replacements.md",
        help="Markdown replacement report.",
    )
    parser.add_argument(
        "--verification-csv",
        default="bom/nixie_clock_digikey_replacements_verified.csv",
        help="CSV report with verified replacement details.",
    )
    return parser


def read_replacements(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        old_number = (row.get("Old Digi-Key Part Number") or "").strip()
        if old_number:
            result[old_number] = row
    return result


def replacement_report_row(
    old_row: dict[str, str],
    replacement: dict[str, str],
    product: dict[str, Any],
    availability: dict[str, Any],
) -> dict[str, Any]:
    best = product.get("best_offer") or {}
    params = product.get("parameter_map") or {}
    return {
        "Reference Designator": old_row.get("Reference Designator", ""),
        "Old Digi-Key Part Number": replacement.get("Old Digi-Key Part Number", ""),
        "Old Manufacturer Part Number": replacement.get("Old Manufacturer Part Number", ""),
        "New Digi-Key Part Number": best.get("digikey_product_number") or replacement.get("New Digi-Key Part Number", ""),
        "New Manufacturer": (product.get("manufacturer") or {}).get("name", ""),
        "New Manufacturer Part Number": product.get("manufacturer_part_number") or replacement.get("New Manufacturer Part Number", ""),
        "Status": product.get("status", ""),
        "Active": bom_common.bool_text(availability.get("active")),
        "Immediate": bom_common.bool_text(availability.get("immediate")),
        "Quantity Available": availability.get("quantity_available", ""),
        "Unit Price JPY": bom_common.money(best.get("unit_price")),
        "Line Total JPY": bom_common.money(best.get("estimated_total_price")),
        "Key Specs": key_specs(params),
        "Reason": replacement.get("Reason", ""),
        "Product URL": product.get("product_url", ""),
        "Datasheet URL": product.get("datasheet_url", ""),
    }


def key_specs(params: dict[str, Any]) -> str:
    keys = [
        "静電容量",
        "抵抗",
        "許容誤差",
        "電圧 - 定格",
        "温度係数",
        "パッケージ/ケース",
        "電力（ワット）",
        "組成",
    ]
    return "; ".join(f"{key}: {params[key]}" for key in keys if params.get(key))


def package_label(product: dict[str, Any], fallback: str) -> str:
    package = (product.get("parameter_map") or {}).get("パッケージ/ケース")
    if not package:
        return fallback
    for label in ["0201", "0402", "0603", "0805", "1206", "1210", "2220"]:
        if label in package:
            return label
    return fallback


def write_replacement_markdown(path: Path, report_rows: list[dict[str, Any]], output_bom: Path) -> None:
    rows = "\n".join(
        "| {ref} | {old_mpn} | {new_mpn} | {dk} | {status} | {stock} | {specs} | {reason} |".format(
            ref=row["Reference Designator"],
            old_mpn=row["Old Manufacturer Part Number"],
            new_mpn=row["New Manufacturer Part Number"],
            dk=row["New Digi-Key Part Number"],
            status=row["Status"],
            stock=row["Quantity Available"],
            specs=row["Key Specs"],
            reason=row["Reason"],
        )
        for row in report_rows
    )
    text = f"""# Digi-Key 代替品選定

在庫 0 または Digi-Key ステータスが新規設計向けに不適合だった BOM 明細について、代替品を選定した。

出力 BOM: `{output_bom}`

| Reference Designator | 旧型番 | 新型番 | 新 Digi-Key 品番 | Status | 在庫 | 主な仕様 | 理由 |
| --- | --- | --- | --- | --- | ---: | --- | --- |
{rows}

## 選定ルール

- 元の値、定格、サイズ、温度特性を維持することを優先した。
- 元と同一メーカーでアクティブかつ在庫ありの候補が見つからない場合のみ、同等仕様の他メーカー品へ広げた。
- 選定後に Digi-Key ProductDetails を再取得し、`アクティブ`、必要数量以上の在庫、即時入手可能を確認した。
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = bom_common.load_config_from_args(args)
        client = digikey_lookup.DigikeyClient(config)
        replacements = read_replacements(Path(args.replacements))
        bom_path = Path(args.bom)
        with bom_path.open("r", encoding=args.encoding, newline="") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
            fieldnames = reader.fieldnames or []

        report_rows: list[dict[str, Any]] = []
        applied_count = 0
        for row in rows:
            old_dk = row.get("Digi-Key Part Number", "")
            replacement = replacements.get(old_dk)
            if not replacement:
                continue

            new_dk = replacement["New Digi-Key Part Number"]
            quantity = digikey_lookup.parse_quantity(row.get("Quantity"))
            raw, cache_hit = client.product_details(new_dk)
            normalized = digikey_lookup.normalize_product_details(
                raw,
                query={
                    "product_number": new_dk,
                    "requested_quantity": quantity,
                    "replacement_for": old_dk,
                },
                config=config,
                requested_quantity=quantity,
                cache_hit=cache_hit,
                include_raw=args.include_raw,
            )
            product = normalized["product"]
            availability = bom_common.evaluate_availability(product, quantity)
            if not availability.get("immediate"):
                raise digikey_lookup.DigikeyLookupError(
                    f"Replacement {new_dk} is not immediately available."
                )

            best = product.get("best_offer") or {}
            old_mpn = row.get("Manufacturer Part Number", "")
            row["Digi-Key Part Number"] = best.get("digikey_product_number") or new_dk
            row["Manufacturer"] = (product.get("manufacturer") or {}).get("name", row.get("Manufacturer", ""))
            row["Manufacturer Part Number"] = product.get("manufacturer_part_number") or replacement.get("New Manufacturer Part Number", "")
            row["Description"] = product.get("description") or row.get("Description", "")
            row["Package"] = package_label(product, row.get("Package", ""))
            suffix = f"Replacement for {old_mpn}: {replacement.get('Reason', '')}"
            row["Notes"] = f"{row.get('Notes', '')}; {suffix}" if row.get("Notes") else suffix

            report_rows.append(replacement_report_row(row, replacement, product, availability))
            applied_count += 1

        output_bom = Path(args.output_bom)
        output_bom.parent.mkdir(parents=True, exist_ok=True)
        with output_bom.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        bom_common.write_csv(Path(args.verification_csv), report_rows)
        write_replacement_markdown(Path(args.report_md), report_rows, output_bom)
        result = {
            "ok": True,
            "applied_count": applied_count,
            "output_bom": str(output_bom),
            "verification_csv": args.verification_csv,
            "report_md": args.report_md,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
        return 0
    except digikey_lookup.DigikeyLookupError as error:
        print(json.dumps(digikey_lookup.build_error_response(error), ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    sys.exit(main())
