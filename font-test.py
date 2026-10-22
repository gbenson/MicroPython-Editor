from PIL import Image, ImageDraw, ImageFont

# Noto Sans Mono Regular 15 | 9x16 | 53x30
# - is probably the best
# - though its opening {}()[] are 1px lower than the closers?!
# - its l looks like chromebook terminal/Topax1.3 (or italic in cb emacs)
#   except the Chromebook hints it differently and it looks more solid
#   than PIL renders it.
#
# DejaVu Sans Mono Book 14 | 9x15 | 53x32
# - is probably second ok
# - it's l looks like chromebook emacs/Topaz2.0
# - everything I use has this style of font, *except* the Chromebook
#   (I obviously like this look) but Noto _Sans_ Mono Regular doesn't
#   show in gnome-terminal menus (and Noto Mono Regular looks nasty)

# Noto Mono Regular 16 | 11x17 | 43x28  <- this is the one with the weird "g"
# Noto Mono Regular 14 | 10x15 | 48x32
# Noto Sans Mono Regular 16 | 10x17 | 48x28
# Noto Sans Mono Regular 15 | 9x16 | 53x30 <= closest to 8x16 (topaz) (+NICE!)
# Noto Sans Mono Regular 14 | 10x15 | 48x32
# Noto Sans Mono Regular 13 | 8x13 | 30x36 - on the small side?
# Noto Sans Mono Regular 10 | 6x12 | 80x40 - just about readable


FONT_PATHS = {
    "dejavu-sans-mono-book":
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "liberation-mono-regular":
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "noto-mono-regular":
    "/usr/share/fonts/truetype/noto/NotoMono-Regular.ttf",
    "noto-sans-mono-regular":
    "/usr/share/fonts/truetype/noto/NotoSansMono-Regular.ttf",
}

# 8 pixels wide?
#  - Liberation Mono Regular 11:  8x11                              9x13
#  - Noto Mono Regular 11:        8x12                              9x13
#  - Noto Sans Mono Regular 13:   8x13 (could prob be 14 high) 7x12 9x16
#  - Dejavu Sans Mono Book 13:    8x14                         7x12 9x15

# Noto Sans Mono Regular 13 (8x13) is nice
# Noto Mono Regular 13 (9x13) is nice
# Dejavu Sans Mono Book 13 (8x14) is nice
# Dejavu Sans Mono Book 14 (9x15) is nice

ALIGNMENT_TEST = False  # Render over a grid to check glyph alignment.
LIFESIZE_TEST = False    # Scale output to appear the right size on...
LIFESIZE_PPMM = 3.925   # ...Dell monitor
LIFESIZE_PPMM = 7.9125  # ...Chromebook
LIFESIZE_PPMM = 4.6667  # ...L380

TARGET_SIZE_PX = (480, 480)
TARGET_SIZE_MM = (100, 100)
SCALED_SIZE_PX = tuple(int(d * LIFESIZE_PPMM) for d in TARGET_SIZE_MM)

RESTRICT_FONT_SIZE = None  # Only work with the most promising size.


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


def main():
    with open("additional_documentation/h") as fp:
        lines = list(fp.readlines())

    WHITE = (255, 255, 255)
    RED = (100, 0, 0)
    GREEN = (0, 100, 0)
    BLUE = (0, 0, 100)
    BLACK = (0, 0, 0)

    for font_name, font_path in FONT_PATHS.items():
      font_name = (font_name.replace("-", " ").title()
                   if len(FONT_PATHS) > 1
                   else "font")
      widths = set()
      for size in reversed(range(9, 22)):
        if RESTRICT_FONT_SIZE not in (None, size):
            continue

        font = load_font(font_path, size)

        w, h = font.width, font.height
        if w > 16:
            continue  # too wide to encode 2bpp in one 32-bit word
        if h > 20:
            continue  # my eyes aren't *that* bad!
        if w in widths:
            continue
        widths.add(w)

        ox, oy = font.offset
        print(f"{font_name} size {size} has {w}x{h} glyphs", end=" => ")

        border = GREEN if ALIGNMENT_TEST else BLACK
        img = Image.new("RGB", TARGET_SIZE_PX, border)
        draw = ImageDraw.Draw(img)
        maxrow = img.height // h
        maxcol = img.width // w
        print(f"{maxcol}x{maxrow} chars")
        offset_x = (img.width - maxcol * w) // 2
        offset_y = (img.height - maxrow * h) // 2

        if font_name != font:
            lines[0] = f"{font_name} {size} | {w}x{h} | {maxcol}x{maxrow}"

        for row in range(maxrow):
            y = offset_y + row * h

            if row >= len(lines):
                break
            line = lines[row]

            for col in range(maxcol):
                x = offset_x + col * w

                if ALIGNMENT_TEST:
                    bg = RED if (row ^ col) & 1 else BLUE
                    draw.rectangle((x, y, x+w-1, y+h-1), fill=bg)

                if col >= len(line):
                    continue
                c = line[col]

                if ord(c) < 33:
                    continue
                assert ord(c) < 128

                draw.text((x+ox, y+oy), c, fill=WHITE, font=font)

        if LIFESIZE_TEST:
            img = img.resize(SCALED_SIZE_PX)

        kc_font_name = font_name.lower().replace(" ", "-")
        img.save(f"{kc_font_name}-{size:02}-{w:02}x{h:02}.png")


if __name__ == "__main__":
    main()
