from __future__ import annotations

import struct
import subprocess
import zlib
from pathlib import Path

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _ffmpeg_decode_rgb(path: Path, width: int, height: int) -> bytes | None:
    command = [
        "ffmpeg",
        "-v",
        "error",
        "-i",
        str(path),
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{width}x{height}",
        "-",
    ]
    try:
        result = subprocess.run(command, capture_output=True, check=False)
    except (FileNotFoundError, OSError):
        return None
    if result.returncode != 0:
        return None
    expected = width * height * 3
    if len(result.stdout) < expected:
        return None
    return result.stdout[:expected]


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def _unfilter_scanlines(raw: bytes, width: int, channels: int) -> bytes:
    stride = width * channels
    rows = []
    offset = 0
    prev = bytearray(stride)
    while offset < len(raw):
        filter_type = raw[offset]
        offset += 1
        cur = bytearray(raw[offset : offset + stride])
        offset += stride

        if filter_type == 1:  # Sub
            for i in range(stride):
                left = cur[i - channels] if i >= channels else 0
                cur[i] = (cur[i] + left) & 0xFF
        elif filter_type == 2:  # Up
            for i in range(stride):
                cur[i] = (cur[i] + prev[i]) & 0xFF
        elif filter_type == 3:  # Average
            for i in range(stride):
                left = cur[i - channels] if i >= channels else 0
                up = prev[i]
                cur[i] = (cur[i] + ((left + up) // 2)) & 0xFF
        elif filter_type == 4:  # Paeth
            for i in range(stride):
                left = cur[i - channels] if i >= channels else 0
                up = prev[i]
                up_left = prev[i - channels] if i >= channels else 0
                cur[i] = (cur[i] + _paeth(left, up, up_left)) & 0xFF
        # filter_type==0 means None

        rows.append(bytes(cur))
        prev = cur
    return b"".join(rows)


def _decode_png_rgb(path: Path, width: int, height: int) -> bytes | None:
    raw = path.read_bytes()
    if not raw.startswith(PNG_SIGNATURE):
        return None

    idx = len(PNG_SIGNATURE)
    idat = bytearray()
    src_w = src_h = 0
    bit_depth = color_type = None
    while idx + 8 <= len(raw):
        chunk_len = struct.unpack(">I", raw[idx : idx + 4])[0]
        chunk_type = raw[idx + 4 : idx + 8]
        data_start = idx + 8
        data_end = data_start + chunk_len
        if data_end + 4 > len(raw):
            return None
        chunk_data = raw[data_start:data_end]
        idx = data_end + 4

        if chunk_type == b"IHDR":
            src_w = struct.unpack(">I", chunk_data[0:4])[0]
            src_h = struct.unpack(">I", chunk_data[4:8])[0]
            bit_depth = int(chunk_data[8])
            color_type = int(chunk_data[9])
        elif chunk_type == b"IDAT":
            idat.extend(chunk_data)
        elif chunk_type == b"IEND":
            break

    if not src_w or not src_h or bit_depth != 8 or color_type not in (2, 6):
        return None

    channels = 3 if color_type == 2 else 4
    inflated = zlib.decompress(bytes(idat))
    unpacked = _unfilter_scanlines(inflated, src_w, channels)
    if len(unpacked) != src_w * src_h * channels:
        return None

    rgb = bytearray(src_w * src_h * 3)
    if channels == 3:
        rgb[:] = unpacked
    else:
        for i in range(src_w * src_h):
            rgb[i * 3 : i * 3 + 3] = unpacked[i * 4 : i * 4 + 3]

    if src_w == width and src_h == height:
        return bytes(rgb)

    # nearest-neighbor resize
    out = bytearray(width * height * 3)
    for y in range(height):
        sy = int((y * src_h) / max(1, height))
        if sy >= src_h:
            sy = src_h - 1
        for x in range(width):
            sx = int((x * src_w) / max(1, width))
            if sx >= src_w:
                sx = src_w - 1
            src_idx = (sy * src_w + sx) * 3
            dst_idx = (y * width + x) * 3
            out[dst_idx : dst_idx + 3] = rgb[src_idx : src_idx + 3]
    return bytes(out)


def _fallback_bytes(path: Path, width: int, height: int) -> bytes:
    raw = path.read_bytes()
    expected = width * height * 3
    if not raw:
        return b"\x00" * expected
    out = bytearray(expected)
    for i in range(expected):
        out[i] = raw[i % len(raw)]
    return bytes(out)


def load_rgb_image(path: Path, width: int, height: int) -> bytes:
    decoded = _ffmpeg_decode_rgb(path, width, height)
    if decoded is not None:
        return decoded
    decoded = _decode_png_rgb(path, width, height)
    if decoded is not None:
        return decoded
    return _fallback_bytes(path, width, height)
