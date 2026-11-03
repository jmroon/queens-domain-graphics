Adds persistent graphics controls to **Options → Video**, with **Original / Modern / Custom** presets.

- **Modern:** full resolution, TAA, 16× anisotropic filtering, dithering off, Smooth + bias gradients, and the original vignette.
- Individual controls for AA, AF, dithering, colour gradients, and vignette. Changes save immediately; existing settings are preserved until you choose an option.
- Smooth + bias reduces colour steps while keeping more of the original palette. Damage and cutscene code remain intact.
- Early Enhanced preferences and console commands remain compatible with the renamed Modern preset.

**Install:** close the game, install [UE4SS 3.0.1](https://github.com/UE4SS-RE/RE-UE4SS/releases/tag/v3.0.1) beside `QueensDomain-Win64-Shipping.exe`, then extract the mod ZIP into the Steam folder containing `QueensDomain.exe`. Merge folders and choose **Video → Graphics preset → Modern**. UE4SS is not included. See the included `INSTALL.txt` for removal and setting explanations.

Tested baseline: **Steam build 26356968 / UE4.27 / D3D11**. DX12 is unverified. Game updates or other mods replacing the same assets may require a rebuild. Smooth modes add texture samples; the Lua mod uses no polling timer.

Source rebuild, shader/GPU checks, control/menu regression tests, and release hash checks pass. The existing in-game preset behavior was user-verified before the label-only rename; the validation record distinguishes automated checks from manual coverage.

[Settings and compatibility](https://github.com/jmroon/queens-domain-graphics#settings) · [Retest guide](https://github.com/jmroon/queens-domain-graphics/blob/main/docs/MAINTENANCE.md)
