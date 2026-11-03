"""Serialize patched material shaders into an overlay PAK; never edit the game.

Pinned to the exact inspected DitherBase asset. This is not a general uasset editor.
Source compiler parameter-map hashes are not recoverable from the stripped DXBC.
New runtime shader IDs are SHA1(namespace + old ID + patched code), sorted with
every material resource index remapped. The resource hash uses Unreal's SHA1 of
the concatenated sorted IDs. Original vertex code/IDs and binding data survive.
"""

import hashlib
import json
import struct
import subprocess

from build_shader import chunks
from inspect_container import ROOT, SOURCE, decompress_lz4, u32
from inspect_frozen import inspect as inspect_frozen
from pak_io import read_entry
from paths import REPAK

# Binary layout of the validated UE4.27 DitherBase asset. These are byte offsets.
MATERIAL_SIZE_OFFSET = 7651
MATERIAL_PAYLOAD_OFFSET = 7655
SHADER_ID_OFFSETS = (7671, 8191)
EXPORT_TABLE_OFFSET = 5806
SERIAL_SIZE_FIELD = 28
SERIAL_OFFSET_FIELD = 36
HEADER_SIZE = 6030
PIXEL_SHADER_FREQUENCY = 3
SHADER_NAMESPACE = b"QueensDomain.SmoothLUT.v1\0"
ORIGINAL_EXPORT_SHA256 = "6ca3a04366a43c890378c8049e99f047742b4f1e6c85db61b5bd8de114d67b01"


def sha1_bytes(data):
    return hashlib.sha1(data).digest()


def pack_uint32(value):
    return struct.pack("<I", value)


def read_resource(data, position):
    resource_hash = data[position : position + 20]
    position += 20
    count = u32(data, position)
    position += 4
    hashes = [data[position + index * 20 : position + (index + 1) * 20] for index in range(count)]
    position += 20 * count
    assert hashes == sorted(hashes) and sha1_bytes(b"".join(hashes)) == resource_hash
    assert u32(data, position) == count
    position += 4
    entries = []
    for index in range(count):
        entry_start = position
        size = u32(data, position)
        position += 4
        code = data[position : position + size]
        position += size
        uncompressed_size = u32(data, position)
        frequency = data[position + 4]
        position += 5
        raw = code if size == uncompressed_size else decompress_lz4(code, uncompressed_size)
        dxbc = raw.index(b"DXBC")
        bcsize = u32(raw, dxbc + 24)
        chunks(raw[dxbc : dxbc + bcsize])
        optional_size = u32(raw, len(raw) - 4)
        assert len(raw) - optional_size == dxbc + bcsize
        entries.append(
            dict(
                hash=hashes[index],
                raw=raw,
                dxbc=dxbc,
                bcsize=bcsize,
                frequency=frequency,
                serialized=data[entry_start:position],
            )
        )
    return entries, position


def serialize_resource(entries):
    """Serialize the sorted hash table and each preserved/replaced shader record."""
    hashes = b"".join(entry["hash"] for entry in entries)
    return (
        sha1_bytes(hashes)
        + pack_uint32(len(entries))
        + hashes
        + pack_uint32(len(entries))
        + b"".join(entry["serialized"] for entry in entries)
    )


def verify_original_resource(original, resource_offset, end, entries):
    # Parse/serialize identity check for all original shader resource bytes.
    hashes = b"".join(entry["hash"] for entry in entries)
    roundtrip = (
        sha1_bytes(hashes)
        + pack_uint32(4)
        + hashes
        + pack_uint32(4)
        + b"".join(entry["serialized"] for entry in entries)
    )
    assert original[resource_offset:end] == roundtrip
    assert original[:resource_offset] + roundtrip + original[end:] == original


def replace_pixel_shaders(entries, shader_dir):
    """Replace DXBC only, preserving each record's bindings and optional suffix."""
    changes = []
    for index, entry in enumerate(entries):
        entry["old_index"] = index
        if entry["frequency"] == PIXEL_SHADER_FREQUENCY:
            bytecode = (shader_dir / f"{index}.shdr").read_bytes()
            raw = (
                entry["raw"][: entry["dxbc"]]
                + bytecode
                + entry["raw"][entry["dxbc"] + entry["bcsize"] :]
            )
            assert raw[: entry["dxbc"]] == entry["raw"][: entry["dxbc"]]
            assert (
                raw[-u32(raw, len(raw) - 4) :]
                == entry["raw"][-u32(entry["raw"], len(entry["raw"]) - 4) :]
            )
            entry["hash"] = sha1_bytes(SHADER_NAMESPACE + entry["hash"] + raw)
            entry["raw"] = raw
            entry["bcsize"] = len(bytecode)
            # Uncompressed entries are explicitly supported when sizes match.
            entry["serialized"] = (
                pack_uint32(len(raw)) + raw + pack_uint32(len(raw)) + bytes([entry["frequency"]])
            )
            changes.append(index)
    assert changes == [2, 3]


def update_material_metadata(original, patched, remap, resource_hash, shader_dir):
    """Update explicit size, identity, instruction-count, and sorted-index fields."""
    delta = len(patched) - len(original)
    frozen = inspect_frozen(original)
    for shader_metadata in frozen["shaders"]:
        struct.pack_into(
            "<I", patched, shader_metadata["index_offset"], remap[shader_metadata["index"]]
        )
        if shader_metadata["frequency"] == PIXEL_SHADER_FREQUENCY:
            lines = (shader_dir / f"{shader_metadata['index']}.asm").read_text().splitlines()
            instructions = sum(
                bool(line.strip()) and not line.strip().startswith(("//", "dcl_", "ps_"))
                for line in lines
            )
            struct.pack_into("<I", patched, shader_metadata["instructions_offset"], instructions)
    # These are identity fields, not material parameters or shader instructions.
    for position in SHADER_ID_OFFSETS:
        patched[position : position + 20] = sha1_bytes(
            SHADER_NAMESPACE + original[position : position + 20] + resource_hash
        )
    assert u32(original, MATERIAL_SIZE_OFFSET) == len(original) - 4 - MATERIAL_PAYLOAD_OFFSET
    struct.pack_into(
        "<I", patched, MATERIAL_SIZE_OFFSET, u32(original, MATERIAL_SIZE_OFFSET) + delta
    )
    return frozen


def update_package_header(header, original, patched):
    patched_header = bytearray(header)
    export_offset = EXPORT_TABLE_OFFSET
    assert (
        struct.unpack_from("<q", header, export_offset + SERIAL_SIZE_FIELD)[0] == len(original) - 4
    )
    assert struct.unpack_from("<q", header, export_offset + SERIAL_OFFSET_FIELD)[0] == len(header)
    struct.pack_into("<q", patched_header, export_offset + SERIAL_SIZE_FIELD, len(patched) - 4)
    original_bulk_pointer = struct.pack("<q", len(header) + len(original) - 4)
    assert header.count(original_bulk_pointer) == 1
    bulk_offset = header.index(original_bulk_pointer)
    assert bulk_offset < 193
    struct.pack_into("<q", patched_header, bulk_offset, len(header) + len(patched) - 4)
    return patched_header, bulk_offset


def verify_patched_material(
    original, patched, header, patched_header, resource_offset, entries, remap, frozen, bulk_offset
):
    export_offset = EXPORT_TABLE_OFFSET
    # Round-trip the NEW container and validate every code block and binding prefix.
    parsed, parsed_end = read_resource(patched, resource_offset)
    assert parsed_end == len(patched) - 4
    for index, entry in enumerate(entries):
        assert parsed[index]["raw"] == entry["raw"] and parsed[index]["hash"] == entry["hash"]
    patched_frozen = inspect_frozen(patched)
    for old, new in zip(frozen["shaders"], patched_frozen["shaders"]):
        assert new["index"] == remap[old["index"]]
        assert parsed[new["index"]]["frequency"] == old["frequency"]
    # Ensure every change before the shader resource table is an explicit metadata field.
    allowed = set(range(MATERIAL_SIZE_OFFSET, MATERIAL_PAYLOAD_OFFSET))
    for identity_offset in SHADER_ID_OFFSETS:
        allowed.update(range(identity_offset, identity_offset + 20))
    for shader_metadata in frozen["shaders"]:
        allowed.update(
            range(shader_metadata["index_offset"], shader_metadata["instructions_offset"] + 4)
        )
    assert all(
        before == after or index in allowed
        for index, (before, after) in enumerate(
            zip(original[:resource_offset], patched[:resource_offset])
        )
    )
    header_allowed = set(
        range(export_offset + SERIAL_SIZE_FIELD, export_offset + SERIAL_OFFSET_FIELD)
    ) | set(range(bulk_offset, bulk_offset + 8))
    assert all(
        before == after or index in header_allowed
        for index, (before, after) in enumerate(zip(header, patched_header))
    )


def write_validation_report(output_dir, pak_path, original, header, patched, remap):
    summary = dict(
        status="Offline build validation passed; in-game retest is a separate requirement",
        original_material_sha256=hashlib.sha256(original).hexdigest(),
        original_header_sha256=hashlib.sha256(header).hexdigest(),
        patch_sha256=hashlib.sha256(pak_path.read_bytes()).hexdigest(),
        original_export_bytes=len(original),
        patched_export_bytes=len(patched),
        shader_index_remap=remap,
        original_resource_roundtrip_identical=True,
        patched_resource_parse_valid=True,
        pak_extract_roundtrip_identical=True,
        preserved_material_properties=True,
        preserved_shader_bindings=True,
        preserved_vertex_shader_code=True,
        modified_pixel_shader_count=2,
        caveats=[
            "This build report does not establish in-game or DX12 compatibility.",
            "16 LUT texture reads per pixel replace 2; performance not yet measured.",
            "New shader/map IDs are derived content identities, not original compiler parameter-map hashes.",
        ],
    )
    (output_dir / "validation.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


def build(*, output_dir, package_dir, shader_dir):
    """Build one material overlay using explicit paths instead of mutable globals."""
    output_dir.mkdir(exist_ok=True, parents=True)
    stage = package_dir / "QueensDomain/Content/VFX/Post"
    stage.mkdir(exist_ok=True, parents=True)
    pak_path = output_dir / "QueensDomain_Graphics_P.pak"
    container_report = json.loads((ROOT / "container.json").read_text())
    original = SOURCE.read_bytes()
    header = SOURCE.with_suffix(".uasset").read_bytes()
    assert hashlib.sha256(original).hexdigest() == ORIGINAL_EXPORT_SHA256
    assert len(header) == HEADER_SIZE
    resource_offset = container_report["resource_offset"]
    entries, end = read_resource(original, resource_offset)
    assert end == len(original) - 4
    verify_original_resource(original, resource_offset, end, entries)
    replace_pixel_shaders(entries, shader_dir)

    entries.sort(key=lambda entry: entry["hash"])
    remap = {entry["old_index"]: index for index, entry in enumerate(entries)}
    resource = serialize_resource(entries)
    resource_hash = resource[:20]
    patched = bytearray(original[:resource_offset] + resource + original[end:])
    frozen = update_material_metadata(original, patched, remap, resource_hash, shader_dir)
    patched_header, bulk_offset = update_package_header(header, original, patched)
    verify_patched_material(
        original,
        patched,
        header,
        patched_header,
        resource_offset,
        entries,
        remap,
        frozen,
        bulk_offset,
    )

    (stage / "DitherBase.uasset").write_bytes(patched_header)
    (stage / "DitherBase.uexp").write_bytes(patched)
    subprocess.run(
        [str(REPAK), "pack", "--version", "V8B", str(package_dir), str(pak_path)], check=True
    )
    for name in ("DitherBase.uasset", "DitherBase.uexp"):
        assert (
            read_entry(pak_path, "QueensDomain/Content/VFX/Post/" + name)
            == (stage / name).read_bytes()
        )
    write_validation_report(output_dir, pak_path, original, header, patched, remap)
    return pak_path
