# 错题本系统

拍照上传错题 → OCR 自动识别成文字草稿 → 核对补充（学科、答案、错因、知识点标签）→ 保存，之后随时翻看。
广东财经大学《软件项目管理》课程项目。个人单机使用，没有账号体系。

## 运行

需要 Python 3.12（推荐用 [uv](https://docs.astral.sh/uv/)）和 Node.js 18+。

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

打开 <http://127.0.0.1:8000> 即可。数据（数据库和原图）保存在 `backend/data/`。

**不想下载 OCR 模型、只想看界面**：加上 `OCR_ENGINE=fake`，识别结果会是固定的假文字。

**用手机拍照录入**：电脑和手机连同一个 Wi-Fi，启动时加 `--host 0.0.0.0`，手机浏览器访问 `http://<电脑的局域网 IP>:8000`。
注意：系统没有登录，同一网络里的任何人都能访问和修改，只在可信网络里这样用。

配置项见 [backend/.env.example](backend/.env.example)。

## 开发与测试

```bash
cd backend  && uv run ruff check . && uv run ruff format --check . && uv run pytest
cd frontend && npm run typecheck && npm test
```

开发遵循 TDD（先写失败的测试再写实现），规范见 [docs/development-conventions.md](docs/development-conventions.md)。

## 文档

| 文档 | 内容 |
| :--- | :--- |
| **[docs/PROGRESS.md](docs/PROGRESS.md)** | **项目进度：做到哪了、下一步做什么、已知问题** |
| [docs/PRD-错题本系统.md](docs/PRD-错题本系统.md) | 需求、范围、验收标准、迭代计划 |
| [docs/architecture.md](docs/architecture.md) | 技术架构、数据模型、接口契约 |
| [docs/ocr-engine-selection.md](docs/ocr-engine-selection.md) | OCR 引擎选型调研与实测 |
| [docs/development-conventions.md](docs/development-conventions.md) | 开发规范 |
| [docs/course/](docs/course/) | 课程资料：课程介绍、组织方式、成绩评分标准 |
| [CLAUDE.md](CLAUDE.md) | 面向 AI 助手的项目说明 |
