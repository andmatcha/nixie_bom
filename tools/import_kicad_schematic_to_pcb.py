#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import pcbnew
except ModuleNotFoundError as exc:
    raise SystemExit(
        "pcbnew Python module was not found. Run this script with KiCad's bundled Python, for example:\n"
        "/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 "
        "tools/import_kicad_schematic_to_pcb.py"
    ) from exc


ROOT = Path(__file__).resolve().parents[1]
KICAD_PROJECT = ROOT / "kicad/nixie_clock"
DEFAULT_SCH = KICAD_PROJECT / "nixie_clock.kicad_sch"
DEFAULT_PCB = KICAD_PROJECT / "nixie_clock.kicad_pcb"
LOCAL_FP_DIR = KICAD_PROJECT / "nixie_clock_bom.pretty"
KICAD_FOOTPRINT_DIR_CANDIDATES = [
    Path(os.environ["KICAD10_FOOTPRINT_DIR"]) if os.environ.get("KICAD10_FOOTPRINT_DIR") else None,
    Path(os.environ["KICAD9_FOOTPRINT_DIR"]) if os.environ.get("KICAD9_FOOTPRINT_DIR") else None,
    Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"),
    Path("/usr/share/kicad/footprints"),
    Path("/usr/local/share/kicad/footprints"),
]


@dataclass
class SchematicFootprint:
    reference: str
    value: str
    footprint: str
    uuid: str
    digikey_part_number: str
    manufacturer_part_number: str
    line_id: str
    description: str


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


def unescape_kicad_string(value: str) -> str:
    return value.replace(r"\\", "\\").replace(r"\"", '"')


def property_value(block: str, name: str) -> str:
    pattern = re.compile(rf'\(property\s+"{re.escape(name)}"\s+"((?:\\.|[^"])*)"')
    match = pattern.search(block)
    return unescape_kicad_string(match.group(1)) if match else ""


def parse_schematic(path: Path) -> tuple[str, list[SchematicFootprint]]:
    text = path.read_text(encoding="utf-8")
    root_uuid_match = re.search(r'^\t\(uuid\s+"([^"]+)"\)', text, flags=re.MULTILINE)
    if not root_uuid_match:
        raise ValueError(f"Root schematic UUID was not found in {path}")
    root_uuid = root_uuid_match.group(1)

    footprints: list[SchematicFootprint] = []
    for match in re.finditer(r"(?m)^\t\(symbol\s*$", text):
        block = balanced_sexp(text, match.start())
        if "(lib_id " not in block:
            continue
        uuid_match = re.search(r'\n\t\t\(uuid\s+"([^"]+)"\)', block)
        if not uuid_match:
            raise ValueError("Placed symbol without uuid was found.")
        item = SchematicFootprint(
            reference=property_value(block, "Reference"),
            value=property_value(block, "Value"),
            footprint=property_value(block, "Footprint"),
            uuid=uuid_match.group(1),
            digikey_part_number=property_value(block, "Digi-Key Part Number"),
            manufacturer_part_number=property_value(block, "Manufacturer Part Number"),
            line_id=property_value(block, "LineId"),
            description=property_value(block, "Description"),
        )
        if not item.reference or not item.footprint:
            raise ValueError(f"Placed symbol is missing Reference or Footprint: {block[:200]}")
        footprints.append(item)
    if not footprints:
        raise ValueError(f"No placed schematic symbols were found in {path}")
    return root_uuid, footprints


def standard_footprint_dir() -> Path:
    for candidate in KICAD_FOOTPRINT_DIR_CANDIDATES:
        if candidate and candidate.is_dir():
            return candidate
    raise FileNotFoundError("KiCad standard footprint directory was not found.")


def footprint_library_path(lib: str) -> Path:
    if lib == "nixie_clock_bom":
        return LOCAL_FP_DIR
    return standard_footprint_dir() / f"{lib}.pretty"


def load_footprint(footprint_id: str):
    lib, name = footprint_id.split(":", 1)
    lib_path = footprint_library_path(lib)
    if not lib_path.is_dir():
        raise FileNotFoundError(f"Footprint library not found for {footprint_id}: {lib_path}")
    footprint_path = lib_path / f"{name}.kicad_mod"
    if not footprint_path.is_file():
        raise FileNotFoundError(f"Footprint file not found for {footprint_id}: {footprint_path}")
    footprint = pcbnew.FootprintLoad(str(lib_path), name)
    if footprint is None:
        raise ValueError(f"KiCad failed to load footprint {footprint_id}")
    footprint.SetFPID(pcbnew.LIB_ID(lib, name))
    return footprint


def set_symbol_path(footprint, root_uuid: str, symbol_uuid: str) -> None:
    path = pcbnew.KIID_PATH()
    path.push_back(pcbnew.KIID(root_uuid))
    path.push_back(pcbnew.KIID(symbol_uuid))
    footprint.SetPath(path)


def set_hidden_field(footprint, name: str, value: str) -> None:
    if not value:
        return
    footprint.SetField(name, value)
    for field in footprint.GetFields():
        if field.GetName() == name:
            field.SetVisible(False)


def place_footprints(board_path: Path, root_uuid: str, items: list[SchematicFootprint], replace: bool) -> None:
    if board_path.exists():
        board = pcbnew.LoadBoard(str(board_path))
    else:
        board = pcbnew.BOARD()

    existing = list(board.GetFootprints())
    if existing and not replace:
        raise ValueError(
            f"{board_path} already contains {len(existing)} footprints. "
            "Re-run with --replace to regenerate placement."
        )
    for footprint in existing:
        board.Delete(footprint)

    cols = 16
    x0_mm = 20.0
    y0_mm = 20.0
    dx_mm = 25.0
    dy_mm = 25.0

    for index, item in enumerate(items):
        footprint = load_footprint(item.footprint)
        footprint.SetReference(item.reference)
        footprint.SetValue(item.value)
        footprint.Reference().SetVisible(True)
        footprint.Value().SetVisible(False)
        col = index % cols
        row = index // cols
        footprint.SetPosition(pcbnew.VECTOR2I_MM(x0_mm + col * dx_mm, y0_mm + row * dy_mm))
        set_symbol_path(footprint, root_uuid, item.uuid)
        set_hidden_field(footprint, "Digi-Key Part Number", item.digikey_part_number)
        set_hidden_field(footprint, "Manufacturer Part Number", item.manufacturer_part_number)
        set_hidden_field(footprint, "LineId", item.line_id)
        set_hidden_field(footprint, "Description", item.description)
        board.Add(footprint)

    board.Save(str(board_path))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Place all schematic footprints into the KiCad PCB file.")
    parser.add_argument("--schematic", type=Path, default=DEFAULT_SCH)
    parser.add_argument("--pcb", type=Path, default=DEFAULT_PCB)
    parser.add_argument("--replace", action="store_true", help="Replace existing footprints in the PCB file.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root_uuid, items = parse_schematic(args.schematic)
    place_footprints(args.pcb, root_uuid, items, args.replace)
    print(f"Placed {len(items)} footprints into {args.pcb.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
