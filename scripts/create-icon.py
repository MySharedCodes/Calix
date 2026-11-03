from pathlib import Path
from PIL import Image, ImageDraw

root = Path(__file__).resolve().parents[1]
dest = root / "src-tauri/icons"
dest.mkdir(parents=True, exist_ok=True)
im = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
draw = ImageDraw.Draw(im)
draw.rounded_rectangle((8, 8, 504, 504), radius=76, fill="#087e80")
scale = 512 / 100
draw.arc(tuple(v * scale for v in (19.5, 10.14, 84.5, 75.14)), start=10, end=230,
         fill="white", width=round(7 * scale))
for x, y in ((80.56, 47.68), (33.36, 20.42)):
    draw.ellipse(tuple(v * scale for v in (x - 3.5, y - 3.5, x + 3.5, y + 3.5)), fill="white")
from math import hypot

start, end = (38.09, 83.57), (50, 39.14)
dx, dy = end[0] - start[0], end[1] - start[1]
length = hypot(dx, dy)
nx, ny = -dy / length * 3.5, dx / length * 3.5
draw.polygon([(x * scale, y * scale) for x, y in (
    (start[0] + nx, start[1] + ny), (end[0] + nx, end[1] + ny),
    (end[0] - nx, end[1] - ny), (start[0] - nx, start[1] - ny),
)], fill="white")
for x, y in (start, end):
    draw.ellipse(tuple(v * scale for v in (x - 3.5, y - 3.5, x + 3.5, y + 3.5)), fill="white")
im.save(dest / "icon.png")
im.save(dest / "icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
