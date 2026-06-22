from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "digikey_lookup.py"
SPEC = importlib.util.spec_from_file_location("digikey_lookup", MODULE_PATH)
assert SPEC and SPEC.loader
digikey_lookup = importlib.util.module_from_spec(SPEC)
sys.modules["digikey_lookup"] = digikey_lookup
SPEC.loader.exec_module(digikey_lookup)

COMMON_PATH = Path(__file__).resolve().parents[1] / "tools" / "digikey_bom_common.py"
COMMON_SPEC = importlib.util.spec_from_file_location("digikey_bom_common", COMMON_PATH)
assert COMMON_SPEC and COMMON_SPEC.loader
digikey_bom_common = importlib.util.module_from_spec(COMMON_SPEC)
sys.modules["digikey_bom_common"] = digikey_bom_common
COMMON_SPEC.loader.exec_module(digikey_bom_common)


class DigikeyLookupTest(unittest.TestCase):
    def test_select_price_uses_highest_eligible_break_and_moq(self) -> None:
        selected = digikey_lookup.select_price(
            [
                {"break_quantity": 1, "unit_price": 120.0, "total_price": 120.0},
                {"break_quantity": 10, "unit_price": 95.0, "total_price": 950.0},
            ],
            requested_quantity=3,
            min_order_quantity=10,
        )

        self.assertEqual(
            selected,
            {
                "requested_quantity": 3,
                "purchase_quantity": 10,
                "break_quantity": 10,
                "unit_price": 95.0,
                "estimated_total_price": 950.0,
            },
        )

    def test_normalize_product_details_extracts_agent_fields(self) -> None:
        config = digikey_lookup.DigikeyConfig(
            client_id="client",
            client_secret="secret",
            account_id="0",
            environment="sandbox",
            site="JP",
            language="ja",
            currency="JPY",
            cache_dir=Path("unused"),
            cache_ttl_seconds=3600,
            timeout_seconds=30,
            max_retries=0,
            refresh=False,
        )
        raw = {
            "Product": {
                "Description": {
                    "ProductDescription": "Boost controller",
                    "DetailedDescription": "Boost controller, 10-HVSSOP",
                },
                "Manufacturer": {"Id": 123, "Name": "Texas Instruments"},
                "ManufacturerProductNumber": "TPS40210DGQR",
                "DatasheetUrl": "https://example.com/tps40210.pdf",
                "ProductUrl": "https://www.digikey.jp/example",
                "QuantityAvailable": 25,
                "ProductStatus": {"Id": 1, "Status": "Active"},
                "NormallyStocking": True,
                "Discontinued": False,
                "EndOfLife": False,
                "Ncnr": False,
                "Classifications": {"RohsStatus": "ROHS3 Compliant"},
                "Parameters": [
                    {
                        "ParameterId": 1,
                        "ParameterText": "Voltage - Supply",
                        "ParameterType": "String",
                        "ValueId": "abc",
                        "ValueText": "4.5V ~ 52V",
                    }
                ],
                "ProductVariations": [
                    {
                        "DigiKeyProductNumber": "296-26969-1-ND",
                        "PackageType": {"Id": 1, "Name": "Cut Tape"},
                        "QuantityAvailableforPackageType": 25,
                        "MinimumOrderQuantity": 1,
                        "StandardPricing": [
                            {
                                "BreakQuantity": 1,
                                "UnitPrice": 346.0,
                                "TotalPrice": 346.0,
                            }
                        ],
                    }
                ],
            }
        }

        normalized = digikey_lookup.normalize_product_details(
            raw,
            query={"product_number": "TPS40210DGQR", "requested_quantity": 2},
            config=config,
            requested_quantity=2,
            cache_hit=False,
            include_raw=False,
        )

        self.assertTrue(normalized["ok"])
        product = normalized["product"]
        self.assertEqual(product["manufacturer"]["name"], "Texas Instruments")
        self.assertEqual(product["manufacturer_part_number"], "TPS40210DGQR")
        self.assertEqual(product["datasheet_url"], "https://example.com/tps40210.pdf")
        self.assertEqual(product["parameter_map"]["Voltage - Supply"], "4.5V ~ 52V")
        self.assertEqual(product["best_offer"]["digikey_product_number"], "296-26969-1-ND")
        self.assertEqual(product["best_offer"]["estimated_total_price"], 692.0)
        self.assertEqual(normalized["warnings"], [])

    def test_find_column_accepts_common_digikey_spellings(self) -> None:
        fieldnames = ["Digi-Key Part Number", "Manufacturer Part Number", "Quantity"]

        self.assertEqual(
            digikey_lookup.find_column(fieldnames, ["DigiKey Part Number"]),
            "Digi-Key Part Number",
        )
        self.assertEqual(
            digikey_lookup.find_column(fieldnames, ["Quantity", "Qty"]),
            "Quantity",
        )

    def test_load_dotenv_reads_root_style_file_without_overriding_env(self) -> None:
        keys = [
            "DIGIKEY_TEST_CLIENT_ID",
            "DIGIKEY_TEST_CLIENT_SECRET",
            "DIGIKEY_TEST_KEEP",
        ]
        original = {key: os.environ.get(key) for key in keys}
        try:
            os.environ["DIGIKEY_TEST_KEEP"] = "from-shell"
            with tempfile.TemporaryDirectory() as tmpdir:
                env_path = Path(tmpdir) / ".env"
                env_path.write_text(
                    "\n".join(
                        [
                            "# local credentials",
                            "DIGIKEY_TEST_CLIENT_ID=abc123",
                            'DIGIKEY_TEST_CLIENT_SECRET="secret value # kept"',
                            "export DIGIKEY_TEST_KEEP=from-dotenv",
                            "",
                        ]
                    ),
                    encoding="utf-8",
                )

                loaded = digikey_lookup.load_dotenv(env_path)

            self.assertTrue(loaded)
            self.assertEqual(os.environ["DIGIKEY_TEST_CLIENT_ID"], "abc123")
            self.assertEqual(
                os.environ["DIGIKEY_TEST_CLIENT_SECRET"],
                "secret value # kept",
            )
            self.assertEqual(os.environ["DIGIKEY_TEST_KEEP"], "from-shell")
        finally:
            for key, value in original.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_config_accepts_short_client_id_aliases(self) -> None:
        keys = [
            "CLIENT_ID",
            "CLIENT_SECRET",
            "DIGIKEY_CLIENT_ID",
            "DIGIKEY_CLIENT_SECRET",
        ]
        original = {key: os.environ.get(key) for key in keys}
        try:
            for key in keys:
                os.environ.pop(key, None)
            os.environ["CLIENT_ID"] = "short-client"
            os.environ["CLIENT_SECRET"] = "short-secret"
            parser = digikey_lookup.build_parser()
            args = parser.parse_args(["part", "TPS40210DGQR"])

            config = digikey_lookup.config_from_args(args)

            self.assertEqual(config.client_id, "short-client")
            self.assertEqual(config.client_secret, "short-secret")
            self.assertEqual(config.environment, "production")
        finally:
            for key, value in original.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_evaluate_availability_requires_active_stock_and_non_marketplace(self) -> None:
        product = {
            "status": "アクティブ",
            "quantity_available": 12,
            "status_flags": {
                "discontinued": False,
                "end_of_life": False,
            },
            "best_offer": {
                "digikey_product_number": "TEST-CT-ND",
                "purchase_quantity": 2,
                "in_stock_enough": True,
            },
            "variations": [
                {
                    "digikey_product_number": "TEST-CT-ND",
                    "marketplace": False,
                }
            ],
        }

        availability = digikey_bom_common.evaluate_availability(product, 2)

        self.assertTrue(availability["active"])
        self.assertTrue(availability["in_stock"])
        self.assertTrue(availability["immediate"])

    def test_total_from_price_rows_adds_money_columns(self) -> None:
        total = digikey_bom_common.total_from_price_rows(
            [
                {"Line Total JPY": "10.10"},
                {"Line Total JPY": "2.20"},
                {"Line Total JPY": ""},
            ]
        )

        self.assertEqual(str(total), "12.30")


if __name__ == "__main__":
    unittest.main()
