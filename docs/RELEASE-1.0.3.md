Clarifies installation for both UE4SS folder layouts. **Standalone still bundles stable UE4SS 3.0.1.** Mod-only now contains separate `PAKs` and `QDGraphics` folders so you can keep your existing loader.

I tested the mod with stable **3.0.1** and experimental **3.0.1-1217-g4fb9b615** on Steam build **26496428**, in **DX11 and DX12** (6 November 2026). Graphics, controls, and saved settings are unchanged. Working v1.0.2 installations do not need an update.

- **No UE4SS installed:** extract **QueensDomain-Graphics-Standalone-1.0.3.zip** into the game folder containing `QueensDomain.exe`.
- **UE4SS already installed:** extract **QueensDomain-Graphics-1.0.3.zip** somewhere temporary. Copy the two files inside `PAKs` to `QueensDomain/Content/Paks`, and the whole `QDGraphics` folder to your active UE4SS `Mods` folder: usually `Win64/Mods` for flat installations, or `Win64/ue4ss/Mods` for nested installations. Keep your loader and other mods unchanged.

Open **Options → Video** for Original / Modern / Custom and individual controls. If rows appear but do nothing, check the active Mods folder and `UE4SS.log`. Later experimental builds need their own testing.

[Installation and settings](https://github.com/jmroon/queens-domain-graphics#install) · [Validation](https://github.com/jmroon/queens-domain-graphics/blob/main/docs/VALIDATION.md#release-103-installation-layouts-and-experimental-compatibility-2026-11-06)
