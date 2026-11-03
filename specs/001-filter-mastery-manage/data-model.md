# Data Model: 迭代 2

## 结论：有表结构变更，经 Alembic 迁移 `0002` 落地

2026-10-27 修订：掌握状态由布尔升级为五级掌握程度（老师"掌握程度分级管理"要求），
`mistake` 表变更：

- `mastered` BOOL 删除，改为 `mastery_level` INTEGER NOT NULL DEFAULT 1（一~五级）；
- 新增 `mastered_at` DATETIME NULL（达到四级时记录，降级清空）。

**数据库版本**：按宪法 v1.1.0，基线 `0001` = 迭代 1 的表结构（含 `mastered` BOOL），
`0002` = 上述变更。旧库启动时先登记为 `0001`，再自动升级到 `0002`（见 research D10、D11）。

| 表 | 本迭代是否变更 | 说明 |
| :--- | :--- | :--- |
| `subject(id, name UNIQUE)` | 否 | 新增重命名、删除；`name` 唯一约束继续兜底 |
| `tag(id, name UNIQUE)` | 否 | 新增重命名、删除 |
| `mistake(…, mastery_level INT NOT NULL DEFAULT 1, mastered_at DATETIME NULL, updated_at, …)` | **是（迁移 0002）** | `mastered` BOOL → `mastery_level`；达到四级写 `mastered_at`（UTC）；编辑与调级都更新 `updated_at` |
| `mistake_tag(mistake_id → mistake ON DELETE CASCADE, tag_id → tag)` | 否 | `mistake_id` 的级联删除使删除错题时关联行自动清理；`tag_id` 外键**没有**级联删除，删除标签仍要先手动删关联行（见 research D1） |

## 迁移 0002 的存量数据映射

| 旧值（`mastered`） | 新值（`mastery_level`） | `mastered_at` |
| :--- | :--- | :--- |
| `true`（已掌握） | 4（可清理的"熟练掌握"） | `NULL`（旧数据没有记录过掌握时间） |
| `false` / 默认 | 1 | `NULL` |

选择 true→4 而不是 5：旧的"已掌握"语义更接近"可以清理了"，四级与清理门槛一致；
若映射为 5，会让一批从未真正"完全掌握"的题直接顶格。

迁移测试要求（沿用 T048/T050 的模式）：升级后每行数据按上表映射正确；升级到最新后的
表结构与 ORM 模型一致（改了模型忘写迁移，测试会失败）。

## 约束与规则

| 规则 | 在哪里保证 |
| :--- | :--- |
| 掌握程度在 1~5 之间 | 请求模型（1~5 整数）+ `mastery_level` 列定义；业务层维护 `mastered_at` 同步（见下） |
| 达到四级写掌握时间、降级清空 | `MistakeService.set_mastery`：旧等级 <4 且新等级 ≥4 → 写入时钟时间；新等级 <4 → 置 NULL；同级幂等不动。时间走可注入时钟，UTC（宪法 I） |
| 学科名、标签名：去掉首尾空格、不为空、各自范围内不重复 | 请求模型（去空格、非空）+ 数据库唯一约束（并发兜底，捕获后转 409） |
| 重命名为当前同名：视为无变化，返回 200 | `Service.rename`：先比较，相同直接返回 |
| 大小写不同的名称视为不同名称 | SQLite 的 `UNIQUE` 默认区分大小写，保持 |
| 学科下有错题时不能删 | `SubjectService.delete`：先统计，大于 0 抛 `ConflictError`（外键开启，是第二道防线） |
| 删除标签只解除关联 | `TagService.delete`：同一事务内 `DELETE FROM mistake_tag WHERE tag_id=?` 再删 `tag` |
| 删除错题清理关联、低于四级拒绝 | `MistakeService.delete`：先读等级，<4 抛 `ConflictError`（`data` 带当前等级）；≥4 删除，关联行由外键级联清理 |
| 失败时数据不变 | 以上操作在一个事务内；异常整体回滚 |

## 查询规则：错题列表筛选

条件之间取交集；全部可选。

| 参数 | 规则 |
| :--- | :--- |
| `subject_id` | `mistake.subject_id = ?`；不存在的值得到空结果 |
| `tag`（可重复） | 对每个标签名各加一个条件"该错题带有这个标签"，取"且"；不存在的标签得到空结果 |
| `mastery_min` / `mastery_max` | 掌握程度区间：`mastery_level >= ?` / `mastery_level <= ?`；范围倒置（min > max）得到空结果而不是报错；不传为不限 |
| `q` | 去首尾空格；空则忽略；否则在 `content`、`answer`、`error_reason` 任一字段上做转义后的、不区分英文大小写的包含匹配 |
| 排序 | `created_at DESC, id DESC`（与迭代 1 一致，保证稳定） |
| 分页与总数 | `total` 是**筛选后**的总数；响应同时带 `overall_total`（不受筛选影响的错题总数，用于容量提醒，FR-026）；越界的 `page` 返回空 `items` |

## 派生数据（不落库）

- `subject.mistake_count`：该学科下的错题数。
- `tag.mistake_count`：带该标签的错题数。
- 均由一次 `LEFT JOIN … GROUP BY` 算出，不存储，避免与真实数据不一致。
