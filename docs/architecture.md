# 错题本系统 技术架构文档

> 状态：草稿 v0.1 ｜ 日期：2026-10-03 ｜ 对应 PRD v0.1 ｜ 实现范围：迭代 1（F1–F4）

本文档回答"怎么做"，PRD 回答"做什么"。每个重要决定都记录了被否决的备选方案，避免后续反复讨论。

## 1. 目标与约束

| 来源 | 约束 |
| :--- | :--- |
| PRD §2.1 | 单机、个人使用、无账号体系 |
| PRD §5 可用性 | 拍照到生成草稿不超过 3 步；页面响应式，手机浏览器可直接拍照录入 |
| PRD §5 可靠性 | 数据持久化，重启不丢；原始图片可追溯 |
| PRD §5 可维护性 | 前后端分离；输入校验；统一错误格式；后续可接账号体系、VLM |
| PRD §7.1 | OCR 准确率不稳定，识别失败不得阻断保存 |
| 环境 | 候选部署机为 2 核 8G、无 GPU |
| 课程 | 期末需提交源码和安装包；每两周交付一个可运行增量 |

## 2. 技术选型

| 层 | 选择 | 说明 |
| :--- | :--- | :--- |
| 后端 | Python 3.12 + FastAPI | 自带 OpenAPI 文档；OCR 生态最完整 |
| 数据校验 | Pydantic v2 | 请求/响应模型即契约 |
| 数据库 | SQLite + SQLAlchemy 2.0 | 零配置，单文件，符合单机场景 |
| OCR | RapidOCR 3.9+（PP-OCRv6 small，ONNX Runtime），经适配器接入 | 离线、CPU 推理；实测在对比的所有配置中最准，体积约 30 MB。详见 [ocr-engine-selection.md](ocr-engine-selection.md) |
| 前端 | Vue 3 + Vite + TypeScript | 响应式，移动端浏览器可用 |
| 后端测试 | pytest + FastAPI TestClient | 见 §9 |
| 前端测试 | Vitest + Vue Test Utils | 见 §9 |
| 环境管理 | uv（后端）、npm（前端） | |

### 被否决的备选方案

| 决定 | 备选 | 否决理由 |
| :--- | :--- | :--- |
| 后端用 Python | TypeScript | OCR 与小模型的工具链以 Python 为先；TS 的优势（Electron 内嵌后端）只在"直接做桌面端"时才成立 |
| 后端用 Python | Go | OCR 生态最弱，要通过 cgo 调 onnxruntime；本项目没有 Go 擅长的高并发需求 |
| OCR 用 RapidOCR | 0.9B–1B 的 OCR 专用 VLM（PaddleOCR-VL、HunyuanOCR） | 逐 token 生成，官方部署面向 GPU；有第三方实测约 53 秒/页（CPU，未核实原文），2 核无 GPU 上预计更慢（本项目未实测）。列为迭代 2 的对比实验 |
| OCR 用 RapidOCR | EasyOCR | 实测同一数据上字符错误率 18.1%（RapidOCR 1.7%），整页 12.8 秒、峰值内存 9.5 GB，8 GB 服务器会内存不足 |
| OCR 用 RapidOCR | 云端 OCR API | 需要密钥、额度和网络，演示有风险 |
| 数据库用 SQLite | MySQL / PostgreSQL | 单机单用户用不上；多一个服务要部署 |
| 先做 Web | 直接做 Electron | 会让 PRD 的"手机拍照"场景失效；Electron 作为迭代 3 或期末的打包选项（见 §10） |
| 同步 OCR | 异步任务队列 | PP-OCR 在 CPU 上耗时为秒级以内，队列只增加复杂度；前端展示加载态即可 |

## 3. 总体架构

```
┌────────────────────────┐        HTTP/JSON        ┌─────────────────────────────────┐
│  前端 (Vue 3 SPA)       │ ─────────────────────▶ │  后端 (FastAPI)                  │
│  上传页 / 列表页 / 详情页 │ ◀───────────────────── │                                 │
└────────────────────────┘                         │  api/       路由，校验，错误格式   │
                                                   │  services/  业务逻辑（可独立测试） │
                                                   │  ocr/       OcrEngine 适配器      │
                                                   │  db         SQLAlchemy + SQLite  │
                                                   └───────┬─────────────┬───────────┘
                                                           │             │
                                                  data/mistakes.db   data/images/<id>.<ext>
```

分层原则：
- `api` 只做协议转换：解析请求、调用 service、组装响应，不含业务规则。
- `services` 持有业务规则，不依赖 FastAPI，可以直接用 pytest 调用。
- `ocr` 通过 `OcrEngine` 接口隔离引擎；业务代码不 import 任何具体 OCR 库。

## 4. 目录结构

```
backend/
  pyproject.toml
  app/
    main.py              # create_app()，应用工厂
    config.py            # 环境变量配置
    db.py                # engine / session
    models.py            # ORM 模型
    schemas.py           # Pydantic 请求/响应模型
    errors.py            # 统一错误类型与处理器
    api/                 # subjects.py  uploads.py  mistakes.py  images.py
    services/            # mistakes.py  images.py  subjects.py
    ocr/                 # base.py  rapid.py  fake.py
  tests/
frontend/
  src/
    api/                 # 接口调用封装
    views/               # UploadView  MistakeListView  MistakeDetailView
    components/
  tests/
docs/architecture.md
data/                    # 运行时生成，已加入 .gitignore
```

## 5. 数据模型

```
subject(id PK, name UNIQUE NOT NULL)
tag(id PK, name UNIQUE NOT NULL)
mistake(
  id PK,
  content        TEXT NOT NULL,
  answer         TEXT NULL,
  error_reason   TEXT NULL,
  subject_id     FK -> subject.id NOT NULL,
  image_id       TEXT NULL,          -- 对应 data/images/ 下的文件
  mastered       BOOLEAN NOT NULL DEFAULT 0,
  created_at     DATETIME NOT NULL,  -- UTC
  updated_at     DATETIME NOT NULL   -- UTC
)
mistake_tag(mistake_id FK, tag_id FK, PRIMARY KEY(mistake_id, tag_id))
```

约定：
- 首次启动写入默认学科（语文、数学、英语、物理、化学、生物、政治、历史、地理），用户可新增。
- 时间一律存 UTC，接口输出 ISO 8601 并带 `Z` 后缀（可含小数秒）；SQLite 不保存时区，由 `UtcDateTime` 类型在读写时统一处理；业务代码通过可注入的时钟取当前时间，便于测试。
- 保存错题时，`tags` 传名称列表，不存在的标签自动创建，已存在的复用；标签名去除首尾空白、去重、忽略空白项；输出时按名称排序，保证列表与详情顺序一致。
- `mastered` 字段从迭代 1 就建好，F4 详情页要展示它；修改它的接口在迭代 2（F5）。

## 6. OCR 适配器

```python
@dataclass(frozen=True)
class OcrResult:
    status: Literal["ok", "empty", "failed"]
    text: str
    message: str | None = None

class OcrEngine(Protocol):
    def recognize(self, image_bytes: bytes) -> OcrResult: ...
```

- `RapidOcrEngine`：真实实现，按识别出的行从上到下拼接成文本。模型在第一次调用时才加载，避免拖慢启动。模型档位由 `OCR_MODEL_TIER=tiny|small|medium` 选择，默认 `small`；`tiny` 供低配机器使用。
- `FakeOcrEngine`：测试和前端联调用，返回预设文本或指定失败。
- 通过环境变量 `OCR_ENGINE=rapidocr|fake` 选择。
- 适配器内部捕获所有异常并转为 `status="failed"`，**OCR 失败不抛 HTTP 错误**，前端据此提示并允许手动输入（PRD F1 验收标准）。
- 以后接小 VLM 只需新增一个实现，不动业务代码。

## 7. 接口契约

所有路径以 `/api` 开头，请求和响应均为 JSON（上传除外）。

| 方法 | 路径 | 说明 | 迭代 |
| :--- | :--- | :--- | :--- |
| GET | `/api/subjects` | 学科列表 | 1 |
| POST | `/api/subjects` | 新建学科 | 1 |
| POST | `/api/uploads` | 上传图片并 OCR，返回草稿 | 1 |
| GET | `/api/images/{image_id}` | 取原始图片 | 1 |
| POST | `/api/mistakes` | 保存错题 | 1 |
| GET | `/api/mistakes` | 列表，时间倒序，分页 | 1 |
| GET | `/api/mistakes/{id}` | 详情 | 1 |
| GET | `/api/mistakes` 增加 `subject_id`、`tag`（可重复，取交集）、`mastered`、`q` | 筛选与搜索 | 2 |
| PUT | `/api/mistakes/{id}/mastered` | 标记掌握状态 | 2 |
| PATCH / DELETE | `/api/mistakes/{id}` | 编辑 / 删除 | 3 |
| PATCH / DELETE | `/api/subjects/{id}`、`/api/tags/{id}`；GET `/api/tags` | 学科与标签管理 | 2 |

迭代 2 的接口细节、错误码与决策依据见 [specs/001-filter-mastery-manage](../specs/001-filter-mastery-manage/contracts/api.md)；该迭代**不改表结构**，但按宪法 v1.1.0 引入 Alembic 并建立基线版本 `0001`（见该目录 research D10）。

所有响应都使用 §7.1 的统一响应格式，下面的示例只展示 `data` 的内容。

### POST /api/uploads

- 请求：`multipart/form-data`，字段 `file`。
- 校验：按文件内容判断类型（JPEG / PNG / WebP），不信任扩展名；大小上限默认 10 MB。
- 成功 `201`，`data` 为：

```json
{
  "image_id": "3f2a9c...",
  "image_url": "/api/images/3f2a9c...",
  "ocr": { "status": "ok", "text": "已知函数 f(x)=...", "message": null }
}
```

`ocr.status` 为 `empty`（没识别到文字）或 `failed` 时仍返回 `201`，图片已保存，前端提示后让用户手动输入。

### POST /api/mistakes

```json
{
  "content": "必填，非空白",
  "subject_id": 2,
  "answer": null,
  "error_reason": null,
  "tags": ["函数", "单调性"],
  "image_id": "3f2a9c..."
}
```

- `content` 和 `subject_id` 必填；`subject_id` 必须存在（否则 422，字段 `subject_id`）；`image_id` 如提供必须对应已上传的图片（否则 422，字段 `image_id`）。
- 成功返回 `201` 和完整错题对象。

### GET /api/mistakes

- 查询参数：`page`（默认 1）、`page_size`（默认 20，最大 100）。
- `data` 为 `{ "items": [...], "total": 53, "page": 1, "page_size": 20 }`，按 `created_at` 倒序；同一时刻按 `id` 倒序，保证稳定。

### 7.1 统一响应格式

**每个接口都返回同一个外层结构，`code` 与 HTTP 状态码相同：**

```json
{ "code": 201, "message": "created", "data": { "id": 12, "...": "..." } }
```

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `code` | int | 与 HTTP 状态码完全一致 |
| `message` | string | 成功固定为 `ok` / `created`；失败时是可直接展示给用户的中文提示 |
| `data` | object / array / null | 成功时是业务数据；失败时是错误详情（例如校验失败的字段列表），没有则为 `null` |

错误响应示例（校验失败，HTTP 422）：

```json
{
  "code": 422,
  "message": "题目内容不能为空",
  "data": { "fields": [{ "field": "content", "message": "不能为空" }] }
}
```

| code | 场景 |
| :--- | :--- |
| 200 | 成功（含删除，`data` 为 `null`） |
| 201 | 创建成功 |
| 400 | 请求无法解析（如 JSON 格式错误、缺少文件字段） |
| 404 | 错题、图片、学科不存在；路由不存在 |
| 405 | 方法不允许 |
| 409 | 冲突（如学科名重复） |
| 413 | 图片超过大小上限 |
| 415 | 不是支持的图片格式 |
| 422 | 字段缺失或不合法 |
| 500 | 未预期的服务端错误，`message` 固定为通用提示，不泄漏内部细节 |

例外：`GET /api/images/{image_id}` 成功时直接返回图片二进制（浏览器 `<img>` 需要），失败时仍返回上面的统一格式。完整规则见 [development-conventions.md](development-conventions.md)。

## 8. 图片存储

- 文件名为随机 UUID（十六进制）加扩展名，存放在 `DATA_DIR/images/`；数据库只存 `image_id`。
- 读取图片时先校验 `image_id` 符合 `^[0-9a-f]{32}$`，杜绝路径穿越。
- 已知限制：上传后未保存的错题会留下孤儿图片，迭代 1 不清理；后续补定期清理任务。

## 9. 测试策略（TDD）

遵循项目内 `.claude/skills/test-driven-development`：没有失败的测试就不写生产代码。

| 层 | 工具 | 做法 |
| :--- | :--- | :--- |
| service / API | pytest + TestClient | 每个用例使用独立的临时 SQLite 与临时数据目录，用 `FakeOcrEngine` |
| OCR 适配器 | pytest | 真实 RapidOCR 的测试标 `integration`，用 Pillow 现场渲染的文字图片作输入；默认测试不跑它 |
| 前端 | Vitest + Vue Test Utils | 覆盖表单必填校验、OCR 失败降级、列表渲染 |
| 验收 | 手动演示脚本 | 按 PRD 验收标准逐条走一遍 |

每个接口至少包含成功、失败、边界三类测试；PRD 里每条验收标准对应至少一个测试。

## 10. 部署与演进

- **开发**：后端和前端各起一个进程，前端通过代理访问 `/api`。
- **运行**：前端构建后由 FastAPI 提供静态文件，只有一个进程、一个端口；同一局域网内手机浏览器可直接访问。手机拍照使用 `<input type="file" accept="image/*" capture>`，不需要 HTTPS。
- **Electron 预留**：后端只监听本机地址；数据目录由 `DATA_DIR` 配置；前端用相对路径访问接口。这样前后端代码不改，即可封装成 Electron 壳（后端用 PyInstaller 打成 sidecar，数据放用户数据目录）。是否做由迭代 3 的进度决定。
- **迁移与版本**：表结构变更必须有版本（宪法 v1.1.0）。迭代 1 的库没有版本记录；迭代 2 引入 Alembic，以迭代 1 的表结构作为基线版本 `0001`，旧库启动时自动登记。此后每次改表都新增迁移并带测试。
- **扩展点**：OCR 引擎（`OcrEngine`）、账号体系（模型预留 `user_id` 的做法留到真正需要时再加，不提前设计）。

## 11. 非功能需求落地

| PRD 要求 | 落地方式 |
| :--- | :--- |
| 核心接口 ≤ 2 秒 | SQLite 本地读写；列表分页；列表接口不返回图片内容 |
| OCR 有加载态 | 前端上传期间显示进度状态，OCR 同步返回 |
| 3 步内完成录入 | ① 选图/拍照 → ② 核对草稿并补充信息 → ③ 保存；上传后自动 OCR，无需额外点击 |
| 数据不丢 | SQLite 事务；图片写盘成功后才返回 `image_id` |
| 输入校验与统一错误 | Pydantic 校验 + `errors.py` 统一处理器；所有响应使用 §7.1 的 `code/message/data` 格式 |
| 浏览器兼容 | 不使用实验性 API；用标准的文件上传与 fetch |

## 12. 风险

| 风险 | 应对 |
| :--- | :--- |
| 手写、公式识别效果差 | 保留手动编辑。选型评测用的是合成数据，**没有真实手写**，结论有局限（见选型报告 §5）；需要组员拍真实错题照片，用 `tools/ocr-bench` 重跑，迭代 2 再据此决定是否换引擎 |
| 填空横线丢失、倾斜拍照时多行顺序错乱 | 实测中出现（选型报告 §4.4）；前端提示用户核对草稿；后续评估倾斜校正 |
| 整页大图内存占用高（v6 small 处理 1200 万像素约 2.6 GB） | 单进程运行，不开多 worker；上传时缩小图片（待验证）；必要时用 `tiny` 档 |
| RapidOCR 依赖在个别平台安装失败 | 用 `FakeOcrEngine` 保证开发和测试不被阻塞；首次加载模型的耗时在 README 中说明 |
| 一人承担核心开发 | 分层清晰，service 与 API 独立可测，便于组员接手单个模块 |
