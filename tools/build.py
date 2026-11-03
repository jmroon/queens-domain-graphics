"""Build the material parameter collection and patch the two LUT pixel shaders."""

import copy
import difflib
import hashlib
import json
import subprocess
import uuid
from dataclasses import dataclass

import build_shader as shader
import package_candidate as package
from asset_io import asset_write, verify_original_roundtrip
from paths import ASSETS, BUILD, PAKS, UASSET

ROOT = BUILD / "graphics"
ROOT.mkdir(parents=True, exist_ok=True)
OUT = PAKS
STAGE = ROOT / "package"
SHADERS = ROOT / "shaders"
SHADERS.mkdir(exist_ok=True, parents=True)
TOOL = UASSET


def build_mpc():
    original = json.loads((ROOT / "json/PixelFilter_MPC.json").read_text())
    check = ROOT / "roundtrip/PixelFilter_MPC.uasset"
    source = ASSETS / "QueensDomain/Content/BaseMaterials/Resources/PixelFilter_MPC.uasset"
    verify_original_roundtrip(original, source, check)
    data = copy.deepcopy(original)
    scalars = next(
        p["Value"] for p in data["Exports"][0]["Data"] if p["Name"] == "ScalarParameters"
    )
    assert len(scalars) == 6
    for name in ("QD_SmoothColours", "QD_Vignette"):
        entry = copy.deepcopy(scalars[0])
        for prop in entry["Value"]:
            if prop["Name"] == "ParameterName":
                prop["Value"] = name
            elif prop["Name"] == "DefaultValue":
                prop["Value"] = 0.0 if name == "QD_SmoothColours" else 1.0
            elif prop["Name"] == "Id":
                prop["Value"][0]["Value"] = (
                    "{"
                    + str(uuid.uuid5(uuid.NAMESPACE_URL, "QueensDomain.Graphics/" + name)).upper()
                    + "}"
                )
        scalars.append(entry)
        data["NameMap"].append(name)
    assert scalars[:6] == next(
        p["Value"] for p in original["Exports"][0]["Data"] if p["Name"] == "ScalarParameters"
    )
    # Six and eight scalars both occupy two float4s. Preserve collection StateId
    # and all existing indices so every unmodified material still binds correctly.
    asset_write(data, STAGE / "QueensDomain/Content/BaseMaterials/Resources/PixelFilter_MPC.uasset")


@dataclass(frozen=True)
class ShaderPatchSpec:
    """Register bindings and exact lookup boundaries for one original pixel shader."""

    index: int
    source_register: str
    texture_bindings: list[tuple[int, int, str]]
    start_marker: str
    end_marker: str
    collection_buffer: int


SHADER_VARIANTS = [
    ShaderPatchSpec(
        index=2,
        source_register="r0",
        texture_bindings=[(4, 1, "r0"), (5, 2, "r2")],
        start_marker="mul r0.y, r0.y, l(15.000000)",
        end_marker="sample_l_indexable(texture2d)(float,float,float,float) r2.xyz, r2.xzxx, t5.xyzw, s2, l(0.000000)",
        collection_buffer=1,
    ),
    ShaderPatchSpec(
        index=3,
        source_register="r1",
        texture_bindings=[(4, 2, "r2"), (3, 1, "r1")],
        start_marker="mul r0.x, r1.y, l(15.000000)",
        end_marker="sample_l_indexable(texture2d)(float,float,float,float) r1.xyz, r1.xzxx, t3.xyzw, s1, l(0.000000)",
        collection_buffer=2,
    ),
]


def patch_shader(spec: ShaderPatchSpec) -> None:
    index = spec.index
    source_register = spec.source_register
    texture_bindings = spec.texture_bindings
    start_marker = spec.start_marker
    end_marker = spec.end_marker
    collection_buffer = spec.collection_buffer
    original = (shader.ROOT / f"extracted/{index}.asm").read_text()
    start = original.index(start_marker)
    stop = original.index(end_marker, start) + len(end_marker)
    original_lookup = original[start:stop]
    # 0=original, 1=existing smooth, 2=smooth with the original sampling bias.
    # Keep the tested smooth block identical unless the new mode is selected.
    lookup = shader.lookup_block(source_register, texture_bindings)
    bias = f"""ge r6.x, cb{collection_buffer}[1].z, l(1.500000)
if_nz r6.x
mad r6.z, r4.z, l(2.000000), l(-15.000000)
add r4.z, r4.z, l(-0.500000)
max r4.z, r4.z, r6.z
max r4.z, r4.z, l(0.000000)
endif
"""
    lookup = lookup.replace("round_ni r5.xyz, r4.xyzx", bias + "round_ni r5.xyz, r4.xyzx")
    block = (
        f"ge r4.x, cb{collection_buffer}[1].z, l(0.500000)\nif_nz r4.x\n"
        + lookup
        + "\nelse\n"
        + original_lookup
        + "\nendif"
    )
    patched = (original[:start] + block + original[stop:]).replace("dcl_temps 4", "dcl_temps 16")
    vignette = "mul_sat r1.w, r1.w, cb3[11].x"
    if index == 3:
        assert patched.count(vignette) == 1
        patched = patched.replace(vignette, vignette + "\nmul r1.w, r1.w, cb2[1].w")
    restored = patched.replace(block, original_lookup).replace("dcl_temps 16", "dcl_temps 4")
    restored = restored.replace(vignette + "\nmul r1.w, r1.w, cb2[1].w", vignette)
    assert restored == original
    path = SHADERS / f"{index}.asm"
    path.write_text(patched)
    (SHADERS / f"{index}.diff").write_text(
        "".join(difflib.unified_diff(original.splitlines(True), patched.splitlines(True)))
    )
    subprocess.run(
        [
            str(shader.ASM),
            "-a",
            "--copy-reflection",
            str(shader.ROOT / f"extracted/{index}.dxbc"),
            str(path),
        ],
        check=True,
    )
    subprocess.run([str(shader.ASM), "-d", "-V", str(path.with_suffix(".shdr"))], check=True)
    original_chunks = shader.chunks((shader.ROOT / f"extracted/{index}.dxbc").read_bytes())
    patched_chunks = shader.chunks(path.with_suffix(".shdr").read_bytes())
    assert original_chunks.keys() == patched_chunks.keys() and all(
        original_chunks[k] == patched_chunks[k]
        for k in original_chunks
        if k not in ("SHEX", "SHDR")
    )


def build_shaders() -> None:
    for spec in SHADER_VARIANTS:
        patch_shader(spec)


def main():
    build_mpc()
    build_shaders()
    pak_path = package.build(output_dir=OUT, package_dir=STAGE, shader_dir=SHADERS)
    report = json.loads((OUT / "validation.json").read_text())
    report.update(
        patch_sha256=hashlib.sha256(pak_path.read_bytes()).hexdigest(),
        configurable_smooth_colours=True,
        configurable_vignette=True,
        gradient_modes={"original": 0, "smooth": 1, "biased": 2},
        original_mpc_roundtrip_identical=True,
        original_mpc_scalars_preserved=True,
    )
    (OUT / "validation.json").write_text(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
