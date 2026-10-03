# Implementation Plan: 错题的筛选搜索、掌握状态与分类管理（迭代 2）

**Branch**: `feat/iteration-2` | **Date**: 2026-10-03 | **Spec**: [spec.md](spec.md)

## Summary

在迭代 1 的基础上增加三块能力：①列表按学科、标签（多选取交集）、掌握状态、关键字组合筛选，条件保存在页面地址里；②在列表和详情里标记"已掌握/未掌握"；③新增"管理"页，整理学科和标签。
**数据库表结构不变**（`mistake.mastered` 字段迭代 1 已建好）：删除标签时在同一事务里先删关联行再删标签，因此本迭代**不引入 Alembic**。后端新增标签接口、扩展错题列表的查询参数、新增掌握状态与学科/标签的重命名删除接口；前端新增筛选栏、标记按钮、管理页。

## Technical Context

**Language/Version**: Python 3.12（后端）；TypeScript 5.9 + Vue 3（前端）
**Primary Dependencies**: FastAPI、SQLAlchemy 2.0、Pydantic v2；Vue Router、Vitest（均沿用迭代 1，无新增依赖）
**Storage**: SQLite（沿用，表结构不变）
**Testing**: pytest + TestClient（后端）；Vitest + Vue Test Utils + 伪造 fetch 的假后端（前端）
**Target Platform**: 手机浏览器优先，兼容桌面浏览器
**Project Type**: Web 应用（`backend/` + `frontend/`，沿用）
**Performance Goals**: 500 道错题下，筛选、标记的响应让用户在 1 秒内看到结果（SC-003、SC-004）
**Constraints**: 单机无账号；不改表结构；不新增依赖；遵守宪法 v1.0.0
**Scale/Scope**: 个人使用，错题数量级为百到千；学科十几个，标签几十到上百个

## Constitution Check

*GATE：已对照 `.specify/memory/constitution.md` v1.0.0。设计前通过；设计后复核通过。*

| 原则 | 结论 | 说明 |
| :--- | :--- | :--- |
| I 测试先行 | ✅ | 每个任务都是"先写失败的测试 → 实现"的成对安排；筛选的每种条件、每个拒绝路径都有测试 |
| II 统一响应契约 | ✅ | 新接口全部返回 `{code,message,data}`；重名 409、空名 422、学科被占用 409、不存在 404；删除成功 `data` 为 `null` |
| III 分层 | ✅ | 新增 `TagService`；筛选逻辑在 `MistakeService`，路由只解析参数；依赖构造函数注入 |
| IV 面向对象 | ✅ | 服务写成类；不引入 `Utils`；不新增接口层（没有第二个实现，不提前抽象） |
| V 失败不阻断，数据不丢 | ✅ | 被占用学科拒绝删除；删标签先二次确认且只解除关联；失败时界面保持原状态（不做乐观更新） |
| VI 范围纪律 | ✅ | 不含 F6（编辑/删除错题）、F8（导出）、批量操作、合并标签、学科转移 |
| VII 移动端优先与可见反馈 | ✅ | 筛选栏手机上可折叠；所有操作有加载态和失败提示；请求全部走封装层 |

**复杂度偏离**：无。

## Project Structure

### Documentation (this feature)

```text
specs/001-filter-mastery-manage/
├── spec.md              # 规格
├── plan.md              # 本文件
├── research.md          # 关键决定与被否决的方案
├── data-model.md        # 数据模型（表结构不变）及查询规则
├── quickstart.md        # 手动验证脚本，对应验收场景
├── contracts/api.md     # 接口契约（新增与变更）
├── tasks.md             # 任务清单
└── checklists/requirements.md
```

### Source Code (repository root)

```text
backend/app/
├── api/
│   ├── mistakes.py        # 变更：列表增加 subject_id/tag/mastered/q；新增 PUT /{id}/mastered
│   ├── subjects.py        # 变更：列表带 mistake_count；新增 PATCH /{id}、DELETE /{id}
│   └── tags.py            # 新增：GET /api/tags、PATCH /{id}、DELETE /{id}
├── services/
│   ├── mistakes.py        # 变更：筛选查询、set_mastered
│   ├── subjects.py        # 变更：rename、delete、带计数的列表
│   └── tags.py            # 新增：TagService
├── schemas.py             # 变更：TagOut、SubjectOut.mistake_count、MasteredUpdate、NameUpdate
├── errors.py              # 变更：FIELD_LABELS 增加 q、tag、mastered 等
└── main.py                # 变更：注册 tags 路由
backend/tests/api/         # 新增：test_mistakes_filter.py、test_mastered.py、
                           #       test_subjects_manage.py、test_tags.py

frontend/src/
├── api/                   # 变更：mistakes.ts（筛选参数、setMastered）；新增 tags.ts；subjects 管理函数
├── filters.ts             # 新增：筛选状态与页面地址查询参数互转（纯函数）
├── components/
│   ├── FilterBar.vue      # 新增：学科、标签、状态、关键字、清除
│   └── MasteryButton.vue  # 新增：列表与详情共用的标记按钮
├── views/
│   ├── MistakeListView.vue    # 变更：接入筛选栏、标记按钮、"没有符合条件"空状态
│   ├── MistakeDetailView.vue  # 变更：标记按钮
│   └── ManageView.vue         # 新增：学科与标签管理
├── router.ts, App.vue     # 变更：新增 /manage 与第三个导航项
└── tests/                 # 新增：filters、filter-bar、mastery-button、manage-view、对应视图测试
```

**Structure Decision**：沿用迭代 1 的前后端分离结构，不新增顶层目录。

## Phase 0：调研（见 research.md）

已决：标签删除不改表结构、搜索用转义后的包含匹配、多标签取交集、筛选条件放页面地址、标记不做乐观更新、非法筛选值的处理方式。

## Phase 1：设计（见 data-model.md、contracts/api.md、quickstart.md）

- 表结构不变；新增的是查询规则与约束的服务层实现。
- 接口新增 7 个、变更 2 个，全部向后兼容（只加字段、加可选参数）。
- 手动验证脚本覆盖 spec 的 23 个验收场景。

## 风险与应对

| 风险 | 应对 |
| :--- | :--- |
| 关键字里的 `%`、`_` 被当成通配符，导致误匹配 | 使用转义后的包含匹配，并为 `%`、`_` 单独写测试 |
| 删除标签时先删关联、后删标签，中途失败会留下半成品 | 同一事务内完成；失败整体回滚；写一条"失败后数据不变"的测试 |
| 多条件组合的 SQL 写错导致漏掉或多出结果（SC-002 要求 0 误差） | 用参数化测试枚举条件组合，对照用 Python 在内存里算出的期望结果 |
| 列表里点"标记"按钮会同时触发卡片整体的跳转（卡片整张可点） | 按钮层级高于卡片的点击层，并写测试验证点击按钮不会跳转 |
| 筛选条件引用了已被删除的学科或标签（FR-010） | 前端加载学科与标签后校验，剔除不存在的条件并提示；后端对未知条件返回空结果而不是报错 |
