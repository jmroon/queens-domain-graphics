"""Create reproducible mod-only and standalone ZIPs; never include user settings."""
import argparse,hashlib,json,zipfile
from paths import REPO
from ue4ss import loader_files

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

def write_zip(target,files):
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in sorted(files.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16
            z.writestr(info,data)
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None and set(z.namelist())==set(files)
        assert all(z.read(n)==d for n,d in files.items())
    checksum=hashlib.sha256(target.read_bytes()).hexdigest()
    print(target);print(checksum)
    return f'{checksum}  {target.name}\n'

def package(ue4ss_archive=None):
    version=(REPO/'VERSION').read_text().strip()
    files=payload()
    expected=json.loads((REPO/'release-files.json').read_text())
    actual={k:hashlib.sha256(v).hexdigest() for k,v in files.items() if k.startswith('QueensDomain/')}
    if actual!=expected:raise RuntimeError('Runtime payload hashes changed; review and update release-files.json before packaging.')
    loader=loader_files(ue4ss_archive)
    if files.keys() & loader.keys():raise RuntimeError('Loader would overwrite a mod payload file')
    out=REPO/'dist';out.mkdir(exist_ok=True)
    targets=[out/f'QueensDomain-Graphics-{version}.zip',out/f'QueensDomain-Graphics-Standalone-{version}.zip']
    checksums=write_zip(targets[0],files)+write_zip(targets[1],dict(files,**loader))
    (out/'SHA256SUMS.txt').write_text(checksums,encoding='ascii')
    return targets

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ue4ss-archive',help='Use a local copy of the pinned upstream archive instead of downloading it.')
    package(parser.parse_args().ue4ss_archive)
