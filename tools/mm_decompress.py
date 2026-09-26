"""DIRTY ROOM: decompress the Majora's Mask (US) ROM for 2S2H's extractor.

    python tools/mm_decompress.py <baserom.us.z64> <out.z64>

Walks dmadata (0x1A500), Yaz0-decodes each compressed file into its virtual
address and rewrites the table as uncompressed (romStart = vromStart, romEnd = 0).
The output is never published.
"""
import struct
import sys

DMADATA = 0x1A500


def yaz0(src, off, size_hint=0):
    assert src[off:off + 4] == b"Yaz0", hex(off)
    n = struct.unpack(">I", src[off + 4:off + 8])[0]
    out = bytearray(n)
    s, d = off + 16, 0
    while d < n:
        code = src[s]
        s += 1
        for bit in range(8):
            if d >= n:
                break
            if code & (0x80 >> bit):
                out[d] = src[s]
                d += 1
                s += 1
            else:
                b1, b2 = src[s], src[s + 1]
                s += 2
                dist = ((b1 & 0xF) << 8 | b2) + 1
                cnt = b1 >> 4
                if cnt == 0:
                    cnt = src[s] + 0x12
                    s += 1
                else:
                    cnt += 2
                p = d - dist
                if dist >= cnt:
                    out[d:d + cnt] = out[p:p + cnt]
                    d += cnt
                else:
                    for _ in range(cnt):
                        out[d] = out[p]
                        d += 1
                        p += 1
    return bytes(out)


def main(src_path, dst_path):
    rom = open(src_path, "rb").read()
    entries = []
    p = DMADATA
    while True:
        vs, ve, ps, pe = struct.unpack(">4I", rom[p:p + 16])
        if vs == 0 and ve == 0 and p > DMADATA:
            break
        entries.append((vs, ve, ps, pe))
        p += 16
    size = max(ve for vs, ve, ps, pe in entries)
    size = (size + 0xFFFFF) & ~0xFFFFF
    out = bytearray(size)
    ncomp = 0
    for vs, ve, ps, pe in entries:
        if ps == 0xFFFFFFFF or ve <= vs:
            continue
        if pe == 0:
            out[vs:ve] = rom[ps:ps + (ve - vs)]
        else:
            data = yaz0(rom, ps)
            out[vs:vs + len(data)] = data[:ve - vs]
            ncomp += 1
    # rewrite dmadata as uncompressed
    for i, (vs, ve, ps, pe) in enumerate(entries):
        q = DMADATA + 16 * i
        if ps == 0xFFFFFFFF:
            out[q:q + 16] = struct.pack(">4I", vs, ve, 0xFFFFFFFF, 0xFFFFFFFF)
        else:
            out[q:q + 16] = struct.pack(">4I", vs, ve, vs, 0)
    open(dst_path, "wb").write(out)
    print(f"{len(entries)} files, {ncomp} decompressed, {len(out) // 0x100000} MB -> {dst_path}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
