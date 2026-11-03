# Release 1.0.0 validation

Baseline: Steam app 1799840, build **26356968**, Windows x64, Unreal 4.27, UE4SS 3.0.1, D3D11. The first release packages the previously tested local mod with Enhanced renamed to Modern.

| Check | Evidence / result |
| --- | --- |
| Native menu controls and persistence | User confirmed all added controls work and saved choices survive a restart. |
| Presets and resolution controls | User confirmed Original/Enhanced/Custom behavior, native resolution updates, and Custom detection before the label rename. |
| Smooth + bias appearance | User compared against Original/Smooth and reported it looked great. |
| Modern rename | Menu asset rebuilt with preserved Blueprint bytecode; mock tests cover menu selection, saved Enhanced migration, and old console alias. A fresh in-game label check is tracked separately from the prior preset test. |
| Clean source rebuild | All six extracted override asset files match the release PAK contents byte-for-byte. |
| Shader integrity | Assembly/container/PAK roundtrips pass; bindings, vertex shaders, and unrelated DXBC chunks preserved. |
| Lookup math | Exact three-mode blocks from both pixel shaders checked against independent CPU references on hardware D3D11 and WARP, four LUTs and 4096 colours per combination. Full pixel shader creation succeeds. |
| Lua integration | First-run preservation, menu callbacks, stale-widget handling, native preset changes, persistence, invalid values, failure rollback, legacy preferences, and unrelated-setting preservation pass. |
| Package | Runtime hashes checked; reproducible ZIP verified after extraction. |

Limits: DX12 is not independently tested. Exhaustive damage/cutscene coverage, every level/palette, controller navigation, and quantified performance across hardware remain manual retest items. Preserving the relevant code paths is not equivalent to exercising every in-game state. Automated CI covers Lua/package checks, not the game itself.
