import hashlib
import json
import struct

from paths import ASSETS, BUILD

ROOT = BUILD / "shader"
ROOT.mkdir(parents=True, exist_ok=True)
SOURCE = ASSETS / "QueensDomain/Content/VFX/Post/DitherBase.uexp"


def u32(data, offset):
    return struct.unpack_from("<I", data, offset)[0]


def decompress_lz4(data, expected_size):
    output = bytearray()
    position = 0
    while position < len(data):
        token = data[position]
        position += 1
        literal_length = token >> 4
        if literal_length == 15:
            while True:
                extra = data[position]
                position += 1
                literal_length += extra
                if extra != 255:
                    break
        assert position + literal_length <= len(data)
        output.extend(data[position : position + literal_length])
        position += literal_length
        if position == len(data):
            break
        offset = data[position] | data[position + 1] << 8
        position += 2
        assert 0 < offset <= len(output)
        match_length = (token & 15) + 4
        if (token & 15) == 15:
            while True:
                extra = data[position]
                position += 1
                match_length += extra
                if extra != 255:
                    break
        assert len(output) + match_length <= expected_size
        for _ in range(match_length):
            output.append(output[-offset])
    assert len(output) == expected_size
    return bytes(output)


def extract():
    data = SOURCE.read_bytes()
    entries = []
    output_directory = ROOT / "extracted"
    output_directory.mkdir(exist_ok=True)
    for offset in range(len(data) - 9):
        length = u32(data, offset)
        end = offset + 4 + length
        if not (32 < length < len(data) and end + 5 <= len(data)):
            continue
        uncompressed_size = u32(data, end)
        frequency = data[end + 4]
        if not (length < uncompressed_size < 100000 and frequency in (0, 3)):
            continue
        try:
            raw = decompress_lz4(data[offset + 4 : end], uncompressed_size)
        except (AssertionError, IndexError):
            continue
        bytecode_offset = raw.find(b"DXBC")
        if bytecode_offset < 0:
            continue
        size = u32(raw, bytecode_offset + 24)
        if size < 32 or bytecode_offset + size > len(raw):
            continue
        code = raw[bytecode_offset : bytecode_offset + size]
        index = len(entries)
        (output_directory / f"{index}.raw").write_bytes(raw)
        (output_directory / f"{index}.dxbc").write_bytes(code)
        entries.append(
            dict(
                index=index,
                entry_offset=offset,
                compressed_size=length,
                raw_size=uncompressed_size,
                frequency=frequency,
                entry_end=end + 5,
                dxbc_offset=bytecode_offset,
                dxbc_size=size,
                sha1_raw=hashlib.sha1(raw).hexdigest(),
                sha1_dxbc=hashlib.sha1(code).hexdigest(),
                prefix=raw[:bytecode_offset].hex(),
                suffix=raw[bytecode_offset + size :].hex(),
            )
        )
    assert len(entries) == 4, entries
    for a, b in zip(entries, entries[1:]):
        assert a["entry_end"] == b["entry_offset"]
    start = entries[0]["entry_offset"]
    assert u32(data, start - 4) == 4
    assert u32(data, start - 88) == 4
    resource = start - 108
    hashes = [data[start - 84 + i * 20 : start - 64 + i * 20].hex() for i in range(4)]
    report = dict(
        source_sha256=hashlib.sha256(data).hexdigest(),
        resource_offset=resource,
        resource_hash=data[resource : resource + 20].hex(),
        shader_hashes=hashes,
        entries=entries,
    )
    (ROOT / "container.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    extract()
