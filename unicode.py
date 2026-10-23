import unicodedata

from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, field

from PIL import Image, ImageDraw, ImageFont

FONT_NAME = "Noto Sans Mono Regular"
FONT_PATH = "/usr/share/fonts/truetype/dejavu/NotoSansMonoRegular.ttf"
FONT_SIZE = 15

def load_font(path, size):
    font = ImageFont.truetype(font=path, size=size)

    # Get bounds from "Box Drawing" and "Block Elements" ranges.
    boxes = [font.getbbox(chr(c)) for c in range(0x2500, 0x25A0)]

    min_x = min(box[0] for box in boxes)
    min_y = min(box[1] for box in boxes)
    max_x = max(box[2] for box in boxes)
    max_y = max(box[3] for box in boxes)

    assert not hasattr(font, "width")
    assert not hasattr(font, "height")
    font.width = max_x - min_x + 1
    font.height = max_y - min_y + 1

    assert not hasattr(font, "offset")
    font.offset = (-min_x, -min_y)

    return font


@dataclass
class RangeMaker:
    _including: bool | None = None
    _thresholds: list[int] = field(default_factory=list)

    def include(self, c: str, wanted: bool) -> None:
        codepoint = ord(c)
        assert not self._thresholds or codepoint > self._thresholds[-1]

        if wanted is bool(self._including):
            return  # no change

        self._thresholds.append(codepoint)
        self._including = wanted

    # no cutoff: 2,778 glyphs in 109 ranges              238 KiB + 436 bytes
    #  1 cutoff: 2,802 glyphs in 61 ranges [g+24, r-47]  240 KiB + 244 bytes
    #  2 cutoff: 2,824 glyphs in 39 ranges [g+46, r-69]  242 KiB + 156 bytes
    #  3 cutoff: 2,833 glyphs in 33 ranges [g+55, r-75]  243 KiB + 132 bytes
    #  4 cutoff: 2,845 glyphs in 27 ranges [g+67, r-81]  244 KiB + 108 bytes
    #
    # glyph encoding:
    # 32 bits = 16 2-bit pairs = 1 row of up to 16 pixels wide
    # glyphs are 15x22; so 22*4 = 88 bytes/glyph
    #  - pico1 has 264 KiB SRAM, 2 MiB QSPI flash
    #  - pico2 has 520 KiB SRAM, 4 MiB QSPI flash
    # maybe copy hot blocks into SRAM, and leave the rest in flash?
    # (maybe maybe with a LRU cache of some flash ones?)
    #  - Basic Latin           = 95 glyphs; 95*88 = 8,360 bytes
    #  - Latin-1 Supplement = also 95 glyphs = also 8,360 bytes


    # no cutoff =>  661 glyphs in 185 ranges, 56 KiB
    #  cutoff=1 =>  678 glyphs in 151 ranges, 58 KiB
    #  cutoff=2 =>  688 glyphs in 141 ranges, 59 KiB
    #  cutoff=3 =>  736 glyphs in 109 ranges, 63 KiB
    #  cutoff=4 =>  740 glyphs in 107 ranges, 63 KiB
    #  cutoff=5 =>  765 glyphs in  97 ranges, 65 KiB
    #  cutoff=7 =>  814 glyphs in  83 ranges, 69 KiB
    #  cutoff=9 =>  865 glyphs in  71 ranges, 74 KiB
    # cutoff=20 => 1029 glyphs in  49 ranges, 88 KiB
    # cutoff=31 => 1133 glyphs in  41 ranges, 97 KiB

    def _cull(self, *, cutoff: int = 31) -> None:
        print = lambda *args: None   # XXX
        thresholds = self._thresholds
        i = 0
        while i < len(thresholds):
            start = 0 if i == 0 else thresholds[i - 1]
            limit = thresholds[i]
            length = limit - start
            msg = f"{i:3}: if codepoint < {limit}"
            if (included := bool(i & 1)):
                print(f"\x1B[32m{msg}: include\x1B[0m")
                i += 1
                continue
            if length > cutoff:
                print(f"\x1B[33m{msg}: exclude\x1B[0m")
                i += 1
                continue

            # rewind to the included->excluded transition
            i -= 1

            # pop the included->excluded transition
            check = thresholds.pop(i)
            print(f"\x1B[31m{i:3}: if codepoint < {check}: include\x1B[0m")
            assert check == start

            # pop the excluded->included transition
            check = thresholds.pop(i)
            print(f"\x1B[31m{i:3}: if codepoint < {check}: exclude\x1B[0m")
            assert check == limit

    @property
    def ranges(self) -> Iterator[tuple[int | None, int | None]]:
        self._cull()
        num_glyphs = 0
        including = False
        start = 0
        for limit in self._thresholds:
            if including:
                offset = start - num_glyphs
                num_glyphs += (limit - start)
            else:
                offset = None
            yield limit, offset
            start = limit
            including = not including
        yield None, None
        print(num_glyphs, "glyphs", end=" ")


def is_east_asian(c: str) -> bool:
    if unicodedata.east_asian_width(c) in "FHW":
        return True

    # https://en.wikipedia.org/wiki/Plane_(Unicode)#Basic_Multilingual_Plane
    # calls these "CJK scripts and symbols".  Stripping them drops 9 glyphs
    # and 4 ranges.
    # ranges.
    # if ord(c) in range(0x2e80, 0xa000):
    #     return True

    return False


def is_right_to_left(c: str) -> bool:
    if unicodedata.bidirectional(c) in {"R", "AL"}:
        return True

    # https://en.wikipedia.org/wiki/Plane_(Unicode)#Basic_Multilingual_Plane
    # calls these "Semitic abjads and other right-to-left scripts", but they
    # aren't obviously right-to-left.  Stripping them loses 50 glyphs and 14
    # ranges.
    # if ord(c) in range(0x0590, 0x0900):
    #     return True

    return False


def is_standalone(c: str) -> bool:
    return unicodedata.combining(c) == 0


def is_supported(c: str) -> bool:
    block = unicodedata.block(c)
    if block.startswith("Combining "):
        return False  # we don't handle combination

    return True


FONT = load_font(FONT_PATH, FONT_SIZE)
SCRATCH_SIZE = (FONT.width * 5, FONT.height * 5)
SCRATCH_L = FONT.width * 2
SCRATCH_R = FONT.width * 3 - 1
SCRATCH_T = FONT.height * 2
SCRATCH_B = FONT.height * 3 - 1
SCRATCH_BBOX = (SCRATCH_L, SCRATCH_T, SCRATCH_R, SCRATCH_B)
SCRATCH_CROP = (SCRATCH_L, SCRATCH_T, SCRATCH_R + 1, SCRATCH_B + 1)
GLYPH_XY = tuple(p + o for p, o in zip(SCRATCH_BBOX[:2], FONT.offset))


def make_glyph(c: str) -> list[int]:
    img = Image.new("L", SCRATCH_SIZE)
    draw = ImageDraw.Draw(img)
    draw.text(GLYPH_XY, c, fill=255, font=FONT)

    # check it doesn't overflow by more than a couple pixels
    bbox = img.getbbox()
    if bbox is None:
        return None
    l, t, r, b = bbox
    ofl = max(0, SCRATCH_L - l)
    ofr = max(0, r - SCRATCH_R)
    oft = max(0, SCRATCH_T - t)
    ofb = max(0, b - SCRATCH_B)
    if any(overflow > 2 for overflow in (ofl, oft, ofr, ofb)):
        raise ValueError(f"U+{ord(c):04X} {c!r}:", bbox, "overflows", SCRATCH_BBOX)

    img = img.crop(SCRATCH_CROP)
    assert img.width == FONT.width
    assert img.height == FONT.height
    assert img.width < 16

    #img.save("glyph.png")
    pixels = bytes(img.get_flattened_data())
    #print(ord(c), ":", pixels)
    pixel_iter = iter(pixels)
    glyph = []
    for y in range(img.height):
        row = 0
        for x in range(img.width):
            row <<= 2
            row |= (next(pixel_iter) >> 6)
        glyph.append(row)

    if not any(glyph):
        return None  # blank

    return glyph


BLANK = make_glyph(" ")
UNPRINTABLE = make_glyph("\uFFFD")


def should_include(c: str) -> bool:
    if not c.isprintable():
        return False

    if c.isascii():
        return True

    if is_east_asian(c):
        return False

    if is_right_to_left(c):
        return False

    if not is_standalone(c):
        return False

    if not is_supported(c):
        return False

    glyph = make_glyph(c)
    #assert glyph is not None
    if glyph == UNPRINTABLE:
        #print(f"U+{ord(c):04X} {c!r} is unprintable!")
        return False

    if glyph is None:
        print(f"U+{ord(c):04X} {c!r}: glyph is None")
    elif glyph == BLANK:
        print(f"U+{ord(c):04X} {c!r}: glyph is blank")
    else:
        return True

    exit()


def main():
    r = RangeMaker()
    for c in map(chr, range(65536)):
        r.include(c, should_include(c))

    first_in_block = {}
    last_in_block = {}
    blocks = defaultdict(int)

    start = count = 0
    for limit, offset in r.ranges:
        count += 1
        if limit is None:
            print("end of list")
            continue
        print(f"\x1B[33m# range length {limit - start}\x1B[0m")
        if offset is None:
            print(f"if codepoint < 0x{limit:04x}: return None  # not included")
        else:
            print(f"if codepoint < 0x{limit:04x}: return codepoint - {offset}")
            for c in range(start, limit):
                block = unicodedata.block(chr(c))
                blocks[block] += 1
                if block not in first_in_block:
                    first_in_block[block] = c
                last_in_block[block] = c
        start = limit
    print("in", count, "ranges")

    print()
    total_bytes = 0
    for block, first in first_in_block.items():
        assert "combining" not in block.lower(), block
        last = last_in_block[block]
        count = blocks[block]
        size_bytes = count * 88
        total_bytes += size_bytes
        size_kib = size_bytes // 1024
        total_kib = total_bytes // 1024
        print(f"{count:5} {block:<48} U+{first:04X}..U+{last:04X} {size_kib:4} KiB")
    print()
    print(total_kib, "KiB")


if __name__ == "__main__":
    main()
