from PIL import Image, ImageDraw, ImageFont

FONT_PATH = "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"

ALIGNMENT_TEST = True


def load_font(path, size):
    font = ImageFont.truetype(font=path, size=size)

    boxes = [font.getbbox(chr(c)) for c in range(32, 128)]
    min_x = min(box[0] for box in boxes)
    min_y = min(box[1] for box in boxes)
    max_x = max(box[2] for box in boxes)
    max_y = max(box[3] for box in boxes)

    assert not hasattr(font, "width")
    assert not hasattr(font, "height")
    font.width = max_x - min_x
    font.height = max_y - min_y

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

    # 10 pixels/column gives 102 columns
    # 11 pixels/column gives 93 columns
    # 12 pixels/column gives 85 columns
    for size in range(10, 20, 2):
        font = load_font(FONT_PATH, size)
        if font.width > 12:
            break
        if font.width < 10:
            continue

        w, h = font.width, font.height
        ox, oy = font.offset
        print(f"font size {size} has {w}x{h} glyphs", end=" => ")
        print(f"{int(1024 / w)}x{int(600 / h)} chars")

        border = GREEN if ALIGNMENT_TEST else BLACK
        img = Image.new("RGB", (1024, 600), border)
        draw = ImageDraw.Draw(img)
        maxrow = img.height // h
        maxcol = img.width // w
        offset_x = (img.width - maxcol * w) // 2
        offset_y = (img.height - maxrow * h) // 2

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

        img.save(f"font-test-{w}x{h}.png")


if __name__ == "__main__":
    main()
