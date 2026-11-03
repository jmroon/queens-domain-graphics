from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
BUILD = REPO / '.build'
TOOLS = REPO / '.tools'
ASSETS = BUILD / 'assets'
PAKS = BUILD / 'paks'
REPAK = TOOLS / 'repak/repak.exe'
UASSET = TOOLS / 'uasset/UAssetGUI.exe'
ASSEMBLER = TOOLS / 'assembler/cmd_Decompiler.exe'
