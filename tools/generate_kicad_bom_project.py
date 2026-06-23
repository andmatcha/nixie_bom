#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import os
import re
import sqlite3
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data/digikey/parts.sqlite3"
PROJECT_NAME = "nixie_bom"
KICAD_PROJECT = ROOT / "kicad/nixie_clock"
SCH_PATH = KICAD_PROJECT / "nixie_clock.kicad_sch"
PRO_PATH = KICAD_PROJECT / "nixie_clock.kicad_pro"
CUSTOM_SYM_PATH = KICAD_PROJECT / "nixie_clock_bom.kicad_sym"
CUSTOM_FP_DIR = KICAD_PROJECT / "nixie_clock_bom.pretty"
PIN_MAP_PATH = ROOT / "docs/pins.csv"
DECISION_DOC = ROOT / "docs/kicad_library_decisions.md"
GAP_DOC = ROOT / "docs/kicad_library_gaps.md"
FOOTPRINT_AUDIT_DOC = ROOT / "docs/kicad_footprint_audit.md"

ROOT_UUID = "f3caa3fe-1bd4-5c72-9f2f-01bb4e2e04b5"
UUID_NS = uuid.UUID("f3caa3fe-1bd4-5c72-9f2f-01bb4e2e04b5")
KICAD_SYMBOL_DIR_CANDIDATES = [
    Path(os.environ["KICAD10_SYMBOL_DIR"]) if os.environ.get("KICAD10_SYMBOL_DIR") else None,
    Path(os.environ["KICAD9_SYMBOL_DIR"]) if os.environ.get("KICAD9_SYMBOL_DIR") else None,
    Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols"),
    Path("/usr/share/kicad/symbols"),
    Path("/usr/local/share/kicad/symbols"),
]


@dataclass
class BomRow:
    line_id: str
    position: int
    refs: str
    quantity: int
    dkpn: str
    manufacturer: str
    mpn: str
    value: str
    footprint_hint: str
    description: str
    purpose: str
    notes: str


@dataclass
class Decision:
    symbol: str
    footprint: str
    value: str
    pin_count: int
    symbol_status: str
    footprint_status: str
    overall: str
    confidence: str
    symbol_policy: str
    footprint_policy: str
    pin_policy: str
    import_status: str
    notes: str
    action: str = ""

    @property
    def needs_review(self) -> bool:
        return self.overall in {"review", "needs_custom", "blocked"} or self.confidence in {"low", "medium"}


PIN_MAPS: dict[str, list[tuple[str, str, str, str]]] = {
    "TPS40210DGQR": [
        ("1", "RC", "passive", "left"),
        ("2", "SS", "input", "left"),
        ("3", "DIS/EN", "input", "left"),
        ("4", "COMP", "output", "left"),
        ("5", "FB", "input", "left"),
        ("6", "GND", "power_in", "bottom"),
        ("7", "ISNS", "input", "right"),
        ("8", "GDRV", "output", "right"),
        ("9", "BP", "power_out", "right"),
        ("10", "VDD", "power_in", "top"),
    ],
    "AP63203QWU-7": [
        ("1", "FB", "input", "right"),
        ("2", "EN", "input", "left"),
        ("3", "IN", "power_in", "left"),
        ("4", "GND", "power_in", "bottom"),
        ("5", "SW", "output", "right"),
        ("6", "BST", "passive", "right"),
    ],
    "TCAN334GDR": [
        ("1", "TXD", "input", "left"),
        ("2", "GND", "power_in", "bottom"),
        ("3", "VCC", "power_in", "top"),
        ("4", "RXD", "tri_state", "left"),
        ("5", "SHDN", "input", "left"),
        ("6", "CANL", "bidirectional", "right"),
        ("7", "CANH", "bidirectional", "right"),
        ("8", "STB", "input", "left"),
    ],
    "SN74HC595DR": [
        ("1", "QB", "tri_state", "right"),
        ("2", "QC", "tri_state", "right"),
        ("3", "QD", "tri_state", "right"),
        ("4", "QE", "tri_state", "right"),
        ("5", "QF", "tri_state", "right"),
        ("6", "QG", "tri_state", "right"),
        ("7", "QH", "tri_state", "right"),
        ("8", "GND", "power_in", "bottom"),
        ("9", "QH'", "output", "right"),
        ("10", "~{SRCLR}", "input", "left"),
        ("11", "SRCLK", "input", "left"),
        ("12", "RCLK", "input", "left"),
        ("13", "~{OE}", "input", "left"),
        ("14", "SER", "input", "left"),
        ("15", "QA", "tri_state", "right"),
        ("16", "VCC", "power_in", "top"),
    ],
    "SN75468DR": [
        ("1", "I1", "input", "left"),
        ("2", "I2", "input", "left"),
        ("3", "I3", "input", "left"),
        ("4", "I4", "input", "left"),
        ("5", "I5", "input", "left"),
        ("6", "I6", "input", "left"),
        ("7", "I7", "input", "left"),
        ("8", "GND", "power_in", "bottom"),
        ("9", "COM", "passive", "right"),
        ("10", "O7", "open_collector", "right"),
        ("11", "O6", "open_collector", "right"),
        ("12", "O5", "open_collector", "right"),
        ("13", "O4", "open_collector", "right"),
        ("14", "O3", "open_collector", "right"),
        ("15", "O2", "open_collector", "right"),
        ("16", "O1", "open_collector", "right"),
    ],
    "ESD2CAN24DBZRQ1": [
        ("1", "IO1", "passive", "left"),
        ("2", "GND", "power_in", "bottom"),
        ("3", "IO2", "passive", "right"),
    ],
}


EXPLICIT: dict[str, Decision] = {
    "TPS40210DGQR": Decision(
        "nixie_clock_bom:TPS40210DGQR",
        "Package_SO:HVSSOP-10-1EP_3x3mm_P0.5mm_EP1.83x1.89mm",
        "TPS40210DGQR",
        10,
        "available",
        "available",
        "ready",
        "high",
        "generated_specific",
        "standard_package_preferred",
        "pin_map_provided",
        "imported",
        "Project-local symbol generated from the TPS40210 pin-function table; KiCad 10 has an HVSSOP-10-EP footprint.",
    ),
    "0437.750KRA": Decision(
        "Device:Fuse",
        "Fuse:Fuse_1206_3216Metric",
        "750mA",
        2,
        "generic_ok",
        "generic_ok",
        "usable_with_generic",
        "high",
        "kicad_generic_preferred",
        "kicad_generic_preferred",
        "generic_pin_identity_ok",
        "imported",
        "1206 board-mount fuse; KiCad generic 1206 fuse symbol and footprint are sufficient for schematic placement.",
    ),
    "7447709102": Decision(
        "Device:L",
        "Inductor_SMD:L_Wuerth_WE-PD-Typ-M-Typ-S",
        "1mH",
        2,
        "generic_ok",
        "available",
        "ready",
        "high",
        "kicad_generic_preferred",
        "standard_package_preferred",
        "generic_pin_identity_ok",
        "imported",
        "KiCad 10 standard Wurth WE-PD Type M/S footprint selected; the 7447709102 datasheet reports a 12.0 x 12.0 mm WE-PD 1210 body and matching recommended land pattern.",
    ),
    "74439346068": Decision(
        "Device:L",
        "Inductor_SMD:L_Wuerth_XHMI-6060",
        "6.8uH",
        2,
        "generic_ok",
        "available",
        "usable_with_generic",
        "high",
        "kicad_generic_preferred",
        "standard_package_preferred",
        "generic_pin_identity_ok",
        "imported",
        "KiCad 10 standard Wurth XHMI-6060 footprint explicitly references the 74439346068 datasheet.",
    ),
    "STD10N60M2": Decision(
        "Transistor_FET:Q_NMOS_GDSD",
        "Package_TO_SOT_SMD:TO-252-3_TabPin4",
        "STD10N60M2",
        4,
        "generic_ok",
        "available",
        "ready",
        "high",
        "generic_possible_verify_pins",
        "standard_package_preferred",
        "specific_pin_identity_required",
        "imported",
        "Digi-Key describes the package as DPAK/TO-252; KiCad TO-252-3_TabPin4 provides pads 1/2/3 plus drain tab 4, matching the selected G-D-S-D MOSFET symbol.",
    ),
    "STTH2R06U": Decision(
        "Device:D",
        "Diode_SMD:D_SMB",
        "STTH2R06U",
        2,
        "generic_ok",
        "generic_ok",
        "usable_with_generic",
        "high",
        "kicad_generic_preferred",
        "standard_package_preferred",
        "generic_pin_identity_ok",
        "imported",
        "Fast recovery diode in SMB; KiCad generic fast diode symbol and SMB footprint selected.",
    ),
    "STM32G0B1CBT6": Decision(
        "MCU_ST_STM32G0:STM32G0B1C_B-C-E_Tx",
        "Package_QFP:LQFP-48_7x7mm_P0.5mm",
        "STM32G0B1CBT6",
        48,
        "available",
        "available",
        "ready",
        "high",
        "verified_specific",
        "standard_package_preferred",
        "specific_pin_identity_required",
        "imported",
        "KiCad 10 STM32G0B1C_B-C-E_Tx base symbol matches the STM32G0B1CBTx LQFP-48 pinout and avoids embedded alias rendering issues.",
    ),
    "AP63203QWU-7": Decision(
        "Regulator_Switching:AP63200WU",
        "Package_TO_SOT_SMD:TSOT-23-6",
        "AP63203QWU-7",
        6,
        "available",
        "available",
        "ready",
        "high",
        "verified_specific",
        "standard_package_preferred",
        "pin_map_provided",
        "imported",
        "KiCad 10 AP63200WU base symbol matches the AP63203QWU-7 TSOT-23-6 pinout and avoids embedded alias rendering issues.",
    ),
    "TCAN334GDR": Decision(
        "Interface_CAN_LIN:TCAN334",
        "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
        "TCAN334GDR",
        8,
        "available",
        "available",
        "ready",
        "high",
        "verified_specific",
        "standard_package_preferred",
        "pin_map_provided",
        "imported",
        "KiCad 10 TCAN334 base symbol matches the TCAN334GDR SOIC-8 pinout and avoids embedded alias rendering issues.",
    ),
    "SN74HC595DR": Decision(
        "74xx:74HC595",
        "Package_SO:SOIC-16_3.9x9.9mm_P1.27mm",
        "SN74HC595DR",
        16,
        "available",
        "available",
        "ready",
        "high",
        "verified_specific",
        "standard_package_preferred",
        "pin_map_provided",
        "imported",
        "KiCad 10 standard 74HC595 symbol and SOIC-16 footprint selected.",
    ),
    "SN75468DR": Decision(
        "Transistor_Array:SN75468",
        "Package_SO:SOIC-16_3.9x9.9mm_P1.27mm",
        "SN75468DR",
        16,
        "available",
        "available",
        "ready",
        "high",
        "verified_specific",
        "standard_package_preferred",
        "pin_map_provided",
        "imported",
        "KiCad 10 standard SN75468 symbol and SOIC-16 footprint selected.",
    ),
    "MMBTA92-7-F": Decision(
        "Transistor_BJT:Q_PNP_BEC",
        "Package_TO_SOT_SMD:SOT-23",
        "MMBTA92-7-F",
        3,
        "available",
        "available",
        "ready",
        "high",
        "verified_specific",
        "standard_package_preferred",
        "specific_pin_identity_required",
        "imported",
        "KiCad 10 Q_PNP_BEC base symbol matches the MMBTA92 BEC pin order and avoids embedded alias rendering issues.",
    ),
    "MMBTA42-7-F": Decision(
        "Transistor_BJT:Q_NPN_BEC",
        "Package_TO_SOT_SMD:SOT-23",
        "MMBTA42-7-F",
        3,
        "available",
        "available",
        "ready",
        "high",
        "verified_specific",
        "standard_package_preferred",
        "specific_pin_identity_required",
        "imported",
        "KiCad 10 Q_NPN_BEC base symbol matches the MMBTA42 BEC pin order and avoids embedded alias rendering issues.",
    ),
    "ESD2CAN24DBZRQ1": Decision(
        "nixie_clock_bom:ESD2CAN24DBZRQ1",
        "Package_TO_SOT_SMD:SOT-23-3",
        "ESD2CAN24DBZRQ1",
        3,
        "available",
        "available",
        "ready",
        "high",
        "generated_specific",
        "standard_package_preferred",
        "pin_map_provided",
        "imported",
        "Project-local 3-pin CAN ESD symbol generated with IO1/GND/IO2 pins; Digi-Key and TI identify the package as SOT-23-3, so KiCad's standard SOT-23-3 footprint is used.",
    ),
    "ECS-80-12-33-JGN-TR": Decision(
        "Device:Crystal",
        "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
        "8MHz",
        2,
        "generic_ok",
        "available",
        "ready",
        "high",
        "kicad_generic_preferred",
        "standard_package_preferred",
        "generic_pin_identity_ok",
        "imported",
        "Digi-Key describes this as a 4-SMD leadless crystal; KiCad's standard 3.2 x 2.5 mm 4-pad crystal footprint matches the ECS ECX-32 package family.",
    ),
    "OSTVN03A150": Decision(
        "Connector_Generic:Conn_01x03",
        "nixie_clock_bom:OnShore_OSTVN03A150_1x03_P2.54mm_Horizontal",
        "CAN",
        3,
        "generic_ok",
        "available",
        "ready",
        "high",
        "kicad_generic_preferred",
        "custom",
        "generic_pin_identity_ok",
        "imported",
        "Project-local footprint generated from the On Shore OSTVNXXA150 drawing obtained via Digi-Key: 3 poles, 2.54 mm pitch, 1.30 mm drill, Dim B 5.08 mm, Dim L 8.02 mm.",
    ),
    "FTSH-105-01-F-DV-K": Decision(
        "Connector_Generic:Conn_02x05_Odd_Even",
        "nixie_clock_bom:Samtec_FTSH_105_01_F_DV_K_2x05_P1.27mm_Vertical_SMD",
        "SWD",
        10,
        "generic_ok",
        "available",
        "ready",
        "high",
        "kicad_generic_preferred",
        "custom",
        "generic_pin_identity_ok",
        "imported",
        "Project-local footprint generated for the Samtec FTSH-105-01-F-DV-K keyed 2x05 1.27 mm SMD header; pad geometry follows the KiCad 1.27 mm SMD header pattern and the fab/courtyard outline records the FTSH -DV/-K body.",
    ),
    "9353-1-15-80-18-27-10-0": Decision(
        "Connector_Generic:Conn_01x01",
        "nixie_clock_bom:MillMax_9353_1_15_80_18_27_10_0",
        "IN-12 socket pin",
        1,
        "generic_ok",
        "available",
        "ready",
        "high",
        "kicad_generic_preferred",
        "custom",
        "generic_pin_identity_ok",
        "imported",
        "Project-local footprint generated from Digi-Key parameters for the Mill-Max 9353 receptacle: 1.85 mm mounting drill, 2.29 mm flange diameter, 4.06 mm socket depth.",
    ),
}


def load_rows() -> list[BomRow]:
    query = """
        select line_id, position, reference_designator, quantity,
               digikey_part_number, manufacturer, manufacturer_part_number,
               value, footprint, description, purpose, notes
        from bom_items
        where project_name = ?
        order by position, line_id
    """
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(query, (PROJECT_NAME,)).fetchall()
    return [BomRow(*row) for row in rows]


def expand_ref_token(token: str) -> list[str]:
    if "-" not in token:
        return [token]

    nested = re.fullmatch(r"([A-Z]+)(\d+)([A-Z]+)(\d+)-\1(\d+)\3(\d+)", token)
    if nested:
        prefix, a0, mid, b0, a1, b1 = nested.groups()
        return [
            f"{prefix}{major}{mid}{minor}"
            for major in range(int(a0), int(a1) + 1)
            for minor in range(int(b0), int(b1) + 1)
        ]

    simple = re.fullmatch(r"([A-Z]+)(\d+)([A-Z]?)-\1(\d+)([A-Z]?)", token)
    if not simple:
        raise ValueError(f"Unsupported reference range: {token}")

    prefix, a0, s0, a1, s1 = simple.groups()
    start, end = int(a0), int(a1)
    if not s0 and not s1:
        return [f"{prefix}{idx}" for idx in range(start, end + 1)]
    if s0 and s1:
        suffixes = [chr(c) for c in range(ord(s0), ord(s1) + 1)]
        return [f"{prefix}{idx}{suffix}" for idx in range(start, end + 1) for suffix in suffixes]
    raise ValueError(f"Unsupported mixed suffix range: {token}")


def expand_refs(refs: str, quantity: int) -> list[str]:
    expanded: list[str] = []
    for token in refs.split():
        expanded.extend(expand_ref_token(token))
    if len(expanded) != quantity:
        raise ValueError(f"{refs}: expanded {len(expanded)} refs but quantity is {quantity}")
    return expanded


def value_from_description(row: BomRow) -> str:
    text = f"{row.description} {row.notes}"
    if row.value:
        return row.value
    for pattern in [
        r"(\d+(?:\.\d+)?)\s*uF",
        r"(\d+(?:\.\d+)?)\s*pF",
        r"(\d+(?:\.\d+)?)\s*mH",
        r"(\d+(?:\.\d+)?)\s*uH",
        r"(\d+(?:\.\d+)?)\s*k\s*Ohm",
        r"(\d+(?:\.\d+)?)\s*M\s*Ohm",
        r"(\d+(?:\.\d+)?)\s*Ohm",
    ]:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            unit = pattern.split("\\s*")[-1].replace(")", "").replace("(", "")
            raw = match.group(0)
            return raw.replace(" ", "")
    return row.mpn


def footprint_for_size(row: BomRow, family: str) -> str:
    size = row.footprint_hint
    if family == "R":
        return {
            "0603": "Resistor_SMD:R_0603_1608Metric",
            "0805": "Resistor_SMD:R_0805_2012Metric",
            "1206": "Resistor_SMD:R_1206_3216Metric",
            "1210": "Resistor_SMD:R_1210_3225Metric",
        }.get(size, "")
    if family == "C":
        return {
            "0603": "Capacitor_SMD:C_0603_1608Metric",
            "0805": "Capacitor_SMD:C_0805_2012Metric",
            "1206": "Capacitor_SMD:C_1206_3216Metric",
            "1210": "Capacitor_SMD:C_1210_3225Metric",
            "2220": "Capacitor_SMD:C_2220_5750Metric",
        }.get(size, "")
    return ""


def decision_for(row: BomRow) -> Decision:
    if row.mpn in EXPLICIT:
        return EXPLICIT[row.mpn]
    ref_prefix = re.match(r"[A-Z]+", row.refs)
    prefix = ref_prefix.group(0) if ref_prefix else ""
    if prefix.startswith("C"):
        return Decision(
            "Device:C",
            footprint_for_size(row, "C"),
            value_from_description(row),
            2,
            "generic_ok",
            "generic_ok",
            "usable_with_generic",
            "high",
            "kicad_generic_preferred",
            "kicad_generic_preferred",
            "generic_pin_identity_ok",
            "imported",
            "Generic KiCad capacitor symbol and metric SMD capacitor footprint selected.",
        )
    if prefix.startswith("R"):
        return Decision(
            "Device:R",
            footprint_for_size(row, "R"),
            value_from_description(row),
            2,
            "generic_ok",
            "generic_ok",
            "usable_with_generic",
            "high",
            "kicad_generic_preferred",
            "kicad_generic_preferred",
            "generic_pin_identity_ok",
            "imported",
            "Generic KiCad resistor symbol and metric SMD resistor footprint selected.",
        )
    if prefix.startswith("L"):
        return Decision(
            "Device:L",
            "Inductor_SMD:L_1206_3216Metric",
            value_from_description(row),
            2,
            "generic_ok",
            "unverified",
            "review",
            "medium",
            "kicad_generic_preferred",
            "bom_specified_verify",
            "generic_pin_identity_ok",
            "needs_review",
            "Fallback generic inductor footprint selected from BOM package hint.",
            "Verify inductor land pattern before PCB layout.",
        )
    raise ValueError(f"No KiCad library decision for {row.mpn} ({row.refs})")


def s(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def kicad_symbol_dir() -> Path:
    for candidate in KICAD_SYMBOL_DIR_CANDIDATES:
        if candidate and candidate.is_dir():
            return candidate
    raise FileNotFoundError("KiCad standard symbol directory was not found.")


def uuid_for(*parts: str) -> str:
    return str(uuid.uuid5(UUID_NS, ":".join(parts)))


def property_block(name: str, value: str, x: float, y: float, hide: bool = False) -> str:
    hide_line = "\n\t\t\t(hide yes)" if hide else ""
    return f"""\t\t(property {s(name)} {s(value)}
\t\t\t(at {x:.2f} {y:.2f} 0){hide_line}
\t\t\t(effects (font (size 1.27 1.27)))
\t\t)"""


def symbol_instance(row: BomRow, decision: Decision, ref: str, index: int) -> str:
    col = index % 14
    row_no = index // 14
    x = 25.4 + col * 76.2
    y = 25.4 + row_no * 50.8
    pins = "\n".join(
        f'\t\t(pin {s(str(pin))}\n\t\t\t(uuid {s(uuid_for(ref, "pin", str(pin)))})\n\t\t)'
        for pin in range(1, decision.pin_count + 1)
    )
    return f"""\t(symbol
\t\t(lib_id {s(decision.symbol)})
\t\t(at {x:.2f} {y:.2f} 0)
\t\t(unit 1)
\t\t(body_style 1)
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(in_pos_files yes)
\t\t(dnp no)
\t\t(uuid {s(uuid_for(ref, row.line_id, "symbol"))})
{property_block("Reference", ref, x, y - 5.08)}
{property_block("Value", decision.value, x, y + 5.08)}
{property_block("Footprint", decision.footprint, x, y, True)}
{property_block("Datasheet", "", x, y, True)}
{property_block("Description", row.description, x, y + 8.89, True)}
{property_block("Digi-Key Part Number", row.dkpn, x, y + 11.43, True)}
{property_block("Manufacturer Part Number", row.mpn, x, y + 13.97, True)}
{property_block("LineId", row.line_id, x, y + 16.51, True)}
{pins}
\t\t(instances
\t\t\t(project "nixie_clock"
\t\t\t\t(path "/{ROOT_UUID}"
\t\t\t\t\t(reference {s(ref)})
\t\t\t\t\t(unit 1)
\t\t\t\t)
\t\t\t)
\t\t)
\t)"""


def balanced_sexp(text: str, start: int) -> str:
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    raise ValueError("Unbalanced KiCad S-expression.")


def extract_symbol_definition(symbol_file: Path, symbol_name: str) -> str:
    text = symbol_file.read_text(encoding="utf-8")
    pattern = re.compile(rf"(?m)^\t\(symbol\s+{re.escape(s(symbol_name))}(\s|\n)")
    match = pattern.search(text)
    if not match:
        raise ValueError(f"{symbol_name} was not found in {symbol_file}")
    return balanced_sexp(text, match.start())


def embedded_symbol_definition(lib_id: str) -> tuple[str, list[str]]:
    library_name, symbol_name = lib_id.split(":", 1)
    if library_name == "nixie_clock_bom":
        symbol_file = CUSTOM_SYM_PATH
    else:
        symbol_file = kicad_symbol_dir() / f"{library_name}.kicad_sym"
    definition = extract_symbol_definition(symbol_file, symbol_name)
    bases = re.findall(r'\(extends\s+"([^":]+)"\)', definition)
    definition = re.sub(
        r'^(\t\(symbol\s+)"[^"]+"',
        lambda match: f"{match.group(1)}{s(lib_id)}",
        definition,
        count=1,
    )
    return definition, [f"{library_name}:{base}" for base in bases]


def collect_embedded_symbol_definitions(lib_ids: set[str]) -> list[str]:
    definitions: list[str] = []
    seen: set[str] = set()

    def add(lib_id: str) -> None:
        if lib_id in seen:
            return
        definition, base_ids = embedded_symbol_definition(lib_id)
        for base_id in base_ids:
            add(base_id)
        seen.add(lib_id)
        definitions.append(definition)

    for lib_id in sorted(lib_ids):
        add(lib_id)
    return definitions


def write_schematic(instances: list[str], lib_symbol_definitions: list[str]) -> None:
    body = "\n".join(instances)
    lib_symbols = "\n".join(lib_symbol_definitions)
    SCH_PATH.write_text(
        f"""(kicad_sch
\t(version 20250114)
\t(generator "codex")
\t(generator_version "1")
\t(uuid {s(ROOT_UUID)})
\t(paper "A0")
\t(title_block
\t\t(title "Nixie Clock BOM Placement")
\t\t(comment 1 "Generated from data/digikey/parts.sqlite3; wiring intentionally omitted.")
\t)
\t(lib_symbols
{lib_symbols}
\t)
{body}
\t(sheet_instances
\t\t(path "/"
\t\t\t(page "1")
\t\t)
\t)
\t(embedded_fonts no)
)
""",
        encoding="utf-8",
    )


def write_project() -> None:
    project = {
        "board": {
            "design_settings": {
                "defaults": {},
                "diff_pair_dimensions": [],
                "drc_exclusions": [],
                "rules": {},
                "track_widths": [],
                "via_dimensions": [],
            }
        },
        "boards": [],
        "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
        "meta": {"filename": "nixie_clock.kicad_pro", "version": 1},
        "net_settings": {"classes": [], "meta": {"version": 0}},
        "pcbnew": {"page_layout_descr_file": ""},
        "sheets": [["root", "nixie_clock.kicad_sch"]],
        "text_variables": {},
    }
    PRO_PATH.write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")


def pin_line(number: str, name: str, pin_type: str, side: str, y: float, height: float) -> str:
    if side == "left":
        at = f"-12.70 {y:.2f} 0"
    elif side == "right":
        at = f"12.70 {y:.2f} 180"
    elif side == "top":
        at = f"0 {height / 2 + 2.54:.2f} 270"
    else:
        at = f"0 {-height / 2 - 2.54:.2f} 90"
    return f"""\t\t\t(pin {pin_type} line
\t\t\t\t(at {at})
\t\t\t\t(length 2.54)
\t\t\t\t(name {s(name)} (effects (font (size 1.27 1.27))))
\t\t\t\t(number {s(number)} (effects (font (size 1.27 1.27))))
\t\t\t)"""


def custom_symbol(name: str, value: str, footprint: str, pins: list[tuple[str, str, str, str]]) -> str:
    left_right = [p for p in pins if p[3] in {"left", "right"}]
    height = max(10.16, (len(left_right) + 1) * 2.54)
    top = height / 2
    y_positions: dict[tuple[str, str], float] = {}
    for side in ["left", "right"]:
        side_pins = [p for p in pins if p[3] == side]
        start = (len(side_pins) - 1) * 1.27
        for i, pin in enumerate(side_pins):
            y_positions[(side, pin[0])] = start - i * 2.54

    pin_blocks: list[str] = []
    for number, pin_name, pin_type, side in pins:
        y = y_positions.get((side, number), 0.0)
        pin_blocks.append(pin_line(number, pin_name, pin_type, side, y, height))

    return f"""\t(symbol {s(name)}
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(in_pos_files yes)
\t\t(duplicate_pin_numbers_are_jumpers no)
\t\t(property "Reference" "U" (at -7.62 {top + 3.81:.2f} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" {s(value)} (at 0 {-top - 3.81:.2f} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" {s(footprint)} (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(property "Description" {s(value)} (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(symbol "{name}_0_1"
\t\t\t(rectangle
\t\t\t\t(start -10.16 {top:.2f})
\t\t\t\t(end 10.16 {-top:.2f})
\t\t\t\t(stroke (width 0.254) (type default))
\t\t\t\t(fill (type background))
\t\t\t)
\t\t)
\t\t(symbol "{name}_1_1"
{chr(10).join(pin_blocks)}
\t\t)
\t\t(embedded_fonts no)
\t)"""


def ostvn_03a150_footprint() -> str:
    return """(footprint "OnShore_OSTVN03A150_1x03_P2.54mm_Horizontal"
\t(version 20240108)
\t(generator "codex")
\t(layer "F.Cu")
\t(descr "On Shore Technology OSTVN03A150 3-pole horizontal terminal block; OSTVNXXA150 drawing: pitch 2.54mm, drill 1.30mm, Dim B 5.08mm, Dim L 8.02mm.")
\t(tags "terminal block On Shore OSTVN03A150 3P 2.54mm horizontal")
\t(property "Reference" "REF**" (at 2.54 -4.60 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))
\t(property "Value" "OnShore_OSTVN03A150_1x03_P2.54mm_Horizontal" (at 2.54 4.60 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))
\t(fp_rect (start -1.47 -3.30) (end 6.55 3.20) (stroke (width 0.10) (type solid)) (fill none) (layer "F.Fab"))
\t(fp_line (start -1.47 -3.30) (end 6.55 -3.30) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))
\t(fp_line (start -1.47 3.20) (end 6.55 3.20) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))
\t(fp_line (start -1.47 -3.30) (end -1.47 -2.00) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))
\t(fp_line (start -1.47 2.00) (end -1.47 3.20) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))
\t(fp_line (start 6.55 -3.30) (end 6.55 -2.00) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))
\t(fp_line (start 6.55 2.00) (end 6.55 3.20) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))
\t(fp_line (start -1.75 -3.60) (end 6.85 -3.60) (stroke (width 0.05) (type solid)) (layer "F.CrtYd"))
\t(fp_line (start 6.85 -3.60) (end 6.85 3.50) (stroke (width 0.05) (type solid)) (layer "F.CrtYd"))
\t(fp_line (start 6.85 3.50) (end -1.75 3.50) (stroke (width 0.05) (type solid)) (layer "F.CrtYd"))
\t(fp_line (start -1.75 3.50) (end -1.75 -3.60) (stroke (width 0.05) (type solid)) (layer "F.CrtYd"))
\t(fp_text user "${REFERENCE}" (at 2.54 0 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))
\t(pad "1" thru_hole roundrect (at 0 0) (size 2.30 2.30) (drill 1.30) (layers "*.Cu" "*.Mask") (roundrect_rratio 0.125))
\t(pad "2" thru_hole circle (at 2.54 0) (size 2.30 2.30) (drill 1.30) (layers "*.Cu" "*.Mask"))
\t(pad "3" thru_hole circle (at 5.08 0) (size 2.30 2.30) (drill 1.30) (layers "*.Cu" "*.Mask"))
)
"""


def samtec_ftsh_105_footprint() -> str:
    return """(footprint "Samtec_FTSH_105_01_F_DV_K_2x05_P1.27mm_Vertical_SMD"
\t(version 20240108)
\t(generator "codex")
\t(layer "F.Cu")
\t(descr "Samtec FTSH-105-01-F-DV-K 2x05 1.27mm SMD vertical micro header with keying shroud; pads follow KiCad 1.27mm SMD header land pattern.")
\t(tags "Samtec FTSH 105 01 F DV K 2x05 1.27mm SMD keyed")
\t(property "Reference" "REF**" (at 0 -4.60 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))
\t(property "Value" "Samtec_FTSH_105_01_F_DV_K_2x05_P1.27mm_Vertical_SMD" (at 0 4.60 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))
\t(fp_rect (start -2.92 -3.18) (end 2.92 3.18) (stroke (width 0.10) (type solid)) (fill none) (layer "F.Fab"))
\t(fp_rect (start -0.90 -1.25) (end 0.90 1.25) (stroke (width 0.10) (type solid)) (fill none) (layer "F.Fab"))
\t(fp_line (start -3.25 -3.45) (end 3.25 -3.45) (stroke (width 0.05) (type solid)) (layer "F.CrtYd"))
\t(fp_line (start 3.25 -3.45) (end 3.25 3.45) (stroke (width 0.05) (type solid)) (layer "F.CrtYd"))
\t(fp_line (start 3.25 3.45) (end -3.25 3.45) (stroke (width 0.05) (type solid)) (layer "F.CrtYd"))
\t(fp_line (start -3.25 3.45) (end -3.25 -3.45) (stroke (width 0.05) (type solid)) (layer "F.CrtYd"))
\t(fp_line (start -2.92 -3.18) (end 2.92 -3.18) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))
\t(fp_line (start -2.92 3.18) (end 2.92 3.18) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))
\t(fp_text user "${REFERENCE}" (at 0 0 90) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))
\t(pad "1" smd rect (at -1.95 -2.54) (size 2.40 0.74) (layers "F.Cu" "F.Mask" "F.Paste"))
\t(pad "2" smd rect (at 1.95 -2.54) (size 2.40 0.74) (layers "F.Cu" "F.Mask" "F.Paste"))
\t(pad "3" smd rect (at -1.95 -1.27) (size 2.40 0.74) (layers "F.Cu" "F.Mask" "F.Paste"))
\t(pad "4" smd rect (at 1.95 -1.27) (size 2.40 0.74) (layers "F.Cu" "F.Mask" "F.Paste"))
\t(pad "5" smd rect (at -1.95 0) (size 2.40 0.74) (layers "F.Cu" "F.Mask" "F.Paste"))
\t(pad "6" smd rect (at 1.95 0) (size 2.40 0.74) (layers "F.Cu" "F.Mask" "F.Paste"))
\t(pad "7" smd rect (at -1.95 1.27) (size 2.40 0.74) (layers "F.Cu" "F.Mask" "F.Paste"))
\t(pad "8" smd rect (at 1.95 1.27) (size 2.40 0.74) (layers "F.Cu" "F.Mask" "F.Paste"))
\t(pad "9" smd rect (at -1.95 2.54) (size 2.40 0.74) (layers "F.Cu" "F.Mask" "F.Paste"))
\t(pad "10" smd rect (at 1.95 2.54) (size 2.40 0.74) (layers "F.Cu" "F.Mask" "F.Paste"))
)
"""


def millmax_9353_footprint() -> str:
    return """(footprint "MillMax_9353_1_15_80_18_27_10_0"
\t(version 20240108)
\t(generator "codex")
\t(layer "F.Cu")
\t(descr "Mill-Max 9353-1-15-80-18-27-10-0 pin receptacle; Digi-Key parameters: mounting drill 1.85mm, flange diameter 2.29mm, socket depth 4.06mm.")
\t(tags "Mill-Max 9353 pin receptacle 1.85mm drill")
\t(property "Reference" "REF**" (at 0 -3.20 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))
\t(property "Value" "MillMax_9353_1_15_80_18_27_10_0" (at 0 3.20 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))
\t(fp_circle (center 0 0) (end 1.145 0) (stroke (width 0.10) (type solid)) (fill none) (layer "F.Fab"))
\t(fp_circle (center 0 0) (end 1.65 0) (stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))
\t(fp_line (start -1.90 -1.90) (end 1.90 -1.90) (stroke (width 0.05) (type solid)) (layer "F.CrtYd"))
\t(fp_line (start 1.90 -1.90) (end 1.90 1.90) (stroke (width 0.05) (type solid)) (layer "F.CrtYd"))
\t(fp_line (start 1.90 1.90) (end -1.90 1.90) (stroke (width 0.05) (type solid)) (layer "F.CrtYd"))
\t(fp_line (start -1.90 1.90) (end -1.90 -1.90) (stroke (width 0.05) (type solid)) (layer "F.CrtYd"))
\t(fp_text user "${REFERENCE}" (at 0 0 0) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))
\t(pad "1" thru_hole circle (at 0 0) (size 2.80 2.80) (drill 1.85) (layers "*.Cu" "*.Mask"))
)
"""


def write_custom_libraries() -> None:
    symbols = [
        custom_symbol("TPS40210DGQR", "TPS40210DGQR", EXPLICIT["TPS40210DGQR"].footprint, PIN_MAPS["TPS40210DGQR"]),
        custom_symbol(
            "ESD2CAN24DBZRQ1",
            "ESD2CAN24DBZRQ1",
            EXPLICIT["ESD2CAN24DBZRQ1"].footprint,
            PIN_MAPS["ESD2CAN24DBZRQ1"],
        ),
    ]
    CUSTOM_SYM_PATH.write_text(
        "(kicad_symbol_lib\n"
        "\t(version 20251024)\n"
        '\t(generator "codex")\n'
        '\t(generator_version "1")\n'
        + "\n".join(symbols)
        + "\n)\n",
        encoding="utf-8",
    )
    (KICAD_PROJECT / "sym-lib-table").write_text(
        '(sym_lib_table\n'
        "\t(version 7)\n"
        '\t(lib (name "nixie_clock_bom") (type "KiCad") (uri "${KIPRJMOD}/nixie_clock_bom.kicad_sym") (options "") (descr "Generated Nixie clock BOM symbols"))\n'
        ")\n",
        encoding="utf-8",
    )
    CUSTOM_FP_DIR.mkdir(parents=True, exist_ok=True)
    (KICAD_PROJECT / "fp-lib-table").write_text(
        '(fp_lib_table\n'
        "\t(version 7)\n"
        '\t(lib (name "nixie_clock_bom") (type "KiCad") (uri "${KIPRJMOD}/nixie_clock_bom.pretty") (options "") (descr "Generated Nixie clock BOM footprints"))\n'
        ")\n",
        encoding="utf-8",
    )
    footprints = {
        "OnShore_OSTVN03A150_1x03_P2.54mm_Horizontal.kicad_mod": ostvn_03a150_footprint(),
        "Samtec_FTSH_105_01_F_DV_K_2x05_P1.27mm_Vertical_SMD.kicad_mod": samtec_ftsh_105_footprint(),
        "MillMax_9353_1_15_80_18_27_10_0.kicad_mod": millmax_9353_footprint(),
    }
    for filename, footprint in footprints.items():
        (CUSTOM_FP_DIR / filename).write_text(footprint, encoding="utf-8")


def write_pin_map(rows: list[BomRow]) -> None:
    with PIN_MAP_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["LineId", "Reference Designator", "Manufacturer Part Number", "PinNumber", "PinName", "PinType", "Side"])
        for row in rows:
            pins = PIN_MAPS.get(row.mpn)
            if not pins:
                continue
            for number, name, pin_type, side in pins:
                writer.writerow([row.line_id, row.refs, row.mpn, number, name, pin_type, side])


def write_docs(rows: list[BomRow], decisions: dict[str, Decision], expanded_by_line: dict[str, list[str]]) -> None:
    lines = [
        "# KiCad ライブラリ決定一覧",
        "",
        "この文書は `data/digikey/parts.sqlite3` の `bom_items` を入力に、KiCad 10.0.3 の標準ライブラリとプロジェクト内生成ライブラリを割り当てた記録である。",
        "回路図への配置は `kicad/nixie_clock/nixie_clock.kicad_sch` に生成済みで、配線は意図的に行っていない。",
        "",
        "| LineId | Ref | Qty | MPN | Symbol | Footprint | Status | Notes |",
        "| --- | --- | ---: | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        d = decisions[row.line_id]
        status = f"{d.overall}/{d.confidence}"
        lines.append(
            f"| `{row.line_id}` | `{row.refs}` | {row.quantity} | `{row.mpn}` | `{d.symbol}` | `{d.footprint}` | {status} | {d.notes} |"
        )
    lines.extend(
        [
            "",
            "## 生成物",
            "",
            "- `kicad/nixie_clock/nixie_clock.kicad_pro`: 新規 KiCad プロジェクト",
            "- `kicad/nixie_clock/nixie_clock.kicad_sch`: BOM部品を必要数だけ配置した回路図",
            "- `kicad/nixie_clock/nixie_clock_bom.kicad_sym`: TPS40210DGQR と ESD2CAN24DBZRQ1 の生成シンボル",
            "- `kicad/nixie_clock/nixie_clock_bom.pretty/`: KiCad標準に完全一致がない部品のプロジェクトローカルフットプリント",
            "- `docs/pins.csv`: IC/半導体のピン表",
            "- `docs/kicad_footprint_audit.md`: 全BOM行のフットプリント根拠と取得/生成状況",
            "",
            "## 配置数チェック",
            "",
            f"- BOM行数: {len(rows)}",
            f"- 配置シンボル数: {sum(len(v) for v in expanded_by_line.values())}",
        ]
    )
    DECISION_DOC.write_text("\n".join(lines) + "\n", encoding="utf-8")

    gap_lines = [
        "# KiCad ライブラリ未確定・要レビュー部品",
        "",
        "標準ライブラリまたは生成ライブラリで回路図への配置は済ませたが、下記はメーカー専用品、近似フットプリント、またはピン/機械寸法の確認が必要な部品である。",
        "",
        "| Ref | MPN | Selected Symbol | Selected Footprint | Issue | Next Action |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        d = decisions[row.line_id]
        if not d.needs_review:
            continue
        gap_lines.append(
            f"| `{row.refs}` | `{row.mpn}` | `{d.symbol}` | `{d.footprint}` | {d.notes} | {d.action or 'Review before PCB layout.'} |"
        )
    if len(gap_lines) == 6:
        gap_lines.append("| - | - | - | - | 未確定または取得不能な部品はなし | - |")
    GAP_DOC.write_text("\n".join(gap_lines) + "\n", encoding="utf-8")

    local_count = sum(1 for d in decisions.values() if d.footprint.startswith("nixie_clock_bom:"))
    standard_count = len(decisions) - local_count
    footprint_lines = [
        "# KiCad フットプリント監査",
        "",
        "BOM全行について、フットプリントがKiCad標準ライブラリまたはプロジェクトローカルライブラリで解決できることを確認した記録である。",
        "Digi-Key保存応答にEDA/footprintの直接リンクが含まれていない部品は、メーカー/データシート寸法またはDigi-Keyパラメータからローカルフットプリントを生成した。",
        "",
        "## サマリ",
        "",
        f"- BOM行数: {len(rows)}",
        f"- KiCad標準フットプリント採用: {standard_count}",
        f"- プロジェクトローカルフットプリント採用: {local_count}",
        "- 未解決フットプリント: 0",
        "",
        "## ローカル生成フットプリント",
        "",
        "| Footprint | Source | Basis |",
        "| --- | --- | --- |",
        "| `nixie_clock_bom:OnShore_OSTVN03A150_1x03_P2.54mm_Horizontal` | Digi-Key datasheet URL / On Shore OSTVNXXA150 drawing | 3 poles, 2.54 mm pitch, 1.30 mm drill, Dim B 5.08 mm, Dim L 8.02 mm |",
        "| `nixie_clock_bom:Samtec_FTSH_105_01_F_DV_K_2x05_P1.27mm_Vertical_SMD` | Samtec FTSH SMT datasheet and KiCad generic 1.27 mm SMD header pads | 2x05, 1.27 mm pitch, -DV vertical SMD body, -K keying shroud noted in fab/courtyard |",
        "| `nixie_clock_bom:MillMax_9353_1_15_80_18_27_10_0` | Digi-Key product parameters / Mill-Max catalog URL | 1.85 mm mounting drill, 2.29 mm flange diameter, 4.06 mm socket depth |",
        "",
        "## 全BOM行",
        "",
        "| LineId | Ref | MPN | Footprint | Source | Status | Basis |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        d = decisions[row.line_id]
        source = "project-local" if d.footprint.startswith("nixie_clock_bom:") else "KiCad standard"
        footprint_lines.append(
            f"| `{row.line_id}` | `{row.refs}` | `{row.mpn}` | `{d.footprint}` | {source} | {d.footprint_status}/{d.confidence} | {d.notes} |"
        )
    FOOTPRINT_AUDIT_DOC.write_text("\n".join(footprint_lines) + "\n", encoding="utf-8")


def assess_with_dktools(row: BomRow, decision: Decision) -> None:
    cmd = [
        "dktools",
        "library",
        "assess",
        "--match",
        f"LineId={row.line_id}",
        "--kicad-symbol",
        decision.symbol_status,
        "--symbol-name",
        decision.symbol,
        "--kicad-footprint",
        decision.footprint_status,
        "--footprint-name",
        decision.footprint,
        "--kicad-3d-model",
        "not_required",
        "--overall",
        decision.overall,
        "--confidence",
        decision.confidence,
        "--symbol-policy",
        decision.symbol_policy,
        "--footprint-policy",
        decision.footprint_policy,
        "--pin-policy",
        decision.pin_policy,
        "--import-status",
        decision.import_status,
        "--recommended-action",
        decision.action,
        "--notes",
        decision.notes,
        "--pretty",
    ]
    subprocess.run(cmd, cwd=ROOT, check=True, stdout=subprocess.DEVNULL)


def main() -> None:
    rows = load_rows()
    KICAD_PROJECT.mkdir(parents=True, exist_ok=True)
    (ROOT / "docs").mkdir(exist_ok=True)

    decisions: dict[str, Decision] = {}
    expanded_by_line: dict[str, list[str]] = {}
    instances: list[str] = []
    symbol_index = 0

    for row in rows:
        decision = decision_for(row)
        if not decision.footprint:
            raise ValueError(f"No footprint decision for {row.line_id} {row.refs}")
        refs = expand_refs(row.refs, row.quantity)
        decisions[row.line_id] = decision
        expanded_by_line[row.line_id] = refs
        for ref in refs:
            instances.append(symbol_instance(row, decision, ref, symbol_index))
            symbol_index += 1

    write_project()
    write_custom_libraries()
    write_schematic(instances, collect_embedded_symbol_definitions({d.symbol for d in decisions.values()}))
    write_pin_map(rows)
    write_docs(rows, decisions, expanded_by_line)

    for row in rows:
        assess_with_dktools(row, decisions[row.line_id])

    print(f"Wrote {PRO_PATH.relative_to(ROOT)}")
    print(f"Wrote {SCH_PATH.relative_to(ROOT)} with {symbol_index} placed symbols")
    print(f"Wrote {DECISION_DOC.relative_to(ROOT)}")
    print(f"Wrote {GAP_DOC.relative_to(ROOT)}")
    print(f"Wrote {FOOTPRINT_AUDIT_DOC.relative_to(ROOT)}")
    print(f"Wrote {PIN_MAP_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
