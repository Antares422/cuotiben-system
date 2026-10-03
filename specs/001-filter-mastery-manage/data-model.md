# Data Model: 迭代 2

## 结论：表结构不变

迭代 1 的表已满足本迭代全部需要，**没有表结构变更，不需要业务迁移**。

**数据库版本**：按宪法 v1.1.0，本迭代建立版本基线 `0001`（= 下表的现有结构），旧库启动时自动登记，见 research D10。今后任何表结构变更都在 `0001` 之后新增迁移。

| 表 | 本迭代是否变更 | 说明 |
| :--- | :--- | :--- |
| `subject(id, name UNIQUE)` | 否 | 新增重命名、删除；`name` 唯一约束继续兜底 |
| `tag(id, name UNIQUE)` | 否 | 新增重命名、删除 |
| `mistake(…, mastered BOOL DEFAULT 0, updated_at, …)` | 否 | `mastered` 字段迭代 1 已建好；标记时更新 `updated_at` |
| `mistake_tag(mistake_id → mistake ON DELETE CASCADE, tag_id → tag)` | 否 | `tag_id` 外键**没有**级联删除，因此删除标签要先手动删关联行（见 research D1） |

## 约束与规则

| 规则 | 在哪里保证 |
| :--- | :--- |
| 学科名、标签名：去掉首尾空格、不为空、各自范围内不重复 | 请求模型（去空格、非空）+ 数据库唯一约束（并发兜底，捕获后转 409） |
| 重命名为当前同名：视为无变化，返回 200 | `Service.rename`：先比较，相同直接返回 |
| 大小写不同的名称视为不同名称 | SQLite 的 `UNIQUE` 默认区分大小写，保持 |
| 学科下有错题时不能删 | `SubjectService.delete`：先统计，大于 0 抛 `ConflictError`（外键开启，是第二道防线） |
| 删除标签只解除关联 | `TagService.delete`：同一事务内 `DELETE FROM mistake_tag WHERE tag_id=?` 再删 `tag` |
| 失败时数据不变 | 以上操作在一个事务内；异常整体回滚 |

## 查询规则：错题列表筛选

条件之间取交集；全部可选。

| 参数 | 规则 |
| :--- | :--- |
| `subject_id` | `mistake.subject_id = ?`；不存在的值得到空结果 |
| `tag`（可重复） | 对每个标签名各加一个条件"该错题带有这个标签"，取"且"；不存在的标签得到空结果 |
| `mastered` | `true` → 已掌握；`false` → 未掌握；不传 → 全部 |
| `q` | 去首尾空格；空则忽略；否则在 `content`、`answer`、`error_reason` 任一字段上做转义后的、不区分英文大小写的包含匹配 |
| 排序 | `created_at DESC, id DESC`（与迭代 1 一致，保证稳定） |
| 分页与总数 | `total` 是**筛选后**的总数；越界的 `page` 返回空 `items` |

## 派生数据（不落库）

- `subject.mistake_count`：该学科下的错题数。
- `tag.mistake_count`：带该标签的错题数。
- 均由一次 `LEFT JOIN … GROUP BY` 算出，不存储，避免与真实数据不一致。
