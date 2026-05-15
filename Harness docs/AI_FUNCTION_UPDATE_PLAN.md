# CodeFlow AI 功能更新计划

> 基于 `CodeFlow AI 功能测试报告.md`
> 方法：Harness Engineering First
> 目标：先立契约、补测试，再实现修复，确保 AI 功能可验收、可回归、错误可解释。

---

## 1. 更新目标

本轮更新不新增 AI 操作类型，重点是把现有 AI 功能从“可用”推进到“可验收、可回归、可诊断”。

需要处理的问题：

| ID | 问题 | 优先级 | 目标状态 |
|---|---|---:|---|
| BUG-001 | `/project/parse` 解析不存在路径时返回空成功项目 | 高 | 无效路径返回 400，不创建空项目 |
| BUG-002 | MiMo Token Plan CN API 超时导致裸 500 | 高 | 超时、认证、限流等错误转成清晰错误信息 |
| BUG-003 | 环境变量加载不一致 | 中 | 已修复，补回归测试锁定 |
| BUG-004 | API 响应字段命名不一致 | 中 | HTTP JSON 统一 camelCase，内部 Python 保持 snake_case |
| TEST-001 | 根目录历史测试依赖缺失的 `example/task-api/src` | 高 | 测试 fixture 修复，全量回归不再假失败 |

---

## 2. Harness Phase 0：更新接口契约

先更新契约，再改实现。契约是后端、前端和测试共同遵守的单一事实来源。

### 2.1 `/project/parse` 路径校验契约

请求：

```json
{
  "root_path": "C:\\bad\\path"
}
```

无效路径响应：

```json
{
  "detail": "Project path does not exist or is not a directory"
}
```

验收规则：

- 路径不存在：返回 `400`
- 路径是文件而不是目录：返回 `400`
- 有效目录：返回 `ParseProjectResponse`
- 无效路径不会写入 project store

### 2.2 Operation 字段命名契约

Python 内部模型继续使用 snake_case：

```python
operation.generated_diffs
operation.error_message
```

HTTP JSON 统一输出 camelCase：

```json
{
  "generatedDiffs": [],
  "errorMessage": null
}
```

验收规则：

- 后端 API 响应不泄漏 `generated_diffs`
- 前端只消费 `generatedDiffs`
- Pydantic alias 支持输入兼容，但输出统一 camelCase

### 2.3 MiMo 错误处理契约

AI 调用错误不直接裸 500 给前端。

建议映射：

| 错误类型 | 后端行为 | 用户提示方向 |
|---|---|---|
| 缺少 token | 操作失败，返回清晰配置错误 | 检查 `XIAOMI_TOKEN_PLAN_CN_API_KEY` |
| 401/403 | 操作失败，返回鉴权错误 | 检查 Token Plan China token |
| 429 | 操作失败，返回限流错误 | 稍后重试 |
| timeout | 操作失败，返回超时错误 | 稍后重试或缩小操作范围 |
| 其他网络错误 | 操作失败，返回连接错误 | 检查网络和服务状态 |

---

## 3. Harness Phase 1：先补自动化测试

先写会失败的测试，再实现修复。这样每个 bug 都能被自动捕获。

### 3.1 新增 `backend/tests/test_project_parse_validation.py`

覆盖：

- 不存在路径返回 `400`
- 文件路径返回 `400`
- 有效目录返回 `200`
- 无效路径不进入 project store

### 3.2 新增 `backend/tests/test_response_aliases.py`

覆盖：

- `Operation.model_dump(by_alias=True)` 输出 `generatedDiffs`
- `/operation/{id}` 响应不包含 `generated_diffs`
- `/operation/{id}/answer` 响应不包含 snake_case 字段
- 前端 TypeScript 类型与 API 响应字段一致

### 3.3 新增 `backend/tests/test_ai_error_handling.py`

使用 mock，不真实调用 MiMo。

覆盖：

- mock timeout，断言返回可读超时错误
- mock 401/403，断言返回鉴权错误
- mock 429，断言返回限流错误
- mock 网络异常，断言返回连接错误
- 操作状态和 `errorMessage` 一致

### 3.4 扩展 `backend/tests/test_mimo_client.py`

已有测试保留，并补充：

- `.env.example` 中的变量能被 `Settings` 识别
- `MIMO_API_TIMEOUT_SECONDS` 默认值不低于 120 秒
- 可选 live smoke test 继续默认跳过，需要手动设置：

```powershell
cd backend
$env:RUN_MIMO_LIVE_TEST='1'
pytest tests/test_mimo_client.py -q
```

### 3.5 修复根目录历史测试 fixture

当前根目录 `pytest tests/ -q` 失败的根因是缺少 `example/task-api/src`。

推荐方案：把历史 phase 测试改用现有 `example/TestProject`，避免维护两套示例项目。

验收：

```powershell
pytest tests/ -q
```

不再因为缺失 fixture 失败。

---

## 4. Harness Phase 2：实现修复

### 4.1 修复 BUG-001：路径校验

修改位置建议：

- `backend/src/routers/project.py`
- 或项目解析服务入口

实现要点：

- 在调用 parser 前检查 `root_path`
- `not exists` 或 `not dir` 时抛出 `HTTPException(status_code=400, detail=...)`
- 不创建空 `ParsedProject`

### 4.2 修复 BUG-004：字段命名统一

修改位置建议：

- `backend/src/models/domain.py`
- `backend/src/routers/operation.py`
- `frontend/src/types/index.ts`
- `frontend/src/services/api.ts`

实现要点：

- Pydantic response 使用 alias 输出
- 前端只使用 camelCase
- 后端内部逻辑仍使用 snake_case
- 增加测试防止后续混用

### 4.3 加固 BUG-002：MiMo 错误处理

修改位置建议：

- `backend/src/services/ai/mimo.py`
- `backend/src/services/ai/generator.py`
- `backend/src/routers/operation.py`
- `frontend/src/hooks/useOperation.ts`
- `frontend/src/components/panels/AIConversation.tsx`

实现要点：

- 在 MiMo client 中包装 `httpx.TimeoutException`
- 包装 `httpx.HTTPStatusError`
- 识别 401/403/429
- generator 不让异常直接冒泡成裸 500
- 前端展示 `errorMessage`

### 4.4 锁定 BUG-003：环境变量一致性

当前已切换到：

```env
XIAOMI_TOKEN_PLAN_CN_API_KEY=
MIMO_TOKEN_PLAN_CN_BASE_URL=https://token-plan-cn.xiaomimimo.com/anthropic
MIMO_MODEL=mimo-v2.5-pro
```

补测试确认：

- `.env.example` 包含这些变量
- `Settings` 能读取这些变量
- 测试 skip 条件使用同一变量名

---

## 5. Harness Phase 3：验收场景更新

把验收计划从 8 个场景扩展到 11 个。

| 场景 | 名称 | 类型 |
|---:|---|---|
| 1 | Project Load 正常路径 | 手动 |
| 2 | Project Load 无效路径 | 手动 + 自动 |
| 3 | Session Creation | 手动 |
| 4 | Delete Operation | 手动 |
| 5 | Import External API | 手动 |
| 6 | Replace Operation | 手动 |
| 7 | Add Insert | 手动 |
| 8 | Add Branch | 手动 |
| 9 | Revert Operation | 手动 |
| 10 | MiMo Token Plan CN 鉴权失败提示 | 自动 + 可选手动 |
| 11 | MiMo Token Plan CN 超时提示 | 自动 |

通过标准：

- `cd backend && pytest tests/ -q` 全绿
- 根目录 `pytest tests/ -q` 不再因缺失 fixture 失败
- 全库旧 provider 扫描无历史供应商名和旧 SDK 残留
- 手动验收至少 9/11 通过
- 场景 10、11 必须有清晰错误文案

---

## 6. 建议执行顺序

1. 修复测试 fixture，让根目录测试不再假失败。
2. 写 `BUG-001` 路径校验测试。
3. 实现 `/project/parse` 路径校验。
4. 写 `BUG-004` 字段命名测试。
5. 统一 Operation 响应字段。
6. 写 MiMo 错误处理测试。
7. 实现 MiMo 错误包装和前端错误展示。
8. 更新验收计划。
9. 跑自动化测试。
10. 做一轮人工 acceptance。

---

## 7. 回滚策略

- 每个 bug 单独提交，避免多个风险混在一起。
- 若字段命名统一影响前端，可临时保留后端输入兼容，但输出仍以 camelCase 为准。
- 若 MiMo 错误包装影响正常生成，先回滚 generator 层异常捕获，保留 client 层测试。
- 若根目录历史测试改造影响范围过大，先把缺失 fixture 补回 `example/task-api/src`，再逐步迁移到 `example/TestProject`。

---

## 8. 完成定义

本计划完成时，应满足：

- BUG-001、BUG-004 有明确自动化测试覆盖并通过
- BUG-002 有 mock 自动化测试覆盖并通过
- BUG-003 有配置一致性测试覆盖并通过
- MiMo Token Plan CN 接入测试通过
- 文档和验收计划同步更新
- 无旧 provider 残留
---

## 9. Implementation Log - 2026-05-15

Status: landed in recommended order.

- TEST-001: restored `example/task-api/src` fixture for historical phase tests.
- BUG-001: `/project/parse` now rejects missing paths and file paths with HTTP 400 before parsing.
- BUG-004: operation apply responses now use FastAPI response models and serialize camelCase fields.
- BUG-002: MiMo Token Plan China client wraps timeout, auth, quota, and network failures as `MimoAPIError`; operation answers return `failed` with `errorMessage` instead of raw 500.
- BUG-003: `.env.example`, `Settings`, fallback token loading, timeout, endpoint, and model are covered by automated tests.

Regression commands:

```powershell
cd backend
pytest tests/ -q

cd ..
pytest tests/ -q
```
