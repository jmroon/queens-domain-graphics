# Queen's Domain Graphics

Adds persistent graphics controls to **Options → Video**, including **Original / Modern / Custom** presets. Smooth colour gradients keep the game's LUT-based grading, damage effects, and vignette available.

**[Comparisons & mod details](https://jmroon.github.io/queens-domain-graphics/)** · [Download the latest release](https://github.com/jmroon/queens-domain-graphics/releases/latest) · [Build and retest](docs/MAINTENANCE.md) · [Source guide](docs/SOURCE_GUIDE.md)

## Install

Close the game and choose **one** download. Existing UE4SS users should use **Mod-only** to keep their loader and other mods intact.

### Standalone — no existing UE4SS

Extract **QueensDomain-Graphics-Standalone-1.0.4.zip** into the game folder containing `QueensDomain.exe`, merging the included `QueensDomain` folder. It includes stable **UE4SS 3.0.1**, configured and ready to use. Do not extract Standalone over an existing UE4SS installation.

### Mod-only — existing UE4SS, either layout

Extract **QueensDomain-Graphics-1.0.4.zip** to a temporary folder, then:

1. Copy the **two files inside `PAKs`** into the game's `QueensDomain/Content/Paks`.
2. Copy the **whole `QDGraphics` folder** into your active UE4SS `Mods` folder:

| Existing loader layout | Usual destination for QDGraphics |
| --- | --- |
| Stable 3.0.1 / flat | `QueensDomain/Binaries/Win64/Mods/QDGraphics` |
| Experimental / nested | `QueensDomain/Binaries/Win64/ue4ss/Mods/QDGraphics` |

Use your existing folder structure as the guide; custom UE4SS setups can use another location. Keep one active copy of QDGraphics. Merge/replace its files when updating, but keep your loader, INI, and other mods. The included `enabled.txt` enables QDGraphics without replacing your mod list; if your list explicitly disables it, enable it there.

Launch, load a save, and open **Options → Video → Graphics preset → Modern**. A fresh installation preserves your settings until you choose an option. Existing installations need no update. Version 1.0.4 provides short, package-specific INSTALL.txt files; graphics, loaders, and saved settings are unchanged.

## Settings

| Setting | What it does |
| --- | --- |
| **Original** | Restores the stock retro resolution behavior, AA off, game-default AF, dithering on, original colour steps, and full vignette. Other settings such as brightness and FOV stay yours. |
| **Modern** | Uses 100% resolution scale with Retro Resolution off, TAA, 16× AF, dithering off, Smooth + bias gradients, and the original vignette. |
| **Custom** | Keeps your individual choices. Changing a mod option, or moving resolution settings away from a preset, selects Custom automatically. |
| **Anti-aliasing** | Off preserves raw pixels; FXAA softens edges; TAA reduces shimmering in motion but can soften detail or leave ghosting. |
| **Anisotropic filtering** | Sharpens textures viewed at an angle. Game default follows texture quality; 1×–16× requests a fixed level. Materials with fixed sampling can ignore it. |
| **Dithering** | Toggles the game's patterned colour noise. |
| **Colour gradients** | Original keeps stepped colours. Smooth blends adjacent palette entries. Smooth + bias also retains more of the original yellow/green character while protecting bright endpoints. |
| **Vignette** | Controls edge darkening: Off through 100%, where 100% is the original strength. |

Changes save immediately and survive restarts. Selecting Custom does not change the picture. **Modern was called Enhanced in early local builds**; saved Enhanced preferences and `qd_preset enhanced` remain compatible.

## Optional console

Standalone includes and enables UE4SS's `ConsoleEnablerMod`: press **F10** for the developer console. With mod-only, enable that helper in your existing UE4SS setup if wanted. The menu works without it. Run `qd_help` for commands:

```text
qd_preset original|modern|custom
qd_aa off|fxaa|taa
qd_af game|1|2|4|8|16
qd_dither 0|1
qd_gradients original|smooth|biased
qd_vignette 0..100
qd_status
qd_apply
qd_defaults
```

`qd_defaults` selects Original. `qd_status` reports saved and runtime values in the console and `UE4SS.log`. Preferences are stored in `%LOCALAPPDATA%\QueensDomain\Saved\QDGraphics.ini`; resolution choices use the game's own settings save.

## Compatibility and removal

I tested the mod with stable **UE4SS 3.0.1** and experimental **3.0.1-1217-g4fb9b615** on Steam build **26496428**, in **DX11 and DX12** (6 November 2026). Standalone continues to bundle stable 3.0.1. Later experimental builds need their own testing.

Smooth gradients add shader work; the performance cost depends on resolution and hardware.

Updates can affect the three overridden assets: `DitherBase`, `PixelFilter_MPC`, and `Video_OptionsList`. Other mods replacing them can conflict. This is a PAK **and** Lua mod; putting everything in `~mods` is insufficient. Original game PAKs remain untouched.

To uninstall, close the game and remove `QueensDomain_Graphics_P.pak`, `QueensDomain_GraphicsMenu_P.pak` from `QueensDomain/Content/Paks`, and the `QDGraphics` folder from UE4SS's `Mods`. Keep other mods and saves. Select Original before uninstalling if you want stock resolution behavior restored. You may also delete the mod's `.ini` and `.ini.bak` to clear its preferences.

If you used standalone and **no other mods use UE4SS**, you can also remove its `dwmapi.dll`, `UE4SS.dll`, `UE4SS-settings.ini`, `UE4SS-LICENSE.txt`, and bundled `Mods/ConsoleEnablerMod`, `Mods/shared/UEHelpers`, and `Mods/mods.txt` from `QueensDomain/Binaries/Win64`. Keep the loader and shared files if other mods use them.

### Menu appears, but controls do nothing?

The PAK adds the menu rows; Lua makes them work. Check that `QDGraphics/Scripts/main.lua` is in the **active** UE4SS `Mods` folder, then inspect that loader's `UE4SS.log` after launching. In the new layout it is `QueensDomain/Binaries/Win64/ue4ss/UE4SS.log`; older flat installs use `Win64/UE4SS.log`. If reporting a problem, include that log, the UE4SS version, and which download you installed. A visible Modern label alone does not prove Lua loaded.

Original code and documentation are MIT licensed. Game-derived assets retain their owners' rights; see [THIRD-PARTY.txt](THIRD-PARTY.txt).
