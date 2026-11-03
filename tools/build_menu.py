"""Clone native video-option rows without changing existing Blueprint bytecode.

Export references are one-based Unreal package indices, not Python list offsets.
All constants below describe the validated original Video_OptionsList asset.
"""

import copy
import hashlib
import json
import subprocess
from pathlib import Path

from asset_io import asset_write, verify_original_roundtrip
from paths import ASSETS, BUILD, PAKS, REPAK, UASSET

WORK = BUILD / "graphics"
STAGE = WORK / "menu-package"
ASSET_PATH = Path("QueensDomain/Content/UI/Menus/OptionsMenu/OptionLists/Video_OptionsList.uasset")
ORIGINAL_EXPORT_COUNT = 102
ROW_EXPORT = 49
CONTROL_EXPORT = 63
SCROLLBOX_EXPORT = 81
SLOT_EXPORT = 85
RESET_SLOT_EXPORT = 96
OPTION_ROWS = [
    ("preset", "Graphics preset", ["Original", "Modern", "Custom"]),
    ("aa", "Anti-aliasing", ["Off", "FXAA", "TAA"]),
    ("af", "Anisotropic filtering", ["Game default", "1x", "2x", "4x", "8x", "16x"]),
    ("dither", "Dithering", ["Off", "On"]),
    ("gradients", "Colour gradients", ["Original", "Smooth", "Smooth + bias"]),
    ("vignette", "Vignette", ["Off", "25%", "50%", "75%", "100% (Original)"]),
]


def property_named(export: dict, name: str) -> dict:
    return next(prop for prop in export["Data"] if prop["Name"] == name)


def remap_references(node, references: dict[int, int]) -> None:
    """Retarget a cloned row's object/dependency references to its cloned children."""
    if isinstance(node, list):
        for child in node:
            remap_references(child, references)
    elif isinstance(node, dict):
        if "ObjectPropertyData" in node.get("$type", "") and node.get("Value") in references:
            node["Value"] = references[node["Value"]]
        for key, value in node.items():
            if key.endswith("Dependencies") and isinstance(value, list):
                node[key] = [references.get(index, index) for index in value]
            else:
                remap_references(value, references)


def clone_property(template: dict, **changes) -> dict:
    result = copy.deepcopy(template)
    result.update(changes)
    return result


def append_option(data: dict, original: dict, key: str, label: str, options: list[str]) -> int:
    """Append one row/control/slot triple; return its one-based slot reference."""
    exports = data["Exports"]
    first = len(exports) + 1
    references = {ROW_EXPORT: first, CONTROL_EXPORT: first + 1, SLOT_EXPORT: first + 2}
    row, control, slot = [copy.deepcopy(original["Exports"][index - 1]) for index in references]
    for export in (row, control, slot):
        remap_references(export, references)

    text_template = property_named(original["Exports"][CONTROL_EXPORT - 1], "Options")["Value"][0]
    flag_template = property_named(original["Exports"][SCROLLBOX_EXPORT - 1], "bIsVariable")
    row["ObjectName"] = "QDGraphicsRow_" + key
    control["ObjectName"] = "QDGraphicsControl_" + key
    slot["ObjectName"] = "QDGraphicsSlot_" + key
    row["Data"][0] = clone_property(text_template, Name="Name", CultureInvariantString=label)
    property_named(row, "Property")["Value"] = "QDGraphics_" + key
    row["Data"].append(clone_property(flag_template, Name="DisableRevert", Value=True))
    property_named(control, "Options")["Value"] = [
        clone_property(text_template, Name=str(index), CultureInvariantString=text)
        for index, text in enumerate(options)
    ]
    control["Data"].append(clone_property(flag_template, Name="SkipSavingOption", Value=True))
    control["Data"].append(copy.deepcopy(property_named(row, "Property")))
    exports.extend([row, control, slot])
    data["DependsMap"].extend([[], [], []])
    return first + 2


def insert_scrollbox_slots(data: dict, new_slots: list[int]) -> list:
    scrollbox = data["Exports"][SCROLLBOX_EXPORT - 1]
    slots = property_named(scrollbox, "Slots")["Value"]
    assert slots[-1]["Value"] == RESET_SLOT_EXPORT
    added = [clone_property(slots[0], Value=index) for index in new_slots]
    # Preset first; individual options immediately before the existing Reset row.
    slots.insert(0, added[0])
    slots[-1:-1] = added[1:]
    for index, slot in enumerate(slots):
        slot["Name"] = str(index)
    scrollbox["CreateBeforeSerializationDependencies"].extend(new_slots)
    return slots


def append_new_names(node, name_map: list[str]) -> None:
    """Preserve existing name indices and append new names in serialization order."""
    if isinstance(node, list):
        for child in node:
            append_new_names(child, name_map)
    elif isinstance(node, dict):
        for key, value in node.items():
            is_name = key in ("Name", "ObjectName") and isinstance(value, str)
            is_name_value = key == "Value" and "NamePropertyData" in node.get("$type", "")
            if (is_name or is_name_value) and value not in name_map:
                name_map.append(value)
            else:
                append_new_names(value, name_map)


def extend_menu(original: dict) -> dict:
    assert len(original["Exports"]) == ORIGINAL_EXPORT_COUNT
    data = copy.deepcopy(original)
    new_slots = [append_option(data, original, *spec) for spec in OPTION_ROWS]
    slots = insert_scrollbox_slots(data, new_slots)
    append_new_names(data["Exports"][ORIGINAL_EXPORT_COUNT:], data["NameMap"])
    append_new_names(slots, data["NameMap"])
    data["Generations"][-1].update(ExportCount=len(data["Exports"]), NameCount=len(data["NameMap"]))
    for index, original_export in enumerate(original["Exports"]):
        if index != SCROLLBOX_EXPORT - 1:
            assert data["Exports"][index] == original_export, (
                f"Original export changed: {index + 1}"
            )
    return data


def verify_patched_roundtrip(original: dict, patched: dict) -> None:
    parsed_path = WORK / "roundtrip/Menu-patched.json"
    subprocess.run(
        [str(UASSET), "tojson", str(STAGE / ASSET_PATH), str(parsed_path), "VER_UE4_27"], check=True
    )
    rebuilt = json.loads(parsed_path.read_text())
    assert len(rebuilt["Exports"]) == ORIGINAL_EXPORT_COUNT + 3 * len(OPTION_ROWS)
    for index, export in enumerate(original["Exports"]):
        if "ScriptBytecode" in export:
            assert export["ScriptBytecode"] == rebuilt["Exports"][index]["ScriptBytecode"]
    for index in range(ORIGINAL_EXPORT_COUNT, len(patched["Exports"])):
        assert patched["Exports"][index]["Data"] == rebuilt["Exports"][index]["Data"], (
            f"Roundtrip new row {index + 1}"
        )
    assert property_named(rebuilt["Exports"][SCROLLBOX_EXPORT - 1], "Slots") == property_named(
        patched["Exports"][SCROLLBOX_EXPORT - 1], "Slots"
    )


def main() -> None:
    original = json.loads((WORK / "json/Video_OptionsList.json").read_text())
    verify_original_roundtrip(
        original, ASSETS / ASSET_PATH, WORK / "roundtrip/Video_OptionsList.uasset"
    )
    patched = extend_menu(original)
    asset_write(patched, STAGE / ASSET_PATH)
    verify_patched_roundtrip(original, patched)
    pak = PAKS / "QueensDomain_GraphicsMenu_P.pak"
    subprocess.run([str(REPAK), "pack", "--version", "V8B", str(STAGE), str(pak)], check=True)
    report = dict(
        original_roundtrip_identical=True,
        original_blueprint_bytecode_preserved=True,
        original_exports_preserved_except_scrollbox=True,
        added_native_rows=len(OPTION_ROWS),
        added_exports=3 * len(OPTION_ROWS),
        modified_assets=[str(ASSET_PATH)],
        sha256=hashlib.sha256(pak.read_bytes()).hexdigest(),
    )
    (PAKS / "menu-validation.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
