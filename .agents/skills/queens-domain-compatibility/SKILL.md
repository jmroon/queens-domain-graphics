---
name: queens-domain-compatibility
description: Retest and maintain the Queen's Domain graphics mod after Steam updates, shader or menu changes, or before releases. Covers asset/build/GPU/Lua checks, guided gameplay validation, and post-test documentation on GitHub, the website, Nexus, and the private update monitor.
---

# Queens Domain Compatibility

Use the repository's [maintenance guide](../../../docs/MAINTENANCE.md) for commands,
asset invariants, and the in-game checklist. Paths in that guide are relative to
the repository root. Read `supported-inputs.json` and `docs/VALIDATION.md` before
making a compatibility claim.

1. Compare the installed Steam build and original assets using `tools/prepare.py
   --game-dir <Steam game root> --inspect`. Do not overwrite baseline hashes just
   to pass a changed-input assertion. Asset equality alone does not validate
   UE4SS hooks, menu lifecycle, or an updated executable.
2. Rebuild only affected components, retaining the serializer's assertions.
   Run `tools/build_all.py`, `tools/check_biased_shader.py`, and `tools/test.py`
   as documented. Inspect differences before accepting new PAKs. Record skipped
   GPU/game checks explicitly rather than weakening them for CI.
   For a packaging-only release, follow the narrower validation path in the
   maintenance guide. Keep mod-only and standalone payloads identical apart from
   the pinned UE4SS bundle; preserve its license and verify both ZIP checksums.
3. For installation testing, close the game and back up only the affected mod
   files and settings first. Use the maintenance checklist for presets, fresh
   preferences, world changes, persistence, visuals, damage/cutscene behavior,
   and frametimes. If the user is playing, ask them to save/quit; do not take over
   gameplay. Keep a whole-save restore separate from routine mod rollback.
4. Preserve the first six MPC scalars and StateId, the untouched material logic,
   and Original-mode behavior. Revalidate shader register/layout assumptions and
   menu export indices against updated originals. Never reintroduce periodic
   object scanning; it previously caused one-second frametime spikes.
5. After actual retesting, complete the maintenance guide's
   [post-test publication checklist](../../../docs/MAINTENANCE.md#post-test-publication-checklist).
   Update the tested baseline, evidence, README, website, current GitHub release
   note, and Nexus compatibility paragraph; record pending publication explicitly.
   An unchanged working mod needs a dated compatibility note, not replacement
   ZIPs or a version bump. Preserve release-time history and published checksums.
   Close the private monitor issue only after the baseline commit is pushed,
   linking the validation result. Publication follows the user's authorized scope;
   the checklist itself does not grant permission to post or deploy.

The monitor repository is `jmroon/queens-domain-graphics-monitor`. It files one
assigned issue per untested public Steam build, in that private repository, using
the built-in Actions token. It must not automatically advance the tested baseline
or publish a new mod. Treat metadata failures as monitor failures, not updates.
