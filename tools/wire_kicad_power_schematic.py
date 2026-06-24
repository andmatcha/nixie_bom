#!/usr/bin/env python3
"""Lay out and wire the power-supply section of the KiCad schematic.

The original BOM schematic is generated as a placement/audit artifact.  This
script makes the power section readable by moving only the power components into
an electrical topology and adding direct wires for the local circuit paths.
Labels are kept for external inputs/outputs and for long nets that cross
between the HV and 3.3 V power blocks.
"""

from __future__ import annotations

import math
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMATIC = PROJECT_ROOT / "kicad" / "nixie_clock" / "nixie_clock.kicad_sch"

UUID_NAMESPACE = uuid.UUID("b8ca5e94-6e4f-4f5b-b2f3-b29b7b79d4a5")
GRID_MM = 0.01


PIN_NETS: dict[str, dict[str, str]] = {
    "U1": {
        "1": "RC",
        "2": "SS",
        "3": "DIS_EN",
        "4": "COMP",
        "5": "FB",
        "6": "GND",
        "7": "ISNS",
        "8": "GDRV",
        "9": "BP",
        "10": "+12V_HV",
    },
    "FHV1": {"1": "+12V_IN", "2": "+12V_HV"},
    "L1": {"1": "+12V_HV", "2": "SW_HV"},
    "Q1": {"1": "GDRV_GATE", "2": "SW_HV", "3": "ISENSE_SRC", "4": "SW_HV"},
    "D1": {"1": "HV170", "2": "SW_HV"},
    "CIN1": {"1": "+12V_HV", "2": "GND"},
    "CIN2": {"1": "+12V_HV", "2": "GND"},
    "CINB1": {"1": "+12V_HV", "2": "GND"},
    "CINB2": {"1": "+12V_HV", "2": "GND"},
    "COUT1": {"1": "HV170", "2": "GND"},
    "COUT2": {"1": "HV170", "2": "GND"},
    "COUT3": {"1": "HV170", "2": "GND"},
    "CVDD1": {"1": "+12V_HV", "2": "GND"},
    "CBP1": {"1": "BP", "2": "GND"},
    "CSS1": {"1": "SS", "2": "GND"},
    "CRC1": {"1": "RC", "2": "GND"},
    "CIFLT1": {"1": "ISNS", "2": "GND"},
    "CCOMP1": {"1": "COMP_Z", "2": "FB"},
    "CHF1": {"1": "COMP", "2": "FB"},
    "RSNS1": {"1": "ISENSE_SRC", "2": "GND"},
    "RIFLT1": {"1": "ISENSE_SRC", "2": "ISNS"},
    "REN1": {"1": "HV_DISABLE", "2": "DIS_EN"},
    "RRC1": {"1": "+12V_HV", "2": "RC"},
    "RG1": {"1": "GDRV", "2": "GDRV_GATE"},
    "RFB1": {"1": "HV170", "2": "FB_DIV1"},
    "RFB2": {"1": "FB_DIV1", "2": "FB_DIV2"},
    "RFB3": {"1": "FB_DIV2", "2": "FB_DIV3"},
    "RFB4": {"1": "FB_DIV3", "2": "FB_DIV4"},
    "RFB5": {"1": "FB_DIV4", "2": "FB"},
    "RFB6": {"1": "FB", "2": "GND"},
    "RCOMP1": {"1": "COMP", "2": "COMP_Z"},
    "RBLD1": {"1": "HV170", "2": "BLD1"},
    "RBLD2": {"1": "BLD1", "2": "BLD2"},
    "RBLD3": {"1": "BLD2", "2": "GND"},
    "RENPD1": {"1": "DIS_EN", "2": "GND"},
    "R3V3EN1": {"1": "+12V_IN", "2": "BUCK_EN"},
    "U3": {
        "1": "+3V3",
        "2": "BUCK_EN",
        "3": "+12V_IN",
        "4": "GND",
        "5": "SW_3V3",
        "6": "BST_3V3",
    },
    "L2": {"1": "SW_3V3", "2": "+3V3"},
    "C3V3IN1": {"1": "+12V_IN", "2": "GND"},
    "C3V3IN2": {"1": "+12V_IN", "2": "GND"},
    "C3V3OUT1": {"1": "+3V3", "2": "GND"},
    "C3V3OUT2": {"1": "+3V3", "2": "GND"},
    "CBOOT1": {"1": "BST_3V3", "2": "SW_3V3"},
    "C3V3HF1": {"1": "+12V_IN", "2": "GND"},
}


POWER_PLACEMENTS: dict[str, tuple[float, float, float]] = {
    "FHV1": (40.64, 52.07, 90),
    "L1": (91.44, 52.07, 90),
    "D1": (124.46, 52.07, 180),
    "Q1": (101.60, 73.66, 0),
    "U1": (45.72, 88.90, 0),
    "CIN1": (58.42, 64.77, 0),
    "CIN2": (66.04, 64.77, 0),
    "CINB1": (73.66, 64.77, 0),
    "CINB2": (81.28, 64.77, 0),
    "COUT1": (134.62, 55.88, 0),
    "COUT2": (142.24, 55.88, 0),
    "COUT3": (149.86, 55.88, 0),
    "CVDD1": (50.80, 64.77, 0),
    "CBP1": (71.12, 99.06, 0),
    "CSS1": (22.86, 93.98, 0),
    "CRC1": (22.86, 81.28, 0),
    "CIFLT1": (76.20, 88.90, 0),
    "CCOMP1": (35.56, 106.68, 90),
    "CHF1": (29.21, 116.84, 90),
    "RSNS1": (78.74, 88.90, 0),
    "RIFLT1": (69.85, 81.28, 90),
    "REN1": (22.86, 88.90, 90),
    "RRC1": (22.86, 68.58, 0),
    "RG1": (64.77, 88.90, 90),
    "RFB1": (162.56, 55.88, 0),
    "RFB2": (162.56, 63.50, 0),
    "RFB3": (162.56, 71.12, 0),
    "RFB4": (162.56, 78.74, 0),
    "RFB5": (162.56, 86.36, 0),
    "RFB6": (162.56, 93.98, 0),
    "RCOMP1": (22.86, 106.68, 90),
    "RBLD1": (185.42, 55.88, 0),
    "RBLD2": (185.42, 63.50, 0),
    "RBLD3": (185.42, 71.12, 0),
    "RENPD1": (35.56, 101.60, 0),
    "R3V3EN1": (474.98, 78.74, 0),
    "U3": (500.38, 76.20, 0),
    "L2": (530.86, 73.66, 90),
    "C3V3IN1": (462.28, 91.44, 0),
    "C3V3IN2": (469.90, 91.44, 0),
    "C3V3OUT1": (543.56, 91.44, 0),
    "C3V3OUT2": (551.18, 91.44, 0),
    "CBOOT1": (520.70, 72.39, 0),
    "C3V3HF1": (477.52, 91.44, 0),
}


LABEL_SPECS: tuple[tuple[str, str, tuple[float, float]], ...] = (
    ("label-hv-in", "+12V_IN", (30.48, 52.07)),
    ("label-hv-12", "+12V_HV", (46.99, 52.07)),
    ("label-hv-sw", "SW_HV", (100.33, 52.07)),
    ("label-hv-out", "HV170", (130.81, 52.07)),
    ("label-hv-disable", "HV_DISABLE", (16.51, 88.90)),
    ("label-hv-gnd", "GND", (22.86, 104.14)),
    ("label-buck-in", "+12V_IN", (462.28, 73.66)),
    ("label-buck-out", "+3V3", (536.58, 73.66)),
    ("label-buck-gnd", "GND", (462.28, 104.14)),
)

JUNCTION_NAMES: tuple[str, ...] = (
    "j-hv-12-fuse",
    "j-hv-12-l1",
    "j-hv-12-u1",
    "j-hv-12-cvdd",
    "j-hv-12-cin1",
    "j-hv-12-cin2",
    "j-hv-12-cinb1",
    "j-hv-12-cinb2",
    "j-hv-12-rrc",
    "j-hv-sw-l1",
    "j-hv-sw-q1d2",
    "j-hv-sw-q1d4",
    "j-hv-sw-d1",
    "j-hv170-d1",
    "j-hv170-cout1",
    "j-hv170-cout2",
    "j-hv170-cout3",
    "j-hv170-rfb",
    "j-hv170-bld",
    "j-hvgnd-u1",
    "j-hvgnd-cvdd",
    "j-hvgnd-cin1",
    "j-hvgnd-cin2",
    "j-hvgnd-cinb1",
    "j-hvgnd-cinb2",
    "j-hvgnd-cout1",
    "j-hvgnd-cout2",
    "j-hvgnd-cout3",
    "j-hvgnd-crc",
    "j-hvgnd-css",
    "j-hvgnd-cbp",
    "j-hvgnd-ciflt",
    "j-hvgnd-rsns",
    "j-hvgnd-renpd",
    "j-hvgnd-rfb",
    "j-hvgnd-bld",
    "j-fb-rfb",
    "j-comp-main",
    "j-fb-comp",
    "j-isense",
    "j-isns",
    "j-buck-in",
    "j-buck-in-r3v3en",
    "j-buck-in-c3v3in1",
    "j-buck-in-c3v3in2",
    "j-buck-in-c3v3hf",
    "j-buck-sw",
    "j-buck-sw-cboot",
    "j-buck-out",
    "j-buck-out-c3v3out1",
    "j-buck-out-c3v3out2",
    "j-buck-gnd",
    "j-buck-gnd-c3v3in1",
    "j-buck-gnd-c3v3in2",
    "j-buck-gnd-c3v3hf",
    "j-buck-gnd-c3v3out1",
    "j-buck-gnd-c3v3out2",
)


@dataclass(frozen=True)
class Pin:
    number: str
    x: float
    y: float


@dataclass(frozen=True)
class PlacedSymbol:
    ref: str
    lib_id: str
    x: float
    y: float
    rotation: float


def tokenize(text: str) -> list[str]:
    return re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', text)


def atom(token: str) -> str:
    if token.startswith('"'):
        return bytes(token[1:-1], "utf-8").decode("unicode_escape")
    return token


def parse_sexpr(text: str) -> list[Any]:
    tokens = tokenize(text)
    position = 0

    def parse_node() -> Any:
        nonlocal position
        if tokens[position] == "(":
            position += 1
            node: list[Any] = []
            while tokens[position] != ")":
                node.append(parse_node())
            position += 1
            return node
        value = atom(tokens[position])
        position += 1
        return value

    return parse_node()


def walk(node: Any) -> Iterable[Any]:
    if isinstance(node, list):
        yield node
        for item in node:
            yield from walk(item)


def child(node: list[Any], name: str) -> list[Any] | None:
    for item in node:
        if isinstance(item, list) and item and item[0] == name:
            return item
    return None


def property_value(node: list[Any], name: str) -> str | None:
    for item in node:
        if isinstance(item, list) and len(item) >= 3 and item[0] == "property" and item[1] == name:
            return str(item[2])
    return None


def parse_schematic(text: str) -> tuple[dict[str, PlacedSymbol], dict[str, dict[str, Pin]]]:
    root = parse_sexpr(text)
    lib_symbols = child(root, "lib_symbols")
    if lib_symbols is None:
        raise ValueError("lib_symbols block was not found")

    pins_by_lib: dict[str, dict[str, Pin]] = {}
    for item in lib_symbols[1:]:
        if not (isinstance(item, list) and item and item[0] == "symbol"):
            continue
        pins: dict[str, Pin] = {}
        for pin in walk(item):
            if not (isinstance(pin, list) and pin and pin[0] == "pin"):
                continue
            number = child(pin, "number")
            at = child(pin, "at")
            if not number or not at:
                continue
            pin_number = str(number[1])
            pins[pin_number] = Pin(pin_number, float(at[1]), float(at[2]))
        pins_by_lib[str(item[1])] = pins

    symbols: dict[str, PlacedSymbol] = {}
    for item in root:
        if not (isinstance(item, list) and item and item[0] == "symbol"):
            continue
        lib_id_node = child(item, "lib_id")
        ref = property_value(item, "Reference")
        at = child(item, "at")
        if not lib_id_node or not ref or not at:
            continue
        symbols[ref] = PlacedSymbol(
            ref=ref,
            lib_id=str(lib_id_node[1]),
            x=float(at[1]),
            y=float(at[2]),
            rotation=float(at[3]) if len(at) >= 4 else 0.0,
        )
    return symbols, pins_by_lib


def top_level_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    depth = 0
    child_start: int | None = None
    in_string = False
    escaped = False

    for index, char in enumerate(text):
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
            continue
        if char == "(":
            if depth == 1:
                child_start = index
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 1 and child_start is not None:
                spans.append((child_start, index + 1))
                child_start = None
    return spans


def generated_uuid(name: str) -> str:
    return str(uuid.uuid5(UUID_NAMESPACE, name))


def fmt(value: float) -> str:
    rounded = round(value / GRID_MM) * GRID_MM
    return f"{rounded:.2f}"


def rotate(x: float, y: float, degrees: float) -> tuple[float, float]:
    angle = math.radians(degrees)
    return x * math.cos(angle) - y * math.sin(angle), x * math.sin(angle) + y * math.cos(angle)


def pin_position(symbol: PlacedSymbol, pin: Pin) -> tuple[float, float]:
    # KiCad symbol-library coordinates are Y-up, while sheet coordinates are
    # Y-down.  Mirror Y before rotating and placing the pin.
    dx, dy = rotate(pin.x, -pin.y, -symbol.rotation)
    return symbol.x + dx, symbol.y + dy


def apply_symbol_placements(text: str) -> str:
    result: list[str] = []
    cursor = 0
    at_re = re.compile(r"(\(at\s+)(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)(\))")

    for start, end in top_level_spans(text):
        block = text[start:end]
        if not block.startswith("(symbol"):
            continue
        match_ref = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', block)
        if not match_ref:
            continue
        ref = match_ref.group(1)
        placement = POWER_PLACEMENTS.get(ref)
        if placement is None:
            continue

        first_at = at_re.search(block)
        if first_at is None:
            raise ValueError(f"{ref}: top-level at block not found")
        old_x = float(first_at.group(2))
        old_y = float(first_at.group(3))
        new_x, new_y, new_rotation = placement
        dx = new_x - old_x
        dy = new_y - old_y
        seen_first = False

        def replace_at(match: re.Match[str]) -> str:
            nonlocal seen_first
            x = float(match.group(2))
            y = float(match.group(3))
            angle = match.group(4)
            if not seen_first:
                seen_first = True
                angle = fmt(new_rotation)
                return f"{match.group(1)}{fmt(new_x)} {fmt(new_y)} {angle}{match.group(5)}"
            return f"{match.group(1)}{fmt(x + dx)} {fmt(y + dy)} {angle}{match.group(5)}"

        result.append(text[cursor:start])
        result.append(at_re.sub(replace_at, block))
        cursor = end

    result.append(text[cursor:])
    return "".join(result)


def legacy_generated_uuids() -> set[str]:
    uuids: set[str] = set()
    for ref, pin_map in PIN_NETS.items():
        for pin_number, net in pin_map.items():
            uuids.add(generated_uuid(f"wire:{ref}:{pin_number}"))
            uuids.add(generated_uuid(f"label:{ref}:{pin_number}:{net}"))
    return uuids


def generated_names() -> set[str]:
    names: set[str] = set()
    for route_name in ROUTE_NAMES:
        for index in range(6):
            names.add(f"wire:{route_name}:{index}")
    for label_name, net, _point in LABEL_SPECS:
        names.add(f"label:{label_name}:{net}")
    for junction_name in JUNCTION_NAMES:
        names.add(f"junction:{junction_name}")
    return names


def generated_uuids() -> set[str]:
    uuids = legacy_generated_uuids()
    uuids.update(generated_uuid(name) for name in generated_names())
    return uuids


def remove_generated_objects(text: str, uuids: set[str]) -> str:
    skip_spans = []
    for start, end in top_level_spans(text):
        chunk = text[start:end]
        if any(uid in chunk for uid in uuids):
            skip_spans.append((start, end))

    if not skip_spans:
        return text

    result: list[str] = []
    cursor = 0
    for start, end in skip_spans:
        result.append(text[cursor:start])
        cursor = end
    result.append(text[cursor:])
    return "".join(result)


def wire_object(name: str, index: int, p1: tuple[float, float], p2: tuple[float, float]) -> str:
    uid = generated_uuid(f"wire:{name}:{index}")
    return (
        "\t(wire\n"
        f"\t\t(pts (xy {fmt(p1[0])} {fmt(p1[1])}) (xy {fmt(p2[0])} {fmt(p2[1])}))\n"
        "\t\t(stroke (width 0) (type default))\n"
        f"\t\t(uuid \"{uid}\")\n"
        "\t)"
    )


def label_object(name: str, net: str, point: tuple[float, float]) -> str:
    uid = generated_uuid(f"label:{name}:{net}")
    return (
        f"\t(label \"{net}\"\n"
        f"\t\t(at {fmt(point[0])} {fmt(point[1])} 0)\n"
        "\t\t(effects\n"
        "\t\t\t(font (size 1.27 1.27))\n"
        "\t\t\t(justify left bottom)\n"
        "\t\t)\n"
        f"\t\t(uuid \"{uid}\")\n"
        "\t)"
    )


def junction_object(name: str, point: tuple[float, float]) -> str:
    uid = generated_uuid(f"junction:{name}")
    return (
        f"\t(junction (at {fmt(point[0])} {fmt(point[1])})\n"
        "\t\t(diameter 0)\n"
        "\t\t(color 0 0 0 0)\n"
        f"\t\t(uuid \"{uid}\")\n"
        "\t)"
    )


def route_points(*points: tuple[float, float]) -> list[tuple[float, float]]:
    route: list[tuple[float, float]] = []
    for point in points:
        if not route or (fmt(route[-1][0]), fmt(route[-1][1])) != (fmt(point[0]), fmt(point[1])):
            route.append(point)
    return route


def route_objects(name: str, *points: tuple[float, float]) -> list[str]:
    route = route_points(*points)
    return [wire_object(name, index, route[index], route[index + 1]) for index in range(len(route) - 1)]


def h_branch(name: str, start: tuple[float, float], x: float) -> list[str]:
    return route_objects(name, start, (x, start[1]))


def v_branch(name: str, start: tuple[float, float], y: float) -> list[str]:
    return route_objects(name, start, (start[0], y))


def orthogonal_x_first(name: str, start: tuple[float, float], end: tuple[float, float]) -> list[str]:
    return route_objects(name, start, (end[0], start[1]), end)


def orthogonal_y_first(name: str, start: tuple[float, float], end: tuple[float, float]) -> list[str]:
    return route_objects(name, start, (start[0], end[1]), end)


def make_pin_getter(
    symbols: dict[str, PlacedSymbol],
    pins_by_lib: dict[str, dict[str, Pin]],
) -> Any:
    def p(ref: str, pin_number: str) -> tuple[float, float]:
        symbol = symbols[ref]
        pin = pins_by_lib[symbol.lib_id][pin_number]
        return pin_position(symbol, pin)

    return p


ROUTE_NAMES: tuple[str, ...] = (
    "hv-input-to-fuse",
    "hv-12-fuse-to-l1",
    "hv-12-u1-vdd",
    "hv-12-cvdd",
    "hv-12-cin1",
    "hv-12-cin2",
    "hv-12-cinb1",
    "hv-12-cinb2",
    "hv-12-rrc",
    "hv-sw-l1-to-d1",
    "hv-sw-q1-drain2",
    "hv-sw-q1-drain4",
    "hv170-main",
    "hv170-cout1",
    "hv170-cout2",
    "hv170-cout3",
    "hv170-rfb",
    "hv170-bld",
    "hv-gnd-main",
    "hv-gnd-u1",
    "hv-gnd-cvdd",
    "hv-gnd-cin1",
    "hv-gnd-cin2",
    "hv-gnd-cinb1",
    "hv-gnd-cinb2",
    "hv-gnd-cout1",
    "hv-gnd-cout2",
    "hv-gnd-cout3",
    "hv-gnd-rrc",
    "hv-gnd-css",
    "hv-gnd-crc",
    "hv-gnd-cbp",
    "hv-gnd-ciflt",
    "hv-gnd-rsns",
    "hv-gnd-renpd",
    "hv-gnd-rfb",
    "hv-gnd-bld",
    "hv-rc-net",
    "hv-ss-net",
    "hv-dis-ren",
    "hv-dis-renpd",
    "hv-comp-rcomp",
    "hv-comp-chf",
    "hv-comp-z",
    "hv-fb-ccomp",
    "hv-fb-chf",
    "hv-fb-divider",
    "hv-gdrv-rg",
    "hv-gate-q1",
    "hv-isense-q1-rsns",
    "hv-isense-riflt",
    "hv-isns-u1-riflt",
    "hv-isns-ciflt",
    "hv-bp-cbp",
    "buck-in-main",
    "buck-in-r3v3en",
    "buck-in-c3v3in1",
    "buck-in-c3v3in2",
    "buck-in-c3v3hf",
    "buck-en",
    "buck-sw-u3-l2",
    "buck-sw-cboot",
    "buck-bst-cboot",
    "buck-out-main",
    "buck-out-feedback",
    "buck-out-c3v3out1",
    "buck-out-c3v3out2",
    "buck-gnd-main",
    "buck-gnd-u3",
    "buck-gnd-c3v3in1",
    "buck-gnd-c3v3in2",
    "buck-gnd-c3v3hf",
    "buck-gnd-c3v3out1",
    "buck-gnd-c3v3out2",
)


def build_objects(symbols: dict[str, PlacedSymbol], pins_by_lib: dict[str, dict[str, Pin]]) -> list[str]:
    missing = [ref for ref in POWER_PLACEMENTS if ref not in symbols]
    if missing:
        raise ValueError("missing placed power symbols: " + ", ".join(sorted(missing)))

    p = make_pin_getter(symbols, pins_by_lib)
    objects: list[str] = []

    hv_y = 52.07
    hv_gnd_y = 104.14
    buck_in_y = 73.66
    buck_out_y = 73.66
    buck_gnd_y = 104.14

    objects += h_branch("hv-input-to-fuse", p("FHV1", "1"), 30.48)
    objects += route_objects("hv-12-fuse-to-l1", p("FHV1", "2"), p("L1", "1"))
    for name, ref, pin in (
        ("hv-12-u1-vdd", "U1", "10"),
        ("hv-12-cin1", "CIN1", "1"),
        ("hv-12-cin2", "CIN2", "1"),
        ("hv-12-cinb1", "CINB1", "1"),
        ("hv-12-cinb2", "CINB2", "1"),
    ):
        objects += v_branch(name, p(ref, pin), hv_y)
    objects += v_branch("hv-12-cvdd", p("CVDD1", "1"), hv_y)
    objects += route_objects(
        "hv-12-rrc",
        p("RRC1", "1"),
        (p("RRC1", "1")[0], 48.26),
        (p("U1", "10")[0], 48.26),
        (p("U1", "10")[0], hv_y),
    )

    objects += route_objects("hv-sw-l1-to-d1", p("L1", "2"), p("D1", "2"))
    objects += v_branch("hv-sw-q1-drain2", p("Q1", "2"), hv_y)
    objects += v_branch("hv-sw-q1-drain4", p("Q1", "4"), hv_y)

    objects += route_objects("hv170-main", p("D1", "1"), (p("RBLD1", "1")[0], hv_y))
    for name, ref, pin in (
        ("hv170-cout1", "COUT1", "1"),
        ("hv170-cout2", "COUT2", "1"),
        ("hv170-cout3", "COUT3", "1"),
        ("hv170-rfb", "RFB1", "1"),
        ("hv170-bld", "RBLD1", "1"),
    ):
        objects += v_branch(name, p(ref, pin), hv_y)

    objects += route_objects("hv-gnd-main", (p("CRC1", "2")[0], hv_gnd_y), (p("RBLD3", "2")[0], hv_gnd_y))
    for name, ref, pin in (
        ("hv-gnd-u1", "U1", "6"),
        ("hv-gnd-cvdd", "CVDD1", "2"),
        ("hv-gnd-cin1", "CIN1", "2"),
        ("hv-gnd-cin2", "CIN2", "2"),
        ("hv-gnd-cinb1", "CINB1", "2"),
        ("hv-gnd-cinb2", "CINB2", "2"),
        ("hv-gnd-cout1", "COUT1", "2"),
        ("hv-gnd-cout2", "COUT2", "2"),
        ("hv-gnd-cout3", "COUT3", "2"),
        ("hv-gnd-rrc", "CRC1", "2"),
        ("hv-gnd-css", "CSS1", "2"),
        ("hv-gnd-crc", "CRC1", "2"),
        ("hv-gnd-cbp", "CBP1", "2"),
        ("hv-gnd-ciflt", "CIFLT1", "2"),
        ("hv-gnd-rsns", "RSNS1", "2"),
        ("hv-gnd-renpd", "RENPD1", "2"),
        ("hv-gnd-rfb", "RFB6", "2"),
        ("hv-gnd-bld", "RBLD3", "2"),
    ):
        objects += v_branch(name, p(ref, pin), hv_gnd_y)

    objects += orthogonal_x_first("hv-rc-net", p("U1", "1"), p("CRC1", "1"))
    objects += orthogonal_y_first("hv-rc-net", p("RRC1", "2"), p("CRC1", "1"))
    objects += orthogonal_x_first("hv-ss-net", p("U1", "2"), p("CSS1", "1"))
    objects += route_objects("hv-dis-ren", p("REN1", "2"), p("U1", "3"))
    objects += orthogonal_y_first("hv-dis-renpd", p("RENPD1", "1"), p("U1", "3"))
    objects += h_branch("hv-dis-ren", p("REN1", "1"), 16.51)

    objects += orthogonal_y_first("hv-comp-rcomp", p("U1", "4"), p("RCOMP1", "1"))
    objects += orthogonal_y_first("hv-comp-chf", p("CHF1", "1"), p("U1", "4"))
    objects += route_objects("hv-comp-z", p("RCOMP1", "2"), p("CCOMP1", "1"))
    objects += route_objects("hv-fb-ccomp", p("CCOMP1", "2"), (45.72, p("CCOMP1", "2")[1]), p("U1", "5"))
    objects += orthogonal_y_first("hv-fb-chf", p("CHF1", "2"), p("U1", "5"))
    objects += route_objects("hv-fb-divider", p("RFB6", "1"), (45.72, p("RFB6", "1")[1]), p("U1", "5"))

    objects += route_objects("hv-gdrv-rg", p("U1", "8"), p("RG1", "1"))
    objects += orthogonal_y_first("hv-gate-q1", p("RG1", "2"), p("Q1", "1"))
    objects += route_objects("hv-isense-q1-rsns", p("Q1", "3"), p("RSNS1", "1"))
    objects += orthogonal_y_first("hv-isense-riflt", p("RIFLT1", "1"), p("Q1", "3"))
    objects += orthogonal_y_first("hv-isns-u1-riflt", p("RIFLT1", "2"), p("U1", "7"))
    objects += orthogonal_x_first("hv-isns-ciflt", p("CIFLT1", "1"), p("RIFLT1", "2"))
    objects += orthogonal_y_first("hv-bp-cbp", p("U1", "9"), p("CBP1", "1"))

    objects += route_objects("buck-in-main", (p("C3V3IN1", "1")[0], buck_in_y), p("U3", "3"))
    for name, ref, pin in (
        ("buck-in-r3v3en", "R3V3EN1", "1"),
        ("buck-in-c3v3in1", "C3V3IN1", "1"),
        ("buck-in-c3v3in2", "C3V3IN2", "1"),
        ("buck-in-c3v3hf", "C3V3HF1", "1"),
    ):
        objects += v_branch(name, p(ref, pin), buck_in_y)
    objects += orthogonal_x_first("buck-en", p("R3V3EN1", "2"), p("U3", "2"))

    objects += route_objects("buck-sw-u3-l2", p("U3", "5"), p("L2", "1"))
    objects += route_objects("buck-sw-cboot", p("CBOOT1", "2"), (p("CBOOT1", "2")[0], p("U3", "5")[1]), p("U3", "5"))
    objects += route_objects(
        "buck-bst-cboot",
        p("CBOOT1", "1"),
        (515.62, p("CBOOT1", "1")[1]),
        (515.62, p("U3", "6")[1]),
        p("U3", "6"),
    )

    objects += route_objects("buck-out-main", p("L2", "2"), (p("C3V3OUT2", "1")[0], buck_out_y))
    objects += route_objects("buck-out-feedback", p("U3", "1"), (p("U3", "1")[0], 83.82), (p("L2", "2")[0], 83.82), p("L2", "2"))
    for name, ref, pin in (
        ("buck-out-c3v3out1", "C3V3OUT1", "1"),
        ("buck-out-c3v3out2", "C3V3OUT2", "1"),
    ):
        objects += v_branch(name, p(ref, pin), buck_out_y)

    objects += route_objects("buck-gnd-main", (p("C3V3IN1", "2")[0], buck_gnd_y), (p("C3V3OUT2", "2")[0], buck_gnd_y))
    for name, ref, pin in (
        ("buck-gnd-u3", "U3", "4"),
        ("buck-gnd-c3v3in1", "C3V3IN1", "2"),
        ("buck-gnd-c3v3in2", "C3V3IN2", "2"),
        ("buck-gnd-c3v3hf", "C3V3HF1", "2"),
        ("buck-gnd-c3v3out1", "C3V3OUT1", "2"),
        ("buck-gnd-c3v3out2", "C3V3OUT2", "2"),
    ):
        objects += v_branch(name, p(ref, pin), buck_gnd_y)

    junction_points = {
        "j-hv-12-fuse": p("FHV1", "2"),
        "j-hv-12-l1": p("L1", "1"),
        "j-hv-12-u1": (p("U1", "10")[0], hv_y),
        "j-hv-12-cvdd": (p("CVDD1", "1")[0], hv_y),
        "j-hv-12-cin1": (p("CIN1", "1")[0], hv_y),
        "j-hv-12-cin2": (p("CIN2", "1")[0], hv_y),
        "j-hv-12-cinb1": (p("CINB1", "1")[0], hv_y),
        "j-hv-12-cinb2": (p("CINB2", "1")[0], hv_y),
        "j-hv-12-rrc": (p("U1", "10")[0], 48.26),
        "j-hv-sw-l1": p("L1", "2"),
        "j-hv-sw-q1d2": (p("Q1", "2")[0], hv_y),
        "j-hv-sw-q1d4": (p("Q1", "4")[0], hv_y),
        "j-hv-sw-d1": p("D1", "2"),
        "j-hv170-d1": p("D1", "1"),
        "j-hv170-cout1": p("COUT1", "1"),
        "j-hv170-cout2": p("COUT2", "1"),
        "j-hv170-cout3": p("COUT3", "1"),
        "j-hv170-rfb": (p("RFB1", "1")[0], hv_y),
        "j-hv170-bld": (p("RBLD1", "1")[0], hv_y),
        "j-hvgnd-u1": (p("U1", "6")[0], hv_gnd_y),
        "j-hvgnd-cvdd": (p("CVDD1", "2")[0], hv_gnd_y),
        "j-hvgnd-cin1": (p("CIN1", "2")[0], hv_gnd_y),
        "j-hvgnd-cin2": (p("CIN2", "2")[0], hv_gnd_y),
        "j-hvgnd-cinb1": (p("CINB1", "2")[0], hv_gnd_y),
        "j-hvgnd-cinb2": (p("CINB2", "2")[0], hv_gnd_y),
        "j-hvgnd-cout1": (p("COUT1", "2")[0], hv_gnd_y),
        "j-hvgnd-cout2": (p("COUT2", "2")[0], hv_gnd_y),
        "j-hvgnd-cout3": (p("COUT3", "2")[0], hv_gnd_y),
        "j-hvgnd-crc": (p("CRC1", "2")[0], hv_gnd_y),
        "j-hvgnd-css": (p("CSS1", "2")[0], hv_gnd_y),
        "j-hvgnd-cbp": (p("CBP1", "2")[0], hv_gnd_y),
        "j-hvgnd-ciflt": (p("CIFLT1", "2")[0], hv_gnd_y),
        "j-hvgnd-rsns": (p("RSNS1", "2")[0], hv_gnd_y),
        "j-hvgnd-renpd": (p("RENPD1", "2")[0], hv_gnd_y),
        "j-hvgnd-rfb": (p("RFB6", "2")[0], hv_gnd_y),
        "j-hvgnd-bld": (p("RBLD3", "2")[0], hv_gnd_y),
        "j-fb-rfb": p("RFB6", "1"),
        "j-comp-main": p("U1", "4"),
        "j-fb-comp": p("U1", "5"),
        "j-isense": p("Q1", "3"),
        "j-isns": p("RIFLT1", "2"),
        "j-buck-in": p("U3", "3"),
        "j-buck-in-r3v3en": (p("R3V3EN1", "1")[0], buck_in_y),
        "j-buck-in-c3v3in1": (p("C3V3IN1", "1")[0], buck_in_y),
        "j-buck-in-c3v3in2": (p("C3V3IN2", "1")[0], buck_in_y),
        "j-buck-in-c3v3hf": (p("C3V3HF1", "1")[0], buck_in_y),
        "j-buck-sw": p("U3", "5"),
        "j-buck-sw-cboot": (p("CBOOT1", "2")[0], p("U3", "5")[1]),
        "j-buck-out": p("L2", "2"),
        "j-buck-out-c3v3out1": (p("C3V3OUT1", "1")[0], buck_out_y),
        "j-buck-out-c3v3out2": (p("C3V3OUT2", "1")[0], buck_out_y),
        "j-buck-gnd": (p("U3", "4")[0], buck_gnd_y),
        "j-buck-gnd-c3v3in1": (p("C3V3IN1", "2")[0], buck_gnd_y),
        "j-buck-gnd-c3v3in2": (p("C3V3IN2", "2")[0], buck_gnd_y),
        "j-buck-gnd-c3v3hf": (p("C3V3HF1", "2")[0], buck_gnd_y),
        "j-buck-gnd-c3v3out1": (p("C3V3OUT1", "2")[0], buck_gnd_y),
        "j-buck-gnd-c3v3out2": (p("C3V3OUT2", "2")[0], buck_gnd_y),
    }
    for name in JUNCTION_NAMES:
        objects.append(junction_object(name, junction_points[name]))

    for name, net, point in LABEL_SPECS:
        objects.append(label_object(name, net, point))

    return objects


def insert_before_embedded_fonts(text: str, objects: list[str]) -> str:
    stripped = text.rstrip()
    if not stripped.endswith(")"):
        raise ValueError("schematic does not end with a root close parenthesis")

    marker = re.search(r"\n\t\(embedded_fonts\s+[^)]+\)\s*\n\)\s*$", stripped)
    generated = "\n\n" + "\n".join(objects)
    if marker:
        embedded_fonts = re.search(r"\n\t\(embedded_fonts\s+[^)]+\)", marker.group(0))
        if embedded_fonts is None:
            raise ValueError("embedded_fonts marker was malformed")
        body = stripped[: marker.start()].rstrip()
        return body + generated + embedded_fonts.group(0) + "\n)\n"

    body = stripped[:-1].rstrip()
    return body + generated + "\n)\n"


def main() -> None:
    text = SCHEMATIC.read_text()
    cleaned = remove_generated_objects(text, generated_uuids())
    placed = apply_symbol_placements(cleaned)
    symbols, pins_by_lib = parse_schematic(placed)
    objects = build_objects(symbols, pins_by_lib)
    SCHEMATIC.write_text(insert_before_embedded_fonts(placed, objects))
    wire_count = sum(1 for obj in objects if obj.startswith("\t(wire"))
    label_count = sum(1 for obj in objects if obj.startswith("\t(label"))
    print(f"wrote {wire_count} wires and {label_count} labels to {SCHEMATIC}")


if __name__ == "__main__":
    main()
