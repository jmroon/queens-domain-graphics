"""Replace only DitherBase's LUT sampling block; no original game file writes."""

import struct

from paths import ASSEMBLER, BUILD

ROOT = BUILD / "shader"
ROOT.mkdir(parents=True, exist_ok=True)
OUT = ROOT / "patched"
OUT.mkdir(exist_ok=True, parents=True)
ASM = ASSEMBLER


def lookup_block(source, targets):
    # Source is R,B,G after the original shader's swizzle. Convert to RGB here.
    lines = [
        f"mul r4.xyz, {source}.xzyx, l(15.000000, 15.000000, 15.000000, 0)",
        "round_ni r5.xyz, r4.xyzx",
        "add r7.xyz, r4.xyzx, -r5.xyzx",
        "add r6.xyz, r5.xyzx, l(1.000000, 1.000000, 1.000000, 0)",
        "min r6.xyz, r6.xyzx, l(15.000000, 15.000000, 15.000000, 0)",
    ]
    for texture, sampler, dest in targets:
        for b in range(2):
            for g in range(2):
                for r in range(2):
                    reg = 8 + b * 4 + g * 2 + r
                    lines += [
                        f"mov r4.x, r{5 + r}.x",
                        f"mad r4.x, r{5 + b}.z, l(16.000000), r4.x",
                        f"mov r4.y, r{5 + g}.y",
                        "add r4.xy, r4.xyxx, l(0.500000, 0.500000, 0, 0)",
                        "mul r4.xy, r4.xyxx, l(0.003906250, 0.062500, 0, 0)",
                        f"sample_l_indexable(texture2d)(float,float,float,float) r{reg}.xyz, r4.xyxx, t{texture}.xyzw, s{sampler}, l(0)",
                    ]
        for reg in (8, 10, 12, 14):
            lines += [
                f"add r{reg + 1}.xyz, r{reg + 1}.xyzx, -r{reg}.xyzx",
                f"mad r{reg}.xyz, r7.xxxx, r{reg + 1}.xyzx, r{reg}.xyzx",
            ]
        for reg in (8, 12):
            lines += [
                f"add r{reg + 2}.xyz, r{reg + 2}.xyzx, -r{reg}.xyzx",
                f"mad r{reg}.xyz, r7.yyyy, r{reg + 2}.xyzx, r{reg}.xyzx",
            ]
        lines += ["add r12.xyz, r12.xyzx, -r8.xyzx", f"mad {dest}.xyz, r7.zzzz, r12.xyzx, r8.xyzx"]
    return "\n".join(lines)


def chunks(blob):
    assert blob[:4] == b"DXBC" and struct.unpack_from("<I", blob, 24)[0] == len(blob)
    count = struct.unpack_from("<I", blob, 28)[0]
    result = {}
    for i in range(count):
        p = struct.unpack_from("<I", blob, 32 + i * 4)[0]
        size = struct.unpack_from("<I", blob, p + 4)[0]
        result[blob[p : p + 4].decode()] = blob[p + 8 : p + 8 + size]
    return result
