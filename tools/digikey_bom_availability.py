#!/usr/bin/env python3
"""Check whether every BOM line is active, in stock, and immediately available."""

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
        "--availability-csv",
        default="bom/nixie_clock_digikey_availability.csv",
        help="Output CSV with active/in-stock/immediate columns.",
    )
    parser.add_argument(
        "--summary-md",
        default="docs/digikey_availability.md",
        help="Output Markdown availability summary.",
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
        rows = bom_common.availability_rows(lookup)
        output_csv = Path(args.availability_csv)
        bom_common.write_csv(output_csv, rows)
        bom_common.write_availability_summary(Path(args.summary_md), lookup, rows, output_csv)
        if args.json_output:
            output = Path(args.json_output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(lookup, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        problem_count = sum(row.get("Immediate") != "yes" for row in rows)
        result = {
            "ok": problem_count == 0 and bool(lookup.get("ok")),
            "rows": len(rows),
            "immediate_count": len(rows) - problem_count,
            "problem_count": problem_count,
            "availability_csv": str(output_csv),
            "summary_md": args.summary_md,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
        return 0 if result["ok"] else 2
    except digikey_lookup.DigikeyLookupError as error:
        print(json.dumps(digikey_lookup.build_error_response(error), ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    sys.exit(main())
