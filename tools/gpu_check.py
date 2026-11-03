"""Run explicitly supplied shader fixtures against the independent LUT reference."""

import random
from functools import lru_cache

import analyze
from validate_gpu import validate


def sample_points():
    """Avoid hardware-dependent point-filter ties while including black/white/grey."""
    rng = random.Random(4112)
    points = [(0, 0, 0), (1, 1, 1), (0.5, 0.5, 0.5)]
    while len(points) < 4096:
        colour = tuple(rng.random() for _ in range(3))
        coordinate = [channel * 15 for channel in colour]
        if min(abs(coordinate[axis] % 1 - 0.5) for axis in (0, 1)) < 0.01:
            continue
        if min(coordinate[2] % 1, 1 - coordinate[2] % 1) < 0.001:
            continue
        points.append(colour)
    return points


@lru_cache(maxsize=4)
def decode_lut(data):
    """Convert stored BGRA8 pixels into RGB floats once per LUT."""
    return [
        tuple(data[index + channel] / 255 for channel in (2, 1, 0))
        for index in range(0, len(data), 4)
    ]


def run(build_fixture, output_directory, modes=("original", "smooth", "endpoint")):
    points = sample_points()
    for mode in modes:
        shader_path = build_fixture(mode)

        def cpu_reference(data, colour):
            return analyze.evaluate(decode_lut(data), colour, mode)

        for driver in (5, 1):
            validate(
                driver,
                compute_shader=shader_path,
                sample_points=points,
                cpu_reference=cpu_reference,
                mode=mode,
                report_path=output_directory / f"gpu-{mode}-{driver}.json",
            )
