"""Verify the real loader, release separation, extraction layout, and license."""

import configparser
import hashlib
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from paths import REPO
from ue4ss import BINARIES, ORIGINAL_FILES, archive_path, loader_files


class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        version = (REPO / "VERSION").read_text().strip()
        cls.original = zipfile.ZipFile(archive_path())
        cls.mod = zipfile.ZipFile(REPO / f"dist/QueensDomain-Graphics-{version}.zip")
        cls.standalone = zipfile.ZipFile(
            REPO / f"dist/QueensDomain-Graphics-Standalone-{version}.zip"
        )

    @classmethod
    def tearDownClass(cls):
        for archive in (cls.original, cls.mod, cls.standalone):
            archive.close()

    def test_exact_separation_and_unmodified_mod_payload(self):
        expected_loader = {
            BINARIES + n
            for n in (*ORIGINAL_FILES, "UE4SS-settings.ini", "Mods/mods.txt", "UE4SS-LICENSE.txt")
        }
        mapped = {}
        for name in self.mod.namelist():
            destination = name
            if name.startswith("PAKs/"):
                destination = "QueensDomain/Content/Paks/" + name.removeprefix("PAKs/")
            elif name.startswith("QDGraphics/"):
                destination = BINARIES + "Mods/" + name
            mapped[destination] = self.mod.read(name)
        self.assertEqual(set(self.standalone.namelist()), set(mapped) | expected_loader)
        for name, data in mapped.items():
            self.assertEqual(data, self.standalone.read(name), name)
        self.assertEqual(
            {n.split("/")[0] for n in self.mod.namelist()},
            {"PAKs", "QDGraphics", "INSTALL.txt", "LICENSE", "THIRD-PARTY.txt"},
        )
        self.assertFalse(
            any(n.endswith((".dll", "mods.txt", "UE4SS-settings.ini")) for n in self.mod.namelist())
        )

    def test_manual_install_in_both_loader_layouts_preserves_existing_files(self):
        for layout in ("", "ue4ss/"):
            with self.subTest(layout=layout), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                loader = root / BINARIES / layout
                existing = {
                    root / BINARIES / "dwmapi.dll": b"existing proxy",
                    loader / "UE4SS.dll": b"existing loader",
                    loader / "UE4SS-settings.ini": b"custom configuration",
                    loader / "Mods/mods.txt": b"OtherMod : 1\n",
                    loader / "Mods/mods.json": b'{"OtherMod": {"enabled": true}}',
                    loader / "Mods/OtherMod/Scripts/main.lua": b"other mod",
                }
                for path, data in existing.items():
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
                # Follow INSTALL.txt: copy the PAKs and the whole QDGraphics folder.
                for name in self.mod.namelist():
                    if name.startswith("PAKs/"):
                        target = root / "QueensDomain/Content/Paks" / Path(name).name
                    elif name.startswith("QDGraphics/"):
                        target = loader / "Mods" / name
                    else:
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(self.mod.read(name))
                for path, data in existing.items():
                    self.assertEqual(path.read_bytes(), data)
                self.assertTrue((loader / "Mods/QDGraphics/Scripts/main.lua").is_file())
                self.assertTrue((loader / "Mods/QDGraphics/enabled.txt").is_file())
                self.assertEqual(len(list((root / "QueensDomain/Content/Paks").glob("*.pak"))), 2)

    def test_upstream_binaries_helpers_and_license_preserved(self):
        for name in ORIGINAL_FILES:
            self.assertEqual(self.standalone.read(BINARIES + name), self.original.read(name))
        license = self.standalone.read(BINARIES + "UE4SS-LICENSE.txt")
        self.assertEqual(license, (REPO / "licenses/UE4SS-3.0.1.txt").read_bytes())
        self.assertIn(b"Copyright (c) 2022 Narknon", license)

    def test_only_tested_settings_differ(self):
        original = configparser.ConfigParser()
        original.read_string(self.original.read("UE4SS-settings.ini").decode("utf-8-sig"))
        packaged = configparser.ConfigParser()
        packaged.read_string(self.standalone.read(BINARIES + "UE4SS-settings.ini").decode())
        original["Debug"]["GuiConsoleEnabled"] = "0"
        self.assertEqual(
            {s: dict(original[s]) for s in original}, {s: dict(packaged[s]) for s in packaged}
        )
        for key in ("ConsoleEnabled", "GuiConsoleEnabled", "GuiConsoleVisible"):
            self.assertEqual(packaged.getint("Debug", key), 0)

    def test_fresh_extraction_has_enabled_entrypoints_and_no_user_data(self):
        names = self.standalone.namelist()
        self.assertEqual(len(names), len(set(n.casefold() for n in names)))
        self.assertFalse(any(n.startswith("/") or ".." in Path(n).parts or ":" in n for n in names))
        self.assertFalse(
            any("/Saved/" in n or n.endswith(("QDGraphics.ini", ".log", ".sav")) for n in names)
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            exe = root / "QueensDomain.exe"
            exe.write_bytes(b"game sentinel")
            self.standalone.extractall(root)
            self.assertEqual(exe.read_bytes(), b"game sentinel")
            binary = root / BINARIES
            self.assertTrue((binary / "dwmapi.dll").is_file())
            enabled = (binary / "Mods/mods.txt").read_text().splitlines()
            self.assertEqual(enabled, ["QDGraphics : 1", "ConsoleEnablerMod : 1"])
            for line in enabled:
                name = line.split(":")[0].strip()
                self.assertTrue((binary / "Mods" / name / "Scripts/main.lua").is_file())
            self.assertTrue((binary / "Mods/QDGraphics/enabled.txt").is_file())

    def test_wrong_loader_archive_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "UE4SS.zip"
            bad.write_bytes(b"wrong archive")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                loader_files(bad)

    def test_both_download_checksums_match(self):
        lines = (REPO / "dist/SHA256SUMS.txt").read_text().splitlines()
        self.assertEqual(len(lines), 2)
        for line in lines:
            expected, name = line.split("  ")
            self.assertEqual(
                expected, hashlib.sha256((REPO / "dist" / name).read_bytes()).hexdigest()
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
