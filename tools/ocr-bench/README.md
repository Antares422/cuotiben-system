# OCR 引擎评测脚本

用于比较 RapidOCR 各模型配置（PP-OCRv4 / v5 / v6，tiny / small / medium）的字符错误率、耗时和内存。
结论与数据见 `docs/ocr-engine-selection.md`。

## 运行

在本目录下（需要 Python 3.12；`gen*.py` 依赖 macOS 自带的中文字体）：

```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python rapidocr onnxruntime pillow numpy fonttools
.venv/bin/python gen.py          # 生成 images/（单行小图，约 106 张）
.venv/bin/python gen_pages.py    # 生成 pages/（整页手机照片，12 张）
for c in v4_mobile v5_mobile v5_server v6_tiny v6_small v6_medium; do .venv/bin/python bench.py $c; done
.venv/bin/python report.py
for c in v4_mobile v6_tiny v6_small v6_medium; do .venv/bin/python bench.py $c pages; done
.venv/bin/python report.py pages
```

首次运行会从 ModelScope 下载模型（`v5_server`、`v6_medium` 较大）。

## 用真实照片评测（强烈建议）

合成数据的局限见 `docs/ocr-engine-selection.md` §5。想用组员拍的真实错题照片：
把图片放进一个目录，写一个 `meta.json`（列表，每项含 `file`、`text`（人工校对的标准答案）、`group`、`cond`），
然后 `python bench.py <配置> <目录名>` 即可。

`images/`、`pages/`、`results/`、`.venv/` 都是生成物，已被 `.gitignore` 忽略。
