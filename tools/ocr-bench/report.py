"""汇总 results/ 下的评测结果。用法: python report.py [images|pages]"""

import json
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).parent
KIND = sys.argv[1] if len(sys.argv) > 1 else "images"
ORDER = ["v4_mobile", "v5_mobile", "v5_server", "v6_tiny", "v6_small", "v6_medium"]
SUFFIX = "" if KIND == "images" else f"_{KIND}"

results = {
    n: json.loads((HERE / "results" / f"{n}{SUFFIX}.json").read_text())
    for n in ORDER
    if (HERE / "results" / f"{n}{SUFFIX}.json").exists()
}

cols = [
    ("印刷·清晰", lambda r: r["group"] == "printed" and r["cond"] == "clean"),
    ("印刷·拍照", lambda r: r["group"] == "printed" and r["cond"] == "photo"),
    ("手写风格·清晰", lambda r: r["group"] == "handstyle" and r["cond"] == "clean"),
    ("手写风格·拍照", lambda r: r["group"] == "handstyle" and r["cond"] == "photo"),
    ("全部", lambda r: True),
]
print("CER（字符错误率，越低越好）；括号内为完全正确的图片占比\n")
print(f"{'配置':<11}" + "".join(f"{c:<20}" for c, _ in cols))
for n, d in results.items():
    line = f"{n:<11}"
    for _, f in cols:
        rs = [r["cer"] for r in d["rows"] if f(r)]
        if not rs:
            line += f"{'-':<20}"
            continue
        line += f"{sum(rs) / len(rs) * 100:5.1f}% ({sum(x == 0 for x in rs) / len(rs) * 100:3.0f}%)      "
    print(line)

print("\n速度与资源（线程限制为 2；Apple Silicon 单核比常见云主机快，绝对值偏乐观，只看相对）")
print(f"{'配置':<11}{'中位耗时(s)':<13}{'最慢(s)':<10}{'峰值内存(MB)':<12}")
for n, d in results.items():
    secs = [r["secs"] for r in d["rows"]]
    print(f"{n:<11}{st.median(secs):<13.3f}{max(secs):<10.3f}{d['peak_mb']:<12.0f}")
