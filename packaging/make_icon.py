"""Draw the application icon (run once; the results are committed).

Writes ``src/money_manager/ui/assets/app_icon.png`` (window/taskbar icon) and
``packaging/app.ico`` (embedded in MoneyManager.exe, 16–256 px).
Uses Pillow, which Matplotlib already requires.
"""

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
PNG = ROOT / "src" / "money_manager" / "ui" / "assets" / "app_icon.png"
ICO = ROOT / "packaging" / "app.ico"
SIZE = 1024
TOP, BOTTOM = (16, 185, 129), (4, 120, 87)  # theme greens (#10B981 → #047857)


def draw() -> Image.Image:
    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    gradient = Image.new("RGBA", (SIZE, SIZE))
    pixels = gradient.load()
    for y in range(SIZE):
        t = y / (SIZE - 1)
        colour = tuple(round(a + (b - a) * t) for a, b in zip(TOP, BOTTOM, strict=True))
        for x in range(SIZE):
            pixels[x, y] = (*colour, 255)
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle((40, 40, SIZE - 40, SIZE - 40), radius=220, fill=255)
    image.paste(gradient, (0, 0), mask)

    pen = ImageDraw.Draw(image)
    white = (255, 255, 255, 255)
    width, gap, base = 170, 80, 790
    left = (SIZE - (3 * width + 2 * gap)) // 2
    for index, height in enumerate((250, 400, 560)):
        x = left + index * (width + gap)
        pen.rounded_rectangle((x, base - height, x + width, base), radius=48, fill=white)
    return image


def main() -> None:
    icon = draw()
    PNG.parent.mkdir(parents=True, exist_ok=True)
    icon.resize((256, 256), Image.Resampling.LANCZOS).save(PNG)
    icon.save(ICO, sizes=[(s, s) for s in (16, 20, 24, 32, 40, 48, 64, 128, 256)])
    print(f"wrote {PNG} and {ICO}")


if __name__ == "__main__":
    main()
