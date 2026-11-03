# Queen's Domain Graphics

Adds persistent graphics controls to **Options → Video**, including **Original / Modern / Custom** presets. Smooth colour gradients keep the game's LUT-based grading, damage effects, and vignette available.

**[Download the latest release](https://github.com/jmroon/queens-domain-graphics/releases/latest)** · [Build and retest](docs/MAINTENANCE.md)

## Install

1. Close the game and choose a download from Releases:
   - **Standalone** (`QueensDomain-Graphics-Standalone-1.0.1.zip`): includes the tested UE4SS 3.0.1 loader, configured and ready. Use this if you do **not** already have UE4SS installed.
   - **Mod-only** (`QueensDomain-Graphics-1.0.1.zip`): use this if UE4SS is already installed, preserving its configuration and other mods.
2. Extract the chosen ZIP into the **Steam game folder containing `QueensDomain.exe`**, merging the included `QueensDomain` folder.
3. Launch, load a save, and open **Options → Video → Graphics preset → Modern**. No configuration editing is needed for standalone.

Standalone includes loader configuration and `Mods/mods.txt`; use mod-only for updates to an existing UE4SS installation. If installing UE4SS manually, extract the basic **[UE4SS 3.0.1](https://github.com/UE4SS-RE/RE-UE4SS/releases/tag/v3.0.1)** package into `QueensDomain/Binaries/Win64`, beside `QueensDomain-Win64-Shipping.exe`, before adding mod-only.

The included `QDGraphics/enabled.txt` enables the mod without replacing `mods.txt`. A fresh installation preserves your existing settings until you choose an option. The ZIP uses UE4SS 3.0.1's standard `Win64/Mods` layout; if you deliberately use a different UE4SS working directory, place `QDGraphics` in that directory's `Mods` folder instead.

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

Tested with **Steam build 26356968**, **UE4.27**, **UE4SS 3.0.1**, and **D3D11**. DX12 is not independently verified. Smooth modes increase LUT samples from 2 to 16 per pixel; the performance cost depends on resolution and hardware. The Lua controls use events, with no polling timer or per-frame callback.

Updates can affect the three overridden assets: `DitherBase`, `PixelFilter_MPC`, and `Video_OptionsList`. Other mods replacing them can conflict. This is a PAK **and** Lua mod; putting everything in `~mods` is insufficient. Original game PAKs remain untouched.

To uninstall, close the game and remove `QueensDomain_Graphics_P.pak`, `QueensDomain_GraphicsMenu_P.pak` from `QueensDomain/Content/Paks`, and the `QDGraphics` folder from UE4SS's `Mods`. Keep other mods and saves. Select Original before uninstalling if you want stock resolution behavior restored. You may also delete the mod's `.ini` and `.ini.bak` to clear its preferences.

If you used standalone and **no other mods use UE4SS**, you can also remove its `dwmapi.dll`, `UE4SS.dll`, `UE4SS-settings.ini`, `UE4SS-LICENSE.txt`, and bundled `Mods/ConsoleEnablerMod`, `Mods/shared/UEHelpers`, and `Mods/mods.txt` from `QueensDomain/Binaries/Win64`. Keep the loader and shared files if you have added other UE4SS mods.

Original code and documentation are MIT licensed. Game-derived assets retain their owners' rights; see [THIRD-PARTY.txt](THIRD-PARTY.txt).
