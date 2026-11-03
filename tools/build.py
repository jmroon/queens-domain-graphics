from pathlib import Path
from paths import BUILD, TOOLS, ASSETS, PAKS, REPAK, UASSET, ASSEMBLER
import sys,json,copy,subprocess,uuid,difflib,hashlib
ROOT=BUILD/'graphics';ROOT.mkdir(parents=True,exist_ok=True)
import build_shader as shader
import package_candidate as package
OUT=PAKS
STAGE=ROOT/'package'
SHADERS=ROOT/'shaders';SHADERS.mkdir(exist_ok=True,parents=True)
TOOL=UASSET

def asset_write(data,path):
    path.parent.mkdir(parents=True,exist_ok=True)
    j=path.with_suffix('.json');j.write_text(json.dumps(data,indent=2))
    subprocess.run([str(TOOL),'fromjson',str(j),str(path)],check=True)
    assert path.exists() and path.with_suffix('.uexp').exists()
    j.unlink() # only the generated staging JSON, never game data

def build_mpc():
    original=json.loads((ROOT/'json/PixelFilter_MPC.json').read_text())
    check=ROOT/'roundtrip/PixelFilter_MPC.uasset'
    asset_write(original,check)
    source=ASSETS/'QueensDomain/Content/BaseMaterials/Resources/PixelFilter_MPC.uasset'
    for ext in ('.uasset','.uexp'):
        assert check.with_suffix(ext).read_bytes()==source.with_suffix(ext).read_bytes(),f'MPC roundtrip {ext}'
    data=copy.deepcopy(original)
    scalars=next(p['Value'] for p in data['Exports'][0]['Data'] if p['Name']=='ScalarParameters')
    assert len(scalars)==6
    for name in ('QD_SmoothColours','QD_Vignette'):
        entry=copy.deepcopy(scalars[0])
        for prop in entry['Value']:
            if prop['Name']=='ParameterName':prop['Value']=name
            elif prop['Name']=='DefaultValue':prop['Value']=0.0 if name=='QD_SmoothColours' else 1.0
            elif prop['Name']=='Id':prop['Value'][0]['Value']='{'+str(uuid.uuid5(uuid.NAMESPACE_URL,'QueensDomain.Graphics/'+name)).upper()+'}'
        scalars.append(entry)
        data['NameMap'].append(name)
    assert scalars[:6]==next(p['Value'] for p in original['Exports'][0]['Data'] if p['Name']=='ScalarParameters')
    # Six and eight scalars both occupy two float4s. Preserve collection StateId
    # and all existing indices so every unmodified material still binds correctly.
    asset_write(data,STAGE/'QueensDomain/Content/BaseMaterials/Resources/PixelFilter_MPC.uasset')

def build_shaders():
    for index,src,targets,begin,end,cb in [
        (2,'r0',[(4,1,'r0'),(5,2,'r2')],'mul r0.y, r0.y, l(15.000000)',
         'sample_l_indexable(texture2d)(float,float,float,float) r2.xyz, r2.xzxx, t5.xyzw, s2, l(0.000000)',1),
        (3,'r1',[(4,2,'r2'),(3,1,'r1')],'mul r0.x, r1.y, l(15.000000)',
         'sample_l_indexable(texture2d)(float,float,float,float) r1.xyz, r1.xzxx, t3.xyzw, s1, l(0.000000)',2)]:
        original=(shader.ROOT/f'extracted/{index}.asm').read_text()
        start=original.index(begin);stop=original.index(end,start)+len(end)
        old=original[start:stop]
        # 0=original, 1=existing smooth, 2=smooth with the original sampling bias.
        # Keep the tested smooth block identical unless the new mode is selected.
        lookup=shader.lookup_block(src,targets)
        bias=f'''ge r6.x, cb{cb}[1].z, l(1.500000)
if_nz r6.x
mad r6.z, r4.z, l(2.000000), l(-15.000000)
add r4.z, r4.z, l(-0.500000)
max r4.z, r4.z, r6.z
max r4.z, r4.z, l(0.000000)
endif
'''
        lookup=lookup.replace('round_ni r5.xyz, r4.xyzx',bias+'round_ni r5.xyz, r4.xyzx')
        block=f'ge r4.x, cb{cb}[1].z, l(0.500000)\nif_nz r4.x\n'+lookup+'\nelse\n'+old+'\nendif'
        patched=(original[:start]+block+original[stop:]).replace('dcl_temps 4','dcl_temps 16')
        vignette='mul_sat r1.w, r1.w, cb3[11].x'
        if index==3:
            assert patched.count(vignette)==1
            patched=patched.replace(vignette,vignette+'\nmul r1.w, r1.w, cb2[1].w')
        restored=patched.replace(block,old).replace('dcl_temps 16','dcl_temps 4')
        restored=restored.replace(vignette+'\nmul r1.w, r1.w, cb2[1].w',vignette)
        assert restored==original
        path=SHADERS/f'{index}.asm';path.write_text(patched)
        (SHADERS/f'{index}.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),patched.splitlines(True))))
        subprocess.run([str(shader.ASM),'-a','--copy-reflection',str(shader.ROOT/f'extracted/{index}.dxbc'),str(path)],check=True)
        subprocess.run([str(shader.ASM),'-d','-V',str(path.with_suffix('.shdr'))],check=True)
        a=shader.chunks((shader.ROOT/f'extracted/{index}.dxbc').read_bytes());b=shader.chunks(path.with_suffix('.shdr').read_bytes())
        assert a.keys()==b.keys() and all(a[k]==b[k] for k in a if k not in ('SHEX','SHDR'))

def main():
    build_mpc();build_shaders()
    package.OUT=OUT;package.STAGE=STAGE/'QueensDomain/Content/VFX/Post'
    package.PAK=OUT/'QueensDomain_Graphics_P.pak';package.SHADER_DIR=SHADERS
    package.PACKAGE_DIR=STAGE
    # package builder verifies material serialization; repack below includes MPC.
    package.build()
    subprocess.run([str(REPAK),'pack','--version','V8B',str(STAGE),str(package.PAK)],check=True)
    report=json.loads((OUT/'validation.json').read_text())
    report.update(patch_sha256=hashlib.sha256(package.PAK.read_bytes()).hexdigest(),
                  configurable_smooth_colours=True,configurable_vignette=True,
                  gradient_modes={'original':0,'smooth':1,'biased':2},
                  original_mpc_roundtrip_identical=True,original_mpc_scalars_preserved=True)
    (OUT/'validation.json').write_text(json.dumps(report,indent=2))

if __name__=='__main__':main()
