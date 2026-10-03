# 错题本系统

广东财经大学《软件项目管理》课程项目。个人使用的错题管理 Web 应用：拍照上传 → OCR 识别生成题目草稿 → 手动核对保存 → 按学科/标签/状态浏览复习。增量开发，每两周交付一个可运行版本参加排位赛，只承诺 P0 功能。

## 文档（改代码前先看对应的文档）

| 文档 | 内容 |
| :--- | :--- |
| `.specify/memory/constitution.md` | **项目宪法（最高优先级）**：七条核心原则、技术与产品约束、开发流程、治理 |
| `PRD-错题本系统.md` | 需求、范围、验收标准、迭代计划 |
| `docs/architecture.md` | 技术选型（含被否决方案）、架构、数据模型、接口契约、部署演进 |
| `docs/ocr-engine-selection.md` | OCR 引擎选型：候选、实测数据、局限、来源 |
| `docs/development-conventions.md` | **响应格式、错误码、分层、测试、前端、Git 规范，必须遵守** |
| `specs/` | 每个迭代的规格、计划、任务（Spec Kit 产物） |
| `.specify/` `.claude/skills/speckit-*` | GitHub Spec Kit（`/speckit-*` 命令） |
| `.claude/skills/test-driven-development` | TDD 流程，开发时使用 |

## 当前状态

- 迭代 1（F1–F4：拍照上传 + OCR、编辑保存、列表、详情）**已完成并在真实浏览器（手机尺寸）里端到端验证过**。
- 后端 72 个快速测试 + 2 个真实 OCR 集成测试；前端 47 个测试；类型检查和构建通过。界面设计说明见 `docs/ui-design.md`。
- **迭代 2（筛选搜索、掌握状态、学科与标签管理）：规格、计划、任务已完成，实现尚未开始。** 入口是 `specs/001-filter-mastery-manage/tasks.md`（51 个任务，按 TDD 逐个做）。
- 未做（迭代 3）：编辑与删除错题（F6）。
- OCR 选型用的是合成数据，**没有真实手写照片**，需要组员提供真实错题照片后用 `tools/ocr-bench` 复测，见 `docs/ocr-engine-selection.md` §5–6。

## 技术栈与整体架构

- 后端：Python 3.12 + FastAPI + SQLAlchemy 2.0 + SQLite，Pydantic v2 做契约。
- OCR：RapidOCR 3.9+（PP-OCRv6 small，ONNX，CPU），通过 `OcrEngine` 适配器接入，业务代码不依赖具体库。选型依据和评测脚本见 `docs/ocr-engine-selection.md`、`tools/ocr-bench/`。
- 前端：Vue 3 + Vite + TypeScript，移动端优先。TypeScript 固定在 5.9（`vue-tsc` 3.x 与 TypeScript 7 不兼容）。
- 单机、无账号。运行时只有一个进程：FastAPI 同时提供 `/api` 和前端静态文件。后续可封装为 Electron（后端用 PyInstaller 打成 sidecar）。

```
前端 (Vue SPA) ──HTTP/JSON──▶ backend/app
                              ├─ api/       路由：解析请求、调用 service、包装响应
                              ├─ services/  业务规则（SubjectService 等类，依赖构造函数注入），不依赖 FastAPI
                              ├─ ocr/       OcrEngine 接口 + RapidOcr / Fake 实现
                              └─ models.py  SQLite（data/mistakes.db，图片在 data/images/）
```

依赖方向只能是 `api → services → models / ocr`。

## 常用命令

后端（在 `backend/` 下）：

```bash
uv sync --extra ocr                          # 安装依赖（含真实 OCR）；只跑测试可省略 --extra ocr
uv run pytest -m "not integration"           # 快速测试（默认）
uv run pytest tests/path.py::test_name -q    # 单个测试
uv run pytest -m integration                 # 需要真实 RapidOCR 的测试
uv run ruff check . && uv run ruff format --check .
OCR_ENGINE=fake uv run uvicorn app.main:create_app --factory --reload   # 开发，用假 OCR
```

提交前必须通过：`uv run ruff check . && uv run ruff format --check . && uv run pytest -m "not integration"`。

前端（在 `frontend/` 下）：

```bash
npm install
npm test                 # Vitest 单元/组件测试
npm run typecheck        # vue-tsc 类型检查
npm run build            # 类型检查 + 构建到 dist/
npm run dev              # 开发服务器，把 /api 代理到 127.0.0.1:8000
```

提交前必须通过：`npm run typecheck && npm test && npm run build`。

运行完整应用（一个进程一个端口）：先 `npm run build`，再在 `backend/` 下 `STATIC_DIR=../frontend/dist uv run uvicorn app.main:create_app --factory --port 8000`。

## 必须遵守的核心规则（完整版见 `docs/development-conventions.md`）

1. **统一响应**：每个接口都返回 `{"code", "message", "data"}`，`code` 必须等于 HTTP 状态码；失败时 `message` 是中文提示，`data` 是错误详情或 `null`。唯一例外是 `GET /api/images/{id}` 成功时返回图片。
2. **校验错误用 422**，请求解析失败用 400，不混用；未预期异常一律 500 且不泄漏细节。
3. **业务错误抛 `AppError` 子类**，只在全局处理器里转成响应；`services` 不 import `fastapi`。
4. **OCR 失败不阻断流程**：适配器把异常转成 `OcrResult(status="failed")`，上传接口仍返回 201，前端提示后让用户手动输入。
5. **TDD**：没有先失败的测试，就不写生产代码。接口测试必须断言完整响应（状态码、`code`、`message`、`data` 结构）。
6. **时间一律 UTC**，接口输出 ISO 8601 带 `Z`；当前时间通过可注入的时钟获取。
7. **上传安全**：按内容校验图片类型，服务端生成文件名，读取前校验 `image_id` 为 32 位十六进制。
8. **范围纪律**：只做当前迭代的 P0；PRD 之外的想法记到 PRD §2.4 或风险表，不顺手实现。
9. **面向对象设计**：service 写成类，依赖（`Session`、`OcrEngine`、时钟）通过构造函数注入；外部能力用 `Protocol` 定义接口并用工厂函数装配；继承只用于 `AppError` 体系和框架基类，其他用组合；禁止 `Utils` 类和构造函数里做 IO；测试替身用 Fake，不用 mock 打补丁。详见 `docs/development-conventions.md` §4。

## 工作方式

- 改接口、数据模型或规范时，同一次提交里更新 `docs/`。
- 提交信息：`<类型>: <中文说明>`，类型为 feat / fix / docs / test / refactor / chore。
- 不提交 `data/`、数据库文件、`.venv/`、`node_modules/`、密钥。
- 遇到文档之间矛盾：宪法 > `docs/development-conventions.md` > 其他文档。发现矛盾要指出来，让用户确认后修正文档，不得带着矛盾继续。
