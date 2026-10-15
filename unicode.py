import unicodedata

from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, field


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

    def _cull(self, *, cutoff: int = 4) -> None:
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
    return unicodedata.east_asian_width(c) in "FHW"


def is_right_to_left(c: str) -> bool:
    return unicodedata.bidirectional(c) in {"R", "AL"}


def is_standalone(c: str) -> bool:
    return unicodedata.combining(c) == 0


_EXCLUDE_BLOCKS = {
    "IPA Extensions",               # dictionary corner
    "Spacing Modifier Letters",     # ditto
}

def probably_not_useful(c: str) -> bool:
    cp = ord(c)
    if cp > 0x0530:
        if cp < 0x2000:
            return True  # so many languages I'll never know
        if cp >= 0x2c00:
            return True
        if cp >= 0x2800:
            # XXX there might be some userful stuff here,
            # but dropping the lot loses 1024 glyphs, so
            # 88 KiB if glyphs are 88 bytes each.
            return True
        # fall through for arrows/symbols/graphics/etc

    block = unicodedata.block(c)
    if block.startswith("Combining "):
        return True  # we don't handle combination

    return block in _EXCLUDE_BLOCKS


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

    if probably_not_useful(c):
        return False

    #if not unicodedata.is_normalized("NFC", c):
    #    print(f"U+{ord(c):04X} {c!r}")

    return True



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
