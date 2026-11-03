Makes the mod source easier to read and maintain. Preferences, rendering, and menu coordination have clearer responsibilities; build and GPU tools use named steps and explicit inputs. Adds a source guide and automatic Python/Lua style checks.

No new graphics settings or intended visual changes. The shader/menu PAKs are unchanged from 1.0.1; existing preferences, including the old Enhanced alias, remain compatible.

**Install or update:** close the game and extract **QueensDomain-Graphics-1.0.2.zip** into the Steam game folder containing `QueensDomain.exe`, merging folders and replacing the mod files. Existing UE4SS users should use this mod-only download. For a game without UE4SS, use **QueensDomain-Graphics-Standalone-1.0.2.zip**, which includes the pinned UE4SS 3.0.1 loader. Open Options > Video for Original / Modern / Custom and individual controls. Settings and removal instructions are in `INSTALL.txt`.

Validation: 51 reference behavior transitions, Lua regressions, package checks, source rebuild comparison, and hardware/WARP shader checks pass. The user confirmed saved settings and Video controls work after updating and launching the game. Broader gameplay and fresh standalone-install retesting remain outside this smoke test. Tested asset baseline: Steam build 26356968 / UE4.27 / D3D11; DX12 is unverified.

[Settings](https://github.com/jmroon/queens-domain-graphics#settings) | [Source guide](https://github.com/jmroon/queens-domain-graphics/blob/main/docs/SOURCE_GUIDE.md)
