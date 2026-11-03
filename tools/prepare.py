"""Extract and compare only the required original game assets; never edit the game."""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
from paths import REPO,BUILD,ASSETS,REPAK,UASSET,ASSEMBLER
from bootstrap import bootstrap
from pak_io import read_entry

def prepare(game,inspect_only=False):
    bootstrap()
    game=Path(game).resolve()
    pak=game/'QueensDomain/Content/Paks/QueensDomain-WindowsNoEditor.pak'
    if not pak.is_file():raise FileNotFoundError('Expected the Steam game root containing QueensDomain.exe: '+str(pak))
    baseline=json.loads((REPO/'supported-inputs.json').read_text())
    ASSETS.mkdir(parents=True,exist_ok=True)
    for rel in baseline['files']:
        dest=ASSETS/rel
        if not dest.resolve().is_relative_to(ASSETS.resolve()):raise ValueError('Invalid asset path')
        data=read_entry(pak,rel)
        dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    actual={rel:hashlib.sha256((ASSETS/rel).read_bytes()).hexdigest() for rel in baseline['files']}
    changed=[rel for rel,digest in actual.items() if digest!=baseline['files'][rel]]
    manifest=game.parents[1]/'appmanifest_1799840.acf'
    match=re.search(r'"buildid"\s+"(\d+)"',manifest.read_text()) if manifest.exists() else None
    build=match[1] if match else None
    report=dict(installed_steam_build=build,tested_steam_build=baseline['steam_build'],changed_files=changed,sha256=actual)
    (BUILD/'input-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if inspect_only:return not changed and build==baseline['steam_build']
    if changed:raise RuntimeError('Original assets changed. Inspect .build/input-report.json; do not bypass the baseline checks.')
    if build!=baseline['steam_build']:
        print('NOTE: Steam build differs or is unavailable. Assets match, but in-game compatibility still needs verification.')
    dest=BUILD/'graphics/json';dest.mkdir(parents=True,exist_ok=True)
    for rel in ('QueensDomain/Content/BaseMaterials/Resources/PixelFilter_MPC.uasset','QueensDomain/Content/UI/Menus/OptionsMenu/OptionLists/Video_OptionsList.uasset'):
        subprocess.run([str(UASSET),'tojson',str(ASSETS/rel),str(dest/(Path(rel).stem+'.json')),'VER_UE4_27'],check=True)
    from inspect_container import extract,ROOT
    extract()
    for index in range(4):
        subprocess.run([str(ASSEMBLER),'-d',str(ROOT/f'extracted/{index}.dxbc')],check=True)
    return True

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-dir',required=True)
    parser.add_argument('--inspect',action='store_true',help='Report input changes without rebuilding.')
    args=parser.parse_args()
    raise SystemExit(0 if prepare(args.game_dir,args.inspect) else 1)
