# Feature Plan: Route Test Panel — 目标服务发现与 UX 优化

> 基于 Harness Engineering 方法论制定
> **P0** — 增强 Base URL 配置 UI，消除用户混淆
> **P1** — 智能端口推断，从被分析项目的源码自动探测 uvicorn/Flask 启动端口

---

## 1. 问题诊断

当前 `RouteTestPanel` 存在两个结构性 UX 缺陷：

| # | 缺陷 | 表现 |
|---|------|------|
| 1 | **Base URL 语义不清** | 标签只写 "Base URL"，用户不清楚这是他们自己项目的地址，而非 CodeFlow 自身 |
| 2 | **无连接反馈** | 点击 Send 才能知道目标服务是否在线，失败只显示原始错误，无引导 |
| 3 | **端口无推断** | 项目已被 AST 解析，但解析结果中没有提取 uvicorn 启动端口信息 |

---

## 2. 数据流（目标态）

```
ParsedProject (含 suggestedPort)
  ↓
RouteTestPanel props
  ↓
初始化时：若 suggestedPort 存在且 localStorage 无缓存
  → 自动预填 baseUrl = http://localhost:{suggestedPort}
  → 显示蓝色横幅："已从项目中推断出端口 {suggestedPort}，请确认"

URL 变更 / 组件 mount 时：
  → 后台 ping baseUrl (via /proxy health check)
  → 显示连接状态指示器 ● 绿/红/灰

Send 时连接失败 (502)：
  → 显示引导性错误：列出 3 个排查步骤
```

---

## 3. 需要修改的文件（按实施顺序）

---

### Step 0 — Harness：扩展类型契约（先于实现）

**Harness 原则：类型先行，实现填入，类型不反复改动。**

#### Step 0-A — `backend/src/models/domain.py`

`ParsedProject` 末尾加入字段：

```python
class ParsedProject(CamelModel):
    ...
    app_instances: list[AppInstance] = []
    suggested_port: int | None = None   # ← 新增
```

#### Step 0-B — `frontend/src/types/index.ts`

```typescript
export interface ParsedProject {
  ...
  appInstances: AppInstance[]
  suggestedPort: number | null   // ← 新增
}
```

---

### Step 1 — P1 后端：新增 `port_detector.py`

**新文件**: `backend/src/services/parser/port_detector.py`

功能：遍历项目所有 `.py` 文件的 AST，匹配以下 uvicorn/Flask 端口声明模式，返回第一个找到的端口号。

**匹配目标模式：**

```python
# Pattern A — uvicorn.run keyword arg
uvicorn.run(app, port=8080)
uvicorn.run("main:app", host="0.0.0.0", port=8080)

# Pattern B — uvicorn.run positional (少见，不处理)

# Pattern C — if __name__ == "__main__" 内的 uvicorn.run
if __name__ == "__main__":
    uvicorn.run(app, port=9000)

# Pattern D — Flask / Starlette app.run
app.run(port=5000)
app.run(host="0.0.0.0", port=5000)
```

**核心逻辑：**

```python
import ast
from pathlib import Path


def detect_suggested_port(py_files: list[tuple[str, str]]) -> int | None:
    """
    py_files: list of (abs_path, rel_path)
    Returns the first detected port or None.
    Priority: uvicorn.run > app.run > router.run
    """
    for abs_path, _ in py_files:
        port = _scan_file_for_port(abs_path)
        if port is not None:
            return port
    return None


def _scan_file_for_port(abs_path: str) -> int | None:
    try:
        source = Path(abs_path).read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (OSError, SyntaxError, UnicodeDecodeError):
        return None

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not _is_run_call(node.func):
            continue
        port = _extract_port_kwarg(node)
        if port is not None:
            return port
    return None


def _is_run_call(func: ast.expr) -> bool:
    # uvicorn.run(...)
    if isinstance(func, ast.Attribute) and func.attr == "run":
        return True
    # run(...) — bare name, less specific but acceptable
    if isinstance(func, ast.Name) and func.id == "run":
        return True
    return False


def _extract_port_kwarg(call: ast.Call) -> int | None:
    for kw in call.keywords:
        if kw.arg == "port" and isinstance(kw.value, ast.Constant):
            v = kw.value.value
            if isinstance(v, int) and 1 <= v <= 65535:
                return v
    return None
```

---

### Step 2 — P1 后端：集成到 `parser/__init__.py`

**修改文件**: `backend/src/services/parser/__init__.py`

在 `parse_project()` 末尾、构建 `ParsedProject` 之前调用：

```python
from src.services.parser.port_detector import detect_suggested_port

# 已有的 py_files 列表（(abs_path, rel_path) tuples）复用即可
suggested_port = detect_suggested_port(py_files)

return ParsedProject(
    ...
    suggested_port=suggested_port,
)
```

> 注意：`py_files` 已在 `parse_project()` 中构建，直接复用，无需重复扫描。

---

### Step 3 — P0 前端：`RouteTestPanel.tsx` — 连接健康检测

**修改文件**: `frontend/src/components/panels/RouteTestPanel.tsx`

新增状态与逻辑：

```typescript
type HealthStatus = 'idle' | 'checking' | 'ok' | 'error'

const [healthStatus, setHealthStatus] = useState<HealthStatus>('idle')
const healthTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

// debounced health check — triggered on baseUrl change
useEffect(() => {
  if (healthTimerRef.current) clearTimeout(healthTimerRef.current)
  setHealthStatus('checking')
  healthTimerRef.current = setTimeout(() => {
    checkHealth(baseUrl)
  }, 600)
  return () => { if (healthTimerRef.current) clearTimeout(healthTimerRef.current) }
}, [baseUrl])

async function checkHealth(url: string) {
  try {
    const res = await fetch('/proxy', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: url.replace(/\/$/, '') + '/', method: 'GET', headers: {}, body: null }),
    })
    // Any non-network response (even 404) means the server is reachable
    setHealthStatus(res.ok || (await res.json().catch(() => null)) !== null ? 'ok' : 'ok')
  } catch {
    setHealthStatus('error')
  }
}
```

健康指示器 UI（放在 Base URL input 右侧）：

```tsx
const healthDot: Record<HealthStatus, string> = {
  idle: 'bg-gray-600',
  checking: 'bg-yellow-500 animate-pulse',
  ok: 'bg-green-500',
  error: 'bg-red-500',
}

const healthTitle: Record<HealthStatus, string> = {
  idle: '未检测',
  checking: '检测中…',
  ok: '服务可达',
  error: '无法连接',
}

// 在 input 右侧插入：
<span
  title={healthTitle[healthStatus]}
  className={`w-2 h-2 rounded-full shrink-0 mt-0.5 ${healthDot[healthStatus]}`}
/>
```

---

### Step 4 — P0 前端：推荐端口横幅 + 快捷预设下拉

**修改文件**: `frontend/src/components/panels/RouteTestPanel.tsx`

#### Props 扩展

`RouteTestPanel` 已接收 `project: ParsedProject | null`，无需改 props，直接读取：

```typescript
const suggestedPort = project?.suggestedPort ?? null
const suggestedUrl = suggestedPort ? `http://localhost:${suggestedPort}` : null
```

#### 推荐端口横幅

在 Base URL input 下方，当 `suggestedUrl` 存在且与当前 `baseUrl` 不同时显示：

```tsx
{suggestedUrl && suggestedUrl !== baseUrl && (
  <div className="flex items-center justify-between bg-blue-950 border border-blue-700 rounded px-2 py-1.5 text-[11px]">
    <span className="text-blue-300">
      从项目中检测到端口 <span className="font-mono font-bold">{suggestedPort}</span>
    </span>
    <button
      onClick={() => handleBaseUrlChange(suggestedUrl)}
      className="text-blue-400 hover:text-blue-200 underline ml-2 shrink-0"
    >
      使用此地址
    </button>
  </div>
)}
```

#### 快捷预设下拉

在 Base URL input 右侧加入预设按钮组（替代下拉，更轻量）：

```tsx
const PRESETS = [3000, 5000, 8000, 8080]

<div className="flex gap-1 mt-1 flex-wrap">
  {PRESETS.map((port) => (
    <button
      key={port}
      onClick={() => handleBaseUrlChange(`http://localhost:${port}`)}
      className={`px-1.5 py-0.5 rounded text-[10px] border transition-colors ${
        baseUrl === `http://localhost:${port}`
          ? 'border-blue-500 text-blue-300 bg-blue-950'
          : 'border-gray-600 text-gray-500 hover:border-gray-400 hover:text-gray-300'
      }`}
    >
      :{port}
    </button>
  ))}
</div>
```

---

### Step 5 — P0 前端：警告横幅 + 错误引导文案

**修改文件**: `frontend/src/components/panels/RouteTestPanel.tsx`

#### Send 前警告横幅

当 `healthStatus === 'error'` 且用户尝试 Send 时，或在 Send 按钮上方常驻显示（`healthStatus === 'error'`）：

```tsx
{healthStatus === 'error' && (
  <div className="bg-yellow-950 border border-yellow-700 rounded px-2 py-1.5 text-[11px] text-yellow-300 space-y-0.5">
    <div className="font-semibold">目标服务未响应</div>
    <div className="text-yellow-500">① 确认你的项目已启动（如 uvicorn main:app）</div>
    <div className="text-yellow-500">② 确认 Base URL 端口与项目一致</div>
    <div className="text-yellow-500">③ 确认防火墙未拦截本地请求</div>
  </div>
)}
```

#### 502 连接错误增强

在 `handleSend` 的 catch/error 处理里，当 `data.detail` 包含 `Could not connect` 时，替换为更友好的文案：

```typescript
const rawDetail: string = data.detail ?? `Proxy error ${res.status}`
const friendlyDetail = rawDetail.includes('Could not connect')
  ? `无法连接到 ${baseUrl}。\n请检查：\n① 目标项目是否已启动\n② Base URL 是否正确\n③ 端口是否与项目配置一致`
  : rawDetail
setError(friendlyDetail)
```

#### Base URL 标签 Tooltip

```tsx
<label className="text-gray-500 uppercase text-[10px] font-bold tracking-wider flex items-center gap-1">
  目标服务地址
  <span
    title="这是你自己项目的运行地址（非 CodeFlow 自身），请在启动项目后填写正确端口"
    className="text-gray-600 cursor-help normal-case font-normal"
  >
    ⓘ
  </span>
</label>
```

---

## 4. 不需要改动的文件

| 文件 | 原因 |
|------|------|
| `backend/src/routers/proxy.py` | 代理逻辑不变，健康检测复用同一 `/proxy` 端点 |
| `backend/src/routers/project.py` | parse_project 调用链无变化，parser 内部处理 |
| `frontend/src/App.tsx` | `RouteTestPanel` props 未扩展，传递 `project` 已有 |
| `frontend/src/services/api.ts` | 无新 API 端点 |
| `frontend/src/store/index.ts` | 无新全局状态 |

---

## 5. 实施顺序与依赖关系

```
Step 0-A (backend types)
  ↓
Step 0-B (frontend types)        ← 可与 0-A 并行
  ↓
Step 1 (port_detector.py)        Step 3 (health check UI)
  ↓                                      ↓
Step 2 (parser integration)       Step 4 (suggested URL banner + presets)
                ↓                        ↓
                └──────────── Step 5 (warning + error copy) ───→ 联调
```

- Step 0 必须最先完成（类型契约）
- Step 1 → 2 串行（后端依赖链）
- Step 3 → 4 → 5 可串行推进（同一文件）
- 后端 Step 2 完成前，前端横幅不会显示（`suggestedPort` 为 null），但健康检测和预设按钮功能完全独立，可提前上线

---

## 6. 边界情况与处理策略

| 情况 | 处理 |
|------|------|
| 项目无 `uvicorn.run` / `app.run` | `suggestedPort = null`，不显示推荐横幅，其余 P0 功能正常 |
| 同一项目有多个端口声明 | 取第一个匹配（主入口文件通常在扫描前列），后续可按优先级优化 |
| `uvicorn.run(port=int_var)` 变量引用 | 无法静态求值，跳过（保守策略，不误报） |
| 健康检测被 CORS 拦截 | 所有 health ping 均走 `/proxy` 端点，无 CORS 问题 |
| 健康检测目标返回 404 | 视为"服务可达"（`healthStatus = 'ok'`），404 是应用层响应，说明进程在跑 |
| 健康检测目标返回 401/403 | 同上，视为可达，不拦截发送 |
| localStorage 已有缓存 URL | 不覆盖，推荐横幅显示建议但不强制，用户点"使用此地址"才切换 |
| Windows 路径中含空格或中文 | `port_detector.py` 使用 `Path.read_text(encoding="utf-8")`，已处理 |

---

## 7. 验收标准

### P0 — UI 增强

- [ ] Base URL 标签显示为"目标服务地址"并带 ⓘ tooltip
- [ ] URL 输入框右侧有颜色状态点（灰/黄闪/绿/红）
- [ ] 输入框下方有 `:3000` `:5000` `:8000` `:8080` 快捷按钮，当前选中项高亮
- [ ] 当 `healthStatus === 'error'` 时，Send 按钮上方出现黄色三步排查横幅
- [ ] 502 连接错误显示友好中文提示（包含三步检查）
- [ ] 更改 URL 后 600ms 内触发健康检测，状态点动态更新

### P1 — 智能端口推断

- [ ] 被分析项目含 `uvicorn.run(app, port=8080)` 时，`ParsedProject.suggestedPort === 8080`
- [ ] 前端收到 `suggestedPort` 后，若与当前 `baseUrl` 不同，显示蓝色推荐横幅
- [ ] 点击"使用此地址"后 `baseUrl` 更新，横幅消失，健康检测重新触发
- [ ] 项目无端口声明时，`suggestedPort === null`，无横幅，其余功能正常
- [ ] TypeScript 无类型错误（`suggestedPort: number | null` 已在 interface 中定义）
- [ ] Python 无 lint 错误，`port_detector.py` 有 pytest 覆盖（`backend/tests/` 中新增测试）
