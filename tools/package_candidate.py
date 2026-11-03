"""Build an experimental overlay PAK. NEVER writes to the game installation.

Pinned to the exact inspected DitherBase asset. This is not a general uasset editor.
Source compiler parameter-map hashes are not recoverable from the stripped DXBC.
New runtime shader IDs are SHA1(old ID + patched code + namespace), sorted with
every material resource index remapped. The resource hash uses Unreal's SHA1 of
the concatenated sorted IDs. Original vertex code/IDs and binding data survive.
"""
from pathlib import Path
from paths import BUILD, TOOLS, ASSETS, PAKS, REPAK, UASSET, ASSEMBLER
import struct, hashlib, json, subprocess
from inspect_container import SOURCE, ROOT, decompress_lz4, u32
from inspect_frozen import inspect as inspect_frozen
from build_shader import chunks
from pak_io import read_entry

OUT=PAKS
STAGE=ROOT/'package/QueensDomain/Content/VFX/Post'
PAK=OUT/'QueensDomain_SmoothLUT_P.pak'
SHADER_DIR=ROOT/'patched'
PACKAGE_DIR=ROOT/'package'

def sha(data):return hashlib.sha1(data).digest()
def p32(value):return struct.pack('<I',value)
def read_resource(data,pos):
    start=pos; resource_hash=data[pos:pos+20];pos+=20
    count=u32(data,pos);pos+=4
    hashes=[data[pos+i*20:pos+(i+1)*20] for i in range(count)];pos+=20*count
    assert hashes==sorted(hashes) and sha(b''.join(hashes))==resource_hash
    assert u32(data,pos)==count;pos+=4
    entries=[]
    for i in range(count):
        entry_start=pos;size=u32(data,pos);pos+=4
        code=data[pos:pos+size];pos+=size
        rawsize=u32(data,pos);frequency=data[pos+4];pos+=5
        raw=code if size==rawsize else decompress_lz4(code,rawsize)
        dxbc=raw.index(b'DXBC');bcsize=u32(raw,dxbc+24)
        chunks(raw[dxbc:dxbc+bcsize])
        optional_size=u32(raw,len(raw)-4)
        assert len(raw)-optional_size==dxbc+bcsize
        entries.append(dict(hash=hashes[i],raw=raw,dxbc=dxbc,bcsize=bcsize,
                            frequency=frequency,serialized=data[entry_start:pos]))
    return entries,pos

def build():
    OUT.mkdir(exist_ok=True,parents=True);STAGE.mkdir(exist_ok=True,parents=True)
    report=json.loads((ROOT/'container.json').read_text())
    original=SOURCE.read_bytes();header=SOURCE.with_suffix('.uasset').read_bytes()
    assert hashlib.sha256(original).hexdigest()=='6ca3a04366a43c890378c8049e99f047742b4f1e6c85db61b5bd8de114d67b01'
    assert len(header)==6030
    resource_offset=report['resource_offset']
    entries,end=read_resource(original,resource_offset)
    assert end==len(original)-4
    # Parse/serialize identity check for all original shader resource bytes.
    hashes=b''.join(e['hash'] for e in entries)
    roundtrip=sha(hashes)+p32(4)+hashes+p32(4)+b''.join(e['serialized'] for e in entries)
    assert original[resource_offset:end]==roundtrip
    assert original[:resource_offset]+roundtrip+original[end:]==original
    changes=[]
    for i,e in enumerate(entries):
        e['old_index']=i
        if e['frequency']==3:
            bytecode=(SHADER_DIR/f'{i}.shdr').read_bytes()
            raw=e['raw'][:e['dxbc']]+bytecode+e['raw'][e['dxbc']+e['bcsize']:]
            assert raw[:e['dxbc']]==e['raw'][:e['dxbc']]
            assert raw[-u32(raw,len(raw)-4):]==e['raw'][-u32(e['raw'],len(e['raw'])-4):]
            e['hash']=sha(b'QueensDomain.SmoothLUT.v1\0'+e['hash']+raw)
            e['raw']=raw;e['bcsize']=len(bytecode)
            # Uncompressed entries are explicitly supported when sizes match.
            e['serialized']=p32(len(raw))+raw+p32(len(raw))+bytes([e['frequency']])
            changes.append(i)
    assert changes==[2,3]
    entries.sort(key=lambda e:e['hash'])
    remap={e['old_index']:i for i,e in enumerate(entries)}
    hashes=b''.join(e['hash'] for e in entries)
    resource_hash=sha(hashes)
    resource=resource_hash+p32(4)+hashes+p32(4)+b''.join(e['serialized'] for e in entries)
    patched=bytearray(original[:resource_offset]+resource+original[end:])
    delta=len(patched)-len(original)
    frozen=inspect_frozen(original)
    for s in frozen['shaders']:
        struct.pack_into('<I',patched,s['index_offset'],remap[s['index']])
        if s['frequency']==3:
            lines=(SHADER_DIR/f"{s['index']}.asm").read_text().splitlines()
            instructions=sum(bool(x.strip()) and not x.strip().startswith(('//','dcl_','ps_')) for x in lines)
            struct.pack_into('<I',patched,s['instructions_offset'],instructions)
    # These are identity fields, not material parameters or shader instructions.
    for pos in (7671,7703+488):
        patched[pos:pos+20]=sha(b'QueensDomain.SmoothLUT.v1\0'+original[pos:pos+20]+resource_hash)
    assert u32(original,7651)==len(original)-4-7655
    struct.pack_into('<I',patched,7651,u32(original,7651)+delta)
    newheader=bytearray(header)
    export_offset=5806
    assert struct.unpack_from('<q',header,export_offset+28)[0]==len(original)-4
    assert struct.unpack_from('<q',header,export_offset+36)[0]==len(header)
    struct.pack_into('<q',newheader,export_offset+28,len(patched)-4)
    oldbulk=struct.pack('<q',len(header)+len(original)-4)
    assert header.count(oldbulk)==1
    bulk_offset=header.index(oldbulk)
    assert bulk_offset<193
    struct.pack_into('<q',newheader,bulk_offset,len(header)+len(patched)-4)
    # Round-trip the NEW container and validate every code block and binding prefix.
    parsed,parsed_end=read_resource(patched,resource_offset)
    assert parsed_end==len(patched)-4
    for i,e in enumerate(entries):assert parsed[i]['raw']==e['raw'] and parsed[i]['hash']==e['hash']
    newfrozen=inspect_frozen(patched)
    for old,new in zip(frozen['shaders'],newfrozen['shaders']):
        assert new['index']==remap[old['index']]
        assert parsed[new['index']]['frequency']==old['frequency']
    # Ensure every change before the shader resource table is an explicit metadata field.
    allowed=set(range(7651,7655))|set(range(7671,7691))|set(range(8191,8211))
    for s in frozen['shaders']:allowed.update(range(s['index_offset'],s['instructions_offset']+4))
    assert all(a==b or i in allowed for i,(a,b) in enumerate(zip(original[:resource_offset],patched[:resource_offset])))
    header_allowed=set(range(export_offset+28,export_offset+36))|set(range(bulk_offset,bulk_offset+8))
    assert all(a==b or i in header_allowed for i,(a,b) in enumerate(zip(header,newheader)))
    (STAGE/'DitherBase.uasset').write_bytes(newheader)
    (STAGE/'DitherBase.uexp').write_bytes(patched)
    repak=REPAK
    subprocess.run([str(repak),'pack','--version','V8B',str(PACKAGE_DIR),str(PAK)],check=True)
    for name in ('DitherBase.uasset','DitherBase.uexp'):
        assert read_entry(PAK,'QueensDomain/Content/VFX/Post/'+name)==(STAGE/name).read_bytes()
    summary=dict(status='Offline build validation passed; in-game retest is a separate requirement',
        original_material_sha256=hashlib.sha256(original).hexdigest(),
        original_header_sha256=hashlib.sha256(header).hexdigest(),
        patch_sha256=hashlib.sha256(PAK.read_bytes()).hexdigest(),
        original_export_bytes=len(original),patched_export_bytes=len(patched),
        shader_index_remap=remap,original_resource_roundtrip_identical=True,
        patched_resource_parse_valid=True,pak_extract_roundtrip_identical=True,
        preserved_material_properties=True,preserved_shader_bindings=True,
        preserved_vertex_shader_code=True,modified_pixel_shader_count=2,
        caveats=['This build report does not establish in-game or DX12 compatibility.',
                 '16 LUT texture reads per pixel replace 2; performance not yet measured.',
                 'New shader/map IDs are derived content identities, not original compiler parameter-map hashes.'])
    (OUT/'validation.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))

if __name__=='__main__':build()
