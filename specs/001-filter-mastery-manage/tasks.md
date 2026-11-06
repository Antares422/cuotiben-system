# Tasks: 错题的筛选搜索、掌握程度分级、编辑清理与分类管理（迭代 2）

**Input**: [spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、[data-model.md](data-model.md)、[contracts/api.md](contracts/api.md)
**Tests**: 必须。宪法 I：每个任务都是一个"红 → 绿 → 重构"循环，先写测试、亲眼看它因断言失败，再写最少的实现。变异检验用于那些"随实现一并写入、测试一写就通过"的守卫。

> **2026-10-27 修订**（spec v2）：掌握状态布尔 → 五级掌握程度 + 掌握时间（迁移 0002）；新增编辑与清理故事（T056–T068）；容量软提醒；取消 500 题性能抽测（T052 改为容量提醒验证）；录入/编辑表单内联新增学科（T069–T071，FR-036）。任务 ID 保持稳定，未认领未完成的旧任务描述直接更新。

## 约定

- 格式：`- [ ] T### [P?] [US?] 描述（文件）`
- `[P]`：与同阶段其他任务改的文件不同，可并行。其余按顺序做。
- **认领**：开始前在任务编号后写 `@姓名`，如 `- [x] T001 @林亮炜 [US1] …`，**先单独提交并推送**再动手；一个任务只能有一个负责人。规则见 `docs/PROGRESS.md`「怎么分工」。
- 后端命令（在 `backend/`）：`uv run pytest tests/api/<文件>::<用例> -q`；前端命令（在 `frontend/`）：`npx vitest run <文件>`
- 每个故事都可独立验收：做完一个故事，系统仍可运行、可演示。

## Phase 1：数据库版本化与迁移（最优先，一切改表代码的前提）

**目标**：库里有版本记录；`mistake` 表迁移到五级掌握程度结构。
**独立验收**：旧库（迭代 1 创建、带数据，`mastered` 有 true/false）启动后自动登记 `0001` 并升级到 `0002`，数据按映射一条不丢（true→4、false→1、mastered_at 为 NULL）。

- [x] T047 引入 Alembic 与基线迁移 `0001`（= 迭代 1 的表结构）；新库启动后数据库版本为最新（`tests/test_db_version.py`、`migrations/`、`db_version.py`、`pyproject.toml`）
- [x] T048 旧库（`create_all` 创建、没有版本记录、带数据）启动时登记为 `0001`，数据一条不丢
- [x] T049 库的版本比代码新时拒绝启动，并给出明确原因
- [x] T050 升级到最新后的表结构与 ORM 模型一致（改了模型忘写迁移，该测试失败）；变异检验：给模型临时加一列，测试必须失败
- [x] T056 迁移 `0002`：`mistake.mastered`(BOOL) → `mastery_level`(INTEGER NOT NULL DEFAULT 1)，新增 `mastered_at`(DATETIME NULL)；旧数据 true→4、false→1（`migrations/`、`tests/test_migration_0002.py`）；逐行断言映射结果；升级后旧数据一条不丢

**检查点**：`models.py` 可改为新结构（`mastery_level`、`mastered_at`），启动时旧库自动升级，后续所有故事在新结构上做。

## Phase 2：故事 1 后端——筛选与搜索 (P1)

**目标**：`GET /api/mistakes` 支持组合筛选；新增 `GET /api/tags`。
**独立验收**：用接口测试覆盖全部条件及组合，结果与内存中算出的期望完全一致（SC-001）。

- [x] T001 [US1] 按 `subject_id` 筛选，`total` 为筛选后总数（`tests/api/test_mistakes_filter.py`、`services/mistakes.py`、`api/mistakes.py`）
- [x] T002 [US1] 按单个 `tag` 筛选
- [x] T003 [US1] 重复的 `tag` 参数取交集（必须同时具备）
- [x] T004 [US1] 按掌握程度区间筛选：`mastery_min` / `mastery_max`（各 1~5，含端点），不传为不限；`mastery_min > mastery_max` 返回 200 空列表
- [x] T005 [US1] 关键字 `q` 同时搜 `content`、`answer`、`error_reason`
- [x] T006 [US1] `q` 不区分英文大小写；首尾空格忽略；全空白等同没有关键字
- [x] T007 [US1] `q` 含 `%`、`_` 时按普通字符匹配（变异检验：去掉转义，测试必须失败）
- [x] T008 [US1] 四类条件组合取交集，且保持"从新到旧 + 分页"（参数化：枚举条件组合，与 Python 内存计算的期望逐条对照）
- [x] T009 [US1] 未知的 `subject_id`、`tag` 返回 200 与空列表，而不是报错
- [x] T010 [US1] 非法参数 422：`mastery_min=0`、`mastery_max=6`、非整数、`q` 超过 100 字；`errors.py` 的 `FIELD_LABELS` 补 `q`、`mastery_min`、`mastery_max`、`tag`，并让"超出范围/格式不正确"的提示是中文
- [x] T011 [US1] `GET /api/tags`：含 0 次使用的标签、按名称排序、带 `mistake_count`（`tests/api/test_tags.py`、新增 `services/tags.py`、`api/tags.py`，在 `main.py` 注册；一次 `LEFT JOIN … GROUP BY`）

**检查点**：后端筛选完整可用，可用 curl 验证。

## Phase 3：故事 1 前端——筛选栏与列表 (P1)

**独立验收**：quickstart 的"故事 1"全部步骤通过（手机与桌面）。

- [x] T012 [P] [US1] `src/filters.ts`：筛选状态 ⇄ 页面地址查询参数的纯函数（空、多标签、非法掌握程度参数回退为不限）（`tests/filters.test.ts`）
- [x] T013 [P] [US1] `src/api`：`listMistakes` 支持筛选参数（`tag` 重复拼接、关键字编码）、新增 `listTags`（`tests/api-functions.test.ts`）
- [x] T014 [US1] `components/FilterBar.vue`：渲染学科、标签、掌握程度范围（最低/最高两级选择）、关键字输入（`tests/filter-bar.test.ts`）
- [x] T015 [US1] `FilterBar`：选择变化与关键字提交时发出事件；"清除全部"按钮
- [x] T016 [US1] 列表页：筛选变化后请求带参数、重置到第一页，并用 `router.replace` 更新地址（`tests/mistake-list-view.test.ts`）
- [x] T017 [US1] 列表页：从地址还原筛选条件（刷新、进详情再返回都保留）
- [x] T018 [US1] 列表页：有筛选但无结果时显示"没有符合条件的错题"和清除入口，与"本子还是空的"区分
- [x] T019 [US1] 列表页：筛选条件里的学科或标签已不存在时，剔除并提示（FR-010）
- [x] T020 [P] [US1] 样式：手机上筛选栏可折叠，标签用可选择的"笔迹标签"样式；符合 `docs/ui-design.md`

## Phase 4：故事 2——掌握程度分级 (P1)

**目标**：`PUT /api/mistakes/{id}/mastery`；列表与详情都能调整等级，达四级记录掌握时间。
**独立验收**：quickstart 的"故事 2"全部步骤通过。

- [x] T021 [US2] 后端：设置掌握程度（1~5），返回完整错题并更新 `updated_at`；升到四级写入 `mastered_at`（注入时钟，断言为当前时间）（`tests/api/test_mastery.py`、`services/mistakes.py`、`api/mistakes.py`）
- [x] T022 [US2] 后端：降级到三级及以下清空 `mastered_at`；降级再升回按新时刻重记；同级重复设置幂等（`mastered_at` 不动）
- [x] T023 [US2] 后端：错题不存在 404；`level` 缺失或非 1~5 整数 422
- [x] T024 [P] [US2] 前端 `api.setMastery`（`tests/api-functions.test.ts`）
- [x] T025 [US2] `components/MasteryControl.vue`：五级选择；展示掌握时间（≥4 时）；等待期间忙碌并禁用；成功后更新；**失败时保持原等级并提示**（`tests/mastery-control.test.ts`）
- [x] T026 [US2] 列表页接入控件；点击控件**不会**跳转到详情（卡片整张可点，控件必须在其之上）
- [x] T027 [US2] 列表正按掌握程度范围筛选时，调级后不再符合条件的题立即消失、总数减 1
- [x] T028 [US2] 详情页接入控件与掌握时间展示；与列表一致
- [x] T029 [US2] 快速连续点击同一控件只提交一次（变异检验：去掉忙碌守卫，测试必须失败）

**检查点**：故事 1 与故事 2 合起来，复习闭环完整（筛低等级 → 逐题复习调级 → 达四级记时间）。

## Phase 5：故事 3——编辑纠错与清理 (P1)

**目标**：`PATCH /api/mistakes/{id}` 编辑；`DELETE /api/mistakes/{id}` 清理（四级门槛）；容量软提醒。
**独立验收**：quickstart 的"故事 3"全部步骤通过。

**后端**

- [x] T057 [US3] `PATCH /api/mistakes/{id}` 编辑成功：可改内容、答案、错因、学科、标签、原图关联，返回完整错题（`tests/api/test_mistakes_edit.py`、`services/mistakes.py`、`api/mistakes.py`、`schemas.py`）
- [x] T058 [US3] 编辑校验：内容空白 422、学科不存在 422、图片不存在 422；错题不存在 404
- [x] T059 [US3] 编辑不动 `mastery_level`、`mastered_at`、`created_at`，`updated_at` 更新（注入时钟断言）
- [x] T060 [US4] `DELETE /api/mistakes/{id}`：四级及以上删除成功，`data` 为 `null`，`mistake_tag` 关联级联清理，其他错题与标签不受影响（`tests/api/test_mistakes_delete.py`）
- [x] T061 [US4] 低于四级 409：`message` 含当前等级、`data` 为 `{"mastery_level": N}`，该题与关联保持不变；不存在 404
- [x] T067 [US4] `GET /api/mistakes` 响应增加 `overall_total`（不受筛选影响的总数）；筛选状态下 `overall_total` 仍等于全量总数

**前端**

- [x] T062 [P] [US3] `src/api`：`updateMistake`、`deleteMistake`（`tests/api-functions.test.ts`）
- [x] T063 [US3] `views/MistakeEditView.vue`：复用录入表单（抽公共表单组件），载入原值，保存成功跳回详情并显示更新内容（`tests/mistake-edit-view.test.ts`）
- [x] T064 [US3] 详情页"编辑"入口（路由 `/mistakes/:id/edit`）；校验失败显示服务端提示且表单保持已填内容
- [x] T065 [US4] 详情页"删除"：低于四级点击时提示需达到四级（展示服务端 409 原因）；达到四级先二次确认，确认后才请求
- [x] T066 [US4] 删除成功：返回列表、该题消失、总数减 1；删除失败显示提示且该题仍在
- [x] T068 [US4] 列表页容量提醒：`overall_total` > 100 时顶部显示"已超过 100 题，建议清理已熟练的题"横幅（可跳转到 ≥四级筛选）；≤100 不显示（`tests/mistake-list-view.test.ts`）

- [x] T072 [US4] 后端：删除错题后同事务自动删除失去全部引用的标签；编辑换标签导致旧标签失去全部引用时同样清理（`tests/api/test_mistakes_delete.py`、`tests/api/test_mistakes_edit.py`）；清理失败整体回滚（见 research D16）
- [x] T073 [US2] 详情页底部"升级一级"/"降级一级"按钮：五级时升级禁用、一级时降级禁用；调级后掌握时间同步显示（`tests/mistake-detail-view.test.ts`）
- [x] T074 录入页步骤条"拍照"改"录入"（文案与测试同步，upload-view.test.ts）
- [x] T075 chore 演示数据脚本 `backend/scripts/seed_demo.py`：联网下载题目图片写入 `data/images`（下载失败则本地生成占位图），注入前两个默认学科 + 1 个自创学科的演示错题（各掌握程度、标签、掌握时间，总量 >100 演示容量提醒）；可重复运行（先清掉旧的演示数据）

**检查点**：录入错了能改、熟练了能清、题多了有提醒，错题本容量可控。

## Phase 6：故事 4——学科与标签管理 (P2)

**目标**：学科、标签的重命名与删除；管理页。
**独立验收**：quickstart 的"故事 4"全部步骤通过。

**后端**

- [x] T030 [US5] `GET /api/subjects` 每项带 `mistake_count`（`tests/api/test_subjects_manage.py`、`services/subjects.py`）
- [x] T031 [US5] `PATCH /api/subjects/{id}` 重命名成功，所有错题显示新名
- [x] T032 [US5] 学科重命名：改成当前同名返回 200；重名 409 `学科已存在`；空名 422；不存在 404
- [x] T033 [US5] 错误提示按资源区分：`name` 字段在学科里显示"学科名称"、在标签里显示"标签名称"（`errors.py`；先写学科与标签两条断言）
- [x] T034 [US5] `DELETE /api/subjects/{id}`：空学科删除成功，`data` 为 `null`
- [x] T035 [US5] 学科下有错题时 409，`message` 含数量、`data` 为 `{"mistake_count": N}`，学科与错题保持不变
- [x] T036 [US5] `PATCH /api/tags/{id}` 重命名成功，带该标签的错题都显示新名（`tests/api/test_tags.py`、`services/tags.py`）
- [x] T037 [US5] 标签重命名：同名 200；重名 409 `标签已存在`；空名 422；不存在 404
- [x] T038 [US5] `DELETE /api/tags/{id}`：解除关联，错题全部保留，其他字段不变
- [x] T039 [US5] 删除标签中途失败时整体回滚、数据不变（测试里让第二步抛错；变异检验：去掉事务，测试必须失败）

**前端**

- [x] T040 [P] [US5] `src/api`：学科与标签的新增、重命名、删除函数（`createSubject` 等，见 T069；`tests/api-functions.test.ts`）
- [x] T041 [US5] `views/ManageView.vue`：展示学科、标签及使用数；无标签时的空状态（`tests/manage-view.test.ts`）
- [x] T042 [US5] 新增学科：成功后立即出现；空名与重名显示提示
- [x] T043 [US5] 行内重命名（学科、标签）；失败显示服务端提示且保持原样
- [x] T044 [US5] 删除学科：被拒绝时在原处显示原因；成功后消失
- [x] T045 [US5] 删除标签：先二次确认，确认后才请求
- [x] T046 [US5] 路由 `/manage` 与底部导航第三项"管理"（`router.ts`、`App.vue`；`tests/app.test.ts` 的导航断言更新为三项，并断言管理页高亮）
- [x] T069 [P] [US5] `src/api`：`createSubject`（`POST /api/subjects` 封装；`tests/api-functions.test.ts`）
- [x] T070 [US5] 录入页（`UploadView.vue`）学科下拉增加"新增学科"选项：内联输入名称，创建成功后选中新学科且表单已填内容不丢；重名/空白显示服务端提示（`tests/upload-view.test.ts`）
- [x] T071 [US5] 编辑页（`MistakeEditView.vue`）同样支持内联新增学科（依赖 T063、T070 的实现模式）

## Phase 7：收尾

- [ ] T051 真实浏览器按 `quickstart.md` 走完全部步骤（手机尺寸与桌面各一遍），记录结果；发现的问题回到对应任务用 TDD 修
- [ ] T052 容量提醒验证：造 101+ 题数据（可脚本批量插入），确认列表页出现提醒、清理至 100 以内后消失，且列表与筛选不受影响
- [x] T053 同步文档：`docs/architecture.md` §5 数据模型与 §7 接口表、`CLAUDE.md` 的"当前状态"与测试数量、`README.md`（如有变化）
- [x] T054 提交前检查全绿：后端 `ruff check`、`ruff format --check`、`pytest`；前端 `typecheck`、`vitest`、`build`
- [ ] T055 扫描密钥与个人信息 → 按主题拆提交 → 推送分支 → 快进合并到 `main` → 打 `v0.2` 标签并推送 → 远端核对

## 需求覆盖

每条功能需求至少有一个任务（先写测试的那一个）：

| 需求 | 任务 | 需求 | 任务 |
| :--- | :--- | :--- | :--- |
| FR-001 学科筛选 | T001、T014 | FR-018 两处一致 | T028 |
| FR-002 标签多选交集 | T002、T003 | FR-019 编辑字段 | T057 |
| FR-003 程度区间筛选 | T004、T014 | FR-020 编辑校验 | T058、T064 |
| FR-004 关键字 | T005–T007 | FR-021 编辑后更新 | T059、T063 |
| FR-005 条件组合 | T008 | FR-022 编辑失败保持 | T064、T065 |
| FR-006 排序分页总数 | T001、T008、T067 | FR-023 门槛删除 | T060、T061 |
| FR-007 结果一致 | T008 | FR-024 确认与关联清理 | T060、T065 |
| FR-008 无结果空状态 | T018 | FR-025 删除失败提示 | T066 |
| FR-009 条件保留 | T016、T017 | FR-026 容量提醒 | T067、T068 |
| FR-010 失效条件清理 | T009、T019 | FR-027 学科增改删 | T031–T035、T042–T044 |
| FR-011 可见可清除 | T014、T015 | FR-028 标签改名/删除 | T036–T038、T043、T045 |
| FR-012 设置等级 | T021、T025、T026、T028 | FR-029 名称校验 | T032、T033、T037 |
| FR-013 立即体现且持久 | T021、T025 | FR-030 改名后全部显示新名 | T031、T036 |
| FR-014 掌握时间写清 | T021、T022 | FR-031 被占用拒删 | T035、T044 |
| FR-015 时间展示与等级一致 | T025、T028 | FR-032 删标签确认与解除 | T038、T039、T045 |
| FR-016 失败保持原状 | T025 | FR-033 显示使用数 | T011、T030、T041 |
| FR-017 筛选下调级后消失 | T027 | FR-034 各处列表一致 | T011、T041、T042 |
|  |  | FR-035 整理失败提示 | T039、T043 |
| FR-036 表单内联新增学科 | T069–T071 |  |  |
| FR-037 升级/降级按钮 | T073 | FR-021/024 孤儿标签清理 | T072 |

## 依赖与顺序

- **Phase 1（数据库版本化与迁移）必须在所有故事之前完成**：后续所有代码都基于 `mastery_level` / `mastered_at` 新结构（spec v2 修订后由"可随时做"变为最优先）。
- Phase 2 → Phase 3（前端依赖后端筛选与 `/api/tags`）。
- Phase 4 只依赖 Phase 1；Phase 5 依赖 Phase 1（删除门槛读取 `mastery_level`）与 Phase 4 的接口约定，建议按 4 → 5 顺序做。
- Phase 6 只依赖迭代 1 的代码，可与 Phase 4/5 并行（不同人改不同文件）。
- T033 应在 T036 之前完成（标签重命名复用 `name` 字段的提示）。
- Phase 7 最后做。

## 建议的实施策略

1. **最小可演示**：完成 Phase 1 + 2 + 3（故事 1），即可演示"按条件找题"。
2. 再做 Phase 4（故事 2），复习闭环完整。
3. 再做 Phase 5（故事 3），编辑纠错与清理可用。
4. 最后做 Phase 6（故事 4），然后收尾。
5. 每个 Phase 结束都跑一遍检查，保证随时可以停下并提交一个可运行的版本。
