# Build and retest

The source reconstructs the two override PAKs from a local, legitimate game installation. It does not modify the game, saves, or installed mod. Only the small modified PAKs are committed; extracted originals and build tools are ignored.

See [SOURCE_GUIDE.md](SOURCE_GUIDE.md) for the module map and formatting commands.

## Setup and build

Use Windows x64 with Python 3.13. From the repository root:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt
.venv/Scripts/python tools/build_all.py --game-dir "D:/SteamLibrary/steamapps/common/QueensDomain"
.venv/Scripts/python tools/check_biased_shader.py
.venv/Scripts/python tools/test.py
```

The builder downloads official repak 0.2.3, UAssetGUI 1.1.0, and cmd_Decompiler 1.3.16 into `.tools`, checking the pinned archive/executable hashes in `tools/toolchain.json`. It extracts 14 required files, validates their SHA-256 hashes, converts the MPC/menu to JSON, disassembles and patches the two pixel shaders, and rebuilds the PAKs under `.build/paks`.

`build_all.py` compares every extracted asset byte with the committed release PAKs. PAK entry ordering may vary; matching asset contents establishes the rebuild result. `tools/test.py` runs Lua mock integration tests, creates both deterministic release ZIPs under `dist`, and tests the real loader/package contents. It checks `release-files.json` for the common mod payload. CI runs these tests and package checks without needing the game. CI does **not** substitute for GPU or in-game tests.

Packaging automatically downloads the pinned official UE4SS 3.0.1 basic archive into `.tools`, verifying its SHA-256 before reading any files. An offline build can use `python tools/package_release.py --ue4ss-archive <archive.zip>`; for `tools/test.py`, place the same archive at `.tools/UE4SS_v3.0.1.zip`. Standalone adds only the two loader DLLs, upstream ConsoleEnablerMod/UEHelpers, license, debug-GUI-disabled settings, and a mod list enabling QDGraphics and ConsoleEnablerMod. Never derive these files from a live user's installation. Do not include saves, caches, logs, personal settings, or unrelated helper mods.

For packaging-only changes with identical Lua/PAK hashes, run the package and Lua tests, compare loader bytes/configuration against the tested setup, and verify the clean-checkout CI ZIP hashes. The existing shader/GPU evidence still applies; a new full game/GPU retest is needed when the runtime, loader version, engine overrides, or affected assets change. State whether a fresh standalone launch was actually exercised. Include both ZIPs and the two-entry `SHA256SUMS.txt` in the release.

`check_biased_shader.py` runs the exact rebuilt lookup blocks on D3D11 hardware and WARP, compares them with an independent CPU reference across all four game LUTs, and asks both drivers to create the complete pixel shaders. It requires a working D3D11 device, and writes reports under `.build/reports/gpu`.

## After a Steam update

1. Record the installed public-branch build from `steamapps/appmanifest_1799840.acf`. Use the local manifest's build, not an assumed latest release.
2. Run the read-only comparison:

   ```powershell
   .venv/Scripts/python tools/prepare.py --game-dir "D:/SteamLibrary/steamapps/common/QueensDomain" --inspect
   ```

   Read `.build/input-report.json`. A nonzero exit means the build differs, an asset changed, or the check failed. If assets changed, inspect fresh originals before changing the baseline or patch offsets. Never replace hashes solely to make a build pass.
3. If inputs changed, rebuild the affected component using the notes below. Review the old/new material, menu, or LUT behavior. Update the appropriate input hashes only after understanding the changes. `build_all.py` deliberately fails when new outputs differ from the released PAKs; inspect those differences, then copy the accepted PAKs from `.build/paks` to `assets` and rerun the comparison.
4. Run the control/menu tests, full build comparison, and GPU tests. Back up the installed two PAKs, Lua module folder, mod `.ini`, and game options save before installing a candidate. Close the game first. Never restore a whole save over newer user progress as routine rollback.
5. Complete the in-game checklist below. Record pass/fail/not-tested, game build, renderer, UE4SS version, and any changed hashes in `docs/VALIDATION.md`.
6. Only after successful retesting, update `steam_build` in `supported-inputs.json`. If code/assets changed, bump `VERSION` and the install/download notes, run `tools/record_payload.py`, review its diff, then run `tools/test.py` to package. Publish the ZIP and `SHA256SUMS.txt` from that tested commit. If no runtime changes were needed, a compatibility documentation update can suffice.
7. Complete the post-test publication checklist below. Closing an issue alone does not acknowledge the tested build.

## Post-test publication checklist

Use the installed build actually tested, test date, mod version, and explicitly
tested renderers consistently. Distinguish automated results from user-reported
gameplay and list checks not repeated. An alert for an older build is not proof
that the intervening build was tested.

| Location | After a successful compatibility retest |
| --- | --- |
| `docs/VALIDATION.md` | Add dated evidence, changed/unchanged inputs, gameplay scope, limitations, and whether a new mod version is needed. Preserve previous entries. |
| `supported-inputs.json` | Advance `steam_build` only after validation. Change asset hashes only for understood, accepted input changes. |
| `README.md` and `site/index.html` | Update current compatibility build/date/renderers and say whether existing users need a new download. Verify the deployed page. |
| Current `docs/RELEASE-<version>.md` and GitHub release body | Add a short dated compatibility note linking the validation record. Read the live body first and preserve author edits; it may differ from the source note. Keep the original release-time evidence. |
| [Nexus description](https://www.nexusmods.com/queensdomain/mods/13) | Update only the full description's Compatibility paragraph, then verify it is saved and visible. Keep the short card description, version, files, artwork, and unrelated prose unchanged for a compatibility-only retest. The current editor is `/games/queensdomain/mods/13/edit/general`; do not use the removed game-suggestion listing. |
| [Private monitor issues](https://github.com/jmroon/queens-domain-graphics-monitor/issues) | After pushing the tested baseline, record the tested build and validation link on the relevant alert and close it. Check the next monitor run or manually run its existing workflow when appropriate. If metadata is stale, report that separately; never regress the tested baseline just to satisfy the monitor. |

For an unchanged working mod, leave `VERSION`, packaged `INSTALL.txt`, existing
release ZIPs, and `SHA256SUMS.txt` unchanged. Their tested-build statements are a
snapshot at packaging time; current online notes carry later compatibility
results. Do not overwrite an existing version's downloads solely to refresh
documentation. If a new package is necessary, follow the release/build process
and update its installation snapshot then.

Within the user's publication authorization, push the documentation, verify CI
and Pages, update the existing GitHub release and Nexus description, and finish
the monitor issue with a link to the committed evidence. Read back each edited
surface. If access or approval blocks one destination, list that destination as
pending rather than calling the post-test work complete. Record completion or
pending destinations in the validation entry without copying private logs or
account details into the public repository.

Suggested short note: "Retested <date>: v<version> works with Steam build <build>
in <tested renderers>. No mod update or reinstall needed. <validation link>"

## In-game checklist

- **Fresh preferences:** temporarily move the mod `.ini` and `.ini.bak` aside. Launch with known native settings; verify the mod adopts them without changing the picture or resolution. Restore the files afterward.
- **Presets:** Original → Modern → Original → Modern. Check the first Video row, native Retro Resolution toggle and resolution scale, AA, AF, dithering, gradients, and vignette. Change an individual option and then each native resolution control; verify Custom detection. Selecting Custom must retain the current values.
- **Persistence:** close/reopen Video, travel to another level, die/reload, and fully restart. Values and fresh menu widgets must agree. Check keyboard/controller navigation as well as arrows.
- **Visuals:** from a stationary view with TAA and dithering off, compare Original, Smooth, and Smooth + bias gradients. Check sky/fog/light shafts, dark surfaces, bright whites, and the palette's warmth. Test the other-world palette when available. Restore TAA and check stability in motion.
- **Effects:** test vignette 0/100, take damage, and observe a cutscene or transition. Verify these effects still work and mod changes do not reset them. Check unrelated brightness, FOV, display, and audio settings.
- **Console/logs:** `qd_status`, `qd_help`, and each switch; invalid values must leave saved settings intact. Inspect the current launch's UE4SS log for hook, callback, or missing-parameter errors. Old `qd_preset enhanced` and saved `preset=enhanced` should map to Modern.
- **Performance:** compare frametimes while stationary, moving, and opening menus. Watch for periodic spikes. No polling timer should be present; measure shader cost separately. Test D3D11; claim DX12 support only after an explicit DX12 test.
- **Removal:** with the game closed, remove only the two PAKs and QDGraphics folder. Check that stock launch/options work, then restore the candidate if needed.

## Fragile implementation details

- `DitherBase`: four embedded SM5 DXBC shaders. Preserve both vertex shaders, binding prefixes, optional metadata, signatures, and non-code DXBC chunks. Pixel shaders are indices 2/3 before hash sorting. The serializer updates explicit UE4.27 size/index/identity fields; its offsets are **specific to the validated original**.
- `PixelFilter_MPC`: preserve `StateId` and the first six scalar entries/indices. `Damage` and `InCutscene` are not ours to control. New smooth/vignette scalars occupy the unused `cb[1].z/w` slots without increasing the two-float4 layout. Smooth defaults to 0 (Original); vignette defaults to 1. A default of 1 for smooth would silently change fresh installs before Lua runs.
- LUT sampling: source registers hold R,B,G. Original rounds red/green and floors blue. Smooth interpolates eight corners per LUT. Biased mode uses `max(0, 15B - 0.5, 30B - 15)` for blue, retaining the floor bias while preserving endpoints. The original branch must remain unchanged. Do not disable the entire material or all postprocessing to remove banding.
- `Video_OptionsList`: start from fresh original JSON; clone native row/control/slot exports. The validated original has 102 exports; we append 18 and change only ScrollBox slots/dependencies. Existing Blueprint bytecode stays intact. Export indices and widget/function names may change in an update.
- Lua: resolve widgets afresh after level changes; do not retain invalid UObject handles. Apply through world/player/options events. The old once-per-second scanning approach caused frametime spikes and must not return. Presets modify only the two native resolution fields through the game's queued save operation.

## Update notifications

The private [queens-domain-graphics-monitor](https://github.com/jmroon/queens-domain-graphics-monitor) checks Steam daily and opens an issue **in that private repository**, assigned to `jmroon`, when the public build differs from this repository's tested baseline. It links this checklist. GitHub's built-in workflow token supplies issue access; no personal-token rotation is required. It never updates the baseline, rebuilds the mod, or publishes releases.

The SteamCMD.net metadata service can cache responses and GitHub can delay scheduled jobs. A build change requests a retest; it does not prove breakage. Unchanged builds produce no issue notification. Lookup failures fail the workflow without inventing an update.
