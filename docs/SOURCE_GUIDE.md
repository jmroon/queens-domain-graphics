# Reading the source

Start with `src/QDGraphics/Scripts/main.lua`. It wires together small modules;
there is no polling loop. Unreal's player/world/options events trigger updates.

## Runtime modules

| File | Responsibility |
| --- | --- |
| `main.lua` | Coordinates initialization, preset/individual changes, rollback, console commands, and lifecycle hooks. |
| `preferences.lua` | Validates values, migrates older preferences, snapshots state, and atomically saves the INI with a backup. No Unreal calls. |
| `renderer.lua` | Resolves current Unreal objects, reads existing rendering settings, applies the owned controls, and reports runtime values. No file I/O. |
| `native.lua` | Reads/writes the game's two native resolution settings and queues its normal options save. |
| `menu.lua` | Connects the added native widgets to the controller API. Tracks widget identities, resolves objects afresh, and guards callbacks. |

The controller owns a `state` table: `values` holds the five individual controls;
`managed` distinguishes observation from user-selected overrides; `preset` is
Original/Modern/Custom; AA quality/algorithm preserve adopted engine settings.
`initialized` is session state and is deliberately not persisted.

On first launch, `apply` adopts the existing picture without writing overrides.
Once a user chooses a setting, `change` snapshots state, validates the request,
saves preferences, updates native resolution if needed, and applies rendering.
If an operation fails, recovery restores the previous state and attempts to
restore the previous native/rendering values. Choosing Custom changes the label
without applying a new picture.

The menu depends on a small callback API (`get`, `change`, `log`, `native`) rather
than reading files or issuing console commands itself. Unreal UObject references
must never be held across garbage collection or level changes. Method/property
names such as `Refreshtext`, `Slider_99`, and `UpdateScreen%` are game-defined;
their unusual spelling is intentional.

## Build and validation tools

| Entry point/module | Responsibility |
| --- | --- |
| `build_all.py` / `prepare.py` | Verify original inputs, orchestrate both builders, compare every rebuilt asset byte with the release. |
| `asset_io.py` | Serialize cooked assets through UAssetGUI and check original roundtrips. |
| `build.py` / `build_shader.py` | Add MPC parameters and replace only the LUT lookup instructions. `ShaderPatchSpec` names each variant's registers and boundaries. |
| `build_menu.py` | Clone row/control/slot exports, remap references, insert slots, and verify untouched exports/bytecode. Constants are one-based Unreal export indices. |
| `package_candidate.py` | Replace pixel shader resources, sort/remap their identities, update explicit material/header metadata, and verify byte preservation. Offsets are pinned to the validated game asset. |
| `inspect_container.py` / `inspect_frozen.py` | Decode the original compressed shader resources and UE4.27 frozen metadata. |
| `check_biased_shader.py` | Extract the exact built lookup blocks and validate complete pixel shaders. |
| `gpu_check.py` / `validate_gpu.py` | Supply samples and independent CPU references explicitly, dispatch the compute fixtures, and compare results. No source-text rewriting or monkeypatching. |
| `d3d11.py` | Own D3D11 COM resources with a context manager. The low-level vtable signatures retain the tested ABI. |
| `package_release.py` / `ue4ss.py` | Package the mod and pinned loader separately; verify hashes and preserve licenses. |

Shader assembly strings intentionally retain exact register names and numeric
instructions. Editing prose, helper functions, or whitespace must still produce
the same cooked assets; the full build comparison verifies that boundary.

## Style and regression checks

```powershell
.venv/Scripts/python tools/format_source.py          # Check Python/Lua style and lint
.venv/Scripts/python tools/format_source.py --write  # Apply formatter fixes
.venv/Scripts/python tools/test.py                   # Runtime and release package checks
```

Ruff 0.17.3 and StyLua 2.6.0 are pinned. Lua uses four-space indentation and never
collapses simple statements onto one line. Prefer descriptive functions and
explicit inputs to global mutation. Add a class only when it owns a resource or
represents a useful data structure; avoid inheritance for ordinary workflows.

`tests/fixtures/unreal.lua` is the readable engine/menu mock. The behavior trace
in `behavior-v1.0.1.json` was captured from commit
`046f81c93a6f0a91be393fb27743b9525f61af03` before the refactor. The parity test
compares material values, CVars, native settings, widget selection, write counts,
and exact INI/backup contents across 51 transitions, including restart and failed
resolution changes. Do not regenerate that baseline from the refactored code to
make a failing test pass. Existing tests separately cover fresh preferences,
legacy migration, widget lifecycle, and invalid inputs.

See [MAINTENANCE.md](MAINTENANCE.md) for the full game-update and GPU workflow.
