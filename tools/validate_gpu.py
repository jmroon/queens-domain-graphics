"""Execute lookup bytecode and compare GPU output with an independent reference."""

import ctypes as C
import json
import math
import random
import struct

from d3d11 import HRESULT, PTR, UINT, D3D11Session, Mapped, SamplerDesc, call, check
from paths import ASSETS


def lut(name):
    folder = ASSETS / "QueensDomain/Content/UI/LUTs"
    data = (folder / f"{name}.uexp").read_bytes()
    p = data.index(b"PF_B8G8R8A8\0") + len(b"PF_B8G8R8A8\0")
    mip, count, cooked, flags, num, size, offset = struct.unpack_from("<6Iq", data, p)
    p += 32
    assert (mip, count, cooked, num, size) == (0, 1, 1, 16384, 16384)
    assert offset == (folder / f"{name}.uasset").stat().st_size + p
    assert struct.unpack_from("<3I", data, p + size) == (256, 16, 1)
    return data[p : p + size]


def reference(data, rgb):
    value = [max(0, min(1, x)) * 15 for x in rgb]
    lo = [math.floor(x) for x in value]
    hi = [min(x + 1, 15) for x in lo]
    frac = [a - b for a, b in zip(value, lo)]
    result = [0.0, 0.0, 0.0]
    for b in range(2):
        for g in range(2):
            for r in range(2):
                x = (hi if b else lo)[2] * 16 + (hi if r else lo)[0]
                y = (hi if g else lo)[1]
                p = (y * 256 + x) * 4
                weight = (
                    (frac[0] if r else 1 - frac[0])
                    * (frac[1] if g else 1 - frac[1])
                    * (frac[2] if b else 1 - frac[2])
                )
                for c, channel in enumerate((2, 1, 0)):
                    result[c] += data[p + channel] / 255 * weight
    return result


def default_sample_points():
    """LUT lattice points, random colours, and both sides of blue-slice boundaries."""
    points = [(r / 15, g / 15, b / 15) for b in range(16) for g in range(16) for r in range(16)]
    rng = random.Random(1703)
    points += [(rng.random(), rng.random(), rng.random()) for _ in range(4096)]
    # Exact boundary values plus closely spaced colours on either side of every blue slice.
    points += [
        (0.43, 0.61, max(0, min(1, b / 15 + delta)))
        for b in range(16)
        for delta in (-1e-6, 0, 1e-6)
    ]
    points += [(0, 0, 0)] * ((-len(points)) % 64)
    return points


def execute_lookup(session, compute_shader, points, cpu_reference):
    """Upload float32 RGB samples, dispatch two LUTs at once, and check readback."""
    count = len(points)
    inbytes = b"".join(struct.pack("<4f", r, b, g, 0) for r, g, b in points)
    # The shader receives float32, so reference the same input values.
    points = [(v[0], v[2], v[1]) for v in struct.iter_unpack("<4f", inbytes)]
    inputbuf = session.buffer(inbytes, len(inbytes), 8, stride=16)
    inputview = session.view(inputbuf, 7)
    outbuf = session.buffer(None, count * 32, 128, stride=32)
    outview = session.view(outbuf, 8)
    staging = session.buffer(None, count * 32, 0, usage=3, cpu=0x20000)
    desc = SamplerDesc(0, 3, 3, 3, 0, 1, 1, (C.c_float * 4)(0, 0, 0, 0), 0, 3.402823466e38)
    sampler = PTR()
    check(
        call(session.device, 23, HRESULT, [PTR, C.POINTER(PTR)], C.byref(desc), C.byref(sampler)),
        "CreateSampler",
    )
    session.keep(sampler)
    cs = session.shader(compute_shader, 18)
    call(session.context, 69, None, [PTR, PTR, UINT], cs, None, 0)
    call(session.context, 67, None, [UINT, UINT, PTR], 7, 1, (PTR * 1)(inputview.value))
    call(session.context, 68, None, [UINT, UINT, PTR, PTR], 0, 1, (PTR * 1)(outview.value), None)
    call(
        session.context, 70, None, [UINT, UINT, PTR], 0, 2, (PTR * 2)(sampler.value, sampler.value)
    )
    names = ["StandardColor", "OtherWorldLUT", "Wincolor", "StandardColor_OtherWorld"]
    results = []
    for first, second in zip(names[::2], names[1::2]):
        tables = [lut(first), lut(second)]
        views = [session.texture(t) for t in tables]
        call(
            session.context, 67, None, [UINT, UINT, PTR], 0, 2, (PTR * 2)(*[v.value for v in views])
        )
        call(session.context, 41, None, [UINT, UINT, UINT], count // 64, 1, 1)
        call(session.context, 47, None, [PTR, PTR], staging, outbuf)
        mapped = Mapped()
        check(
            call(
                session.context,
                14,
                HRESULT,
                [PTR, UINT, UINT, UINT, PTR],
                staging,
                0,
                1,
                0,
                C.byref(mapped),
            ),
            "Map",
        )
        output = C.string_at(mapped.Data, count * 32)
        call(session.context, 15, None, [PTR, UINT], staging, 0)
        values = list(struct.iter_unpack("<8f", output))
        for j, name in enumerate((first, second)):
            err = 0.0
            griderr = 0.0
            for i, p in enumerate(points):
                expected = cpu_reference(tables[j], p)
                actual = values[i][j * 4 : j * 4 + 3]
                assert all(math.isfinite(x) for x in actual)
                difference = max(abs(a - b) for a, b in zip(actual, expected))
                err = max(err, difference)
                if i < 4096:
                    griderr = max(griderr, difference)
            assert err < 2e-6, (name, err)
            results.append(
                dict(lut=name, samples=count, max_absolute_error=err, lattice_max_error=griderr)
            )
    return results


def validate(driver, *, compute_shader, sample_points, cpu_reference, report_path, mode):
    """Validate one lookup mode on one driver, with explicit inputs and output path."""
    with D3D11Session(driver) as session:
        results = execute_lookup(session, compute_shader, sample_points, cpu_reference)
        report = dict(
            driver="WARP" if driver == 5 else "hardware",
            feature_level=hex(session.feature.value),
            mode=mode,
            standalone_compute_shader=True,
            results=results,
        )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    print(mode, driver, "max error", max(result["max_absolute_error"] for result in results))
    return report
