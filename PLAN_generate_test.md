# Feature Plan: `generate_test` Operation

> 基于 Harness Engineering 方法论制定  
> 目标：为用户 FastAPI 项目的路由函数，AI 生成 pytest + TestClient 测试文件

---

## 1. 功能概述

用户右键图中任意函数节点 → 选择「Generate Test」→ AI 根据函数签名、参数类型、关联 Schema 字段生成测试骨架文件 → Diff 预览 → Apply 写入磁盘。

**不执行测试**（第一期）。生成完整可读的 pytest 文件，`Depends()` 相关 override 以 `# TODO` 注释骨架呈现。

---

## 2. 数据流

```
右键节点
  → ContextMenu "Generate Test"
  → App.tsx: startOperation(sessionId, "generate_test", nodeId)
  → POST /operation  { operation_type: "generate_test", target_node_id }
  → analyzer._analyze_generate_test()       # 程序化生成问题，无 AI 调用
      Q1: 测试场景（成功/错误/全部）
      Q2: 测试文件路径（默认 tests/test_{source}.py）
  → status: awaiting_user → 前端展示问题
  → 用户回答 → POST /operation/{id}/answer
  → generator._generate_test_diffs()        # 调用 Moonshot AI 生成代码
      - 构建 prompt：函数签名 + schema 字段 + 路由路径 + HTTP 方法
      - AI 输出完整测试文件内容
      - 写入新文件 diff（old_content="" → new_content=生成内容）
  → status: ready → 前端展示 Diff 预览
  → Apply → 文件写入磁盘
```

---

## 3. 需要修改的文件（按实施顺序）

### Step 1 — 扩展 domain 模型

**文件**: `backend/src/models/domain.py`

- `Operation.type` Literal 加入 `"generate_test"`
- `SubmitOperationRequest.operation_type` Literal 同步加入 `"generate_test"`
- `ParsedProject` 加入 `app_instances: list[AppInstance]`（新子模型）

新增子模型：
```python
class AppInstance(CamelModel):
    var_name: str        # "app" / "router"
    file_path: str       # "main.py"
    instance_type: Literal["fastapi", "apirouter"]
```

---

### Step 2 — Parser：检测 FastAPI app 实例

**新文件**: `backend/src/services/parser/app_detector.py`

功能：遍历 AST，找到 `app = FastAPI()` / `router = APIRouter()` 形式的赋值语句，返回 `list[AppInstance]`。

核心逻辑：
```python
# 匹配：Name = Call(func=Name(id="FastAPI") | Attribute(attr="FastAPI"))
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        if _is_fastapi_call(node.value):
            ...
```

**修改文件**: `backend/src/services/parser/__init__.py`

- `parse_project()` 末尾调用 `detect_app_instances()`，结果存入 `ParsedProject.app_instances`

---

### Step 3 — 分析器：`_analyze_generate_test`

**修改文件**: `backend/src/services/ai/analyzer.py`

```python
def _analyze_generate_test(operation, project) -> Operation:
    fn = {f.id: f for f in project.functions}.get(operation.target_node_id)
    questions = [
        AIQuestion(
            id="q-scenario",
            question="需要生成哪些测试场景？",
            options=["仅成功路径", "仅错误路径（4xx）", "成功 + 错误路径"],
            user_answer=None,
        ),
        AIQuestion(
            id="q-filepath",
            question="测试文件保存路径？",
            options=[f"tests/test_{fn.file_path.replace('/', '_')}", "自定义"],
            user_answer=None,
        ),
    ]
    return operation.model_copy(update={
        "status": "awaiting_user",
        "ai_questions": questions,
    })
```

`analyze_operation()` dispatch 加入 `generate_test` 分支。

---

### Step 4 — Prompt 模板

**修改文件**: `backend/src/services/ai/prompts.py`

新增常量 `GENERATE_TEST_PROMPT`：

```
你是一个 Python 测试专家。根据以下 FastAPI 路由函数信息，生成完整的 pytest 测试文件。

函数名: {fn_name}
HTTP方法 + 路径: {http_method} {route_path}
参数: {params}
返回类型: {return_type}
关联 Schema:
{schemas_detail}
FastAPI app 导入路径: {app_import}
测试场景: {scenarios}

要求：
1. 使用 from fastapi.testclient import TestClient
2. 用 pytest fixture 创建 client
3. 对每个 Depends 依赖生成 app.dependency_overrides[...] = lambda: ...，并注释 # TODO: 替换为真实 mock
4. 对 Schema 字段生成合理的测试数据（必填字段用最小合法值，可选字段省略）
5. 每个测试函数有清晰的 docstring
6. 只输出完整 Python 文件内容，不要加 markdown 代码块
```

---

### Step 5 — 生成器：`_generate_test_diffs`

**修改文件**: `backend/src/services/ai/generator.py`

```python
async def _generate_test_diffs(operation, project) -> Operation:
    fn = {f.id: f for f in project.functions}[operation.target_node_id]
    schemas = {s.id: s for s in project.schemas}

    # 从 ai_questions 读取用户回答
    answers = {q.id: q.user_answer for q in operation.ai_questions}
    scenario = answers.get("q-scenario", "成功 + 错误路径")
    test_file_path = answers.get("q-filepath", f"tests/test_{fn.file_path.replace('/', '_')}")

    # 找关联 Schema 详情
    used_schemas = [schemas[sid] for sid in fn.uses_schemas if sid in schemas]
    schemas_detail = "\n".join(
        f"  {s.name}: " + ", ".join(f"{f.name}: {f.type}" for f in s.fields)
        for s in used_schemas
    )

    # 找 app 实例导入路径
    app_instance = project.app_instances[0] if project.app_instances else None
    app_import = (
        f"from {_file_path_to_module(app_instance.file_path)} import {app_instance.var_name}"
        if app_instance else "from main import app  # TODO: 调整导入路径"
    )

    # 从 EntryPoint 推断 HTTP method + path
    entry = next(
        (e for e in project.entry_points if e.function_id == fn.id), None
    )
    http_info = entry.label if entry else f"UNKNOWN /{fn.name}"

    prompt = GENERATE_TEST_PROMPT.format(
        fn_name=fn.name,
        http_method=http_info,
        params=_fmt_params(fn.params),
        return_type=fn.return_type or "Any",
        schemas_detail=schemas_detail or "（无关联 Schema）",
        app_import=app_import,
        scenarios=scenario,
    )

    client = _make_client()
    resp = await client.chat.completions.create(
        model=MOONSHOT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    test_content = resp.choices[0].message.content.strip()

    diff = _make_diff(
        file_path=test_file_path,
        old_content="",          # 新文件
        new_content=test_content,
    )
    return operation.model_copy(update={
        "status": "ready",
        "generated_diffs": [diff],
    })
```

`generate_diffs()` dispatch 加入 `generate_test` 分支。

---

### Step 6 — 前端 types

**修改文件**: `frontend/src/types/index.ts`

```typescript
// Operation.type union
export type OperationType =
  | 'replace' | 'delete' | 'add_insert' | 'add_branch' | 'add_api'
  | 'generate_test'   // ← 新增

// ParsedProject 加入
appInstances: AppInstance[]

// 新接口
export interface AppInstance {
  varName: string
  filePath: string
  instanceType: 'fastapi' | 'apirouter'
}
```

---

### Step 7 — 右键菜单

**修改文件**: `frontend/src/components/panels/ContextMenu.tsx`

- 新增 `onGenerateTest?: () => void` prop
- 在 `nodeType === 'function'` 区块加入按钮：

```tsx
{onGenerateTest && (
  <button
    onClick={() => { onGenerateTest(); onClose() }}
    className="w-full text-left px-3 py-2 text-green-300 hover:bg-green-900/40 transition-colors flex items-center gap-2"
  >
    <span>🧪</span>
    <span>Generate Test</span>
  </button>
)}
```

---

### Step 8 — App.tsx 串联

**修改文件**: `frontend/src/App.tsx`

- `handleGenerateTest(nodeId)` → 调用 `startOperation(sessionId, 'generate_test', nodeId, null)`
- `onNodeContextMenu` 里的 `contextMenu` state 已有 `nodeId`，直接复用
- `ContextMenu` 组件传入 `onGenerateTest={() => handleGenerateTest(contextMenu.nodeId)}`
- 无需改 RightPanel：`generate_test` 的问答流程与 `add_branch` 完全一致，现有 `AIConversation` 组件可直接处理

---

## 4. 不需要改动的文件

| 文件 | 原因 |
|------|------|
| `routers/operation.py` | dispatch 逻辑已经是通用的，无需改动 |
| `RightPanel.tsx` | 问答 UI 与 Diff 预览已经通用 |
| `DiffPreview.tsx` | 支持新文件（old_content=""）已有逻辑 |
| `store/index.ts` | 无新状态 |

---

## 5. 实施顺序与依赖关系

```
Step 1 (domain)
  ↓
Step 2 (parser) ── Step 6 (frontend types)
  ↓                        ↓
Step 3 (analyzer)    Step 7 (ContextMenu)
  ↓                        ↓
Step 4 (prompt)      Step 8 (App.tsx)
  ↓
Step 5 (generator)
```

Step 1 → 2 → 3 → 4 → 5 必须串行（后端依赖链）  
Step 6 → 7 → 8 可与后端并行，最后集成联调

---

## 6. 边界情况与处理策略

| 情况 | 处理 |
|------|------|
| 项目无 FastAPI app 实例 | app_import 用 `# TODO` 注释，继续生成 |
| 函数非路由（无 EntryPoint） | http_info 设为 `UNKNOWN`，让 AI 根据函数名推断 |
| `Depends()` 依赖 | AI prompt 明确要求生成 `dependency_overrides` 骨架 + TODO 注释 |
| tests/ 目录不存在 | Apply 写文件时 `os.makedirs` 创建（现有 apply 逻辑已处理） |
| 同名测试文件已存在 | old_content 读取已有文件内容，AI merge（或提示用户） |

---

## 7. 验收标准

- [ ] 右键任意函数节点出现「Generate Test」选项
- [ ] 问答流程正常（2 个问题，选择后进入 generating）
- [ ] Diff 预览显示新测试文件内容
- [ ] Apply 后 `tests/` 目录下出现对应 `.py` 文件
- [ ] 生成的文件包含：import、fixture、至少 1 个测试函数、Depends TODO 骨架
- [ ] 对无 EntryPoint 的普通函数也可正常触发（降级处理）
- [ ] TypeScript 无类型错误
