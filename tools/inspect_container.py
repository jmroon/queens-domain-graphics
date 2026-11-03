from pathlib import Path
from paths import BUILD, TOOLS, ASSETS, PAKS, REPAK, UASSET, ASSEMBLER
import struct, json, hashlib

ROOT = BUILD/'shader';ROOT.mkdir(parents=True,exist_ok=True)
SOURCE = ASSETS / 'QueensDomain/Content/VFX/Post/DitherBase.uexp'

def u32(data, offset):
    return struct.unpack_from('<I', data, offset)[0]

def decompress_lz4(data, expected):
    out = bytearray()
    pos = 0
    while pos < len(data):
        token = data[pos]; pos += 1
        literal = token >> 4
        if literal == 15:
            while True:
                extra = data[pos]; pos += 1; literal += extra
                if extra != 255: break
        assert pos + literal <= len(data)
        out.extend(data[pos:pos+literal]); pos += literal
        if pos == len(data): break
        offset = data[pos] | data[pos+1] << 8; pos += 2
        assert 0 < offset <= len(out)
        match = (token & 15) + 4
        if (token & 15) == 15:
            while True:
                extra = data[pos]; pos += 1; match += extra
                if extra != 255: break
        assert len(out) + match <= expected
        for _ in range(match): out.append(out[-offset])
    assert len(out) == expected
    return bytes(out)

def extract():
    data = SOURCE.read_bytes()
    entries = []
    outdir = ROOT / 'extracted'; outdir.mkdir(exist_ok=True)
    for offset in range(len(data)-9):
        length = u32(data, offset)
        end = offset + 4 + length
        if not (32 < length < len(data) and end + 5 <= len(data)): continue
        rawsize = u32(data, end)
        frequency = data[end+4]
        if not (length < rawsize < 100000 and frequency in (0, 3)): continue
        try:
            raw = decompress_lz4(data[offset+4:end], rawsize)
        except (AssertionError, IndexError): continue
        dxbc = raw.find(b'DXBC')
        if dxbc < 0: continue
        size = u32(raw, dxbc+24)
        if size < 32 or dxbc + size > len(raw): continue
        code = raw[dxbc:dxbc+size]
        index = len(entries)
        (outdir/f'{index}.raw').write_bytes(raw)
        (outdir/f'{index}.dxbc').write_bytes(code)
        entries.append(dict(index=index, entry_offset=offset, compressed_size=length,
            raw_size=rawsize, frequency=frequency, entry_end=end+5,
            dxbc_offset=dxbc, dxbc_size=size, sha1_raw=hashlib.sha1(raw).hexdigest(),
            sha1_dxbc=hashlib.sha1(code).hexdigest(), prefix=raw[:dxbc].hex(),
            suffix=raw[dxbc+size:].hex()))
    assert len(entries) == 4, entries
    for a,b in zip(entries, entries[1:]): assert a['entry_end'] == b['entry_offset']
    start = entries[0]['entry_offset']
    assert u32(data,start-4) == 4
    assert u32(data,start-88) == 4
    resource = start-108
    hashes = [data[start-84+i*20:start-64+i*20].hex() for i in range(4)]
    report = dict(source_sha256=hashlib.sha256(data).hexdigest(), resource_offset=resource,
        resource_hash=data[resource:resource+20].hex(), shader_hashes=hashes, entries=entries)
    (ROOT/'container.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    return report

if __name__ == '__main__': extract()
