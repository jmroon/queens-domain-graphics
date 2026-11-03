"""Validate original lookup and three offline variants on D3D11/WARP.
Reuse the earlier standalone resource harness; never attach to the game.
"""
from pathlib import Path
from paths import BUILD, TOOLS, ASSETS, PAKS, REPAK, UASSET, ASSEMBLER
import sys,inspect,subprocess,random,json
import analyze
import validate_gpu as gpu
from build_shader import lookup_block
ROOT=BUILD/'colour';ROOT.mkdir(parents=True,exist_ok=True)

def build(mode):
    if mode=='original':
        block='''mul r4.x, r0.y, l(15.000000)
mad r4.yz, r0.xxzx, l(0.000000, 0.0585937500, 0.937500, 0.000000), l(0.000000, 0.00195312500, 0.031250, 0.000000)
round_ni r4.x, r4.x
mad r4.x, r4.x, l(0.062500), r4.y
sample_l_indexable(texture2d)(float,float,float,float) r0.xyz, r4.xzxx, t0.xyzw, s0, l(0.000000)
sample_l_indexable(texture2d)(float,float,float,float) r2.xyz, r4.xzxx, t1.xyzw, s1, l(0.000000)'''
    else:
        block=lookup_block('r0',[(0,0,'r0'),(1,1,'r2')])
        insert=''
        if mode=='shifted':insert='add r4.z, r4.z, l(-0.500000)\nmax r4.z, r4.z, l(0.000000)\n'
        elif mode=='endpoint':insert='''mad r6.z, r4.z, l(2.000000), l(-15.000000)
add r4.z, r4.z, l(-0.500000)
max r4.z, r4.z, r6.z
max r4.z, r4.z, l(0.000000)
'''
        block=block.replace('round_ni r5.xyz, r4.xyzx',insert+'round_ni r5.xyz, r4.xyzx')
    source='''cs_5_0
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
'''+block+'''
store_structured u0.xyz, vThreadID.x, l(0), r0.xyzx
store_structured u0.xyz, vThreadID.x, l(16), r2.xyzx
ret
'''
    path=ROOT/f'{mode}.asm';path.write_text(source)
    subprocess.run([str(gpu.ASM),'-a',str(path)],check=True,capture_output=True)
    subprocess.run([str(gpu.ASM),'-d','-V',str(path.with_suffix('.shdr'))],check=True,capture_output=True)

def run():
    # Test arbitrary colours away from point-filter tie boundaries, plus exact
    # endpoints and the reported mid-grey example. Tie behavior is device-defined
    # at finite subtexel precision; it must not be confused with a LUT math error.
    rng=random.Random(4112);points=[(0,0,0),(1,1,1),(.5,.5,.5)]
    while len(points)<4096:
        p=tuple(rng.random() for _ in range(3));q=[x*15 for x in p]
        if min(abs(q[i]%1-.5) for i in (0,1))<.01:continue
        if min(q[2]%1,1-q[2]%1)<.001:continue
        points.append(p)
    source=inspect.getsource(gpu.validate)
    start=source.index('        for index in (2,3):');stop=source.index('        inbytes=',start)
    source=source[:start]+'        points=TEST_POINTS\n        count=len(points)\n'+source[stop:]
    source=source.replace("ROOT/'validation.shdr'","ANALYSIS_ROOT/f'{MODE}.shdr'")
    source=source.replace("reference(tables[j],p)","cpu_reference(tables[j],p)")
    source=source.replace("ROOT/f'gpu-validation-{driver}.json'","ANALYSIS_OUT/f'gpu-{MODE}-{driver}.json'")
    source=source.replace('pixel_shaders_accepted=True','mode=MODE,standalone_compute_shader=True')
    source=source.replace('print(json.dumps(report,indent=2))',"print(MODE,driver,'max error',max(x['max_absolute_error'] for x in results))")
    for mode in analyze.MODES:
        build(mode)
        def cpu_reference(data,p):
            t=[tuple(data[i+c]/255 for c in (2,1,0)) for i in range(0,len(data),4)]
            return analyze.evaluate(t,p,mode)
        # Cache decoded bytes, as the old harness passes texture byte buffers.
        from functools import lru_cache
        @lru_cache(maxsize=4)
        def decode(data):return [tuple(data[i+c]/255 for c in (2,1,0)) for i in range(0,len(data),4)]
        ns=dict(vars(gpu),MODE=mode,ANALYSIS_ROOT=ROOT,ANALYSIS_OUT=analyze.OUT,TEST_POINTS=points,
                cpu_reference=lambda d,p:analyze.evaluate(decode(d),p,mode))
        exec(source,ns)
        for driver in (5,1):ns['validate'](driver)
if __name__=='__main__':run()
