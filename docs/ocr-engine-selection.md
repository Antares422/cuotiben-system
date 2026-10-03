# OCR 引擎选型报告

> 日期：2026-10-03 ｜ 对应架构文档 §2、§6、§12 ｜ 评测脚本：[tools/ocr-bench](../tools/ocr-bench/README.md)

## 1. 结论

**采用 RapidOCR 3.9+，使用 PP-OCRv6 small 模型（ONNX Runtime，CPU 推理），通过 `OcrEngine` 适配器接入。**

| 理由 | 数据 |
| :--- | :--- |
| 准确率最好 | 106 张小图上字符错误率（CER）1.7%，在所有测过的配置里最低；整页手机照片上 0.2% |
| 速度够用 | 整页（约 1200 万像素）中位 0.71 秒（2 线程，Apple Silicon，见 §5 的偏乐观说明） |
| 体积小 | 模型 det 9.5 MB + rec 20.3 MB；`rapidocr` 轮子 27 MB；适合 PyInstaller / Electron 打包 |
| 已是库的默认值 | RapidOCR 3.9.0 起默认模型即 PP-OCRv6 small，无需额外配置 |
| 比同类强得多 | EasyOCR 在同一数据上 CER 18.1%，整页 12.8 秒、峰值内存 9.5 GB，在 8 GB 服务器上会内存不足 |

**配置项**：`OCR_MODEL_TIER=tiny|small|medium`，默认 `small`。`tiny` 更快更省内存（CER 3.6%），作为低配机器的退路；`medium` 不推荐（见 §4）。

## 2. 候选与取舍

| 候选 | 是否实测 | 结论 | 依据 |
| :--- | :--- | :--- | :--- |
| **RapidOCR + PP-OCRv6 small** | 是 | **采用** | §4 |
| RapidOCR + PP-OCRv6 tiny | 是 | 备选（低配机器） | CER 3.6%，最快 |
| RapidOCR + PP-OCRv6 medium | 是 | 不采用 | 没有更准，慢 4 倍、多占约 1 GB 内存 |
| RapidOCR + PP-OCRv5 / v4 | 是 | 不采用 | 在本评测里都不如 v6 |
| EasyOCR | 是 | 不采用 | CER 高 10 倍、内存 9.5 GB、安装环境 864 MB |
| PaddleOCR（官方包） | 否 | 不采用 | 与 RapidOCR 用的是同一批 PP-OCR 模型（RapidOCR 官方文档称已对 PaddleOCR 的模型做了统一转换），预期准确率相近（未实测）；但默认依赖 PaddlePaddle，轮子 105–195 MB。官方也支持 onnxruntime 引擎，那样就与 RapidOCR 重合，没有额外好处 |
| Tesseract | 否 | 不采用 | 没有测：需要在你的电脑上安装系统软件，我没有擅自安装。第三方资料称其手写识别明显偏弱（见 §7，二手资料，未核实） |
| OCR 专用小 VLM（PaddleOCR-VL 0.9B、HunyuanOCR 1B） | 否 | 本迭代不采用 | 官方部署面向 GPU；搜索结果里有一份第三方实测称 PaddleOCR-VL 在 Apple M5 Pro 的 CPU 上约 53 秒/页（未能定位原文，仅供参考）。2 核无 GPU 的服务器上预计更慢。列为迭代 2 的对比实验 |
| 云端 OCR API | 否 | 不采用 | 需要密钥和网络，演示有风险，且 PRD 要求单机 |
| 公式识别模型（PP-FormulaNet 58–181M、UniMERNet 107–325M） | 否 | 本迭代不做 | 输出 LaTeX，是另一类模型；PRD 允许 OCR 出错后手动改，公式放到后续迭代评估 |

## 3. 评测方法

- **引擎**：RapidOCR 3.9.2（`onnxruntime` 1.30），6 个配置：v4 mobile、v5 mobile、v5 server、v6 tiny、v6 small、v6 medium。另测 EasyOCR 1.7.2（PyTorch 2.14）。
- **线程**：ONNX Runtime `intra_op=2, inter_op=1`；PyTorch `set_num_threads(2)`，近似 2 核服务器。
- **数据**：12 段典型错题文本（语数英理化，含 `x² √ △ ∠ ∩ ₂ ³` 等符号），用 5 种字体渲染。
  - 印刷体：苹方、宋体。
  - 手写风格：楷体、行楷、手札（只是字体，不是真人手写）。
  - 每张图两种画质：清晰；以及"拍照"（旋转 ±2.5°、纸面光照不均、缩放模糊、噪声、JPEG q55）。
  - 共 106 张 1–5 行的小图（宽约 1100 像素，拍照版缩小到 0.7 倍）。另有 12 张整页照片（3024×4084，每页 4 道题，约 1200 万像素）。
- **指标**：字符错误率 CER = 编辑距离 / 标准答案长度。比较前统一做 NFKC 规范化、去空白、大小写不敏感，并**不计入下划线**。
- **排除了字体本身有缺陷的组合**：目视检查发现行楷把 `∩` 画成 `∪`、宋体的 `² ³ ÷ ₂` 是空白字形、宋体和手札把 `√` 画成对勾。这些组合已排除，否则会把字体缺陷算成 OCR 的错。
- 脚本和随机种子都在 `tools/ocr-bench`，用项目里的脚本重跑 v6 small 复现了同样的数字。

## 4. 结果

### 4.1 小图（106 张，1–5 行，CER，括号内为完全正确占比）

| 配置 | 印刷·清晰 | 印刷·拍照 | 手写风格·清晰 | 手写风格·拍照 | 全部 | 中位耗时 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| v4 mobile | 4.2% (32%) | 9.2% (37%) | 4.8% (24%) | 5.8% (26%) | 5.8% (28%) | 0.41 s |
| v5 mobile | 5.6% (26%) | 11.0% (5%) | 6.0% (18%) | 15.4% (18%) | 9.8% (17%) | 0.42 s |
| v5 server | 5.2% (47%) | 5.7% (58%) | 4.5% (41%) | 4.4% (56%) | 4.8% (50%) | 4.51 s |
| v6 tiny | 1.9% (53%) | 2.3% (42%) | 4.2% (47%) | 4.6% (56%) | 3.6% (50%) | 0.26 s |
| **v6 small** | **0.5% (84%)** | 3.0% (74%) | **1.8% (68%)** | **1.6% (68%)** | **1.7% (72%)** | 0.56 s |
| v6 medium | 0.9% (68%) | 5.2% (74%) | 1.8% (68%) | 1.6% (74%) | 2.2% (71%) | 2.43 s |
| EasyOCR | — | — | — | — | 18.1% (4%) | 0.17 s |

### 4.2 整页手机照片（12 张，3024×4084）

| 配置 | CER | 中位耗时 | 最慢 | 峰值内存 |
| :--- | :--- | :--- | :--- | :--- |
| v4 mobile | 3.6% | 0.62 s | 0.76 s | 2.5 GB |
| v6 tiny | 0.4% | 0.29 s | 0.33 s | 2.1 GB |
| **v6 small** | **0.2%** | **0.71 s** | 0.88 s | 2.6 GB |
| v6 medium | 0.0% | 3.14 s | 3.95 s | 3.7 GB |
| EasyOCR | 19.2% | 12.83 s | 13.79 s | **9.5 GB** |

### 4.3 解读

- **v6 small 是性价比最高的点**：比 tiny 错误少一半，速度只慢 2 倍；比 medium 在小图上更准，速度快 4 倍。medium 在整页上略好（0.0% 对 0.2%），但慢 4 倍、多占 1 GB 内存，不值得。
- **v5 反而不如 v4 / v6**：这是本数据集上的结果，我没有深究原因，也不据此判断 v5 的一般水平。
- **EasyOCR 的错误是真实的识别错误**：抽查样例里"已"被认成"己"、`f` 被认成 `[`、`x²` 被认成 `x?`；单行短文本的 CER 也有 24%，排除了是多行拼接顺序造成的。
- **整页比小图更准**：一个可能的原因是 RapidOCR 默认配置会把图片短边放大到至少 736 像素（`limit_type: min`），宽而矮的小图被放大后变糊；这只是根据配置做的推测，我没有做对照实验去验证。无论原因如何，评测数据对"整页"偏容易，不能直接外推到真实照片。

### 4.4 剩余的主要错误（v6 small）

- **填空横线 `____` 全部丢失**（所有字体、所有配置）。已不计入 CER，但产品上会表现为填空题的空白处不见了，用户需要手动补。
- **倾斜拍照时多行文字阅读顺序错乱**：有一张 `Choose the best answer…` 的拍照图，第二行文字被插进了第一行里（CER 46%）。需要后续评估倾斜校正。
- `x²`、`³` 等上标被读成普通数字，公式结构无法保留。

## 5. 局限（务必当作结论的前提）

1. **没有真实手写**。"手写风格"只是楷体、行楷、手札字库，笔画规整、字距均匀。真人手写、涂改、潦草的识别率会明显更差，本报告无法给出这部分的数字。
2. **文本是我写的**，不是真实错题；拍照退化是粗略模拟，没有透视变形、阴影、手指遮挡、折痕。
3. **Apple Silicon 单核比常见云主机快**，耗时的绝对值偏乐观，只能看配置之间的相对关系。在目标服务器上的真实耗时需要实测。
4. **内存较高**：v6 small 处理 1200 万像素整页时峰值约 2.6 GB。2 核 8 GB 的服务器跑单个进程可以，但不应开多个 worker。可以在上传时先缩小图片来降低（待验证）。
5. 没有实测 Tesseract 和各类 VLM（原因见 §2），这两项只有二手资料。

## 6. 落地与后续

**落地（本迭代）**
- `pyproject.toml` 的 OCR 可选依赖由已停更的 `rapidocr-onnxruntime`（最后版本 1.4.4，2025-01）改为 `rapidocr>=3.9` + `onnxruntime`。
- 新增 `RapidOcrEngine`（适配器），首次识别时才加载模型；用 `OCR_MODEL_TIER` 选择档位，默认 `small`。
- 真实 RapidOCR 的测试标 `integration`，默认不跑。

**后续（需要真实数据）**
1. **请组员各拍 5–10 张真实错题照片**（含手写、拍照角度不正、光线一般的），人工校对标准答案后用 `tools/ocr-bench` 重跑。这是确认本选型最重要的一步。
2. 在目标服务器上实测耗时和内存。
3. 评估倾斜校正对阅读顺序的改善。
4. 迭代 2 做对比实验：小 VLM（PaddleOCR-VL 等）和公式模型，用真实照片的 CER 和耗时决定是否换。

## 7. 来源

核实过的（直接查阅原页面）：
- [rapidocr · PyPI](https://pypi.org/project/rapidocr/)：3.9.2，2026-07-21 发布，Python 3.8–3.13，轮子 27.3 MB，Apache-2.0。
- [rapidocr-onnxruntime · PyPI](https://pypi.org/project/rapidocr-onnxruntime/)：1.4.4，2025-01-17 发布，Python 3.6–3.12。
- [RapidOCR 模型列表](https://rapidai.github.io/RapidOCRDocs/main/model_list/)：支持 PP-OCRv4 / v5 / v6，3.9.0 起默认 v6 small。
- [RapidOCR Releases](https://github.com/RapidAI/RapidOCR/releases)：3.9.0 引入 PP-OCRv6 并作为默认模型。
- [PP-OCRv6 论文](https://arxiv.org/abs/2606.13108)：medium 34.5M 参数、tiny 1.5M；tiny 在 Xeon CPU 上比 PP-OCRv5 mobile 快 3.9 倍。摘要中没有手写数据。
- [PaddleOCR 通用 OCR 流水线文档](https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/OCR.html)：默认 PP-OCRv6 medium，需要 PaddlePaddle，支持 onnxruntime 引擎，支持手写文本。
- [PaddlePaddle · PyPI](https://pypi.org/project/paddlepaddle/)：3.3.1，macOS arm64 轮子约 104.5 MB，Linux x86-64 约 194.8 MB。
- [PP-OCRv5 · Hugging Face](https://huggingface.co/blog/baidu/ppocrv5)：手机版在 Xeon Gold 6271C 上每秒处理 370+ 字符；文中未给出具体手写数字。
- [HunyuanOCR 技术报告](https://arxiv.org/abs/2511.19575) 与 [vLLM 部署页](https://recipes.vllm.ai/tencent/HunyuanOCR)：1B 参数，部署为 vLLM 服务，面向 GPU。
- [UniMERNet](https://arxiv.org/html/2404.15254v1)、[PP-FormulaNet](https://www.alphaxiv.org/abs/2503.18382)：公式识别模型体积（UniMERNet 107M–325M，PP-FormulaNet 58M–181M）。

**二手资料，未核实，仅供参考**（来自搜索结果摘要，我没有打开原文核对数字）：
- 第三方对比称手写识别准确率 PaddleOCR 72.8%、EasyOCR 61.5%、Tesseract 45.2%（如 [GigaGPU 的对比文章](https://gigagpu.com/paddleocr-vs-tesseract-vs-easyocr/)）。
- PaddleOCR-VL 在 Apple M5 Pro CPU 上约 53 秒/页。
- **更正**：我之前在对话里口头引用过"PP-OCRv5 手写中文准确率约 41.7%"，该数字同样来自搜索摘要，我没能在原文中核实，请不要采用。
