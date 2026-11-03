# Implementation Plan: 错题的筛选搜索、掌握状态与分类管理（迭代 2）

**Branch**: `feat/iteration-2` | **Date**: 2026-10-03（2026-10-27 按 spec v2 修订） | **Spec**: [spec.md](spec.md)

## Summary

在迭代 1 的基础上增加五块能力：①列表按学科、标签（多选取交集）、掌握程度范围（mastery_min/mastery_max）、关键字组合筛选，条件保存在页面地址里；②在列表和详情里按一~五级设置掌握程度，达到四级记录掌握时间（可注入时钟，UTC）；③编辑已保存错题（PATCH），校验规则与录入一致；④清理：掌握程度达四级及以上才可删除（409 + 当前等级），删除需二次确认；⑤新增"管理"页，整理学科和标签；另有容量软提醒（总数 > 100 时列表页提醒清理，软提醒不设硬上限）。
**数据库表结构有变更**（2026-10-27 修订，原"表结构不变"结论作废）：`mistake.mastered` BOOL 改为 `mistake.mastery_level` INTEGER（一~五级），新增 `mastered_at`（UTC，可空）。变更经 Alembic 迁移 `0002` 落地（基线 `0001` = 迭代 1 结构，旧库自动登记后升级；存量 `mastered=true → 4`、`false → 1`，见 research D11）。后端新增标签接口、扩展错题列表的查询参数、新增掌握程度/编辑/删除与学科/标签的重命名删除接口；前端新增筛选栏、掌握程度控件、编辑页、管理页与容量提醒。

## Technical Context

**Language/Version**: Python 3.12（后端）；TypeScript 5.9 + Vue 3（前端）
**Primary Dependencies**: FastAPI、SQLAlchemy 2.0、Pydantic v2；Vue Router、Vitest（沿用迭代 1）；**新增 Alembic**（数据库版本化与迁移 0002，宪法 v1.1.0）
**Storage**: SQLite（沿用；本迭代经 Alembic 迁移 0002 改 `mistake` 表）
**Testing**: pytest + TestClient（后端）；Vitest + Vue Test Utils + 伪造 fetch 的假后端（前端）
**Target Platform**: 手机浏览器优先，兼容桌面浏览器
**Project Type**: Web 应用（`backend/` + `frontend/`，沿用）
**Performance Goals**: 不设性能抽测：容量目标 100 题以内（上限约 200），SQLite 全表扫描在此量级远低于 1 秒（research D2、D15）；保留 SC-002（界面反馈 1 秒内）
**Constraints**: 单机无账号；改表必须经 Alembic 迁移并有迁移测试（宪法 v1.1.0）；掌握时间经注入时钟取 UTC（宪法 I）；删除等破坏性操作二次确认（宪法 V）
**Scale/Scope**: 个人使用，错题容量目标 100 题以内、上限约 200（老师建议，软提醒不强制）；学科十几个，标签几十到上百个

## Constitution Check

*GATE：已对照 `.specify/memory/constitution.md` v1.1.0。设计前通过；设计后复核通过。*

| 原则 | 结论 | 说明 |
| :--- | :--- | :--- |
| I 测试先行 | ✅ | 每个任务都是"先写失败的测试 → 实现"的成对安排；筛选的每种条件、每个拒绝路径、掌握时间的写清时机都有测试（注入时钟固定时间断言） |
| II 统一响应契约 | ✅ | 新接口全部返回 `{code,message,data}`；重名 409、空名 422、学科被占用 409、低于四级删除 409（带当前等级）、不存在 404；删除成功 `data` 为 `null` |
| III 分层 | ✅ | 新增 `TagService`；筛选、调级、编辑、删除逻辑在 `MistakeService`，路由只解析参数；依赖构造函数注入 |
| IV 面向对象 | ✅ | 服务写成类；不引入 `Utils`；不新增接口层（没有第二个实现，不提前抽象） |
| V 失败不阻断，数据不丢 | ✅ | 被占用学科拒绝删除；删标签先二次确认且只解除关联；删题需达四级且二次确认，失败时界面保持原状态（不做乐观更新）；低于四级的删除一律拒绝 |
| VI 范围纪律 | ✅ | 范围变更（F6 提前、F5 五级化、新增 F9）已先更新 PRD v0.2 与本规格；不含 F8（导出）、批量操作、合并标签、回收站、自动清理 |
| 约束：表结构变更必须版本化 | ✅ | 基线 `0001` + 迁移 `0002`（mastered→mastery_level、新增 mastered_at）；迁移测试覆盖「存量数据映射正确」「升级后数据不丢」「结构与模型一致」 |
| VII 移动端优先与可见反馈 | ✅ | 筛选栏手机上可折叠；所有操作有加载态和失败提示；请求全部走封装层 |

**复杂度偏离**：无。

## Project Structure

### Documentation (this feature)

```text
specs/001-filter-mastery-manage/
├── spec.md              # 规格
├── plan.md              # 本文件
├── research.md          # 关键决定与被否决的方案
├── data-model.md        # 数据模型（mistake 表变更，迁移 0002）及查询规则
├── quickstart.md        # 手动验证脚本，对应验收场景
├── contracts/api.md     # 接口契约（新增与变更）
├── tasks.md             # 任务清单
└── checklists/requirements.md
```

### Source Code (repository root)

```text
backend/app/
├── api/
│   ├── mistakes.py        # 变更：列表增加 subject_id/tag/mastery_min/mastery_max/q；新增 PUT /{id}/mastery、PATCH /{id}、DELETE /{id}
│   ├── subjects.py        # 变更：列表带 mistake_count；新增 PATCH /{id}、DELETE /{id}
│   └── tags.py            # 新增：GET /api/tags、PATCH /{id}、DELETE /{id}
├── migrations/            # 新增：Alembic 迁移；0001 = 迭代 1 表结构（基线），0002 = mastery_level/mastered_at
├── db_version.py          # 新增：启动时登记基线、自动升级、拒绝比代码新的库
├── services/
│   ├── mistakes.py        # 变更：筛选查询、set_mastery（维护 mastered_at）、update、delete（四级门槛）
│   ├── subjects.py        # 变更：rename、delete、带计数的列表
│   └── tags.py            # 新增：TagService
├── models.py              # 变更：Mistake.mastered → mastery_level + mastered_at
├── schemas.py             # 变更：MistakeOut（mastery_level、mastered_at、overall_total）、MasteryUpdate、MistakeUpdate、TagOut、SubjectOut.mistake_count、NameUpdate
├── errors.py              # 变更：FIELD_LABELS 增加 q、tag、mastery_min、mastery_max、level 等
└── main.py                # 变更：注册 tags 路由；启动时跑迁移
backend/tests/api/         # 新增：test_mistakes_filter.py、test_mastery.py、test_mistakes_edit.py、
                           #       test_mistakes_delete.py、test_subjects_manage.py、test_tags.py
backend/tests/test_migration_0002.py  # 新增：存量数据映射与结构一致性

frontend/src/
├── api/                   # 变更：mistakes.ts（筛选参数、setMastery、updateMistake、deleteMistake）；新增 tags.ts；subjects 管理函数
├── filters.ts             # 新增：筛选状态与页面地址查询参数互转（纯函数）
├── components/
│   ├── FilterBar.vue      # 新增：学科、标签、掌握程度范围、关键字、清除
│   └── MasteryControl.vue # 新增：五级掌握程度选择（列表与详情共用）
├── views/
│   ├── UploadView.vue         # 变更：学科下拉支持"新增学科"（FR-036）
│   ├── MistakeListView.vue    # 变更：接入筛选栏、掌握程度控件、容量提醒横幅、"没有符合条件"空状态
│   ├── MistakeDetailView.vue  # 变更：掌握程度控件、编辑入口、删除按钮
│   ├── MistakeEditView.vue    # 新增：编辑错题（复用录入表单）；学科下拉支持内联新增学科
│   └── ManageView.vue         # 新增：学科与标签管理
├── router.ts, App.vue     # 变更：新增 /manage、/mistakes/:id/edit 与导航项
└── tests/                 # 新增：filters、filter-bar、mastery-control、mistake-edit-view、manage-view、对应视图测试
```

**Structure Decision**：沿用迭代 1 的前后端分离结构，不新增顶层目录。

## Phase 0：调研（见 research.md）

已决：标签删除不改表结构、搜索用转义后的包含匹配、多标签取交集、筛选条件放页面地址、调级不做乐观更新、非法筛选值的处理方式、掌握程度五级化与迁移映射、掌握时间语义、删除门槛、容量软提醒、不设性能抽测。

## Phase 1：设计（见 data-model.md、contracts/api.md、quickstart.md）

- `mistake` 表变更经迁移 `0002` 落地（基线 `0001`）；新增的是查询规则、调级/编辑/删除的服务层实现。
- 接口新增 9 个、变更 2 个。注意：`MistakeOut` 用 `mastery_level`/`mastered_at` 取代迭代的 `mastered` 字段，这是对既有响应的**不兼容变更**，由迁移 0002 同步处理存量数据与代码，本迭代尚未对外发布故可接受。
- 手动验证脚本覆盖 spec 的全部验收场景。

## 风险与应对

| 风险 | 应对 |
| :--- | :--- |
| 关键字里的 `%`、`_` 被当成通配符，导致误匹配 | 使用转义后的包含匹配，并为 `%`、`_` 单独写测试 |
| 删除标签时先删关联、后删标签，中途失败会留下半成品 | 同一事务内完成；失败整体回滚；写一条"失败后数据不变"的测试 |
| 多条件组合的 SQL 写错导致漏掉或多出结果（SC-001 要求 0 误差） | 用参数化测试枚举条件组合，对照用 Python 在内存里算出的期望结果 |
| 列表里点掌握程度控件会同时触发卡片整体的跳转（卡片整张可点） | 控件层级高于卡片的点击层，并写测试验证点击控件不会跳转 |
| 筛选条件引用了已被删除的学科或标签（FR-010） | 前端加载学科与标签后校验，剔除不存在的条件并提示；后端对未知条件返回空结果而不是报错 |
| 迁移 0002 把存量 `mastered=true` 映射错等级 | 映射规则（true→4、false→1）写入 data-model.md；迁移测试逐行断言映射结果；升级后结构与模型一致由 T050 守卫 |
| `mastered_at` 与等级不同步（代码绕过入口直接改列） | 调级只走 `MistakeService.set_mastery` 一个入口集中维护；测试断言升级/降级/幂等三条路径的时间字段 |
