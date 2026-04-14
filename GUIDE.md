# CodeFlow 使用指南

> **版本：** 当前构建（2026-04）  
> **语言支持：** Python 3.11+  
> **AI 模型：** Moonshot（Kimi）`moonshot-v1-32k`

---

## 目录

1. [项目评估](#项目评估)
2. [快速开始](#快速开始)
3. [界面总览](#界面总览)
4. [核心功能详解](#核心功能详解)
5. [AI 操作工作流](#ai-操作工作流)
6. [路由测试器](#路由测试器)
7. [操作历史与回滚](#操作历史与回滚)
8. [已知限制](#已知限制)
9. [常见问题](#常见问题)

---

## 项目评估

### 创意性 ★★★★★

CodeFlow 的核心创意在于打通了代码工具链中长期割裂的两端：

| 传统工具 | CodeFlow |
|---------|---------|
| 代码可视化工具只能"读" | 可视化 + 直接编辑，闭环完整 |
| AI 聊天框生成代码（黑盒） | 结构化问答 → 生成 → diff 预览 → 一键应用 |
| 重构需要开发者手动追踪调用链 | 调用链图谱自动生成，影响范围一目了然 |
| Swagger 测试与代码割裂 | 路由测试器内嵌图谱，测什么改什么 |

**最有价值的创意点：**
- **结构化操作流程**（而非聊天框）：每次操作都是类型化工作流，AI 先问问题再生成代码，有效降低幻觉
- **跨文件生成**：两次顺序 LLM 调用，自动处理新函数的导入和调用点更新
- **操作历史回滚**：不只是"撤销"，而是针对任意历史 checkpoint 的精准还原
- **Schema 可视化边**：三种颜色的边（调用 / 返回类型 / 参数类型）直接揭示数据流向
- **整个项目由 Claude Code CLI 全程 AI 辅助构建**，本身就是一个 Harness Engineering 的实践范本

### 实用性 ★★★★☆

**高价值场景：**
- 接手陌生 Python 项目，需要快速理解调用链结构
- 重构 FastAPI 服务：删除函数、添加中间层、替换外部依赖
- 评估改动影响范围（看调用图，而不是全局搜索）
- 为 FastAPI 路由快速生成 pytest 测试文件
- 在开发环境直接测试 API 路由（内嵌类 Swagger 测试器）

**当前不适合的场景：**
- 超大型代码库（AST 解析时间较长，图会非常复杂）
- 非 Python 项目（目前仅支持 Python）
- 生产环境重构（无代码审查流程，无 git 集成）

### 技术完整度 ★★★★☆

| 维度 | 评分 | 说明 |
|------|------|------|
| 前后端分离架构 | ✅ | FastAPI + React/TypeScript，REST API 清晰 |
| 类型安全 | ✅ | Pydantic v2 + TypeScript，全链路类型覆盖 |
| 测试覆盖 | ✅ | 16+ 后端集成测试，涵盖 parser/analyzer/generator/router |
| 错误处理 | ✅ | 操作失败显示在 AI 标签，支持 cancel 和 manually 终止 |
| 状态持久化 | ⚠️ | 内存存储，后端重启后需重新加载项目 |
| 多用户 | ❌ | 单用户本地工具，未设计多用户场景 |

**总体结论：** CodeFlow 是一个创意领先、工程完整度较高的 MVP，适合在个人开发/小团队中作为重构辅助工具使用。核心创意（可编辑的代码图谱）在市场上少有同类产品。

---

## 快速开始

### 前置条件

| 工具 | 版本要求 |
|------|---------|
| Python | 3.11+ |
| Node.js | 18+ |
| Moonshot API Key | [申请地址](https://platform.moonshot.cn/) |

### 安装与启动

```bash
# 1. 克隆仓库
git clone https://github.com/1Max1mus1/CodeFlow.git
cd CodeFlow

# 2. 后端（终端 1）
cd backend
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，填入你的 MOONSHOT_API_KEY
python -m uvicorn src.application:create_app --factory --host 0.0.0.0 --port 8000 --reload

# 3. 前端（终端 2）
cd frontend
npm install
npm run dev
# → 打开 http://localhost:5173
```

> **注意：** 如遇 Windows 端口被占用（`[WinError 10048]`），改用其他端口（如 `--port 8001`），并同步修改 `frontend/vite.config.ts` 中的代理地址。

---

## 界面总览

```
┌──────────────────┬────────────────────────────────────┬─────────────────────┐
│   左侧栏          │          主画布（图谱）              │     右侧面板         │
│                  │                                    │                     │
│  📁 项目加载      │   [函数节点] ──蓝色──► [函数节点]   │  🔍 Inspector       │
│                  │        │                           │  ✨ AI Assistant    │
│  ⚡ Entry Points │   [Schema节点] ←─紫色── [函数]      │  ▷  Tester         │
│  POST /tasks     │                                    │                     │
│  GET  /tasks     │   节点可拖拽、平移、缩放              │                     │
│  ...             │                                    │                     │
└──────────────────┴────────────────────────────────────┴─────────────────────┘
          ↑                      ↑                               ↑
    加载项目 / 选择              交互式图谱                    AI 对话 / 代码检查
    入口点 / 生成测试
```

### 图谱节点颜色

| 节点颜色 | 类型 | 说明 |
|---------|------|------|
| 🔵 蓝色 | `FunctionNode` | Python 函数或方法 |
| 🟣 紫色 | `SchemaNode` | Pydantic 模型 / TypedDict / dataclass |
| 🟢 绿色 | `ExternalAPINode` | 手动导入的外部 REST API |

### 图谱边颜色

| 边颜色 | 线型 | 含义 |
|--------|------|------|
| 🔵 蓝色 实线 | → | 调用边（A 调用 B） |
| 🟠 橙色 虚线 | ⟶ | 数据流边（函数的返回类型指向 Schema） |
| 🟣 紫色 实线 | → | Schema 使用边（函数的参数类型使用了某 Schema） |
| 🔴 红色 | 任意 | 类型不兼容（Schema 不匹配） |

> 图谱左下角有**图例说明**，悬停即可查看。

---

## 核心功能详解

### 1. 加载项目

1. 在左侧栏 **Project** 输入框中填入 Python 项目的**绝对路径**
2. 点击 **Load** 按钮
3. 系统自动解析所有 `.py` 文件，提取函数、Schema 和调用关系
4. 左侧 Entry Points 列表自动填充检测到的 FastAPI 路由

**示例路径：**
```
C:\Users\Victor\Desktop\Codeflow\example\TestProject
```

### 2. 切换入口点

点击左侧 Entry Points 中的任意路由（如 `POST /tasks`），主画布将只显示该路由执行路径上的节点，过滤掉无关函数。

### 3. 节点操作

| 操作 | 效果 |
|------|------|
| **单击节点** | 右面板显示函数签名、参数、源代码预览 |
| **双击节点** | 打开内置 Monaco 编辑器，直接编辑源代码 |
| **右键节点** | 弹出操作菜单（Delete / Add Branch） |
| **拖拽节点** | 重新排列画布布局 |
| **点击调用边** | 触发"插入中间函数"流程 |

### 4. 右侧面板三个标签

| 标签 | 图标 | 功能 |
|------|------|------|
| **Inspector** | 🔍 | 查看选中节点的源码、参数、文件位置 |
| **AI Assistant** | ✨ | AI 操作问答、diff 预览、应用/撤销 |
| **Tester** | ▷ | 直接向选中路由发送 HTTP 请求（详见下节） |

---

## AI 操作工作流

所有 AI 操作遵循统一流程：**提交 → 分析（问答）→ 生成 Diff → 预览 → 应用**

### 删除函数（Delete）

1. 右键目标函数节点 → **Delete**
2. 弹出确认对话框，点击 **Confirm Delete**
3. AI 分析调用链，询问如何处理调用方（保留原调用 / 直接删除 / 手动处理）
4. 回答问题后 AI 生成 diff（修改所有调用方文件）
5. 右面板显示 diff 预览，确认后点击 **Apply Changes**
6. 画布自动更新，删除的节点消失

### 添加分支（Add Branch）

1. 右键目标函数节点 → **Add Branch**
2. AI 提问（顺序回答）：
   - 触发新分支的条件表达式（如 `data.priority > 3`）
   - 新分支的功能描述（自然语言）
   - 新函数放在哪个 `.py` 文件中
3. AI 生成新函数代码 + 在原函数中插入条件判断
4. 预览 diff → Apply

### 插入中间函数（Add Insert）

1. **单击**画布上任意蓝色调用边
2. 确认插入点后，AI 提问：
   - 新中间函数的功能描述
   - 目标文件
3. AI 生成新函数，并在原调用链中插入（A → 新函数 → B）
4. 预览 diff → Apply

### 替换为外部 API（Replace with API）

1. 点击左下角工具栏 **+ Import External API**
2. 填写 API 信息（名称、端点 URL、Method、输入/输出 Schema 字段）
3. 将绿色 ExternalAPINode 拖拽到要替换的函数节点上
4. AI 分析 Schema 差异，生成适配器代码
5. 预览 diff → Apply

### 生成 pytest 测试文件（Generate Test）

1. 左侧 Entry Points 列表中，鼠标悬停目标路由
2. 点击出现的 **🧪** 按钮
3. AI 提问：
   - 测试场景（仅成功路径 / 仅错误路径 / 成功+错误路径）
   - 测试文件保存路径（默认 `tests/test_{filename}.py`）
4. AI 生成 pytest 测试文件（包含 `TestClient` + 真实请求用例）
5. Apply 后文件写入项目目录

### AI 问答界面说明

- **选择题**：点击选项即可选中（高亮蓝色）
- **自定义输入**：点击「自定义输入…」按钮，出现文本框，输入自定义内容
- **所有问题回答完毕后**，点击 **Generate →** 触发代码生成（约 10–30 秒）
- 生成中显示「AI is thinking…」动画

---

## 路由测试器

内置类 Swagger "Try it out" 功能，无需离开 CodeFlow 即可测试你的 FastAPI 路由。

### 使用方法

1. 左侧 Entry Points 中，鼠标悬停目标路由
2. 点击出现的 **▷** 按钮（绿色）
3. 右侧面板自动切换到 **Tester** 标签
4. 填写 **Base URL**（你的 FastAPI 应用地址，如 `http://localhost:8000`）
   - Base URL 会自动保存到浏览器 localStorage，下次打开无需重填
5. 表单自动从 Schema 生成输入字段（无需手写 JSON）
6. 点击 **▷ Send POST**（或对应的 HTTP Method）
7. 右侧显示响应状态码 + 响应时间 + JSON 结果

### 路由测试器工作原理

```
浏览器 → Codeflow 后端 /proxy → 你的 FastAPI 应用
```

请求通过 Codeflow 后端的代理端点转发，绕过浏览器的 CORS 限制，无需修改你的应用配置。

> **前提：** 你要测试的 FastAPI 应用必须已经在运行（在本机任意端口）。

---

## 操作历史与回滚

### 查看历史

顶部导航栏右侧显示所有已执行的操作 chip，颜色表示类型：
- 🔵 `replace` — 节点替换
- 🔴 `delete` — 函数删除
- 🟡 `add_*` — 添加操作
- 🟢 `generate_test` — 测试生成

### 回滚到某个 Checkpoint

1. 点击顶部任意已应用的操作 chip（绿色 `applied` 状态）
2. 弹出确认对话框：**"此操作不可逆，确认后将还原文件至该操作前的状态"**
3. 点击 **确认回滚**
4. Codeflow 将该操作的 `old_content` 重新写入对应文件
5. 图谱自动重新解析，反映还原后的代码状态

> **注意：** 回滚仅还原该单次操作修改的文件，不影响其他操作的文件。

---

## 已知限制

| 限制 | 说明 | 建议 |
|------|------|------|
| **仅支持 Python** | AST 解析器仅处理 `.py` 文件 | 使用 Python 项目 |
| **内存状态** | 后端重启后所有项目/会话丢失 | 不要在操作途中重启后端 |
| **入口点检测** | 仅检测 FastAPI `app = FastAPI()` 和 `router = APIRouter()` 装饰的路由 | 其他框架暂不支持 |
| **AI API 依赖** | 依赖 Moonshot API，若 API 限速（429）需等待重试 | 操作失败时稍后重试 |
| **无 git 集成** | Apply 直接写文件，不创建 commit | 建议操作前手动 commit |
| **Windows 端口问题** | 某些情况下端口被 ghost 进程占用 | 换用其他端口号 |

---

## 常见问题

### Q: 加载项目后 Entry Points 为空？

**A:** 请确认：
1. 项目使用了 FastAPI，并有 `app = FastAPI()` 或 `router = APIRouter()` 实例
2. 路由函数使用了 `@app.get/post/...` 或 `@router.get/post/...` 装饰器
3. 项目路径正确（绝对路径，无多余空格）

### Q: AI 操作后节点没有消失（删除无效）？

**A:** 最可能的原因是前端连接到了旧版后端。请检查：
1. 右侧面板 AI 标签是否显示红色错误信息
2. 后端终端是否有 500 错误输出
3. 尝试重新加载项目（重新输入路径点 Load）

### Q: 生成 Diff 时显示 429 错误？

**A:** Moonshot API 限速，稍等片刻后重试操作即可。

### Q: Apply Changes 后代码变化了，但图谱没更新？

**A:** 图谱在 Apply 后会自动重新解析项目。如果没有更新：
1. 检查右侧面板是否显示错误
2. 手动重新加载项目（重新输入路径点 Load）

### Q: 测试器（▷）发送请求后显示 502？

**A:** 你要测试的 FastAPI 应用没有运行，或 Base URL 填写有误。请先启动目标应用，然后确认 Base URL 和端口号正确。

### Q: 路由测试器无法显示请求体字段？

**A:** 该路由的参数类型没有被识别为 Pydantic Schema（可能是 Query 参数或 Path 参数）。路径参数会在"Path Parameters"区域单独显示。

---

## 项目结构参考

```
CodeFlow/
├── backend/
│   ├── src/
│   │   ├── application.py          # FastAPI 应用工厂
│   │   ├── models/domain.py        # 所有 Pydantic 领域模型
│   │   ├── routers/
│   │   │   ├── project.py          # GET/POST /project
│   │   │   ├── session.py          # POST /session
│   │   │   ├── operation.py        # POST /operation, /apply, /rollback 等
│   │   │   └── proxy.py            # POST /proxy（路由测试器转发）
│   │   └── services/
│   │       ├── parser/             # astroid AST 解析 + FastAPI 实例检测
│   │       ├── session/            # 内存 Store（project/session/operation）
│   │       └── ai/
│   │           ├── analyzer.py     # 程序化生成澄清问题
│   │           ├── generator.py    # Moonshot API → FileDiff 生成
│   │           └── prompts.py      # 所有 LLM Prompt 模板
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.tsx                 # 根组件，所有事件连线
│   │   ├── components/
│   │   │   ├── edges/              # CallEdge / DataFlowEdge 渲染
│   │   │   ├── nodes/              # FunctionNode / SchemaNode / ExternalAPINode
│   │   │   ├── panels/
│   │   │   │   ├── LeftSidebar.tsx
│   │   │   │   ├── RightPanel.tsx
│   │   │   │   ├── AIConversation.tsx   # AI 问答表单
│   │   │   │   ├── DiffPreview.tsx      # Diff 预览
│   │   │   │   └── RouteTestPanel.tsx   # 路由测试器
│   │   │   ├── nav/TopNav.tsx      # 操作历史 chips
│   │   │   └── ide/                # Monaco 编辑器面板
│   │   ├── hooks/
│   │   │   ├── useOperation.ts     # 操作生命周期管理
│   │   │   ├── useProject.ts       # 项目解析
│   │   │   └── useSession.ts       # 会话管理
│   │   ├── services/api.ts         # 后端 HTTP 客户端
│   │   ├── store/index.ts          # Zustand 全局状态
│   │   ├── types/index.ts          # 所有 TypeScript 类型定义
│   │   └── utils/projectToFlow.ts  # project → ReactFlow nodes/edges 转换
│   └── vite.config.ts              # 开发服务器 + 代理配置
├── tests/                          # 后端集成测试（Phase 0–6）
├── example/TestProject/            # 示例 Python 项目（FastAPI 任务管理器）
└── GUIDE.md                        # 本文件
```

---

*CodeFlow — Built with Claude Code (Anthropic Harness Engineering)*
