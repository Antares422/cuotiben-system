"""生成 OCR 评测用的合成错题图片。

局限（务必在报告里说明）：
- 文本是我写的典型错题，不是真实照片。
- “手写风格”只是楷体/行楷/手札字库，不是真人手写。
- 画质退化（旋转、模糊、噪声、JPEG）只是对手机拍照的粗略模拟。
"""

import json
import random
from pathlib import Path

import numpy as np
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).parent / "images"
OUT.mkdir(exist_ok=True)

A = "/System/Library/AssetsV2/com_apple_MobileAsset_Font8"
FONTS = {
    "pingfang": ("printed", f"{A}/86ba2c91f017a3749571a82f2c6d890ac7ffb2fb.asset/AssetData/PingFang.ttc"),
    "songti": ("printed", "/System/Library/Fonts/Supplemental/Songti.ttc"),
    "kaiti": ("handstyle", f"{A}/88d6cc32a907955efa1d014207889413890573be.asset/AssetData/Kaiti.ttc"),
    "xingkai": ("handstyle", f"{A}/13b8ce423f920875b28b551f9406bf1014e0a656.asset/AssetData/Xingkai.ttc"),
    "hannotate": ("handstyle", f"{A}/00bfc46ccb002b730e29def5116e0a571fb617d8.asset/AssetData/Hannotate.ttc"),
}

TEXTS = [
    "已知函数 f(x)=x²-4x+3，求 f(x) 在区间 [0,3] 上的最大值和最小值。",
    "下列关于光合作用的叙述，正确的是（  ）\nA. 光反应在叶绿体基质中进行\nB. 暗反应需要光照直接参与\nC. 光合作用释放的氧气来自水\nD. 光合作用产物只有葡萄糖",
    "Choose the best answer: She ______ to the library every Sunday.\nA. go  B. goes  C. going  D. gone",
    "一辆汽车以 20 m/s 的速度行驶，刹车后加速度大小为 5 m/s²，求刹车后 6 s 内的位移。",
    "在△ABC中，∠A=60°，AB=4，AC=6，则BC=____。",
    "已知集合 A={x|x²-3x+2=0}，B={1,2,3}，则 A∩B=（  ）",
    "The mitochondria is the powerhouse of the cell. 线粒体是细胞的“动力车间”。",
    "2H₂ + O₂ = 2H₂O，标准状况下 22.4 L 氢气完全燃烧需要氧气多少摩尔？",
    "计算：(-2)³ + √16 - |-5| ÷ 5 = ____",
    "求极限 lim(x→0) sin x / x 的值。",
    "第12题 答案：C  错误原因：审题不仔细，漏看了“不正确”三个字。",
    "某同学测得小灯泡的额定电压为 2.5 V，电流为 0.3 A，则额定功率 P=UI=0.75 W。",
]


def pick_face(path: str) -> int:
    """TTC 里挑简体中文的那一个字面。"""
    try:
        n = len(TTFont(path, fontNumber=0).reader.__class__ and [0])
    except Exception:
        n = 1
    best = 0
    for i in range(12):
        try:
            tt = TTFont(path, fontNumber=i, lazy=True)
        except Exception:
            break
        name = " ".join(r.toUnicode() for r in tt["name"].names if r.nameID in (1, 4))
        if "SC" in name or "Simplified" in name:
            return i
        best = best
    return best


# 目视检查对照表后确认字形有误的组合（字体, 字符）：
# 行楷把 ∩ 画成 ∪；宋体和手札把 √ 画成对勾。排除它们，避免把字体缺陷算成 OCR 错误。
BAD_GLYPHS = {("xingkai", "∩"), ("songti", "√"), ("hannotate", "√")}


def covers(fname: str, path: str, index: int, text: str) -> bool:
    cmap = TTFont(path, fontNumber=index, lazy=True).getBestCmap()
    font = ImageFont.truetype(path, 44, index=index)
    for c in text:
        if c.isspace():
            continue
        if ord(c) not in cmap or (fname, c) in BAD_GLYPHS:
            return False
        # cmap 有映射但字形可能是空白（宋体的 ² ³ ÷ ₂），必须真的画得出来
        if font.getmask(c).getbbox() is None:
            return False
    return True


def wrap(text: str, font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    lines: list[str] = []
    for para in text.split("\n"):
        cur = ""
        for ch in para:
            if font.getlength(cur + ch) > max_w and cur:
                lines.append(cur)
                cur = ch
            else:
                cur += ch
        lines.append(cur)
    return lines


def render_clean(text: str, path: str, index: int) -> Image.Image:
    font = ImageFont.truetype(path, 40, index=index)
    lines = wrap(text, font, 1000)
    img = Image.new("RGB", (1100, 40 + 62 * len(lines)), "white")
    d = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        d.text((50, 25 + 62 * i), line, font=font, fill=(20, 20, 20))
    return img


def to_photo(img: Image.Image, rng: random.Random) -> Image.Image:
    w, h = img.size
    # 纸面底色 + 一侧光线偏暗
    arr = np.asarray(img).astype(np.float32)
    paper = np.array([236, 232, 224], dtype=np.float32) / 255.0
    arr = arr / 255.0 * paper
    gradient = np.linspace(1.0, rng.uniform(0.80, 0.92), w, dtype=np.float32)[None, :, None]
    arr = arr * gradient
    img = Image.fromarray((arr * 255).clip(0, 255).astype(np.uint8))
    img = img.rotate(rng.uniform(-2.5, 2.5), expand=True, fillcolor=(210, 206, 198), resample=Image.BICUBIC)
    img = img.resize((int(img.width * 0.7), int(img.height * 0.7)), Image.BILINEAR)
    img = img.filter(ImageFilter.GaussianBlur(0.8))
    noise = np.random.default_rng(rng.randint(0, 10**6)).normal(0, 6, (img.height, img.width, 3))
    img = Image.fromarray((np.asarray(img).astype(np.float32) + noise).clip(0, 255).astype(np.uint8))
    return img


def main() -> None:
    rng = random.Random(20261003)
    meta = []
    faces = {k: pick_face(p) for k, (_, p) in FONTS.items()}
    print("faces:", faces)
    for ti, text in enumerate(TEXTS):
        for fname, (group, path) in FONTS.items():
            idx = faces[fname]
            if not covers(fname, path, idx, text):
                print(f"skip text{ti} font={fname}: missing glyphs")
                continue
            clean = render_clean(text, path, idx)
            for cond in ("clean", "photo"):
                img = clean if cond == "clean" else to_photo(clean, rng)
                name = f"t{ti:02d}_{fname}_{cond}.jpg" if cond == "photo" else f"t{ti:02d}_{fname}_{cond}.png"
                if cond == "photo":
                    img.save(OUT / name, quality=55)
                else:
                    img.save(OUT / name)
                meta.append({"file": name, "text": text, "font": fname, "group": group, "cond": cond})
    (OUT / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    print("images:", len(meta))


if __name__ == "__main__":
    main()
