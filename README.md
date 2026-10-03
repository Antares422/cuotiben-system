# 错题本系统

拍照上传错题 → OCR 自动识别成文字草稿 → 核对补充（学科、答案、错因、知识点标签）→ 保存，之后随时翻看。
广东财经大学《软件项目管理》课程项目。个人单机使用，没有账号体系。

## 运行

需要 Python 3.12（推荐用 [uv](https://docs.astral.sh/uv/)，它会自动装好对应版本）和 **Node.js 22.12 或更高**（前端的 Vite 8 要求 ≥ 20.19，Vitest 5 要求 ≥ 22.12，版本太低测试跑不起来）。

```bash
# 1. 构建前端
cd frontend
npm install
npm run build

# 2. 启动后端（同时托管前端），首次识别时会自动下载约 30 MB 的 OCR 模型
cd ../backend
uv sync --extra ocr
STATIC_DIR=../frontend/dist uv run uvicorn app.main:create_app --factory --port 8000
```

Windows PowerShell 不支持上面的 `变量=值 命令` 写法，改用（未在 Windows 上实测）：

```powershell
$env:STATIC_DIR = "../frontend/dist"; uv run uvicorn app.main:create_app --factory --port 8000
```

打开 <http://127.0.0.1:8000> 即可。数据（数据库和原图）保存在 `backend/data/`。

**不想下载 OCR 模型、只想看界面**：加上 `OCR_ENGINE=fake`，识别结果会是固定的假文字。

**用手机拍照录入**：电脑和手机连同一个 Wi-Fi，启动时加 `--host 0.0.0.0`，手机浏览器访问 `http://<电脑的局域网 IP>:8000`。
注意：系统没有登录，同一网络里的任何人都能访问和修改，只在可信网络里这样用。

配置项见 [backend/.env.example](backend/.env.example)。

## 开发流程（必须遵循 Spec 驱动）

> **没有规格、计划、任务，就不要写代码。** 这是[项目宪法](.specify/memory/constitution.md)的原则 VI，不是建议。

每个迭代都按下面的顺序走，不跳步。每一步都有对应的 Spec Kit 命令，用什么 AI agent 都一样。

| 步骤 | 做什么 | 产物（在 `specs/<序号>-<名称>/`） | 命令 |
| :--- | :--- | :--- | :--- |
| 1. 规格 | 写清楚**做什么、为什么、怎么算做完**，不写技术实现 | `spec.md`、`checklists/` | `/speckit-specify` |
| 2. 计划 | 定技术方案：接口、数据模型、风险，并对照宪法检查 | `plan.md`、`research.md`、`data-model.md`、`contracts/`、`quickstart.md` | `/speckit-plan` |
| 3. 任务 | 拆成可认领、可勾选的任务，每个任务都是一个 TDD 循环 | `tasks.md` | `/speckit-tasks` |
| 4. 实现 | 认领任务，按 TDD 逐个做（先写失败的测试），做完打勾 | 代码 + 测试 | `/speckit-implement` |
| 5. 验收 | 按 `quickstart.md` 在浏览器里走一遍 | — | — |

可选的辅助命令：`/speckit-clarify`（规格有含糊处时提问）、`/speckit-analyze`（检查规格、计划、任务是否一致）、`/speckit-checklist`。

**动手前先问自己**

- 我要做的事，对应当前迭代 `tasks.md` 里的哪个任务？**找不到对应任务，就先别写代码。**
- 想加规格里没有的功能、或要改变已有功能的行为 → **先改规格和任务，再写代码**（范围变更必须先改规格）。
- 范围之外的想法，记到 [PRD](docs/PRD-错题本系统.md) 的"后续迭代方向"或风险表，不要顺手实现。

**不需要新规格的情况**：修复已有功能的 bug（但必须先写一个能复现它的失败测试）；文档笔误；纯样式微调。

**当前在做什么**：看 [docs/PROGRESS.md](docs/PROGRESS.md)，或运行 `tools/progress.sh`。迭代 2 的规格、计划、任务已经写好，在 `specs/001-filter-mastery-manage/`，下一步是从 `tasks.md` 认领任务。

## 开发与测试

```bash
cd backend  && uv run ruff check . && uv run ruff format --check . && uv run pytest
cd frontend && npm run typecheck && npm test
```

开发遵循 TDD（先写失败的测试再写实现），规范见 [docs/development-conventions.md](docs/development-conventions.md)。这些检查也由 CI 在每次推送和合并请求时自动运行，CI 红了不要合并。

## 文档

| 文档 | 内容 |
| :--- | :--- |
| **[docs/PROGRESS.md](docs/PROGRESS.md)** | **项目进度与分工：做到哪了、下一步做什么、怎么认领任务** |
| **[.specify/memory/constitution.md](.specify/memory/constitution.md)** | **项目宪法（最高规则）：七条原则、技术约束、开发流程、治理** |
| [specs/](specs/) | 每个迭代的规格、计划、任务（Spec Kit 产物），先读这里再动手 |
| [docs/PRD-错题本系统.md](docs/PRD-错题本系统.md) | 需求、范围、验收标准、迭代计划 |
| [docs/architecture.md](docs/architecture.md) | 技术架构、数据模型、接口契约 |
| [docs/ocr-engine-selection.md](docs/ocr-engine-selection.md) | OCR 引擎选型调研与实测 |
| [docs/development-conventions.md](docs/development-conventions.md) | 开发规范 |
| [docs/course/](docs/course/) | 课程资料：课程介绍、组织方式、成绩评分标准 |
| [CLAUDE.md](CLAUDE.md) | 面向 AI 助手的项目说明 |
