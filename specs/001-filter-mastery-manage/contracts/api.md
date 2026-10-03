# API Contracts: 迭代 2 新增与变更

所有接口遵守统一响应格式：`{"code": <HTTP 状态码>, "message": "...", "data": ...}`。下面的 `data` 只写成功时的内容。
变更均**向后兼容**：只加字段、加可选参数。

## 变更：GET /api/mistakes

新增可选查询参数，全部可组合，取交集。

| 参数 | 类型 | 说明 |
| :--- | :--- | :--- |
| `subject_id` | int | 学科 |
| `tag` | string，可重复 | 标签名；多个时必须同时具备 |
| `mastered` | bool | `true` 已掌握 / `false` 未掌握；不传为全部 |
| `q` | string，最长 100 | 关键字，搜 `content`、`answer`、`error_reason` |
| `page` / `page_size` | int | 同迭代 1 |

- `data.total` 是筛选后的总数。
- 校验失败 → 422（如 `mastered=maybe`、`q` 超长）。未知的 `subject_id`、`tag` → 200 空列表。

## 新增：PUT /api/mistakes/{id}/mastered

- 请求：`{"mastered": true}`（必填布尔）
- 200：更新后的完整错题（含新的 `mastered`、`updated_at`）
- 404：`错题不存在`；422：`mastered` 缺失或不是布尔

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
| `mastered` | 掌握状态 |
| `tag` | 标签 |
| `subject_id`（已有） | 学科 |
| `name`（已有，学科名称） | 需按资源区分为"学科名称"/"标签名称" |

> 注意：`name` 目前统一映射为"学科名称"。标签重命名会复用这个字段名，需要让提示按资源区分（任务 T033 处理）。
