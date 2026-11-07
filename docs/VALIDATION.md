# Validation record

## Release 1.0.3: installation layouts and experimental compatibility, 2026-11-06

Standalone retains the previously tested stable UE4SS **3.0.1**, with the same
loader/helper bytes and configuration as v1.0.2. All 15 runtime files were
compared against the checksum-verified, published v1.0.2 standalone ZIP and
match byte-for-byte. Mod-only now contains `PAKs`
and `QDGraphics` folders; users copy them to the game's Paks and their active
UE4SS Mods folder, respectively. Lua and PAK bytes are unchanged from v1.0.2.
The canonical runtime manifest keeps the standalone's flat installation paths.

Experimental compatibility was also tested on 2026-11-06 against Steam build
26496428, using official UE4SS `3.0.1-1217-g4fb9b615` from `experimental2`.
Its ZIP SHA-256 is
`fbdacd0fae434e23d53b1181f6b085219d7cbf7e2cc8a13a00303f842c38194f`.
That experimental archive is **not** bundled in either released download.

The game was closed before the loader swap. The previous root loader files,
mod payload, and affected preferences were backed up. The old root Mods folder
was retained, and rollback restores the old loader without restoring saves.
All backup hashes and unchanged preferences were verified. All 15 installed
runtime files matched the temporary experimental candidate package exactly;
the final release intentionally retains the stable loader instead. The rollback script
passed a dry run; an actual rollback has not been exercised.

All 14 original inputs match the baseline. A full rebuild matches the released
PAK contents; D3D11 hardware/WARP shader checks, Lua regressions, 51 behavior
transitions, seven package checks, and formatting/lint pass. Package checks cover
the stable standalone layout, identical mod bytes across the different package
paths, and the documented manual install into both flat and nested layouts,
preserving an existing loader, configuration, mod lists, and other mods.

The user reported that both DX11 and DX12 work after being asked to test presets,
gradients, vignette, console status, level/restart persistence, and new stutters.
This is user-reported gameplay validation, not measured performance data or an
itemized result for every checklist entry. The final launch log identifies Git
SHA `4fb9b615`, the nested Mods/configuration paths, successful QDGraphics/menu
hook registration, player-ready application, Original/Modern changes, and F10
console setup. There are no QDGraphics callback errors in that log. UE4SS reports
an unavailable `FObjectPtrProperty` size during startup; the mod does not use it.

Fresh-preference adoption, removal, controller navigation, damage/cutscenes,
exhaustive palette coverage, and combinations with other mods were not separately
retested. The clean minimal experimental loader contents were installed and launched, but not
on a second machine or a fresh save. Later experimental builds are not covered.

GitHub v1.0.3 and both Nexus files were published on 2026-11-06. GitHub CI
passed and reproduced both ZIP hashes; GitHub asset digests and Nexus's scan
links match those hashes. Both Nexus downloads are available after scanning.
The full description, file descriptions, and version were read back publicly.
Older Nexus files are retained in the archive; all GitHub v1.0.2 asset digests
remain unchanged. The website deployment passed; its live v1.0.3 download
links, stable-loader wording, and both mod-only destinations were verified.
The rendered installation section was checked and no browser console errors
were reported. Local browser preview was unavailable, so visual verification
used the deployed page.

Release SHA-256:
- Mod-only: `b570535d4065d3538a2a793602ed88d940d2902169fed875818b4242fd5e1864`
- Standalone: `b2cf8da1ab88abc229f8d9e7947f2be02f33c7e861d6f0b0be80319c21e74212`

## Steam update 26496428: compatibility confirmed, 2026-11-06

The monitor reported build 26477048; Steam subsequently finished installing
26496428 locally. The checks below apply to installed build **26496428**, not a
separate test of 26477048. The tested baseline is now 26496428.

- All 14 original input files match the supported hashes exactly, including the
  material, parameter collection, Video menu, and four colour LUTs.
- A full source rebuild produces asset contents identical to both released PAKs.
- D3D11 hardware and WARP accept both complete pixel shaders; all three lookup
  modes match the independent CPU references.
- Lua preset/menu tests, all 51 behavior-parity transitions, and six package tests
  pass. All eight installed mod payload files match the release manifest.
- The latest launch log shows native menu hooks registering and player-ready
  settings applying. The console's initial invalid-object message is followed
  by successful F10/Subtract key setup.

The maintainer confirmed that the requested gameplay checks pass in both DX11
and DX12: Original/Modern preset cycling, individual gradient and vignette
controls, persistence across a level change and restart, and no new periodic
stutters in motion. This is user-reported in-game validation; the automated GPU
checks above use D3D11 hardware/WARP.

Release 1.0.2 remains compatible; no runtime changes, replacement installation,
or new download package were needed. Fresh-preference adoption, removal,
controller navigation, and exhaustive damage/cutscene/palette coverage were
not separately repeated for this update. Historical release records below
retain their original tested builds.

Post-test publication completed on 2026-11-06: the baseline, README, and website
are current; the [v1.0.2 release](https://github.com/jmroon/queens-domain-graphics/releases/tag/v1.0.2)
has a dated retest note, and the [Nexus description](https://www.nexusmods.com/queensdomain/mods/13)
shows the tested build and renderers. Both were read back after saving. The
private monitor alert is closed with linked validation evidence, and a manual
monitor run passed against the new baseline. Release asset IDs and digests were
verified unchanged. Packaged installation notes remain the release-time snapshot.

## Release 1.0.2: readability refactor

Preferences and rendering are separate Lua modules; menu/native callbacks use
descriptive names and expanded control flow. Build phases are named functions;
GPU validation uses explicit inputs and owned D3D11 resources. Python/Lua style
checks run in CI. Runtime behavior is compared with 51 transitions captured from
release 1.0.1, including exact preference/backup contents and rollback. Rebuilt
PAK asset contents remain byte-identical to 1.0.1.

The local installation was updated from the verified mod-only package with a
backup of affected mod files and settings. Existing preferences and loader files
were preserved. Hardware/WARP GPU checks, source rebuild comparison, Lua
regressions, 51-transition parity, formatting/lint, and package checks passed.
On 2026-11-03, the user confirmed that saved settings and Video controls work
after installing 1.0.2 and launching the game. The current launch log also confirms
mod initialization, menu hook registration, and applying settings when the player
is ready. This covers the initial in-game smoke test; an additional restart after
changing settings, level travel, damage/cutscene behavior, and a fresh standalone
installation were not independently retested for this release. Steam baseline
remains 26356968.

On 2026-11-03, the maintainer additionally reported that the installed 1.0.2 mod
works in DX12 mode. This records a successful in-game DX12 test; the automated
shader checks still use D3D11 hardware/WARP, and this report does not establish
exhaustive DX12 performance or every effect/level combination. Earlier release
entries below describe the evidence available at their original validation dates.

## Release 1.0.1: standalone packaging

Adds an extract-and-play package with UE4SS 3.0.1. The six common mod payload hashes
(two PAKs, three Lua files, enable marker) are unchanged from 1.0.0; the previous
asset and GPU results below still apply. Steam baseline remains 26356968.

Validation covers the pinned upstream archive, unchanged loader/helper bytes,
configuration comparison, enabled mod entrypoints, license inclusion, fresh ZIP
extraction layout, separation from mod-only, rejection of incorrect loader archives,
both download checksums, and the existing Lua regression tests. CI repeats the
checks from a clean checkout. Standalone's loader settings match the already tested
installation; unrelated built-in helper mods are omitted.

A fresh in-game launch from the standalone ZIP has not been performed. The user's
installed game and settings were deliberately left unchanged. DX12 remains unverified.

## Release 1.0.0

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
