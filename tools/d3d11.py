"""Minimal D3D11 COM bindings used only by the offline shader checks.

Vtable slots and ctypes signatures mirror ID3D11Device/ID3D11DeviceContext.
The session owns created resources and releases them even when validation fails.
No game process is opened or injected.
"""

import ctypes as C
from pathlib import Path

UINT = C.c_uint
PTR = C.c_void_p
HRESULT = C.c_long


class BufferDesc(C.Structure):
    _fields_ = [
        (n, UINT)
        for n in (
            "ByteWidth",
            "Usage",
            "BindFlags",
            "CPUAccessFlags",
            "MiscFlags",
            "StructureByteStride",
        )
    ]


class TextureDesc(C.Structure):
    _fields_ = [
        (n, UINT)
        for n in (
            "Width",
            "Height",
            "MipLevels",
            "ArraySize",
            "Format",
            "SampleCount",
            "SampleQuality",
            "Usage",
            "BindFlags",
            "CPUAccessFlags",
            "MiscFlags",
        )
    ]


class Subresource(C.Structure):
    _fields_ = [("Data", PTR), ("Pitch", UINT), ("SlicePitch", UINT)]


class SamplerDesc(C.Structure):
    _fields_ = [
        ("Filter", UINT),
        ("AddressU", UINT),
        ("AddressV", UINT),
        ("AddressW", UINT),
        ("MipLODBias", C.c_float),
        ("MaxAnisotropy", UINT),
        ("ComparisonFunc", UINT),
        ("BorderColor", C.c_float * 4),
        ("MinLOD", C.c_float),
        ("MaxLOD", C.c_float),
    ]


class Mapped(C.Structure):
    _fields_ = [("Data", PTR), ("RowPitch", UINT), ("DepthPitch", UINT)]


def call(obj, idx, restype, args, *values):
    vt = C.cast(obj, C.POINTER(C.POINTER(PTR))).contents
    return C.WINFUNCTYPE(restype, PTR, *args)(vt[idx])(obj, *values)


def check(hr, label):
    if hr < 0:
        raise RuntimeError(f"{label}: HRESULT {hr & 0xFFFFFFFF:08x}")


def release(obj):
    if obj:
        call(obj, 2, C.c_ulong, [])


class D3D11Session:
    """Own a device, immediate context, and the resources created for one test."""

    def __init__(self, driver=5):
        self.device = PTR()
        self.context = PTR()
        self.feature = UINT()
        create = C.WinDLL("d3d11.dll").D3D11CreateDevice
        create.argtypes = [
            PTR,
            UINT,
            PTR,
            UINT,
            PTR,
            UINT,
            UINT,
            C.POINTER(PTR),
            C.POINTER(UINT),
            C.POINTER(PTR),
        ]
        create.restype = HRESULT
        check(
            create(
                None,
                driver,
                None,
                0,
                None,
                0,
                7,
                C.byref(self.device),
                C.byref(self.feature),
                C.byref(self.context),
            ),
            "CreateDevice",
        )
        self.objects = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        release(self.context)
        for resource in reversed(self.objects):
            release(resource)
        release(self.device)

    def keep(self, p):
        self.objects.append(p)
        return p

    def shader(self, path, idx):
        code = Path(path).read_bytes()
        blob = C.create_string_buffer(code)
        p = PTR()
        check(
            call(
                self.device,
                idx,
                HRESULT,
                [PTR, C.c_size_t, PTR, C.POINTER(PTR)],
                blob,
                len(code),
                None,
                C.byref(p),
            ),
            "CreateShader",
        )
        return self.keep(p)

    def buffer(self, data, size, bind, usage=0, cpu=0, stride=0):
        desc = BufferDesc(size, usage, bind, cpu, 64 if stride else 0, stride)
        initial = C.create_string_buffer(data) if data is not None else None
        sub = Subresource(C.cast(initial, PTR), 0, 0) if initial is not None else None
        p = PTR()
        check(
            call(
                self.device,
                3,
                HRESULT,
                [PTR, PTR, C.POINTER(PTR)],
                C.byref(desc),
                C.byref(sub) if sub else None,
                C.byref(p),
            ),
            "CreateBuffer",
        )
        return self.keep(p)

    def view(self, resource, idx):
        p = PTR()
        check(
            call(self.device, idx, HRESULT, [PTR, PTR, C.POINTER(PTR)], resource, None, C.byref(p)),
            "CreateView",
        )
        return self.keep(p)

    def texture(self, data):
        desc = TextureDesc(256, 16, 1, 1, 87, 1, 0, 1, 8, 0, 0)
        blob = C.create_string_buffer(data)
        sub = Subresource(C.cast(blob, PTR), 1024, 16384)
        p = PTR()
        check(
            call(
                self.device,
                5,
                HRESULT,
                [PTR, PTR, C.POINTER(PTR)],
                C.byref(desc),
                C.byref(sub),
                C.byref(p),
            ),
            "CreateTexture2D",
        )
        return self.view(self.keep(p), 7)
