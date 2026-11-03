import json
import struct

from inspect_container import ROOT, SOURCE


def inspect(data=None):
    data = SOURCE.read_bytes() if data is None else data
    start = 7703
    size = struct.unpack_from("<I", data, start - 4)[0]
    frozen = data[start : start + size]

    def u32(p):
        return struct.unpack_from("<I", frozen, p)[0]

    def ptr(p):
        packed = struct.unpack_from("<q", frozen, p)[0]
        assert packed & 1, (p, packed)
        return p + (packed >> 1)

    def array(p, pointers=False):
        count, cap = struct.unpack_from("<II", frozen, p + 8)
        assert count == cap
        if count == 0:
            return []
        loc = ptr(p)
        return [ptr(loc + i * 8) for i in range(count)] if pointers else (loc, count)

    shaders = []

    def shader(p):
        for offset in (0, 16, 32, 48, 72, 88, 104, 120, 144, 160):
            array(p + offset)
        target = u32(p + 192)
        index = u32(p + 196)
        instructions = u32(p + 200)
        assert target in (0, 3) and index in range(4), (p, target, index, instructions)
        shaders.append(
            dict(
                frozen_offset=p,
                index_offset=start + p + 196,
                index=index,
                frequency=target,
                instructions=instructions,
                instructions_offset=start + p + 200,
            )
        )

    def content(p):
        for s in array(p + 56, True):
            shader(s)
        assert array(p + 72) == [], "Shader pipelines not implemented"

    content(0)
    for p in array(96, True):
        content(p)
    assert sorted(x["index"] for x in shaders) == [0, 1, 2, 3]
    result = dict(frozen_offset=start, frozen_size=size, shaders=shaders)
    return result


if __name__ == "__main__":
    result = inspect()
    (ROOT / "frozen.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
