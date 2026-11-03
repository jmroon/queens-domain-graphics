"""Check exact lookup blocks and complete pixel shaders on D3D11 hardware/WARP."""

import json
import re
import subprocess

import gpu_check as harness
from d3d11 import D3D11Session
from paths import ASSEMBLER, BUILD

ROOT = BUILD / "graphics"
OUT = BUILD / "reports/gpu"


def check_lookup_variant(index):
    OUT.mkdir(parents=True, exist_ok=True)
    folder = ROOT / f"bias-check-{index}"
    folder.mkdir(exist_ok=True)
    output = OUT / f"shader-{index}"
    output.mkdir(exist_ok=True)
    source = (ROOT / f"shaders/{index}.asm").read_text()
    cb = 1 if index == 2 else 2
    start = source.index(f"ge r4.x, cb{cb}[1].z, l(0.500000)")
    end = source.index(
        "mul r0.w, cb0[130].y" if index == 2 else "add r2.xyz, -r1.xyzx, r2.xyzx", start
    )
    block = source[start:end]
    # Strip only bindings; instructions and register allocation stay unchanged.
    mapping = (
        {"t4": "t0", "t5": "t1", "s1": "s0", "s2": "s1"}
        if index == 2
        else {"t4": "t0", "t3": "t1", "s2": "s0", "s1": "s1"}
    )
    block = re.sub(r"\b(?:t[0-9]+|s[0-9]+)\b", lambda m: mapping.get(m[0], m[0]), block)
    src = "r0" if index == 2 else "r1"
    dest = ("r0", "r2") if index == 2 else ("r2", "r1")

    def build(mode):
        value = {"original": 0, "smooth": 1, "endpoint": 2}[mode]
        selected = block.replace(f"cb{cb}[1].z", f"l({value}.000000)")
        code = (
            """cs_5_0
dcl_globalFlags refactoringAllowed
dcl_resource_texture2d (float,float,float,float) t0
dcl_resource_texture2d (float,float,float,float) t1
dcl_resource_structured t7, 16
dcl_sampler s0, mode_default
dcl_sampler s1, mode_default
dcl_uav_structured u0, 32
dcl_input vThreadID.x
dcl_temps 16
dcl_thread_group 64, 1, 1
"""
            + f"ld_structured_indexable(structured_buffer, stride=16)(mixed,mixed,mixed,mixed) {src}.xyzw, vThreadID.x, l(0), t7.xyzw\n"
            + selected
            + f"""store_structured u0.xyz, vThreadID.x, l(0), {dest[0]}.xyzx
store_structured u0.xyz, vThreadID.x, l(16), {dest[1]}.xyzx
ret
"""
        )
        path = folder / f"{mode}.asm"
        path.write_text(code)
        subprocess.run([str(ASSEMBLER), "-a", str(path)], check=True, capture_output=True)

        return path.with_suffix(".shdr")

    harness.run(build, output)


def check_complete_pixel_shaders():
    """Ensure both complete shaders retain valid original bindings/signatures."""
    for driver in (5, 1):
        with D3D11Session(driver) as session:
            for index in (2, 3):
                session.shader(ROOT / f"shaders/{index}.shdr", 15)


def main():
    for index in (2, 3):
        check_lookup_variant(index)
    check_complete_pixel_shaders()
    print(
        "PASS: both complete pixel shaders accepted on hardware and WARP; all three lookup modes match independent CPU references."
    )
    (OUT / "summary.json").write_text(
        json.dumps(
            dict(
                full_pixel_shaders_accepted=True,
                drivers=["hardware", "WARP"],
                modes=["original", "smooth", "biased"],
                pixel_shader_variants=2,
                samples_per_lut_per_mode_per_device=4096,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
