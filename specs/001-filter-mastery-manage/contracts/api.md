# API Contracts: 迭代 2 新增与变更

所有接口遵守统一响应格式：`{"code": <HTTP 状态码>, "message": "...", "data": ...}`。下面的 `data` 只写成功时的内容。

**兼容性说明**（2026-10-27 修订）：`MistakeOut` 用 `mastery_level` / `mastered_at` 取代迭代 1 的 `mastered` 字段，这是对既有响应的**不兼容变更**，由迁移 `0002` 同步处理存量数据（`true→4`、`false→1`）。本迭代尚未对外发布，故可接受；其余变更均为向后兼容（只加字段、加可选参数）。

## 变更：GET /api/mistakes

新增可选查询参数，全部可组合，取交集。

| 参数 | 类型 | 说明 |
| :--- | :--- | :--- |
| `subject_id` | int | 学科 |
| `tag` | string，可重复 | 标签名；多个时必须同时具备 |
| `mastery_min` | int，1~5 | 掌握程度下限（含）；不传为不限 |
| `mastery_max` | int，1~5 | 掌握程度上限（含）；不传为不限；`mastery_min > mastery_max` 得到空列表 |
| `q` | string，最长 100 | 关键字，搜 `content`、`answer`、`error_reason` |
| `page` / `page_size` | int | 同迭代 1 |

- `data.total` 是筛选后的总数；**新增** `data.overall_total`：不受筛选影响的错题总数（容量提醒用，FR-026）。
- 校验失败 → 422（如 `mastery_min=0`、`mastery_max=6`、非整数、`q` 超长）。未知的 `subject_id`、`tag` → 200 空列表。

## 新增：PUT /api/mistakes/{id}/mastery

- 请求：`{"level": 3}`（必填，1~5 整数）
- 200：更新后的完整错题（含 `mastery_level`、`mastered_at`、`updated_at`）。等级从 <4 升到 ≥4 时写入 `mastered_at`；降到 <4 时置 `null`；同级重复设置幂等，不动 `mastered_at`
- 404：`错题不存在`；422：`level` 缺失或不是 1~5 的整数

## 新增：PATCH /api/mistakes/{id}

编辑错题（F6 纠错），校验规则与录入一致。

- 请求：与 `POST /api/mistakes` 相同的字段（`content`、`subject_id` 必填；`answer`、`error_reason`、`tags`、`image_id` 可选）
- 200：更新后的完整错题；`mastery_level`、`mastered_at`、`created_at` 不变，`updated_at` 更新
- 404：`错题不存在`；422：内容为空、学科不存在、图片不存在等（同录入）

## 新增：DELETE /api/mistakes/{id}

清理已熟练的错题（F6/F9）。

- 掌握程度 ≥4：200，`data` 为 `null`；`mistake_tag` 关联行级联清理，原始图片文件保留（与迭代 1 孤儿图片策略一致）
- 掌握程度 <4：409，`message` 为 `掌握程度达到四级后才能清理（当前：N 级）`，`data` 为 `{"mastery_level": N}`；该题保持不变
- 404：`错题不存在`

## 变更：GET /api/subjects

每项增加 `mistake_count`：

```json
{ "items": [{ "id": 2, "name": "数学", "mistake_count": 12 }] }
```

## 新增：PATCH /api/subjects/{id}

- 请求：`{"name": "高中数学"}`
- 200：`{id, name, mistake_count}`；改成当前同名也返回 200
- 404：`学科不存在`；409：`学科已存在`；422：名称为空或超过 50 字

## 新增：DELETE /api/subjects/{id}

- 200：`data` 为 `null`
- 404：`学科不存在`
- 409：`该学科下还有 N 道错题，请先处理这些错题`，`data` 为 `{"mistake_count": N}`；学科与错题保持不变

## 新增：GET /api/tags

- 200：`{"items": [{"id": 1, "name": "函数", "mistake_count": 8}]}`，按名称排序，**包含** `mistake_count` 为 0 的标签

## 新增：PATCH /api/tags/{id}

- 请求：`{"name": "函数与方程"}`
- 200：`{id, name, mistake_count}`；改成当前同名也返回 200
- 404：`标签不存在`；409：`标签已存在`；422：名称为空或超过 50 字

## 新增：DELETE /api/tags/{id}

- 200：`data` 为 `null`；带该标签的错题全部保留，只是不再带这个标签
- 404：`标签不存在`

## 错误字段中文名（`errors.py` 的 `FIELD_LABELS` 需补充）

| 字段 | 中文名 |
| :--- | :--- |
| `q` | 关键字 |
| `mastery_min` | 最低掌握程度 |
| `mastery_max` | 最高掌握程度 |
| `level` | 掌握程度 |
| `tag` | 标签 |
| `subject_id`（已有） | 学科 |
| `name`（已有，学科名称） | 需按资源区分为"学科名称"/"标签名称" |

> 注意：`name` 目前统一映射为"学科名称"。标签重命名会复用这个字段名，需要让提示按资源区分（任务 T033 处理）。
