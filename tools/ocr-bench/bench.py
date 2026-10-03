"""单个 RapidOCR 配置的评测。用法: python bench.py <config> ，结果写入 results/<config>.json

线程限制为 2（intra_op=2, inter_op=1），近似 2 核服务器。注意 Apple Silicon 单核比常见云主机快，
绝对耗时偏乐观，只适合横向比较各配置的相对速度。
"""

import json
import re
import resource
import sys
import time
import unicodedata
from pathlib import Path

from rapidocr import ModelType, OCRVersion, RapidOCR

HERE = Path(__file__).parent
V4, V5, V6 = OCRVersion.PPOCRV4, OCRVersion.PPOCRV5, OCRVersion.PPOCRV6
CONFIGS = {
    "v4_mobile": (V4, ModelType.MOBILE),
    "v5_mobile": (V5, ModelType.MOBILE),
    "v5_server": (V5, ModelType.SERVER),
    "v6_tiny": (V6, ModelType.TINY),
    "v6_small": (V6, ModelType.SMALL),
    "v6_medium": (V6, ModelType.MEDIUM),
}


def normalize(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = s.translate(str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'", "−": "-", "–": "-"}))
    return re.sub(r"\s+", "", s).lower().replace("_", "")  # 填空横线不计入 CER


def levenshtein(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def cer(ref: str, hyp: str) -> float:
    ref, hyp = normalize(ref), normalize(hyp)
    return levenshtein(ref, hyp) / max(len(ref), 1)


def main(name: str, img_dir: str = "images") -> None:
    version, model_type = CONFIGS[name]
    meta = json.loads((HERE / img_dir / "meta.json").read_text())

    t0 = time.perf_counter()
    engine = RapidOCR(
        params={
            "Global.log_level": "warning",
            "Det.ocr_version": version,
            "Det.model_type": model_type,
            "Rec.ocr_version": version,
            "Rec.model_type": model_type,
            "EngineConfig.onnxruntime.intra_op_num_threads": 2,
            "EngineConfig.onnxruntime.inter_op_num_threads": 1,
        }
    )
    load_s = time.perf_counter() - t0

    engine(str(HERE / img_dir / meta[0]["file"]))  # 预热，不计入耗时

    rows = []
    for m in meta:
        t = time.perf_counter()
        out = engine(str(HERE / img_dir / m["file"]))
        secs = time.perf_counter() - t
        hyp = "".join(out.txts) if out.txts else ""
        rows.append({**m, "hyp": hyp, "cer": cer(m["text"], hyp), "secs": secs})

    peak_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024)  # macOS 单位是字节
    out_dir = HERE / "results"
    out_dir.mkdir(exist_ok=True)
    (out_dir / (f"{name}.json" if img_dir == "images" else f"{name}_{img_dir}.json")).write_text(
        json.dumps({"config": name, "load_s": load_s, "peak_mb": peak_mb, "rows": rows}, ensure_ascii=False)
    )
    print(f"{name}: load={load_s:.2f}s peak={peak_mb:.0f}MB n={len(rows)}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "images")
