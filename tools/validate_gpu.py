"""Exercise the exact replacement assembly in a standalone D3D11 compute harness.
No game injection, installation, window or saved-game interaction.
"""
from pathlib import Path
from paths import BUILD, TOOLS, ASSETS, PAKS, REPAK, UASSET, ASSEMBLER
import ctypes as C
import struct, random, math, json, subprocess
from build_shader import lookup_block, ROOT, ASM

UINT=C.c_uint; PTR=C.c_void_p; HRESULT=C.c_long
class BufferDesc(C.Structure):
    _fields_=[(n,UINT) for n in ('ByteWidth','Usage','BindFlags','CPUAccessFlags','MiscFlags','StructureByteStride')]
class TextureDesc(C.Structure):
    _fields_=[(n,UINT) for n in ('Width','Height','MipLevels','ArraySize','Format','SampleCount','SampleQuality','Usage','BindFlags','CPUAccessFlags','MiscFlags')]
class Subresource(C.Structure):
    _fields_=[('Data',PTR),('Pitch',UINT),('SlicePitch',UINT)]
class SamplerDesc(C.Structure):
    _fields_=[('Filter',UINT),('AddressU',UINT),('AddressV',UINT),('AddressW',UINT),('MipLODBias',C.c_float),('MaxAnisotropy',UINT),('ComparisonFunc',UINT),('BorderColor',C.c_float*4),('MinLOD',C.c_float),('MaxLOD',C.c_float)]
class Mapped(C.Structure):
    _fields_=[('Data',PTR),('RowPitch',UINT),('DepthPitch',UINT)]

def call(obj,idx,restype,args,*values):
    vt=C.cast(obj,C.POINTER(C.POINTER(PTR))).contents
    return C.WINFUNCTYPE(restype,PTR,*args)(vt[idx])(obj,*values)
def check(hr,label):
    if hr<0: raise RuntimeError(f'{label}: HRESULT {hr&0xffffffff:08x}')
def release(obj):
    if obj: call(obj,2,C.c_ulong,[])

def lut(name):
    folder=ASSETS/'QueensDomain/Content/UI/LUTs'
    data=(folder/f'{name}.uexp').read_bytes()
    p=data.index(b'PF_B8G8R8A8\0')+len(b'PF_B8G8R8A8\0')
    mip,count,cooked,flags,num,size,offset=struct.unpack_from('<6Iq',data,p)
    p+=32
    assert (mip,count,cooked,num,size)==(0,1,1,16384,16384)
    assert offset==(folder/f'{name}.uasset').stat().st_size+p
    assert struct.unpack_from('<3I',data,p+size)==(256,16,1)
    return data[p:p+size]

def reference(data,rgb):
    value=[max(0,min(1,x))*15 for x in rgb]
    lo=[math.floor(x) for x in value]; hi=[min(x+1,15) for x in lo]
    frac=[a-b for a,b in zip(value,lo)]
    result=[0.,0.,0.]
    for b in range(2):
        for g in range(2):
            for r in range(2):
                x=(hi if b else lo)[2]*16+(hi if r else lo)[0]
                y=(hi if g else lo)[1]
                p=(y*256+x)*4
                weight=(frac[0] if r else 1-frac[0])*(frac[1] if g else 1-frac[1])*(frac[2] if b else 1-frac[2])
                for c,channel in enumerate((2,1,0)): result[c]+=data[p+channel]/255*weight
    return result

def validate(driver=5, shader_dir=None):
    # WARP is Microsoft's software implementation; hardware is an optional second pass.
    device=PTR(); context=PTR(); feature=UINT()
    create=C.WinDLL('d3d11.dll').D3D11CreateDevice
    create.argtypes=[PTR,UINT,PTR,UINT,PTR,UINT,UINT,C.POINTER(PTR),C.POINTER(UINT),C.POINTER(PTR)]
    create.restype=HRESULT
    check(create(None,driver,None,0,None,0,7,C.byref(device),C.byref(feature),C.byref(context)),'CreateDevice')
    objects=[]
    def keep(p): objects.append(p); return p
    def shader(path,idx):
        code=Path(path).read_bytes(); blob=C.create_string_buffer(code); p=PTR()
        check(call(device,idx,HRESULT,[PTR,C.c_size_t,PTR,C.POINTER(PTR)],blob,len(code),None,C.byref(p)),'CreateShader')
        return keep(p)
    def buffer(data,size,bind,usage=0,cpu=0,stride=0):
        desc=BufferDesc(size,usage,bind,cpu,64 if stride else 0,stride)
        initial=C.create_string_buffer(data) if data is not None else None
        sub=Subresource(C.cast(initial,PTR),0,0) if initial is not None else None
        p=PTR()
        check(call(device,3,HRESULT,[PTR,PTR,C.POINTER(PTR)],C.byref(desc),C.byref(sub) if sub else None,C.byref(p)),'CreateBuffer')
        return keep(p)
    def view(resource,idx):
        p=PTR(); check(call(device,idx,HRESULT,[PTR,PTR,C.POINTER(PTR)],resource,None,C.byref(p)),'CreateView');return keep(p)
    def texture(data):
        desc=TextureDesc(256,16,1,1,87,1,0,1,8,0,0)
        blob=C.create_string_buffer(data);sub=Subresource(C.cast(blob,PTR),1024,16384);p=PTR()
        check(call(device,5,HRESULT,[PTR,PTR,C.POINTER(PTR)],C.byref(desc),C.byref(sub),C.byref(p)),'CreateTexture2D')
        return view(keep(p),7)
    try:
        for index in (2,3):
            shader(ROOT/f'extracted/{index}.dxbc',15)
            shader((Path(shader_dir) if shader_dir else ROOT/'patched')/f'{index}.shdr',15)
        print(f'Driver {driver}: original and patched pixel shaders accepted by Direct3D')
        points=[(r/15,g/15,b/15) for b in range(16) for g in range(16) for r in range(16)]
        rng=random.Random(1703)
        points += [(rng.random(),rng.random(),rng.random()) for _ in range(4096)]
        # Exact boundary values plus closely spaced colours on either side of every blue slice.
        points += [(0.43,0.61,max(0,min(1,b/15+delta))) for b in range(16) for delta in (-1e-6,0,1e-6)]
        points += [(0,0,0)] * ((-len(points))%64)
        count=len(points)
        inbytes=b''.join(struct.pack('<4f',r,b,g,0) for r,g,b in points)
        # The shader receives float32, so reference the same input values.
        points=[(v[0],v[2],v[1]) for v in struct.iter_unpack('<4f',inbytes)]
        inputbuf=buffer(inbytes,len(inbytes),8,stride=16);inputview=view(inputbuf,7)
        outbuf=buffer(None,count*32,128,stride=32);outview=view(outbuf,8)
        staging=buffer(None,count*32,0,usage=3,cpu=0x20000)
        desc=SamplerDesc(0,3,3,3,0,1,1,(C.c_float*4)(0,0,0,0),0,3.402823466e38)
        sampler=PTR();check(call(device,23,HRESULT,[PTR,C.POINTER(PTR)],C.byref(desc),C.byref(sampler)),'CreateSampler');keep(sampler)
        cs=shader(ROOT/'validation.shdr',18)
        call(context,69,None,[PTR,PTR,UINT],cs,None,0)
        call(context,67,None,[UINT,UINT,PTR],7,1,(PTR*1)(inputview.value))
        call(context,68,None,[UINT,UINT,PTR,PTR],0,1,(PTR*1)(outview.value),None)
        call(context,70,None,[UINT,UINT,PTR],0,2,(PTR*2)(sampler.value,sampler.value))
        names=['StandardColor','OtherWorldLUT','Wincolor','StandardColor_OtherWorld']
        results=[]
        for first,second in zip(names[::2],names[1::2]):
            tables=[lut(first),lut(second)]; views=[texture(t) for t in tables]
            call(context,67,None,[UINT,UINT,PTR],0,2,(PTR*2)(*[v.value for v in views]))
            call(context,41,None,[UINT,UINT,UINT],count//64,1,1)
            call(context,47,None,[PTR,PTR],staging,outbuf)
            mapped=Mapped();check(call(context,14,HRESULT,[PTR,UINT,UINT,UINT,PTR],staging,0,1,0,C.byref(mapped)),'Map')
            output=C.string_at(mapped.Data,count*32)
            call(context,15,None,[PTR,UINT],staging,0)
            values=list(struct.iter_unpack('<8f',output))
            for j,name in enumerate((first,second)):
                err=0.;griderr=0.
                for i,p in enumerate(points):
                    expected=reference(tables[j],p)
                    actual=values[i][j*4:j*4+3]
                    assert all(math.isfinite(x) for x in actual)
                    difference=max(abs(a-b) for a,b in zip(actual,expected))
                    err=max(err,difference)
                    if i<4096:griderr=max(griderr,difference)
                assert err < 2e-6,(name,err)
                results.append(dict(lut=name,samples=count,max_absolute_error=err,lattice_max_error=griderr))
        report=dict(driver='WARP' if driver==5 else 'hardware',feature_level=hex(feature.value),pixel_shaders_accepted=True,results=results)
        (ROOT/f'gpu-validation-{driver}.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(report,indent=2))
    finally:
        release(context)
        for obj in reversed(objects):release(obj)
        release(device)

def build_validation():
    text='''cs_5_0
dcl_globalFlags refactoringAllowed
dcl_resource_texture2d (float,float,float,float) t0
dcl_resource_texture2d (float,float,float,float) t1
dcl_resource_structured t7, 16
dcl_sampler s0, mode_default
dcl_sampler s1, mode_default
dcl_uav_structured u0, 32
dcl_input vThreadID.x
dcl_temps 16
dcl_thread_group 64, 1, 1
ld_structured_indexable(structured_buffer, stride=16)(mixed,mixed,mixed,mixed) r0.xyzw, vThreadID.x, l(0), t7.xyzw
'''+lookup_block('r0',[(0,0,'r0'),(1,1,'r2')])+'''
store_structured u0.xyz, vThreadID.x, l(0), r0.xyzx
store_structured u0.xyz, vThreadID.x, l(16), r2.xyzx
ret
'''
    path=ROOT/'validation.asm';path.write_text(text)
    subprocess.run([str(ASM),'-a',str(path)],check=True)

if __name__=='__main__':
    build_validation()
    validate(5)
    validate(1)
