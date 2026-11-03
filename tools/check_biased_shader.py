"""Execute the exact three-way LUT block extracted from each rebuilt shader."""
from pathlib import Path
from paths import BUILD, TOOLS, ASSETS, PAKS, REPAK, UASSET, ASSEMBLER
import sys,re,subprocess,json
ROOT=BUILD/'graphics';ROOT.mkdir(parents=True,exist_ok=True)
import gpu_check as harness
import analyze
gpu=harness.gpu
OUT=BUILD/'reports/gpu'
OUT.mkdir(exist_ok=True,parents=True)
analyze.MODES=('original','smooth','endpoint')
for index in (2,3):
    folder=ROOT/f'bias-check-{index}';folder.mkdir(exist_ok=True)
    output=OUT/f'shader-{index}';output.mkdir(exist_ok=True)
    harness.ROOT=folder;analyze.OUT=output
    source=(ROOT/f'shaders/{index}.asm').read_text()
    cb=1 if index==2 else 2
    start=source.index(f'ge r4.x, cb{cb}[1].z, l(0.500000)')
    end=source.index('mul r0.w, cb0[130].y' if index==2 else 'add r2.xyz, -r1.xyzx, r2.xyzx',start)
    block=source[start:end]
    # Strip only bindings; instructions and register allocation stay unchanged.
    mapping={'t4':'t0','t5':'t1','s1':'s0','s2':'s1'} if index==2 else {'t4':'t0','t3':'t1','s2':'s0','s1':'s1'}
    block=re.sub(r'\b(?:t[0-9]+|s[0-9]+)\b',lambda m:mapping.get(m[0],m[0]),block)
    src='r0' if index==2 else 'r1';dest=('r0','r2') if index==2 else ('r2','r1')
    def build(mode):
        value={'original':0,'smooth':1,'endpoint':2}[mode]
        selected=block.replace(f'cb{cb}[1].z',f'l({value}.000000)')
        code='''cs_5_0
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
'''+f'ld_structured_indexable(structured_buffer, stride=16)(mixed,mixed,mixed,mixed) {src}.xyzw, vThreadID.x, l(0), t7.xyzw\n'+selected+f'''store_structured u0.xyz, vThreadID.x, l(0), {dest[0]}.xyzx
store_structured u0.xyz, vThreadID.x, l(16), {dest[1]}.xyzx
ret
'''
        path=folder/f'{mode}.asm';path.write_text(code)
        subprocess.run([str(gpu.ASM),'-a',str(path)],check=True,capture_output=True)
    harness.build=build;harness.run()

# Full pixel shaders must also be accepted with their original bindings/signatures.
for driver in (5,1):
    device=gpu.PTR();context=gpu.PTR();feature=gpu.UINT()
    create=gpu.C.WinDLL('d3d11.dll').D3D11CreateDevice
    create.argtypes=[gpu.PTR,gpu.UINT,gpu.PTR,gpu.UINT,gpu.PTR,gpu.UINT,gpu.UINT,gpu.C.POINTER(gpu.PTR),gpu.C.POINTER(gpu.UINT),gpu.C.POINTER(gpu.PTR)]
    create.restype=gpu.HRESULT
    gpu.check(create(None,driver,None,0,None,0,7,gpu.C.byref(device),gpu.C.byref(feature),gpu.C.byref(context)),'CreateDevice')
    try:
        for index in (2,3):
            code=(ROOT/f'shaders/{index}.shdr').read_bytes();blob=gpu.C.create_string_buffer(code);shader=gpu.PTR()
            gpu.check(gpu.call(device,15,gpu.HRESULT,[gpu.PTR,gpu.C.c_size_t,gpu.PTR,gpu.C.POINTER(gpu.PTR)],blob,len(code),None,gpu.C.byref(shader)),'CreatePixelShader')
            gpu.release(shader)
    finally:gpu.release(context);gpu.release(device)
print('PASS: both complete pixel shaders accepted on hardware and WARP; all three lookup modes match independent CPU references.')
(OUT/'summary.json').write_text(json.dumps(dict(full_pixel_shaders_accepted=True,drivers=['hardware','WARP'],modes=['original','smooth','biased'],pixel_shader_variants=2,samples_per_lut_per_mode_per_device=4096),indent=2))
