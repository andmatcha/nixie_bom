#!/usr/bin/env python3
"""Generate a Digi-Key price CSV and Markdown summary for a BOM."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import digikey_bom_common as bom_common
import digikey_lookup


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    bom_common.add_bom_common_arguments(parser)
    parser.add_argument(
        "--price-csv",
        default="bom/nixie_clock_digikey_price_list.csv",
        help="Output CSV with price and stock columns.",
    )
    parser.add_argument(
        "--summary-md",
        default="docs/parts_cost_summary.md",
        help="Output Markdown summary.",
    )
    parser.add_argument("--json-output", help="Optional raw normalized lookup JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = bom_common.load_config_from_args(args)
        client = digikey_lookup.DigikeyClient(config)
        lookup = bom_common.fetch_bom(
            client,
            Path(args.bom),
            config=config,
            encoding=args.encoding,
            include_raw=args.include_raw,
        )
        rows = bom_common.price_rows(lookup)
        price_csv = Path(args.price_csv)
        bom_common.write_csv(price_csv, rows)
        bom_common.write_price_summary(Path(args.summary_md), lookup, rows, price_csv)
        if args.json_output:
            output = Path(args.json_output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(lookup, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result = {
            "ok": lookup.get("ok"),
            "rows": len(rows),
            "price_csv": str(price_csv),
            "summary_md": args.summary_md,
            "total_jpy": str(bom_common.total_from_price_rows(rows)),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
        return 0 if lookup.get("ok") else 2
    except digikey_lookup.DigikeyLookupError as error:
        print(json.dumps(digikey_lookup.build_error_response(error), ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    sys.exit(main())
