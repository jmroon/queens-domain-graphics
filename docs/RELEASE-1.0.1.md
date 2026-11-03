Adds a **Standalone** download with the tested **UE4SS 3.0.1** loader included and configured. The graphics controls, shaders, and saved-setting behavior are unchanged.

**Choose one ZIP:**

- **QueensDomain-Graphics-Standalone-1.0.1.zip** — for a game without UE4SS. Extract into the Steam game folder containing `QueensDomain.exe`, merge folders, and launch.
- **QueensDomain-Graphics-1.0.1.zip** — mod-only, for existing UE4SS users and upgrades. Preserves your loader configuration and other mods.

Then choose **Options → Video → Graphics preset → Modern**. Standalone also enables the **F10** console. No manual configuration edits are required; debug windows are disabled. Original / Modern / Custom presets and individual AA, AF, dithering, gradient, and vignette controls are explained in the included `INSTALL.txt` and [README](https://github.com/jmroon/queens-domain-graphics#settings).

Tested baseline remains **Steam build 26356968 / UE4.27 / D3D11**. The mod payload is byte-identical to 1.0.0. Loader, extraction, license, checksum, and Lua regression checks pass. The bundled loader matches the tested installation; a separate fresh-install game launch was not performed. DX12 remains unverified.
