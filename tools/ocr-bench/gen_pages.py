"""生成整页手机照片（约 3024x4000，接近 1200 万像素）：一页 4 道题。"""

import json
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import gen

OUT = Path(__file__).parent / "pages"
OUT.mkdir(exist_ok=True)


def render_page(questions: list[str], path: str, index: int) -> Image.Image:
    font = ImageFont.truetype(path, 38, index=index)
    page = Image.new("RGB", (1700, 2300), "white")
    d = ImageDraw.Draw(page)
    y = 110
    for q_no, text in enumerate(questions, 1):
        for line in gen.wrap(f"{q_no}. {text}", font, 1500):
            d.text((100, y), line, font=font, fill=(25, 25, 25))
            y += 62
        y += 90
    return page


def main() -> None:
    rng = random.Random(7)
    faces = {k: gen.pick_face(p) for k, (_, p) in gen.FONTS.items()}
    meta = []
    for i in range(12):
        fname = "pingfang" if i % 2 == 0 else "kaiti"
        group, path = gen.FONTS[fname]
        ok = [t for t in gen.TEXTS if gen.covers(fname, path, faces[fname], t)]
        qs = rng.sample(ok, 4)
        page = render_page(qs, path, faces[fname])
        photo = gen.to_photo(page, rng)
        photo = photo.resize((3024, int(photo.height * 3024 / photo.width)), Image.BICUBIC)
        name = f"p{i:02d}_{fname}.jpg"
        photo.save(OUT / name, quality=85)
        truth = "".join(f"{n}.{t}" for n, t in enumerate(qs, 1))
        meta.append({"file": name, "text": truth, "font": fname, "group": group, "cond": "page"})
    (OUT / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    print("pages:", len(meta), "size:", Image.open(OUT / meta[0]["file"]).size)


if __name__ == "__main__":
    main()
