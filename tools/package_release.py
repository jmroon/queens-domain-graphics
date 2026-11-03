"""Create a reproducible, mod-only ZIP. UE4SS and user configuration are excluded."""
import hashlib,json,zipfile
from paths import REPO

def payload():
    files={}
    for p in sorted((REPO/'assets').glob('*.pak')):
        files['QueensDomain/Content/Paks/'+p.name]=p.read_bytes()
    for p in sorted((REPO/'src/QDGraphics/Scripts').glob('*.lua')):
        files['QueensDomain/Binaries/Win64/Mods/QDGraphics/Scripts/'+p.name]=p.read_bytes()
    files['QueensDomain/Binaries/Win64/Mods/QDGraphics/enabled.txt']=b''
    for name in ('INSTALL.txt','LICENSE','THIRD-PARTY.txt'):
        files[name]=(REPO/name).read_bytes()
    return files

def package():
    version=(REPO/'VERSION').read_text().strip()
    files=payload()
    expected=json.loads((REPO/'release-files.json').read_text())
    actual={k:hashlib.sha256(v).hexdigest() for k,v in files.items() if k.startswith('QueensDomain/')}
    if actual!=expected:raise RuntimeError('Runtime payload hashes changed; review and update release-files.json before packaging.')
    out=REPO/'dist';out.mkdir(exist_ok=True)
    target=out/f'QueensDomain-Graphics-{version}.zip'
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in sorted(files.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16
            z.writestr(info,data)
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None and set(z.namelist())==set(files)
        assert all(z.read(n)==d for n,d in files.items())
    checksum=hashlib.sha256(target.read_bytes()).hexdigest()
    (out/'SHA256SUMS.txt').write_text(f'{checksum}  {target.name}\n',encoding='ascii')
    print(target);print(checksum)
    return target
if __name__=='__main__':package()
