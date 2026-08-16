#!/usr/bin/env python3
"""Generate resources/icon.png.

Pure stdlib (zlib + struct) so the only binary in the repo can be rebuilt from
source without pulling in an image library. 3x supersampled for smooth edges.

    uv run python scripts/make_icon.py
"""

import pathlib
import struct
import zlib

SIZE = 512
SUPERSAMPLE = 3

BACKGROUND = (24, 32, 43)
BUBBLE = (245, 179, 1)
GLYPH = (24, 32, 43)

OUTPUT = pathlib.Path(__file__).resolve().parent.parent / (
    "service.omnimessage/resources/icon.png"
)


def inside_rounded_rect(x, y, x0, y0, x1, y1, radius):
    if not (x0 <= x <= x1 and y0 <= y <= y1):
        return False
    cx = min(max(x, x0 + radius), x1 - radius)
    cy = min(max(y, y0 + radius), y1 - radius)
    return (x - cx) ** 2 + (y - cy) ** 2 <= radius**2


def inside_circle(x, y, cx, cy, radius):
    return (x - cx) ** 2 + (y - cy) ** 2 <= radius**2


def inside_tail(x, y):
    """Right triangle hanging off the bottom-left of the bubble."""
    if not (150 <= x <= 250 and 360 <= y <= 470):
        return False
    return (y - 360) <= (250 - x) * (110 / 100)


def sample(x, y):
    """Colour of one sample point: a speech bubble with an exclamation mark."""
    on_bubble = inside_rounded_rect(x, y, 56, 56, 456, 380, 56) or inside_tail(x, y)
    if not on_bubble:
        return BACKGROUND
    if inside_rounded_rect(x, y, 236, 120, 276, 262, 20):
        return GLYPH
    if inside_circle(x, y, 256, 312, 26):
        return GLYPH
    return BUBBLE


def render():
    rows = []
    step = 1.0 / SUPERSAMPLE
    offsets = [(i + 0.5) * step for i in range(SUPERSAMPLE)]
    samples_per_pixel = SUPERSAMPLE * SUPERSAMPLE

    for py in range(SIZE):
        row = bytearray()
        row.append(0)  # PNG filter type: none
        for px in range(SIZE):
            r = g = b = 0
            for dy in offsets:
                for dx in offsets:
                    sr, sg, sb = sample(px + dx, py + dy)
                    r += sr
                    g += sg
                    b += sb
            row += bytes(
                (
                    r // samples_per_pixel,
                    g // samples_per_pixel,
                    b // samples_per_pixel,
                )
            )
        rows.append(bytes(row))
    return b"".join(rows)


def chunk(tag, data):
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def write_png(path, raw):
    header = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 2, 0, 0, 0)  # 8-bit RGB
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


if __name__ == "__main__":
    write_png(OUTPUT, render())
    print("wrote {} ({} bytes)".format(OUTPUT, OUTPUT.stat().st_size))
