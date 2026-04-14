# CodeFlow

**An AI-powered Python codebase visualiser with live graph editing.**

**基于 AI 的 Python 代码库可视化工具，支持实时图谱编辑。**

[English](#english) · [中文](#中文) · [使用指南 / User Guide](GUIDE.md)

---

<a name="english"></a>

## English

CodeFlow parses your Python project into an interactive call-graph, lets you explore function relationships visually, and uses an LLM to perform structural code changes — delete functions, branch logic, insert intermediaries, or replace implementations with external APIs — all with diff preview and one-click apply/undo.

> **Built entirely with AI-assisted engineering via the Claude Code CLI (Anthropic Harness Engineering).** Every feature — from the AST parser to the ReactFlow graph, AI prompts, and operation pipeline — was designed, implemented, debugged, and acceptance-tested through natural-language conversation with Claude Code. No boilerplate was written by hand.

### What it does

| Feature | Description |
|---|---|
| **Call-graph visualisation** | Parses Python files with `astroid` and renders functions, schemas, and external APIs as an interactive directed graph |
| **Entry-point filtering** | Switch between HTTP route entry points to focus the graph on a specific execution path |
| **Node inspector** | Single-click any node to preview its source code in the right panel; double-click to open it in the built-in Monaco editor |
| **AI-powered operations** | Right-click a node to delete it, add a branch, or insert an intermediate function — the AI asks clarifying questions then generates diffs |
| **File-selection for new functions** | Choose which `.py` file a newly generated function lands in (same file or any other file in the project) |
| **External API replace** | Import an external REST API spec and drag it onto a function to replace it; AI handles schema mapping |
| **Diff preview** | Review every line change before writing anything to disk |
| **Apply & Undo** | Apply diffs to disk with one click; roll back with another |
| **Resizable panel** | Drag the right panel edge to adjust its width |
| **Operation history** | Every applied/reverted operation is tracked in the top nav |

### Tech stack

**Backend**
- Python 3.11+ · FastAPI · Uvicorn
- `astroid` — Python AST analysis and call-graph extraction
- `openai` SDK → Moonshot (Kimi) `moonshot-v1-32k` model for code generation
- `pydantic-settings` — typed config, reads `.env` automatically
- `pytest` + `pytest-asyncio` — phase-by-phase integration tests

**Frontend**
- React 18 + TypeScript · Vite
- `@xyflow/react` (ReactFlow) — interactive node-edge canvas
- `@monaco-editor/react` — in-browser code editor
- `zustand` — lightweight global state
- `tailwindcss` — utility-first styling
- `vitest` — unit/component tests

### Getting started

**Prerequisites:** Python 3.11+, Node.js 18+, a [Moonshot API key](https://platform.moonshot.cn/)

```bash
# 1. Clone
git clone https://github.com/1Max1mus1/CodeFlow.git && cd CodeFlow

# 2. Backend
cd backend && pip install -r requirements.txt
cp .env.example .env          # add your MOONSHOT_API_KEY
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000

# 3. Frontend (new terminal)
cd frontend && npm install && npm run dev
# → http://localhost:5173
```

Then enter the **absolute path** to any Python project in the sidebar and click **Load**. An example project is included at `example/TestProject/`.

For a full feature walkthrough, see the **[User Guide →](GUIDE.md)**

### AI operations walkthrough

**Delete a function** — Right-click → Delete → confirm → AI asks how to handle call sites → review diff → Apply

**Add a branch** — Right-click → Add Branch → fill in: condition expression · what the branch does · which file to place it in

**Insert an intermediary** — Click any call edge → confirm → describe the new function · choose its destination file

**Replace with API** — Import an API via the toolbar → drag onto a function → AI maps schemas → review diff → Apply

### What makes it different

**Most code-visualisation tools are read-only.** CodeFlow closes the loop: parse → visualise → edit → apply — all in one interface, with an LLM doing the heavy lifting.

**Structured operations, not a chat box.** Every operation is a typed workflow with programmatically-generated clarifying questions. The AI only writes code after all questions are answered — reducing hallucination and keeping diffs minimal.

**Cross-file generation.** Users pick the destination file for new functions. For cross-file placements, CodeFlow runs two sequential LLM calls: one to write the function, one to add the import and call-site update — deriving the new function name automatically by diffing `def` statements.

**Built with Harness Engineering.** Architecture, implementation, testing, and iteration were completed entirely through Claude Code (Anthropic's agentic CLI). The codebase demonstrates what AI-assisted engineering can produce end-to-end: from PRD to a working, tested product.

### Running tests

```bash
pytest tests/ -v
```

### Environment variables

| Variable | Description |
|---|---|
| `MOONSHOT_API_KEY` | Moonshot (Kimi) API key — required for all AI operations |

---

<a name="中文"></a>

## 中文

CodeFlow 将你的 Python 项目解析为交互式函数调用图，让你直观地探索函数之间的调用关系，并通过大语言模型执行结构性代码修改——删除函数、添加分支、插入中间函数、或将实现替换为外部 API——全程提供 diff 预览，一键应用与撤销。

> **本项目完全通过 Claude Code CLI（Anthropic Harness Engineering）以 AI 辅助工程的方式完成。** 从 AST 解析器、ReactFlow 图谱、AI Prompt 设计到操作流水线，每一个功能都通过与 Claude Code 的自然语言对话来设计、实现、调试和验收测试，无任何手写样板代码。

### 功能介绍

| 功能 | 说明 |
|---|---|
| **函数调用图可视化** | 使用 `astroid` 解析 Python 文件，将函数、数据模型和外部 API 渲染为可交互的有向图 |
| **入口点过滤** | 在 HTTP 路由入口点之间切换，将图聚焦于特定执行路径 |
| **节点检查器** | 单击节点在右侧面板预览源代码；双击在内置 Monaco 编辑器中打开 |
| **AI 操作** | 右键节点即可删除、添加分支或插入中间函数——AI 提问澄清后自动生成代码 diff |
| **新函数文件选择** | 自由选择新生成的函数放入哪个 `.py` 文件（当前文件或项目中任意文件） |
| **外部 API 替换** | 导入外部 REST API 规格，拖拽到函数节点上即可替换；AI 自动处理 Schema 映射 |
| **Diff 预览** | 写入磁盘前逐行审查所有变更 |
| **应用与撤销** | 一键将 diff 写入磁盘；另一键还原所有文件 |
| **面板宽度拖拽** | 拖动右侧面板边缘自由调整宽度 |
| **操作历史记录** | 所有已应用/已撤销的操作显示在顶部导航栏 |

### 技术栈

**后端**
- Python 3.11+ · FastAPI · Uvicorn
- `astroid` — Python AST 分析与调用图提取
- `openai` SDK → Moonshot（Kimi）`moonshot-v1-32k` 模型生成代码
- `pydantic-settings` — 类型化配置，自动读取 `.env`
- `pytest` + `pytest-asyncio` — 按阶段划分的集成测试

**前端**
- React 18 + TypeScript · Vite
- `@xyflow/react`（ReactFlow）— 交互式节点图画布
- `@monaco-editor/react` — 浏览器内代码编辑器
- `zustand` — 轻量级全局状态管理
- `tailwindcss` — 原子化 CSS
- `vitest` — 单元/组件测试

### 快速开始

**前置条件：** Python 3.11+、Node.js 18+、[Moonshot API Key](https://platform.moonshot.cn/)

```bash
# 1. 克隆仓库
git clone https://github.com/1Max1mus1/CodeFlow.git && cd CodeFlow

# 2. 启动后端
cd backend && pip install -r requirements.txt
cp .env.example .env          # 填入你的 MOONSHOT_API_KEY
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000

# 3. 启动前端（新终端）
cd frontend && npm install && npm run dev
# → http://localhost:5173
```

打开页面后，在左侧边栏输入任意 Python 项目的**绝对路径**并点击 **Load**。仓库中包含示例项目 `example/TestProject/` 可直接体验。

完整功能说明请参阅 **[使用指南 →](GUIDE.md)**

### AI 操作使用说明

**删除函数** — 右键 → Delete → 确认 → AI 询问如何处理调用方 → 预览 diff → Apply

**添加分支** — 右键 → Add Branch → 依次填写：触发条件表达式 · 新函数的功能描述 · 放入哪个文件

**插入中间函数** — 点击任意调用边 → 确认 → 描述新函数的功能 · 选择目标文件

**替换为外部 API** — 工具栏导入 API → 拖拽到函数节点 → AI 映射 Schema → 预览 diff → Apply

### 项目结构

```
CodeFlow/
├── backend/
│   ├── src/
│   │   ├── main.py               # FastAPI 入口
│   │   ├── models/domain.py      # Pydantic 领域模型
│   │   ├── routers/              # REST 接口（project / session / operation）
│   │   └── services/
│   │       ├── parser/           # astroid Python AST 解析器
│   │       ├── session/          # 内存存储
│   │       └── ai/
│   │           ├── analyzer.py   # 程序化问题生成
│   │           ├── generator.py  # Moonshot API → FileDiff 生成
│   │           └── prompts.py    # 所有 LLM Prompt 模板
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.tsx               # 根组件，事件连线
│   │   ├── components/           # ReactFlow 节点、边、面板、IDE 视图
│   │   ├── hooks/                # useOperation / useProject / useSession
│   │   ├── services/api.ts       # 后端 HTTP 客户端
│   │   ├── store/                # Zustand 全局状态
│   │   └── utils/projectToFlow.ts# 项目数据 → ReactFlow 节点/边
│   └── package.json
├── tests/                        # 后端集成测试（Phase 0–6）
└── example/TestProject/          # 用于测试的示例 Python 项目
```

### 核心亮点

**绝大多数代码可视化工具只能读，不能改。** CodeFlow 打通了完整闭环：解析 → 可视化 → 编辑 → 应用，全在一个界面内完成，由 LLM 承担繁重的重构工作。

**结构化操作流程，而非聊天框。** 每个操作都是类型化的工作流（delete / add_branch / add_insert / replace），配以程序化生成的澄清问题。AI 只有在用户回答所有问题之后才开始生成代码，有效降低幻觉、保持 diff 最小化。

**跨文件代码生成。** 用户可为新函数指定目标文件。跨文件场景下，CodeFlow 依次发起两次 LLM 调用：第一次在目标文件中写入新函数，第二次在源文件中添加导入语句和调用点更新——通过对比 `def` 语句自动推断新函数名。

**基于 Harness Engineering 构建。** 本项目的架构设计、功能实现、测试编写和迭代优化，全程通过 Claude Code（Anthropic 的 Agentic CLI）完成。这是 AI 辅助工程从零到完整可测产品的端到端实践。

### 运行测试

```bash
pytest tests/ -v
```

### 环境变量

| 变量 | 说明 |
|---|---|
| `MOONSHOT_API_KEY` | Moonshot（Kimi）API Key，所有 AI 操作必填 |

---

## License

MIT
