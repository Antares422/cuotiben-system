# Tasks: 错题的筛选搜索、掌握状态与分类管理（迭代 2）

**Input**: [spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、[data-model.md](data-model.md)、[contracts/api.md](contracts/api.md)
**Tests**: 必须。宪法 I：每个任务都是一个"红 → 绿 → 重构"循环，先写测试、亲眼看它因断言失败，再写最少的实现。变异检验用于那些"随实现一并写入、测试一写就通过"的守卫。

## 约定

- 格式：`- [ ] T### [P?] [US?] 描述（文件）`
- `[P]`：与同阶段其他任务改的文件不同，可并行。其余按顺序做。
- 后端命令（在 `backend/`）：`uv run pytest tests/api/<文件>::<用例> -q`；前端命令（在 `frontend/`）：`npx vitest run <文件>`
- 每个故事都可独立验收：做完一个故事，系统仍可运行、可演示。

## Phase 1：故事 1 后端——筛选与搜索 (P1)

**目标**：`GET /api/mistakes` 支持组合筛选；新增 `GET /api/tags`。表结构不变。
**独立验收**：用接口测试覆盖全部条件及组合，结果与内存中算出的期望完全一致（SC-002）。

- [ ] T001 [US1] 按 `subject_id` 筛选，`total` 为筛选后总数（`tests/api/test_mistakes_filter.py`、`services/mistakes.py`、`api/mistakes.py`）
- [ ] T002 [US1] 按单个 `tag` 筛选
- [ ] T003 [US1] 重复的 `tag` 参数取交集（必须同时具备）
- [ ] T004 [US1] 按 `mastered` 筛选：`true` / `false` / 不传（全部）
- [ ] T005 [US1] 关键字 `q` 同时搜 `content`、`answer`、`error_reason`
- [ ] T006 [US1] `q` 不区分英文大小写；首尾空格忽略；全空白等同没有关键字
- [ ] T007 [US1] `q` 含 `%`、`_` 时按普通字符匹配（变异检验：去掉转义，测试必须失败）
- [ ] T008 [US1] 四类条件组合取交集，且保持"从新到旧 + 分页"（参数化：枚举条件组合，与 Python 内存计算的期望逐条对照）
- [ ] T009 [US1] 未知的 `subject_id`、`tag` 返回 200 与空列表，而不是报错
- [ ] T010 [US1] 非法参数 422：`mastered=maybe`、`q` 超过 100 字；`errors.py` 的 `FIELD_LABELS` 补 `q`、`mastered`、`tag`，并让"超出范围/格式不正确"的提示是中文
- [ ] T011 [US1] `GET /api/tags`：含 0 次使用的标签、按名称排序、带 `mistake_count`（`tests/api/test_tags.py`、新增 `services/tags.py`、`api/tags.py`，在 `main.py` 注册；一次 `LEFT JOIN … GROUP BY`）

**检查点**：后端筛选完整可用，可用 curl 验证。

## Phase 2：故事 1 前端——筛选栏与列表 (P1)

**独立验收**：quickstart 的"故事 1"全部步骤通过（手机与桌面）。

- [ ] T012 [P] [US1] `src/filters.ts`：筛选状态 ⇄ 页面地址查询参数的纯函数（空、多标签、非法 `status` 回退为全部）（`tests/filters.test.ts`）
- [ ] T013 [P] [US1] `src/api`：`listMistakes` 支持筛选参数（`tag` 重复拼接、关键字编码）、新增 `listTags`（`tests/api-functions.test.ts`）
- [ ] T014 [US1] `components/FilterBar.vue`：渲染学科、标签、状态、关键字输入（`tests/filter-bar.test.ts`）
- [ ] T015 [US1] `FilterBar`：选择变化与关键字提交时发出事件；"清除全部"按钮
- [ ] T016 [US1] 列表页：筛选变化后请求带参数、重置到第一页，并用 `router.replace` 更新地址（`tests/mistake-list-view.test.ts`）
- [ ] T017 [US1] 列表页：从地址还原筛选条件（刷新、进详情再返回都保留）
- [ ] T018 [US1] 列表页：有筛选但无结果时显示"没有符合条件的错题"和清除入口，与"本子还是空的"区分
- [ ] T019 [US1] 列表页：筛选条件里的学科或标签已不存在时，剔除并提示（FR-010）
- [ ] T020 [P] [US1] 样式：手机上筛选栏可折叠，标签用可选择的"笔迹标签"样式；符合 `docs/ui-design.md`

## Phase 3：故事 2——掌握状态 (P1)

**目标**：`PUT /api/mistakes/{id}/mastered`；列表与详情都能标记。
**独立验收**：quickstart 的"故事 2"全部步骤通过。

- [ ] T021 [US2] 后端：标记为已掌握，返回完整错题并更新 `updated_at`（`tests/api/test_mastered.py`、`services/mistakes.py`、`api/mistakes.py`）
- [ ] T022 [US2] 后端：改回未掌握；重复设置同一状态是幂等的
- [ ] T023 [US2] 后端：错题不存在 404；`mastered` 缺失或不是布尔 422
- [ ] T024 [P] [US2] 前端 `api.setMastered`（`tests/api-functions.test.ts`）
- [ ] T025 [US2] `components/MasteryButton.vue`：点击调用接口；等待期间忙碌并禁用；成功后更新；**失败时保持原状态并提示**（`tests/mastery-button.test.ts`）
- [ ] T026 [US2] 列表页接入按钮；点击按钮**不会**跳转到详情（卡片整张可点，按钮必须在其之上）
- [ ] T027 [US2] 列表正按状态筛选时，标记后该题立即消失、总数减 1
- [ ] T028 [US2] 详情页接入按钮；与列表一致
- [ ] T029 [US2] 快速连续点击同一按钮只提交一次（变异检验：去掉忙碌守卫，测试必须失败）

**检查点**：故事 1 与故事 2 合起来，复习闭环完整（筛未掌握 → 标已掌握）。

## Phase 4：故事 3——学科与标签管理 (P2)

**目标**：学科、标签的重命名与删除；管理页。
**独立验收**：quickstart 的"故事 3"全部步骤通过。

**后端**

- [ ] T030 [US3] `GET /api/subjects` 每项带 `mistake_count`（`tests/api/test_subjects_manage.py`、`services/subjects.py`）
- [ ] T031 [US3] `PATCH /api/subjects/{id}` 重命名成功，所有错题显示新名
- [ ] T032 [US3] 学科重命名：改成当前同名返回 200；重名 409 `学科已存在`；空名 422；不存在 404
- [ ] T033 [US3] 错误提示按资源区分：`name` 字段在学科里显示"学科名称"、在标签里显示"标签名称"（`errors.py`；先写学科与标签两条断言）
- [ ] T034 [US3] `DELETE /api/subjects/{id}`：空学科删除成功，`data` 为 `null`
- [ ] T035 [US3] 学科下有错题时 409，`message` 含数量、`data` 为 `{"mistake_count": N}`，学科与错题保持不变
- [ ] T036 [US3] `PATCH /api/tags/{id}` 重命名成功，带该标签的错题都显示新名（`tests/api/test_tags.py`、`services/tags.py`）
- [ ] T037 [US3] 标签重命名：同名 200；重名 409 `标签已存在`；空名 422；不存在 404
- [ ] T038 [US3] `DELETE /api/tags/{id}`：解除关联，错题全部保留，其他字段不变
- [ ] T039 [US3] 删除标签中途失败时整体回滚、数据不变（测试里让第二步抛错；变异检验：去掉事务，测试必须失败）

**前端**

- [ ] T040 [P] [US3] `src/api`：学科与标签的新增、重命名、删除函数（`tests/api-functions.test.ts`）
- [ ] T041 [US3] `views/ManageView.vue`：展示学科、标签及使用数；无标签时的空状态（`tests/manage-view.test.ts`）
- [ ] T042 [US3] 新增学科：成功后立即出现；空名与重名显示提示
- [ ] T043 [US3] 行内重命名（学科、标签）；失败显示服务端提示且保持原样
- [ ] T044 [US3] 删除学科：被拒绝时在原处显示原因；成功后消失
- [ ] T045 [US3] 删除标签：先二次确认，确认后才请求
- [ ] T046 [US3] 路由 `/manage` 与底部导航第三项"管理"（`router.ts`、`App.vue`；`tests/app.test.ts` 的导航断言更新为三项，并断言管理页高亮）

## Phase 5：收尾

- [ ] T047 真实浏览器按 `quickstart.md` 走完全部步骤（手机尺寸与桌面各一遍），记录结果；发现的问题回到对应任务用 TDD 修
- [ ] T048 在 500 道错题数据上抽测筛选与标记的响应时间（SC-001、SC-003、SC-004）；超过 1 秒则回到 research D2 评估索引
- [ ] T049 同步文档：`docs/architecture.md` §7 的接口表、`CLAUDE.md` 的"当前状态"与测试数量、`README.md`（如有变化）
- [ ] T050 提交前检查全绿：后端 `ruff check`、`ruff format --check`、`pytest`；前端 `typecheck`、`vitest`、`build`
- [ ] T051 扫描密钥与个人信息 → 按主题拆提交 → 推送分支 → 快进合并到 `main` → 打 `v0.2` 标签并推送 → 远端核对

## 需求覆盖

每条功能需求至少有一个任务（先写测试的那一个）：

| 需求 | 任务 | 需求 | 任务 |
| :--- | :--- | :--- | :--- |
| FR-001 学科筛选 | T001、T014 | FR-014 立即体现且持久 | T021、T025 |
| FR-002 标签多选交集 | T002、T003 | FR-015 失败保持原状 | T025 |
| FR-003 状态筛选 | T004 | FR-016 筛选下标记后消失 | T027 |
| FR-004 关键字 | T005–T007 | FR-017 两处一致 | T028 |
| FR-005 条件组合 | T008 | FR-018 学科新增/改名/删除 | T031–T035、T042–T044 |
| FR-006 排序分页总数 | T001、T008 | FR-019 标签改名/删除 | T036–T038、T043、T045 |
| FR-007 结果一致 | T008 | FR-020 名称校验 | T032、T033、T037 |
| FR-008 无结果空状态 | T018 | FR-021 改名后全部显示新名 | T031、T036 |
| FR-009 条件保留 | T016、T017 | FR-022 被占用拒删 | T035、T044 |
| FR-010 失效条件清理 | T009、T019 | FR-023 删标签确认与解除 | T038、T039、T045 |
| FR-011 可见可清除 | T014、T015 | FR-024 显示使用数 | T011、T030、T041 |
| FR-012 列表标记 | T021、T026 | FR-025 各处列表一致 | T011、T041、T042 |
| FR-013 详情标记 | T028 | FR-026 整理失败提示 | T039、T043 |

## 依赖与顺序

- Phase 1 → Phase 2（前端依赖后端筛选与 `/api/tags`）。
- Phase 3 与 Phase 4 互相独立，都只依赖迭代 1 的代码；按优先级先做 Phase 3。
- T033 应在 T036 之前完成（标签重命名复用 `name` 字段的提示）。
- Phase 5 最后做。

## 建议的实施策略

1. **最小可演示**：完成 Phase 1 + 2（故事 1），即可演示"按条件找题"。
2. 再做 Phase 3（故事 2），复习闭环完整。
3. 最后做 Phase 4（故事 3），然后收尾。
4. 每个 Phase 结束都跑一遍检查，保证随时可以停下并提交一个可运行的版本。
