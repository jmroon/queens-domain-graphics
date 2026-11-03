"""Append native option rows, preserving original exports and Blueprint bytecode."""
from pathlib import Path
from paths import BUILD, TOOLS, ASSETS, PAKS, REPAK, UASSET, ASSEMBLER
import copy,json,subprocess,hashlib
from build import ROOT,OUT,TOOL,asset_write

STAGE=ROOT/'menu-package'
REL=Path('QueensDomain/Content/UI/Menus/OptionsMenu/OptionLists/Video_OptionsList.uasset')
SPECS=[
    ('preset','Graphics preset',['Original','Modern','Custom']),
    ('aa','Anti-aliasing',['Off','FXAA','TAA']),
    ('af','Anisotropic filtering',['Game default','1x','2x','4x','8x','16x']),
    ('dither','Dithering',['Off','On']),
    ('gradients','Colour gradients',['Original','Smooth','Smooth + bias']),
    ('vignette','Vignette',['Off','25%','50%','75%','100% (Original)']),
]
def prop(e,name):return next(p for p in e['Data'] if p['Name']==name)
def main():
    original=json.loads((ROOT/'json/Video_OptionsList.json').read_text())
    check=ROOT/'roundtrip/Video_OptionsList.uasset'
    asset_write(original,check)
    for ext in ('.uasset','.uexp'):
        assert check.with_suffix(ext).read_bytes()==(ASSETS/REL).with_suffix(ext).read_bytes(),f'Menu roundtrip {ext}'
    data=copy.deepcopy(original);exports=data['Exports']
    text_template=prop(exports[62],'Options')['Value'][0]
    bool_template=prop(exports[80],'bIsVariable')
    def text(name,value):
        t=copy.deepcopy(text_template);t.update(Name=name,CultureInvariantString=value);return t
    def flag(name):
        t=copy.deepcopy(bool_template);t.update(Name=name,Value=True);return t
    def remap(node,refs):
        if isinstance(node,list):
            for x in node:remap(x,refs)
        elif isinstance(node,dict):
            if 'ObjectPropertyData' in node.get('$type','') and node.get('Value') in refs:node['Value']=refs[node['Value']]
            for k,v in node.items():
                if k.endswith('Dependencies') and isinstance(v,list):node[k]=[refs.get(x,x) for x in v]
                else:remap(v,refs)
    newslots=[]
    for key,label,options in SPECS:
        first=len(exports)+1;refs={49:first,63:first+1,85:first+2}
        row,control,slot=[copy.deepcopy(original['Exports'][i-1]) for i in (49,63,85)]
        for e in (row,control,slot):remap(e,refs)
        row['ObjectName']='QDGraphicsRow_'+key
        control['ObjectName']='QDGraphicsControl_'+key
        slot['ObjectName']='QDGraphicsSlot_'+key
        row['Data'][0]=text('Name',label)
        prop(row,'Property')['Value']='QDGraphics_'+key
        row['Data'].append(flag('DisableRevert'))
        prop(control,'Options')['Value']=[text(str(i),s) for i,s in enumerate(options)]
        control['Data'].append(flag('SkipSavingOption'))
        control['Data'].append(copy.deepcopy(prop(row,'Property')))
        exports.extend([row,control,slot]);data['DependsMap'].extend([[],[],[]])
        newslots.append(first+2)
    scroll=exports[80];slots=prop(scroll,'Slots')['Value']
    # Keep all original rows and their ordering; insert immediately before Reset.
    assert slots[-1]['Value']==96
    added=[]
    for index in newslots:
        s=copy.deepcopy(slots[0]);s['Value']=index;added.append(s)
    slots.insert(0,added[0])
    slots[-1:-1]=added[1:]
    for i,s in enumerate(slots):s['Name']=str(i)
    scroll['CreateBeforeSerializationDependencies'].extend(newslots)
    def names(node):
        if isinstance(node,list):
            for x in node:names(x)
        elif isinstance(node,dict):
            for k,v in node.items():
                if k in ('Name','ObjectName') and isinstance(v,str) and v not in data['NameMap']:data['NameMap'].append(v)
                elif k=='Value' and 'NamePropertyData' in node.get('$type','') and v not in data['NameMap']:data['NameMap'].append(v)
                else:names(v)
    names(exports[102:]);names(slots)
    data['Generations'][-1].update(ExportCount=len(exports),NameCount=len(data['NameMap']))
    for i in range(102):
        if i!=80:assert exports[i]==original['Exports'][i],f'Original export changed: {i+1}'
    asset_write(data,STAGE/REL)
    parsed=ROOT/'roundtrip/Menu-patched.json'
    subprocess.run([str(TOOL),'tojson',str(STAGE/REL),str(parsed),'VER_UE4_27'],check=True)
    rebuilt=json.loads(parsed.read_text())
    assert len(rebuilt['Exports'])==102+3*len(SPECS)
    for i,e in enumerate(original['Exports']):
        if 'ScriptBytecode' in e:assert e['ScriptBytecode']==rebuilt['Exports'][i]['ScriptBytecode']
    for i in range(102,len(exports)):
        assert exports[i]['Data']==rebuilt['Exports'][i]['Data'],f'Roundtrip new row {i+1}'
    assert prop(rebuilt['Exports'][80],'Slots')==prop(scroll,'Slots')
    pak=OUT/'QueensDomain_GraphicsMenu_P.pak'
    subprocess.run([str(REPAK),'pack','--version','V8B',str(STAGE),str(pak)],check=True)
    report=dict(original_roundtrip_identical=True,original_blueprint_bytecode_preserved=True,
                original_exports_preserved_except_scrollbox=True,added_native_rows=len(SPECS),
                added_exports=3*len(SPECS),modified_assets=[str(REL)],sha256=hashlib.sha256(pak.read_bytes()).hexdigest())
    (OUT/'menu-validation.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
