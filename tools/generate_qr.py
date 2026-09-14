"""Generátor QR kódu do statického SVG – jen standardní knihovna Pythonu.

Použití:
    python tools/generate_qr.py --all          # všechny kódy podle tools/qr_targets.json
    python tools/generate_qr.py --url "https://..." --out assets/qr/nazev.svg --dark "#111111"

Kódování: byte mode (UTF-8), korekce chyb M, verze se volí automaticky (1–40),
maska podle penalizačních pravidel ISO/IEC 18004. Po vygenerování se QR
nezávisle přečte zpět (formát, syndromy Reed-Solomon, obsah) a porovná se vstupem.
"""
import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TARGETS = ROOT / "tools" / "qr_targets.json"
DEFAULT_URL = ("https://www.motivacnidarky.cz/"
               "?utm_source=doporucovaci-hub&utm_medium=qr&utm_campaign=doporuceni")
DEFAULT_OUT = ROOT / "assets" / "qr" / "motivacnidarky.svg"

# Úroveň korekce: (index do tabulek, formátové bity)
ECL = {"L": (0, 1), "M": (1, 0), "Q": (2, 3), "H": (3, 2)}

ECC_CODEWORDS_PER_BLOCK = (
    (-1, 7, 10, 15, 20, 26, 18, 20, 24, 30, 18, 20, 24, 26, 30, 22, 24, 28, 30, 28, 28, 28, 28, 30, 30, 26, 28, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30),
    (-1, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26, 30, 22, 22, 24, 24, 28, 28, 26, 26, 26, 26, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28),
    (-1, 13, 22, 18, 26, 18, 24, 18, 22, 20, 24, 28, 26, 24, 20, 30, 24, 28, 28, 26, 30, 28, 30, 30, 30, 30, 28, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30),
    (-1, 17, 28, 22, 16, 22, 28, 26, 26, 24, 28, 24, 28, 22, 24, 24, 30, 28, 28, 26, 28, 30, 24, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30),
)
NUM_ERROR_CORRECTION_BLOCKS = (
    (-1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 4, 4, 4, 4, 4, 6, 6, 6, 6, 7, 8, 8, 9, 9, 10, 12, 12, 12, 13, 14, 15, 16, 17, 18, 19, 19, 20, 21, 22, 24, 25),
    (-1, 1, 1, 1, 2, 2, 4, 4, 4, 5, 5, 5, 8, 9, 9, 10, 10, 11, 13, 14, 16, 17, 17, 18, 20, 21, 23, 25, 26, 28, 29, 31, 33, 35, 37, 38, 40, 43, 45, 47, 49),
    (-1, 1, 1, 2, 2, 4, 4, 6, 6, 8, 8, 8, 10, 12, 16, 12, 17, 16, 18, 21, 20, 23, 23, 25, 27, 29, 34, 34, 35, 38, 40, 43, 45, 48, 51, 53, 56, 59, 62, 65, 68),
    (-1, 1, 1, 2, 4, 4, 4, 5, 6, 8, 8, 11, 11, 16, 16, 18, 16, 19, 21, 25, 25, 25, 34, 30, 32, 35, 37, 40, 42, 45, 48, 51, 54, 57, 60, 63, 66, 70, 74, 77, 81),
)

MASKS = (
    lambda x, y: (x + y) % 2 == 0,
    lambda x, y: y % 2 == 0,
    lambda x, y: x % 3 == 0,
    lambda x, y: (x + y) % 3 == 0,
    lambda x, y: (x // 3 + y // 2) % 2 == 0,
    lambda x, y: x * y % 2 + x * y % 3 == 0,
    lambda x, y: (x * y % 2 + x * y % 3) % 2 == 0,
    lambda x, y: ((x + y) % 2 + x * y % 3) % 2 == 0,
)


# ---------------------------------------------------------------- GF(256) ---
def gf_mul(x, y):
    z = 0
    for i in reversed(range(8)):
        z = (z << 1) ^ ((z >> 7) * 0x11D)
        z ^= ((y >> i) & 1) * x
    return z


def rs_divisor(degree):
    result = [0] * (degree - 1) + [1]
    root = 1
    for _ in range(degree):
        for j in range(degree):
            result[j] = gf_mul(result[j], root)
            if j + 1 < degree:
                result[j] ^= result[j + 1]
        root = gf_mul(root, 0x02)
    return result


def rs_remainder(data, divisor):
    result = [0] * len(divisor)
    for b in data:
        factor = b ^ result.pop(0)
        result.append(0)
        for i, coef in enumerate(divisor):
            result[i] ^= gf_mul(coef, factor)
    return result


# ------------------------------------------------------------- struktura ---
def num_raw_data_modules(ver):
    result = (16 * ver + 128) * ver + 64
    if ver >= 2:
        numalign = ver // 7 + 2
        result -= (25 * numalign - 10) * numalign - 55
        if ver >= 7:
            result -= 36
    return result


def num_data_codewords(ver, ecl_idx):
    return (num_raw_data_modules(ver) // 8
            - ECC_CODEWORDS_PER_BLOCK[ecl_idx][ver] * NUM_ERROR_CORRECTION_BLOCKS[ecl_idx][ver])


def alignment_positions(ver):
    if ver == 1:
        return []
    size = ver * 4 + 17
    numalign = ver // 7 + 2
    step = (ver * 8 + numalign * 3 + 5) // (numalign * 4 - 4) * 2
    return list(reversed([size - 7 - i * step for i in range(numalign - 1)] + [6]))


def format_bits(ecl_bits, mask):
    data = ecl_bits << 3 | mask
    rem = data
    for _ in range(10):
        rem = (rem << 1) ^ ((rem >> 9) * 0x537)
    return (data << 10 | rem) ^ 0x5412


class QR:
    def __init__(self, text, ecl="M"):
        data = text.encode("utf-8")
        self.ecl_idx, self.ecl_bits = ECL[ecl]
        for ver in range(1, 41):
            count_bits = 8 if ver <= 9 else 16
            if 4 + count_bits + len(data) * 8 <= num_data_codewords(ver, self.ecl_idx) * 8:
                break
        else:
            raise ValueError("Data se nevejdou do QR verze 40")
        self.version = ver
        self.size = ver * 4 + 17
        self.modules = [[False] * self.size for _ in range(self.size)]
        self.isfunc = [[False] * self.size for _ in range(self.size)]

        self._draw_function_patterns()
        codewords = self._add_ecc_and_interleave(self._encode_data(data, count_bits))
        self._draw_codewords(codewords)

        best, best_penalty = 0, None
        for m in range(8):
            self._apply_mask(m)
            self._draw_format(m)
            p = self._penalty()
            if best_penalty is None or p < best_penalty:
                best, best_penalty = m, p
            self._apply_mask(m)  # XOR zpět
        self.mask = best
        self._apply_mask(best)
        self._draw_format(best)

    # -- vzory ---------------------------------------------------------------
    def _set_func(self, x, y, dark):
        self.modules[y][x] = dark
        self.isfunc[y][x] = True

    def _draw_function_patterns(self):
        s = self.size
        for i in range(s):
            self._set_func(6, i, i % 2 == 0)
            self._set_func(i, 6, i % 2 == 0)
        for cx, cy in ((3, 3), (s - 4, 3), (3, s - 4)):
            for dy in range(-4, 5):
                for dx in range(-4, 5):
                    xx, yy = cx + dx, cy + dy
                    if 0 <= xx < s and 0 <= yy < s:
                        self._set_func(xx, yy, max(abs(dx), abs(dy)) not in (2, 4))
        pos = alignment_positions(self.version)
        n = len(pos)
        for i in range(n):
            for j in range(n):
                if (i, j) in ((0, 0), (0, n - 1), (n - 1, 0)):
                    continue
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        self._set_func(pos[i] + dx, pos[j] + dy, max(abs(dx), abs(dy)) != 1)
        self._draw_format(0)
        if self.version >= 7:
            rem = self.version
            for _ in range(12):
                rem = (rem << 1) ^ ((rem >> 11) * 0x1F25)
            bits = self.version << 12 | rem
            for i in range(18):
                bit = (bits >> i) & 1 == 1
                a, b = s - 11 + i % 3, i // 3
                self._set_func(a, b, bit)
                self._set_func(b, a, bit)

    def _draw_format(self, mask):
        bits = format_bits(self.ecl_bits, mask)
        bit = lambda i: (bits >> i) & 1 == 1
        s = self.size
        for i in range(6):
            self._set_func(8, i, bit(i))
        self._set_func(8, 7, bit(6))
        self._set_func(8, 8, bit(7))
        self._set_func(7, 8, bit(8))
        for i in range(9, 15):
            self._set_func(14 - i, 8, bit(i))
        for i in range(8):
            self._set_func(s - 1 - i, 8, bit(i))
        for i in range(8, 15):
            self._set_func(8, s - 15 + i, bit(i))
        self._set_func(8, s - 8, True)

    # -- data ----------------------------------------------------------------
    def _encode_data(self, data, count_bits):
        bits = []
        add = lambda val, n: bits.extend((val >> i) & 1 for i in reversed(range(n)))
        add(0b0100, 4)
        add(len(data), count_bits)
        for b in data:
            add(b, 8)
        capacity = num_data_codewords(self.version, self.ecl_idx) * 8
        add(0, min(4, capacity - len(bits)))
        add(0, -len(bits) % 8)
        pad = 0xEC
        while len(bits) < capacity:
            add(pad, 8)
            pad ^= 0xEC ^ 0x11
        return [int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8)]

    def _add_ecc_and_interleave(self, data):
        ver, e = self.version, self.ecl_idx
        numblocks = NUM_ERROR_CORRECTION_BLOCKS[e][ver]
        ecclen = ECC_CODEWORDS_PER_BLOCK[e][ver]
        raw = num_raw_data_modules(ver) // 8
        numshort = numblocks - raw % numblocks
        shortlen = raw // numblocks
        divisor = rs_divisor(ecclen)
        blocks, k = [], 0
        for i in range(numblocks):
            dat = data[k:k + shortlen - ecclen + (0 if i < numshort else 1)]
            k += len(dat)
            ecc = rs_remainder(dat, divisor)
            if i < numshort:
                dat = dat + [0]
            blocks.append(dat + ecc)
        out = []
        for i in range(len(blocks[0])):
            for j, blk in enumerate(blocks):
                if i != shortlen - ecclen or j >= numshort:
                    out.append(blk[i])
        assert len(out) == raw
        return out

    def _draw_codewords(self, codewords):
        s, i, total = self.size, 0, len(codewords) * 8
        right = s - 1
        while right >= 1:
            if right == 6:
                right = 5
            for vert in range(s):
                for j in range(2):
                    x = right - j
                    upward = ((right + 1) & 2) == 0
                    y = (s - 1 - vert) if upward else vert
                    if not self.isfunc[y][x] and i < total:
                        self.modules[y][x] = (codewords[i >> 3] >> (7 - (i & 7))) & 1 == 1
                        i += 1
            right -= 2

    def _apply_mask(self, mask):
        fn = MASKS[mask]
        for y in range(self.size):
            for x in range(self.size):
                if not self.isfunc[y][x] and fn(x, y):
                    self.modules[y][x] = not self.modules[y][x]

    # -- penalizace (ISO/IEC 18004, 7.8.3) -----------------------------------
    def _penalty(self):
        s, m = self.size, self.modules
        lines = [m[y] for y in range(s)] + [[m[y][x] for y in range(s)] for x in range(s)]
        result = 0
        finder_a = [True, False, True, True, True, False, True, False, False, False, False]
        finder_b = finder_a[::-1]
        for line in lines:
            run = 1
            for i in range(1, s + 1):
                if i < s and line[i] == line[i - 1]:
                    run += 1
                else:
                    if run >= 5:
                        result += 3 + (run - 5)
                    run = 1
            padded = [False] * 4 + list(line) + [False] * 4
            for i in range(len(padded) - 10):
                window = padded[i:i + 11]
                if window == finder_a or window == finder_b:
                    result += 40
        for y in range(s - 1):
            for x in range(s - 1):
                c = m[y][x]
                if c == m[y][x + 1] == m[y + 1][x] == m[y + 1][x + 1]:
                    result += 3
        dark = sum(row.count(True) for row in m)
        total = s * s
        k = (abs(dark * 20 - total * 10) + total - 1) // total - 1
        result += max(k, 0) * 10
        return result

    # -- výstup --------------------------------------------------------------
    def to_svg(self, border=4, dark="#0F3652", light="#FFFFFF", title=""):
        dim = self.size + border * 2
        parts = []
        for y in range(self.size):
            x = 0
            while x < self.size:
                if self.modules[y][x]:
                    start = x
                    while x < self.size and self.modules[y][x]:
                        x += 1
                    parts.append(f"M{start + border} {y + border}h{x - start}v1h-{x - start}z")
                else:
                    x += 1
        t = f"<title>{title}</title>" if title else ""
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {dim} {dim}" '
                f'shape-rendering="crispEdges" role="img">{t}'
                f'<rect width="{dim}" height="{dim}" fill="{light}"/>'
                f'<path fill="{dark}" d="{"".join(parts)}"/></svg>\n')


# ----------------------------------------------- nezávislé zpětné čtení ---
def verify(matrix, ecl_idx):
    """Přečte QR matici jinou cestou než encoder a vrátí dekódovaný text."""
    size = len(matrix)
    ver = (size - 17) // 4
    get = lambda x, y: matrix[y][x]

    # 1) formátová informace – nejbližší platné kódové slovo (Hammingova vzdálenost)
    read_a = [get(8, i) for i in range(6)] + [get(8, 7), get(8, 8), get(7, 8)] + [get(14 - i, 8) for i in range(9, 15)]
    read_b = [get(size - 1 - i, 8) for i in range(8)] + [get(8, size - 15 + i) for i in range(8, 15)]
    val_a = sum(int(b) << i for i, b in enumerate(read_a))
    val_b = sum(int(b) << i for i, b in enumerate(read_b))
    best = None
    for ecl_bits in range(4):
        for mask in range(8):
            code = format_bits(ecl_bits, mask)
            dist = bin(code ^ val_a).count("1") + bin(code ^ val_b).count("1")
            if best is None or dist < best[0]:
                best = (dist, ecl_bits, mask)
    dist, ecl_bits, mask = best
    assert dist == 0, f"formátové bity nesedí (vzdálenost {dist})"
    assert ecl_bits == [v[1] for v in ECL.values()][ecl_idx], "úroveň korekce nesedí"

    # 2) mapa funkčních oblastí – z tabulky ISO pro polohy zarovnávacích vzorů
    iso_align = {1: [], 2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30], 6: [6, 34],
                 7: [6, 22, 38], 8: [6, 24, 42], 9: [6, 26, 46], 10: [6, 28, 50]}
    assert ver in iso_align, "ověření je implementováno pro verze 1–10"
    func = [[False] * size for _ in range(size)]
    def mark(x0, y0, w, h):
        for yy in range(y0, y0 + h):
            for xx in range(x0, x0 + w):
                func[yy][xx] = True
    mark(0, 0, 9, 9)
    mark(size - 8, 0, 8, 9)
    mark(0, size - 8, 9, 8)
    mark(6, 0, 1, size)
    mark(0, 6, size, 1)
    pos = iso_align[ver]
    for ay in pos:
        for ax in pos:
            if not ((ax < 9 and ay < 9) or (ax > size - 9 and ay < 9) or (ax < 9 and ay > size - 9)):
                mark(ax - 2, ay - 2, 5, 5)
    if ver >= 7:
        mark(size - 11, 0, 3, 6)
        mark(0, size - 11, 6, 3)

    # 3) čtení bitů po dvousloupcích zprava, střídavě nahoru/dolů
    bits = []
    cols = [c for c in range(size - 1, 0, -2)]
    cols = [c if c > 6 else c - 1 for c in cols]
    for n, c in enumerate(cols):
        rows = range(size - 1, -1, -1) if n % 2 == 0 else range(size)
        for y in rows:
            for x in (c, c - 1):
                if not func[y][x]:
                    bits.append(get(x, y) ^ MASKS[mask](x, y))
    codewords = [int("".join("1" if b else "0" for b in bits[i:i + 8]), 2) for i in range(0, len(bits) // 8 * 8, 8)]

    # 4) de-interleave a kontrola syndromů S_i = C(α^i) == 0
    numblocks = NUM_ERROR_CORRECTION_BLOCKS[ecl_idx][ver]
    ecclen = ECC_CODEWORDS_PER_BLOCK[ecl_idx][ver]
    total = len(codewords)
    datatotal = total - numblocks * ecclen
    long_count = datatotal % numblocks
    short_len = datatotal // numblocks
    lens = [short_len] * (numblocks - long_count) + [short_len + 1] * long_count
    blocks_d = [[] for _ in range(numblocks)]
    idx = 0
    for i in range(max(lens)):
        for b in range(numblocks):
            if i < lens[b]:
                blocks_d[b].append(codewords[idx]); idx += 1
    blocks_e = [[] for _ in range(numblocks)]
    for i in range(ecclen):
        for b in range(numblocks):
            blocks_e[b].append(codewords[idx]); idx += 1
    alpha = [1]
    for _ in range(ecclen):
        alpha.append(gf_mul(alpha[-1], 2))
    data = []
    for b in range(numblocks):
        cw = blocks_d[b] + blocks_e[b]
        for i in range(ecclen):
            acc = 0
            for c in cw:  # Hornerovo schéma, nejvyšší mocnina první
                acc = gf_mul(acc, alpha[i]) ^ c
            assert acc == 0, f"syndrom bloku {b} nenulový"
        data += blocks_d[b]

    # 5) parsování byte segmentu
    bitstr = "".join(f"{c:08b}" for c in data)
    assert bitstr[:4] == "0100", "očekáván byte mode"
    count_bits = 8 if ver <= 9 else 16
    length = int(bitstr[4:4 + count_bits], 2)
    start = 4 + count_bits
    payload = bytes(int(bitstr[start + 8 * i:start + 8 * i + 8], 2) for i in range(length))
    return payload.decode("utf-8"), ver, mask


def build(url, out, ecl="M", dark="#0F3652", title=""):
    qr = QR(url, ecl)
    decoded, ver, mask = verify(qr.modules, ECL[ecl][0])
    if decoded != url:
        sys.exit(f"CHYBA: zpětně přečtený obsah nesedí:\n{decoded!r}")
    out = pathlib.Path(out)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(qr.to_svg(dark=dark, title=title), encoding="utf-8")
    print(f"OK  {out.relative_to(ROOT).as_posix()}  verze {ver}, maska {mask}, "
          f"{qr.size}x{qr.size} modulů, ověřeno zpětným čtením")
    print(f"    {url}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--all", action="store_true", help="vygenerovat všechny kódy podle tools/qr_targets.json")
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--ecl", default="M", choices=list(ECL))
    ap.add_argument("--dark", default="#0F3652", help="barva modulů – držte ji tmavou kvůli čitelnosti")
    ap.add_argument("--title", default="QR kód: motivacnidarky.cz")
    args = ap.parse_args()

    if args.all:
        for target in json.loads(TARGETS.read_text(encoding="utf-8")):
            build(target["url"], target["out"], args.ecl, target.get("dark", "#111111"), target.get("title", ""))
    else:
        build(args.url, args.out, args.ecl, args.dark, args.title)


if __name__ == "__main__":
    main()
