"""Bundle the tested official UE4SS archive, with a minimal enabled mod list."""
import configparser,hashlib,re,zipfile
from pathlib import Path
from urllib.request import Request,urlopen
from paths import REPO,TOOLS

VERSION='3.0.1'
URL=f'https://github.com/UE4SS-RE/RE-UE4SS/releases/download/v{VERSION}/UE4SS_v{VERSION}.zip'
SHA256='4b47d4bceddd2f561a4e395bfa00924ccfc945af576a2d0c613e6537846c57ec'
BINARIES='QueensDomain/Binaries/Win64/'
ORIGINAL_FILES=('dwmapi.dll','UE4SS.dll','Mods/ConsoleEnablerMod/Scripts/main.lua',
                'Mods/shared/UEHelpers/UEHelpers.lua')

def archive_path(supplied=None):
    path=Path(supplied) if supplied else TOOLS/f'UE4SS_v{VERSION}.zip'
    if not path.exists() and supplied is None:
        req=Request(URL,headers={'User-Agent':'QueensDomain-Graphics-build'})
        with urlopen(req,timeout=120) as response:data=response.read()
        if hashlib.sha256(data).hexdigest()!=SHA256:raise ValueError('UE4SS archive hash mismatch')
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    if hashlib.sha256(path.read_bytes()).hexdigest()!=SHA256:
        raise ValueError('Use the pinned official UE4SS 3.0.1 basic archive; hash mismatch')
    return path

def loader_files(supplied=None):
    with zipfile.ZipFile(archive_path(supplied)) as archive:
        files={BINARIES+name:archive.read(name) for name in ORIGINAL_FILES}
        settings=archive.read('UE4SS-settings.ini').decode('utf-8-sig').replace('\r','')
    # Match the existing tested installation: no external console/GUI, no engine override.
    for key in ('ConsoleEnabled','GuiConsoleEnabled','GuiConsoleVisible'):
        settings,count=re.subn(rf'(?m)^{key}[ \t]*=[ \t]*[01][ \t]*$',f'{key} = 0',settings)
        if count!=1:raise ValueError('Unexpected UE4SS setting: '+key)
    cfg=configparser.ConfigParser();cfg.read_string(settings)
    assert not cfg['EngineVersionOverride']['MajorVersion'].strip()
    assert not cfg['EngineVersionOverride']['MinorVersion'].strip()
    assert cfg.getboolean('General','bUseUObjectArrayCache')
    files[BINARIES+'UE4SS-settings.ini']=settings.encode('utf-8')
    files[BINARIES+'Mods/mods.txt']=b'QDGraphics : 1\nConsoleEnablerMod : 1\n'
    files[BINARIES+'UE4SS-LICENSE.txt']=(REPO/'licenses/UE4SS-3.0.1.txt').read_bytes()
    return files
