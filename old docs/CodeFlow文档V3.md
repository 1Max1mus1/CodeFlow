完美！让我整合所有内容，生成**完整且详细的技术文档 v3.0**。

------

# 📘 CodeFlow 完整技术文档 v3.0

## 可视化代码依赖重构工具 - 详细设计与实现方案

---

## 🆕 V3.0 更新说明

**本次重大更新（2026-01-21）**：

✅ **三层分离视图体系** - 不再是混合节点展开/折叠，而是完全独立的三个视图
✅ **函数视图泳道布局** - 创新的垂直泳道式布局，清晰展示跨文件调用关系
✅ **动态折叠机制** - 智能展开相关泳道，避免信息过载
✅ **视图导航系统** - 面包屑+Tab切换+渐进式钻取
✅ **核心价值聚焦** - 强化"跨文件函数调用可视化"的产品定位

**主要修改章节**：
- 3.1 主界面布局 - 增加视图切换Tab和面包屑导航
- 3.2 依赖图节点设计 - 完全重写为三层视图体系
- 保持其他章节架构不变

---


## 可视化代码依赖重构工具 - 详细设计与实现方案

------

## 目录

1. [产品概述](https://claude.ai/chat/3e83eea2-900b-4682-92c1-26b83b9b96ca#1-产品概述)
2. [核心功能架构](https://claude.ai/chat/3e83eea2-900b-4682-92c1-26b83b9b96ca#2-核心功能架构)
3. [详细功能设计](https://claude.ai/chat/3e83eea2-900b-4682-92c1-26b83b9b96ca#3-详细功能设计)
4. [特性1：异步/同步调用检测](https://claude.ai/chat/3e83eea2-900b-4682-92c1-26b83b9b96ca#4-特性1异步同步调用检测)
5. [特性2：数据结构Diff可视化](https://claude.ai/chat/3e83eea2-900b-4682-92c1-26b83b9b96ca#5-特性2数据结构diff可视化)
6. [技术实现方案](https://claude.ai/chat/3e83eea2-900b-4682-92c1-26b83b9b96ca#6-技术实现方案)
7. [Demo Example](https://claude.ai/chat/3e83eea2-900b-4682-92c1-26b83b9b96ca#7-demo-example)
8. [开发计划](https://claude.ai/chat/3e83eea2-900b-4682-92c1-26b83b9b96ca#8-开发计划)

------

## 1. 产品概述

### 1.1 产品定位

CodeFlow 是一款基于 Web 的代码可视化与重构工具，通过**依赖图 + AI 辅助**的方式，帮助开发者：

- 🔍 快速理解复杂项目架构
- 🔧 安全、直观地重构代码结构
- 👥 提升团队协作中的代码审查效率
- 🐛 发现潜在的逻辑问题和代码坏味道

### 1.2 核心价值主张

**"从拖拽依赖图到自动生成代码"** - 降低重构的技术门槛和心智负担

### 1.3 目标用户场景

- **高效理解程序架构**：新人接手遗留代码
- **团队协作重构**：多人协同修改复杂项目
- **辅助代码审查**：可视化展示 PR 的影响范围
- **API 迁移重构**：从旧 API 迁移到新 API（如 magic_pdf → MinerU）

------

## 2. 核心功能架构

### 2.1 系统整体架构

```
┌─────────────────────────────────────────────────────┐
│                   CodeFlow 系统                      │
├──────────────┬──────────────┬───────────────────────┤
│  项目解析器   │  可视化引擎   │   AI辅助系统          │
├──────────────┼──────────────┼───────────────────────┤
│ • AST解析    │ • 依赖图渲染  │ • 代码理解（RAG）      │
│ • 关系提取   │ • 交互式编辑  │ • 重构建议             │
│ • 增量更新   │ • Diff可视化  │ • 错误检测             │
│ • 类型推断   │ • 版本对比    │ • 适配器生成           │
└──────────────┴──────────────┴───────────────────────┘
         │              │                  │
         └──────────────┴──────────────────┘
                        │
              ┌─────────▼─────────┐
              │   本地文件系统     │
              │  (MVP无后端存储)   │
              └───────────────────┘
```

### 2.2 功能模块清单

| 模块             | 功能                           | 优先级 |
| ---------------- | ------------------------------ | ------ |
| **代码解析引擎** | AST解析、关系提取、类型推断    | P0     |
| **依赖图可视化** | 节点渲染、连接线管理、拖拽交互 | P0     |
| **异步调用检测** | sync/async冲突检测、影响链分析 | P0     |
| **数据结构适配** | 类型对比、字段映射、适配器生成 | P0     |
| **AI助手**       | 侧边栏对话、问题检测、代码建议 | P1     |
| **Diff预览**     | 代码差异展示、批量修改         | P1     |
| **版本对比**     | Git集成、依赖图diff            | P2     |

------

## 3. 详细功能设计

### 3.1 主界面布局

```
┌────────────────────────────────────────────────────────────────┐
│ 🎨 CodeFlow                    project.zip  [⚙️设置] [❓帮助]   │
│     📊 24 functions | 6 classes | 3 modules   [💾待保存: 2]    │
├────────────────────────────────────────────────────────────────┤
│ 面包屑: CodeFlow / 📦 所有模块 / ⚙️ 函数视图                   │
├────────────────────────────────────────────────────────────────┤
│ 视图切换: [📦 模块视图] [🏛️ 类视图] [⚙️ 函数视图 ●]          │
├────────┬───────────────────────┬───────────────────────────────┤
│        │                       │                               │
│  文件树 │    依赖图画布          │      详情 & AI助手侧边栏      │
│  📁src │   (当前视图)          │   ⚙️ get_status() 详情        │
│  ├─main│                       │   ┌─────────────────────┐    │
│  ├─utils│  [根据视图显示]       │   │ 📍 位置             │    │
│  └─api │   不同布局            │   │ • api_client.py     │    │
│        │                       │   │ • Line 145-178      │    │
│  [🔍搜索]│  [🔎放大] [📏适配]    │   │                     │    │
│        │  [📸快照] [⏮️撤销]    │   │ 💬 AI 分析          │    │
│        │                       │   │ "这个函数负责..."    │    │
│        │                       │   └─────────────────────┘    │
│        │                       │   🔔 检测到的问题 (2)        │
│        │                       │   ⚠️ async_sync_conflict    │
│        │                       │   ⚠️ missing_field_bbox      │
├────────┴───────────────────────┴───────────────────────────────┤
│  底部工具栏                                                     │
│  [−] ━━●━━ [+]  [🔎 适配]  [📸 快照]  [⏮️ 撤销]        [重置]  │
└────────────────────────────────────────────────────────────────┘
```

**布局特点：**

- **新增**：顶部面包屑导航，显示当前位置和层级
- **新增**：视图切换Tab，在模块/类/函数三层视图间切换
- 三栏布局，中间画布根据当前视图显示不同布局
- 右侧改为"详情 & AI助手"，点击节点时显示详情面板
- 文件树支持过滤（只显示被选中节点相关的文件）
- 底部工具栏提供缩放、快照、撤销等操作

------

### 3.2 三层分离的视图体系设计

**设计理念**：三层视图完全独立，专注展示不同粒度的调用关系。用户通过全局切换或点击节点在视图间导航。

**核心价值**：
> "在IDE中需要一个一个找函数才知道调用关系，在CodeFlow中可以直接看到跨文件的函数调用链"

------

#### 3.2.1 视图1：模块级视图（📦 Module View）

**用途**：展示项目的文件间依赖关系，适合理解整体架构

**布局方式**: 
- 节点：每个文件/模块一个节点
- 连接线：import/from导入关系
- 排列：自动布局（力导向图或分层布局）

**节点设计**:
```
┌─────────────────────────────────┐
│ 📦 api_client.py                │
│                                 │
│ 📊 3 classes | 12 functions     │
│ 📥 imports: requests, json      │
│ 📤 used by: processor.py        │
│                                 │
│ [🔍 钻取到类视图]                │ ← 点击进入该文件的类视图
└─────────────────────────────────┘
```

**交互**:
- 点击节点 → 进入该文件的类视图
- 悬浮显示 → 文件统计信息、主要导出内容
- 右侧面板 → 显示模块的README、主要功能说明

**示例场景**:
```
┌──────────────┐     imports     ┌──────────────┐
│ api_client.py├────────────────→│ utils.py     │
└──────┬───────┘                 └──────────────┘
       │ imports
       ↓
┌──────────────┐
│processor.py  │
└──────────────┘
```

------

#### 3.2.2 视图2：类级视图（🏛️ Class View）

**用途**：展示文件内的类结构和类间关系（继承、组合等）

**布局方式**: 
- 节点：每个类/独立函数一个节点
- 连接线：继承、Mixin、类间调用
- 排列：继承树布局（父类在上）

**节点设计**:
```
┌────────────────────────────────┐
│ 🏛️ DataProcessor               │
│                                │
│ 📌 继承自: BaseProcessor       │
│ 🔧 Mixin: LoggerMixin          │
│                                │
│ 📊 5 methods (3 public)        │
│ ⚡ 2 async methods             │
│                                │
│ [🔍 钻取到函数视图]              │ ← 点击进入该类的函数视图
└────────────────────────────────┘
```

**交互**:
- 点击节点 → 进入该类的函数视图
- 悬浮显示 → 类的方法列表、属性列表
- 右侧面板 → 显示类的文档字符串、设计模式分析

**示例场景**:
```
      ┌─────────────────┐
      │ BaseProcessor   │ (父类)
      └────────┬────────┘
               │ inherits
               ↓
      ┌─────────────────┐
      │ DataProcessor   │
      └─────────────────┘
```

------

#### 3.2.3 视图3：函数级视图（⚙️ Function View） - **核心视图**

**用途**：展示跨文件的函数调用关系链，这是产品的核心价值所在

**布局方式**：**垂直泳道式（Swimlane）**
- 每个文件是一个垂直泳道（从左到右排列）
- 调用关系的箭头从左往右流动
- 动态折叠：只展开当前关注的调用链涉及的文件

**泳道设计**:

**展开状态的泳道**:
```
╔═══════════════════════════╗
║ 📄 api_client.py          ║
╠═══════════════════════════╣
║                           ║
║  ┌─────────────────────┐  ║
║  │ ⚙️ get()            │  ║
║  │ Line 45-67          │  ║
║  │ Returns: Response   │  ║
║  │ Async: ⚡ Yes       │  ║
║  └─────────────────────┘  ║
║           │               ║
║           │ calls         ║
║  ┌────────▼────────────┐  ║
║  │ ⚙️ post()           │  ║
║  │ Line 89-102         │  ║
║  └─────────────────────┘  ║
║                           ║
╚═══════════════════════════╝
```

**折叠状态的泳道**:
```
╔═╗
║a║ ← 文件名竖排（或缩写）
║p║
║i║
║_║
║c║
║l║
║i║
║.║
║.║
╚═╝
  ↑ 鼠标悬浮显示完整文件名和函数数量
```

**跨泳道调用的箭头设计**:

**场景A - 直接调用（相邻泳道）**:
```
[api_client.py]          [processor.py]
┌──────────────┐         ┌──────────────┐
│ get() ───────┼────────→│ parse()      │
└──────────────┘         └──────────────┘
```

**场景B - 跨越折叠泳道（虚线+节点提示）**:
```
[api_client.py]    [折│    [utils.py]
┌──────────────┐    叠│   ┌──────────────┐
│ get()        │     │   │              │
│      ────────┼─→ [•2] ──→│ validate()   │
└──────────────┘     │   └──────────────┘
                     │        ↑
                 tooltip: "途经 processor.py, helpers.py"
```

**函数节点设计（函数视图中）**:
```
┌──────────────────────────────┐
│ ⚙️ get_job_status()           │
│ 📍 api_client.py:45-67        │ ← 文件名+行号
├──────────────────────────────┤
│ Args: job_id: str            │
│ Returns: dict                │
│ Async: ⚡ Yes                │
│ Complexity: 3                │
├──────────────────────────────┤
│ 🔗 Called by: 2 functions    │ ← 点击展开上游
│ 📞 Calls: 3 functions        │ ← 点击展开下游
└──────────────────────────────┘
```

**交互行为（函数视图 - 最重要）**:

**点击函数节点时触发**:
1. **高亮调用链**: 
   - 上游调用者和下游被调用者的函数节点高亮
   - 相关箭头变粗+高亮颜色
   
2. **自动展开相关泳道**:
   - 调用链路径上的所有文件泳道自动展开
   - 无关文件的泳道自动折叠
   
3. **右侧详情面板显示**:
   - 函数代码片段（语法高亮）
   - 参数和返回值详细说明
   - 调用链路径列表（可点击跳转）
   - AI分析："这个函数的作用是..."

**示例：完整的函数级视图（展示核心场景）**

```
╔════════════════╗  ╔════════════════╗  ╔═╗
║ api_client.py  ║  ║ processor.py   ║  ║u║ (折叠)
╠════════════════╣  ╠════════════════╣  ║t║
║ ┌────────────┐ ║  ║ ┌────────────┐ ║  ║i║
║ │get_status()│ ║  ║ │            │ ║  ║l║
║ │Async:⚡    │─╬──╬→│parse_json()│─╬──╬→║
║ └────────────┘ ║  ║ │            │ ║  ║s║
║      │         ║  ║ └────────────┘ ║  ╚═╝
║      │ calls   ║  ║                ║
║      ▼         ║  ║                ║
║ ┌────────────┐ ║  ║                ║
║ │client.get()│ ║  ║                ║
║ │Async:⚡    │ ║  ║                ║
║ └────────────┘ ║  ║                ║
╚════════════════╝  ╚════════════════╝
```

------

#### 3.2.4 视图间导航

**导航方式**:

1. **全局视图切换（顶部工具栏）**:
   ```
   [📦 模块视图] [🏛️ 类视图] [⚙️ 函数视图] ← Tab切换
   ```

2. **渐进式钻取**:
   - 模块视图中点击文件 → 进入该文件的类视图
   - 类视图中点击类 → 进入该类的函数视图
   - 函数视图中点击函数 → 高亮调用链+展开右侧详情

3. **面包屑导航**:
   ```
   CodeFlow / 📦 所有模块 / 🏛️ api_client.py / ⚙️ get_status()
   ```
   点击任意层级可返回上级视图

------

#### 3.2.5 右侧详情面板（配合函数视图）

当用户点击函数节点时，右侧面板显示：

```
┌─────────────────────────────────────┐
│ ⚙️ get_status() 详情                 │
├─────────────────────────────────────┤
│                                     │
│ 📍 位置                              │
│ • 文件: api_client.py               │
│ • 行号: 145-178                     │
│ • 调用者: 2 个函数                   │
│ • 被调用: 3 个函数                   │
│                                     │
│ ─────────────────────────────────  │
│                                     │
│ 📄 代码预览                          │
│ ┌─────────────────────────────────┐ │
│ │ async def get_status(job_id):   │ │
│ │     status_response = await     │ │
│ │         client.get(             │ │
│ │             status_url,         │ │
│ │             params={"job_id"... │ │
│ │     )                           │ │
│ │     status_result = ...         │ │
│ └─────────────────────────────────┘ │
│ [📖 查看完整代码]                    │
│                                     │
│ ─────────────────────────────────  │
│                                     │
│ 🔗 调用链路径                        │
│ ┌─────────────────────────────────┐ │
│ │ 1. process_batch()              │ │
│ │    └→ 2. get_status() [当前]   │ │
│ │         └→ 3. client.get()     │ │
│ │              └→ 4. parse_json()│ │
│ └─────────────────────────────────┘ │
│ 点击任意函数可跳转定位               │
│                                     │
│ ─────────────────────────────────  │
│                                     │
│ 💬 AI 分析                          │
│ "这个函数负责查询异步任务的状态...   │
│  它调用了 MinerU API 的 status     │
│  endpoint，解析返回的 JSON..."      │
│                                     │
│ [❓ 询问AI更多问题]                  │
│                                     │
└─────────────────────────────────────┘
```

------

### 3.3 连接线类型设计

| 关系类型         | 线条样式 | 颜色             | 箭头        | 标识             |
| ---------------- | -------- | ---------------- | ----------- | ---------------- |
| **函数调用**     | 实线     | `#4A90E2` (蓝色) | 单向箭头 →  | 默认             |
| **继承关系**     | 虚线     | `#7B68EE` (紫色) | 空心箭头 ⇢  | `extends`        |
| **引用/导入**    | 点线     | `#50C878` (绿色) | 双向箭头 ↔  | `import`         |
| **待保存修改**   | 加粗实线 | `#FF6B6B` (橙红) | 闪烁动画 ⟹  | `pending`        |
| **待删除关系**   | 删除线   | `#95A5A6` (灰色) | 半透明 -/→  | `delete`         |
| **异步调用冲突** | 波浪线   | `#FFA500` (橙色) | 警告图标 ⚠️→ | `async_conflict` |

------

### 3.4 AI助手侧边栏

#### 3.4.1 对话区（顶部60%）

```
┌─────────────────────────────────┐
│ 💬 与AI对话                      │
├─────────────────────────────────┤
│ 你: create_user 的作用是什么？   │
│                                 │
│ AI: 这个函数负责创建新用户...    │
│     分析了以下内容：             │
│     • 函数签名和参数             │
│     • 调用的其他函数             │
│     • 使用的数据结构             │
│     [📎 相关代码] [📊 调用链]    │
│                                 │
│ 📝 输入问题...        [发送 ↗️]  │
└─────────────────────────────────┘
```

**快捷提问按钮：**

- "这个函数做什么？"
- "为什么A调用B？"
- "如何重构这段代码？"
- "这里有什么问题？"
- "这个schema是什么结构？"

#### 3.4.2 问题检测区（底部40%）

```
┌─────────────────────────────────┐
│ 🔍 检测到的问题                  │
├─────────────────────────────────┤
│ ⚠️ 异步调用冲突 (Severity: High)│
│    default_pdf_analyzer() [sync]│
│    → _call_mineru_api() [async] │
│    [查看] [修复建议]             │
│                                 │
│ ⚠️ 数据结构不匹配                │
│    bbox 字段缺失                 │
│    [查看] [配置默认值]           │
│                                 │
│ ℹ️ 复杂度过高: process_order()   │
│    循环复杂度: 15 (建议<10)      │
│    [查看] [重构建议]             │
└─────────────────────────────────┘
```

------

## 4. 特性1：异步/同步调用检测

### 4.1 核心工作流程

```
用户拖拽: funcA (同步) → funcB (异步)
    ↓
┌──────────────────────────────────────────────┐
│ Step 1: AI 深度分析影响链                     │
│ - 向上追溯所有调用 funcA 的函数               │
│ - 理解每层的：循环、调用关系、schemas、      │
│   数据结构、错误处理                          │
│ - 检测每一层的修改复杂度                      │
│ - 标记"安全修改层"和"需要用户决策层"          │
└──────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────┐
│ Step 2: 双重展示（图 + 列表）                 │
│ 左侧: 依赖图高亮影响路径                      │
│ 右侧: 侧边栏显示详细影响列表                  │
└──────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────┐
│ Step 3: 分层修复策略（智能边界）              │
│ Layer 1 (当前层): 自动改为 async             │
│ Layer 2-N: 显示预览，用户选择应用前N层       │
│ Layer N+1: 提示"已达上下文限制"              │
│           建议"先应用前N层，测试后再继续"     │
└──────────────────────────────────────────────┘
```

------

### 4.2 界面设计（双视图 - 简便版）

#### 4.2.1 左侧：依赖图可视化

```
┌──────────────────────────────────────────────┐
│ 📊 异步影响分析                               │
├──────────────────────────────────────────────┤
│                                              │
│    [Layer 4] 🔴 需要决策                     │
│    ┌──────────────────┐                     │
│    │ api_endpoint()   │ ← ⚠️ FastAPI路由     │
│    └────────┬─────────┘    (需确认)          │
│             │ (虚线 - 待确认)                │
│             ↓                                │
│    [Layer 3] 🟡 影响中                       │
│    ┌──────────────────┐                     │
│    │ process_batch()  │ ← 循环调用            │
│    └────────┬─────────┘    (AI建议)          │
│             │ (黄色线)                        │
│             ↓                                │
│    [Layer 2] 🟢 自动修复                     │
│    ┌──────────────────┐                     │
│    │ process_file()   │ ← ✓ 安全              │
│    └────────┬─────────┘                     │
│             │ (绿色线)                        │
│             ↓                                │
│    [Layer 1] ✅ 当前修改                     │
│    ┌────────────────────────┐               │
│    │ default_pdf_analyzer() │               │
│    └────────┬───────────────┘               │
│             │ (橙红闪烁 - 新建异步)           │
│             ↓                                │
│    ┌─────────────────────┐                  │
│    │ _call_mineru_api()  │ ⚡                │
│    └─────────────────────┘                  │
│                                              │
└──────────────────────────────────────────────┘
```

**图例说明：**

- 🟢 绿色线：安全修改层（自动修复）
- 🟡 黄色线：需要AI建议（如循环中调用）
- 🔴 红色线：需要用户确认（涉及框架）
- 虚线：待确认的修改
- 实线：已确认的修改

#### 4.2.2 右侧：侧边栏详细信息（简化版）

```
┌─────────────────────────────────────────────┐
│ ⚠️ 异步调用冲突检测                          │
├─────────────────────────────────────────────┤
│                                             │
│ 📍 当前修改                                  │
│ ✓ default_pdf_analyzer()                   │
│   → 调用 _call_mineru_api() [async]        │
│   → 自动改为: async def                     │
│   [✅ 已应用]                                │
│                                             │
│ ─────────────────────────────────────────  │
│                                             │
│ 🔼 影响链分析 (检测到4层)                    │
│                                             │
│ Layer 2: process_file() ──── 🟢 安全       │
│ • 修改: def → async def                    │
│ • 调用点: 2处                               │
│ • AI分析: 无外部依赖，可自动修复             │
│   [🔧 包含在自动修复]                        │
│                                             │
│ Layer 3: process_batch() ──── 🟡 需建议    │
│ • 修改: def → async def                    │
│ • 特殊情况: for循环中调用process_file()     │
│ • AI分析:                                   │
│   - 当前: 顺序执行                          │
│   - 建议: asyncio.gather并发 (快3-10x)     │
│   [📋 查看两种方案]                          │
│                                             │
│ Layer 4: api_endpoint() ──── 🔴 需确认     │
│ • 修改: def → async def                    │
│ • 风险: FastAPI路由入口                     │
│ • AI分析: FastAPI支持async，但需测试        │
│   [⚠️ 需要确认]                             │
│                                             │
│ ⚠️ 上下文限制提示                            │
│ 已分析4层，预计token使用: 6.2k/8k          │
│ 建议操作:                                   │
│ ├─ 应用Layer 1-3 (推荐) ← 点击选择层数      │
│ ├─ 应用Layer 1-2 (保守)                    │
│ └─ 全部应用 (谨慎)                          │
│                                             │
│ 💡 分批策略:                                 │
│ 建议先应用前3层，测试通过后再继续向上追溯    │
│                                             │
│ ─────────────────────────────────────────  │
│                                             │
│ [✅ 应用选中层] [🔍 预览修改] [❌ 取消]       │
└─────────────────────────────────────────────┘
```

------

### 4.3 AI深度理解能力

#### 4.3.1 需要理解的代码元素

```python
class DeepCodeAnalyzer:
    """
    AI需要深度理解的代码元素
    """
    def analyze_function_context(self, function_node):
        return {
            # 1. 循环结构
            'loops': self._extract_loops(function_node),
            # for/while循环，嵌套层级
            
            # 2. 调用关系
            'calls': self._extract_function_calls(function_node),
            # 调用了哪些函数，调用位置，参数传递
            
            # 3. Schemas/数据结构
            'schemas': self._extract_data_structures(function_node),
            # 使用的类、Pydantic模型、TypedDict等
            
            # 4. 数据流
            'data_flow': self._analyze_data_flow(function_node),
            # 变量如何在函数间传递、转换
            
            # 5. 错误处理
            'error_handling': self._extract_error_handling(function_node),
            # try/except结构，异常类型
            
            # 6. 返回值
            'return_analysis': self._analyze_returns(function_node),
            # 返回值类型、多返回路径
        }
```

#### 4.3.2 示例：AI理解循环结构

**原代码：**

```python
def process_batch(file_list: List[str]) -> List[Result]:
    results = []
    for file in file_list:
        result = process_file(file)  # 要改成async
        if result.success:
            results.append(result)
        else:
            logger.error(f"Failed: {file}")
    return results
```

**AI分析结果：**

```json
{
  "loop_type": "for",
  "iteration_var": "file",
  "iterable": "file_list",
  "loop_body_calls": [
    {
      "function": "process_file",
      "args": ["file"],
      "return_used": true,
      "conditional_logic": "result.success check"
    }
  ],
  "side_effects": ["results.append", "logger.error"],
  "data_dependencies": {
    "results": "accumulator pattern"
  },
  "async_conversion_strategy": {
    "safe_option": "sequential_await",
    "optimized_option": "asyncio.gather_with_error_handling"
  }
}
```

**AI生成的两种方案：**

```python
# 方案A：保守 - 顺序执行（默认生成）
async def process_batch(file_list: List[str]) -> List[Result]:
    results = []
    for file in file_list:
        result = await process_file(file)  # 顺序等待
        if result.success:
            results.append(result)
        else:
            logger.error(f"Failed: {file}")
    return results


# 方案B：优化 - 并发执行（用户选择）
async def process_batch(file_list: List[str]) -> List[Result]:
    results = []
    
    # 并发处理，但保留原有的错误处理逻辑
    tasks = [process_file(file) for file in file_list]
    task_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for file, result in zip(file_list, task_results):
        if isinstance(result, Exception):
            logger.error(f"Failed: {file}, Error: {result}")
        elif result.success:
            results.append(result)
        else:
            logger.error(f"Failed: {file}")
    
    return results
```

------

### 4.4 分层修复策略（上下文窗口管理）

#### 4.4.1 Layer风险评估

```python
class LayerRiskAnalyzer:
    def calculate_risk_score(self, function_node, context):
        """
        计算修改风险分数
        """
        score = 0
        reasons = []
        
        # 检测1: 是否是框架入口
        if self._is_framework_entry(function_node):
            score += 10
            reasons.append("FastAPI/Flask/Django路由入口")
        
        # 检测2: 装饰器复杂度
        decorators = len(function_node.decorator_list)
        if decorators > 0:
            score += decorators * 2
            reasons.append(f"有{decorators}个装饰器")
        
        # 检测3: 循环调用
        if self._has_loop_calls(function_node):
            score += 3
            reasons.append("在循环中调用")
        
        # 检测4: 外部调用者数量
        callers = len(context.get('callers', []))
        if callers > 5:
            score += 5
            reasons.append(f"被{callers}个函数调用")
        
        # 检测5: 函数复杂度
        complexity = self._calculate_complexity(function_node)
        if complexity > 10:
            score += complexity // 2
            reasons.append(f"复杂度{complexity}")
        
        # 分级
        if score == 0:
            return 'AUTO', reasons  # 🟢 自动修复
        elif score < 10:
            return 'SUGGEST', reasons  # 🟡 AI建议
        else:
            return 'CONFIRM', reasons  # 🔴 需确认
```

#### 4.4.2 上下文窗口管理

```python
class ContextWindowManager:
    MAX_TOKENS = 8000  # Claude上下文限制
    SAFETY_MARGIN = 0.8  # 80%阈值
    
    def should_stop_tracing(self, analyzed_layers, code_content):
        """
        判断是否应该停止向上追溯
        """
        # 估算当前token使用
        current_tokens = self._estimate_tokens(code_content)
        limit = self.MAX_TOKENS * self.SAFETY_MARGIN
        
        if current_tokens > limit:
            return True, {
                'reason': 'context_limit',
                'message': f'已分析{len(analyzed_layers)}层，token使用{current_tokens}/{self.MAX_TOKENS}',
                'suggestion': '建议先应用当前修改，测试后再继续'
            }
        
        if len(analyzed_layers) > 10:
            return True, {
                'reason': 'depth_limit',
                'message': f'调用链过深(>{len(analyzed_layers)}层)',
                'suggestion': '建议重构架构，减少调用层级'
            }
        
        return False, None
    
    def _estimate_tokens(self, code_content):
        """
        估算代码的token数量
        粗略算法: 字符数 / 4
        """
        total_chars = sum(len(code) for code in code_content.values())
        return total_chars // 4
```

#### 4.4.3 分批应用界面

```
┌─────────────────────────────────────────────┐
│ 📊 选择应用层级                              │
├─────────────────────────────────────────────┤
│                                             │
│ 已分析4层，请选择应用范围:                   │
│                                             │
│ ○ 应用Layer 1 (仅当前)                      │
│   └─ 修改1个函数                             │
│   └─ 风险: 无                                │
│   └─ 测试成本: 低                            │
│                                             │
│ ○ 应用Layer 1-2 (保守)                      │
│   └─ 修改2个函数                             │
│   └─ 风险: 低                                │
│   └─ 测试成本: 低                            │
│                                             │
│ ● 应用Layer 1-3 (推荐) ← AI推荐             │
│   └─ 修改3个函数                             │
│   └─ 风险: 中 (包含循环优化)                 │
│   └─ 测试成本: 中                            │
│   └─ token使用: 6.2k/8k (78%)               │
│                                             │
│ ○ 应用Layer 1-4 (全部)                      │
│   └─ 修改4个函数                             │
│   └─ 风险: 高 (涉及API入口)                  │
│   └─ 测试成本: 高                            │
│   └─ token使用: 7.8k/8k (98%) ⚠️            │
│                                             │
│ ─────────────────────────────────────────  │
│                                             │
│ 💡 建议工作流:                               │
│ 1. 应用Layer 1-3                            │
│ 2. 运行单元测试                              │
│ 3. 如果通过，再处理Layer 4                  │
│                                             │
│ [✅ 应用选中层级] [🔍 预览代码] [❌ 取消]     │
└─────────────────────────────────────────────┘
```

------

### 4.5 循环异步处理（最不容易出错）

#### 4.5.1 检测与分析

```python
class LoopAsyncAnalyzer:
    def analyze_loop_async_call(self, loop_node, async_call):
        """
        分析循环中的异步调用
        """
        analysis = {
            'loop_type': type(loop_node).__name__,  # For/While
            'iteration_count': self._estimate_iterations(loop_node),
            'call_location': 'loop_body',
            'data_dependencies': self._check_dependencies(loop_node),
            'error_handling': self._extract_error_handling(loop_node),
            'performance_impact': self._estimate_impact(loop_node, async_call)
        }
        
        # 生成两种方案
        return {
            'safe_strategy': self._generate_sequential(loop_node, async_call),
            'optimized_strategy': self._generate_concurrent(loop_node, async_call),
            'analysis': analysis
        }
```

#### 4.5.2 默认生成：保守方案

```python
def _generate_sequential(self, loop_node, async_call):
    """
    生成顺序执行的代码（最不容易出错）
    """
    return {
        'code': self._transform_to_sequential_await(loop_node),
        'pros': [
            "保持原有执行顺序",
            "错误处理逻辑不变",
            "不会资源耗尽",
            "调试简单"
        ],
        'cons': [
            "性能无提升",
            "如果单次耗时长，总耗时=N*单次"
        ],
        '适用场景': [
            "文件数量<100",
            "单次处理<1秒",
            "对顺序有严格要求"
        ]
    }
```

**生成示例：**

```python
# 原代码
for item in items:
    result = process(item)
    handle(result)

# 生成代码（保守）
for item in items:
    result = await process(item)  # 仅添加await
    handle(result)
```

#### 4.5.3 优化方案：并发执行

```python
def _generate_concurrent(self, loop_node, async_call):
    """
    生成并发执行的代码（性能优化）
    """
    return {
        'code': self._transform_to_concurrent(loop_node),
        'pros': [
            "性能提升3-10x",
            "充分利用IO等待时间",
            "支持批量控制"
        ],
        'cons': [
            "需要测试并发安全性",
            "错误处理更复杂",
            "调试难度增加"
        ],
        '注意事项': [
            "确保process()无副作用",
            "检查是否有共享状态",
            "建议限制并发数(如5-10)"
        ]
    }
```

**生成示例：**

```python
# 原代码
results = []
for item in items:
    result = process(item)
    if result.success:
        results.append(result)
    else:
        logger.error(f"Failed: {item}")

# 生成代码（优化）
import asyncio

results = []

# 分批并发，限制并发数
MAX_CONCURRENT = 5
for i in range(0, len(items), MAX_CONCURRENT):
    batch = items[i:i+MAX_CONCURRENT]
    
    # 并发执行当前批次
    batch_results = await asyncio.gather(
        *[process(item) for item in batch],
        return_exceptions=True  # 单个失败不影响其他
    )
    
    # 保留原有的结果处理逻辑
    for item, result in zip(batch, batch_results):
        if isinstance(result, Exception):
            logger.error(f"Failed: {item}, Error: {result}")
        elif result.success:
            results.append(result)
        else:
            logger.error(f"Failed: {item}")
```

#### 4.5.4 用户选择界面

```
┌─────────────────────────────────────────────┐
│ 🔄 循环中的异步调用优化                      │
├─────────────────────────────────────────────┤
│                                             │
│ 检测到: process_batch() 在循环中调用异步函数 │
│                                             │
│ 原代码:                                     │
│   for file in file_list:                   │
│       result = process_file(file)          │
│                                             │
│ 🤖 AI 分析:                                  │
│ • 预计迭代次数: 未知 (运行时确定)           │
│ • 单次耗时: 约2-5秒 (涉及API调用)           │
│ • 如果100个文件 → 总耗时200-500秒           │
│                                             │
│ ─────────────────────────────────────────  │
│                                             │
│ ✅ 方案A: 顺序执行 (默认，已生成)            │
│                                             │
│ 修改方式:                                   │
│   for file in file_list:                   │
│       result = await process_file(file)    │
│                                             │
│ ✓ 优点: 安全，逻辑不变                      │
│ ✗ 缺点: 性能无提升                          │
│                                             │
│ 适用场景:                                   │
│ • 文件数量<100                              │
│ • 对执行顺序有要求                          │
│ • 优先保证稳定性                            │
│                                             │
│ ─────────────────────────────────────────  │
│                                             │
│ 🚀 方案B: 并发执行 (可选)                    │
│                                             │
│ 修改方式:                                   │
│   # 分批并发，每批5个                        │
│   for batch in chunks(file_list, 5):       │
│       results = await asyncio.gather(...)  │
│                                             │
│ ✓ 优点: 性能提升3-10x                       │
│ ✗ 缺点: 需要测试并发安全性                  │
│                                             │
│ 注意事项:                                   │
│ • 确保process_file()无副作用                │
│ • 检查是否有共享状态                        │
│ • 建议先用小数据集测试                      │
│                                             │
│ [📋 查看完整代码]                            │
│                                             │
│ ─────────────────────────────────────────  │
│                                             │
│ 您的选择:                                   │
│ ○ 使用方案A (保守，推荐)                    │
│ ○ 使用方案B (性能优化)                      │
│                                             │
│ [💾 应用选中方案] [❌ 取消]                  │
└─────────────────────────────────────────────┘
```

------

## 5. 特性2：数据结构Diff可视化

### 5.1 核心工作流程

```
用户拖拽: funcA() → funcB()
    ↓
┌───────────────────────────────────────────────┐
│ Step 1: 提取返回值结构                         │
│ 优先级1: 读取类型注解                          │
│ 优先级2: AI分析函数体推断                      │
│ 优先级3: 用户提供示例JSON (fallback)          │
└───────────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────────┐
│ Step 2: AI智能映射                             │
│ - 语义匹配字段 (content ↔ text)              │
│ - 检测嵌套/数组结构差异                        │
│ - 识别需要转换的字段 (page_idx+1)             │
│ - 标记缺失字段                                 │
│ - 理解schemas和数据结构                        │
└───────────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────────┐
│ Step 3: 生成适配函数                           │
│ - 模拟原函数的处理方式:                        │
│   • 循环结构                                   │
│   • 调用关系                                   │
│   • 错误处理                                   │
│   • 数据验证                                   │
│ - 对每个缺失字段单独询问用户                   │
└───────────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────────┐
│ Step 4: 用户确认与调整                         │
│ - 显示映射关系可视化                           │
│ - 逐个处理缺失字段                             │
│ - 用户可手动调整映射                           │
└───────────────────────────────────────────────┘
```

------

### 5.2 类型推断策略

#### 5.2.1 优先级系统

```python
class TypeInferenceEngine:
    def infer_return_type(self, function_node, context):
        """
        三级优先级推断返回值类型
        """
        # 优先级1: 类型注解
        if function_node.returns:
            annotation = self._parse_annotation(function_node.returns)
            return {
                'source': 'type_annotation',
                'type': annotation,
                'confidence': 1.0
            }
        
        # 优先级2: AI分析函数体
        ai_result = self._ai_analyze_function(function_node, context)
        if ai_result['confidence'] > 0.8:
            return {
                'source': 'ai_inference',
                'type': ai_result['type'],
                'confidence': ai_result['confidence']
            }
        
        # 优先级3: 用户提供示例
        return {
            'source': 'user_input',
            'type': None,
            'confidence': 0.0,
            'action': 'request_example'
        }
```

#### 5.2.2 AI分析函数体

~~~python
def _ai_analyze_function(self, function_node, context):
    """
    AI深度分析函数，推断返回值
    """
    # 提取函数的完整上下文
    function_code = ast.unparse(function_node)
    imports = context.get('imports', [])
    schemas = context.get('schemas', [])
    
    prompt = f"""
你是Python代码分析专家。分析这个函数，推断返回值的数据结构。

## 函数代码
```python
{function_code}
~~~

## 上下文信息

- 导入的模块: {imports}
- 使用的Schema/数据类: {schemas}
- 调用的其他函数: {context.get('calls', [])}

## 分析重点

1. 所有return语句
2. 变量赋值和转换
3. 使用的数据结构 (dict/list/Pydantic模型等)
4. 循环和条件分支

## 输出格式

以JSON返回: {{ "return_type": "类型描述 (如 Dict[str, List[Dict]])", "structure": {{ "字段名": {{ "type": "具体类型", "nested": true/false, "optional": true/false, "example": "示例值", "description": "用途说明" }} }}, "confidence": 0.0-1.0, "reasoning": "推断依据", "alternative_returns": ["其他可能的返回路径"] }} """

```
response = llm.invoke(prompt)
return json.loads(response)
**示例分析结果：**
```json
{
  "return_type": "Tuple[List[KnowDataObject], List[KnowDataObject], LayoutAnalysisMetrics, Response]",
  "structure": {
    "success_list": {
      "type": "List[KnowDataObject]",
      "nested": true,
      "element_structure": {
        "data_type": {"type": "str", "values": ["TEXT", "IMAGE", "TABLE"]},
        "raw_data": {"type": "str"},
        "coord_x1": {"type": "float"},
        "coord_y1": {"type": "float"},
        "coord_x2": {"type": "float"},
        "coord_y2": {"type": "float"},
        "page_start": {"type": "int"},
        "page_end": {"type": "int"},
        "knowledge_id": {"type": "str"}
      }
    },
    "fail_list": {
      "type": "List[KnowDataObject]",
      "nested": true
    }
  },
  "confidence": 0.95,
  "reasoning": "从函数体中的多个return语句和success_list.append()调用推断"
}
```

------

### 5.3 智能字段映射

#### 5.3.1 映射策略

```python
class FieldMapper:
    def map_fields(self, old_structure, new_structure):
        """
        智能映射两个数据结构的字段
        """
        mappings = []
        
        for old_field, old_info in old_structure.items():
            # 1. 精确匹配
            if old_field in new_structure:
                mappings.append({
                    'old': old_field,
                    'new': old_field,
                    'confidence': 1.0,
                    'type': 'exact_match'
                })
                continue
            
            # 2. 语义匹配
            semantic_match = self._semantic_match(
                old_field, 
                old_info,
                new_structure
            )
            if semantic_match['confidence'] > 0.85:
                mappings.append(semantic_match)
                continue
            
            # 3. 结构匹配 (嵌套数组等)
            structural_match = self._structural_match(
                old_field,
                old_info,
                new_structure
            )
            if structural_match:
                mappings.append(structural_match)
                continue
            
            # 4. 标记为缺失
            mappings.append({
                'old': old_field,
                'new': None,
                'confidence': 0.0,
                'type': 'missing',
                'action': 'ask_user'
            })
        
        return mappings
    
    def _semantic_match(self, old_field, old_info, new_structure):
        """
        使用LLM进行语义匹配
        """
        prompt = f"""
判断这两个字段是否表示相同的概念：

字段1: {old_field}
- 类型: {old_info['type']}
- 用途: {old_info.get('description', '')}
- 示例: {old_info.get('example', '')}

候选字段2列表:
{json.dumps(new_structure, indent=2)}

返回JSON:
{{
    "best_match": "字段名或null",
    "confidence": 0.0-1.0,
    "reasoning": "原因"
}}
"""
        result = llm.invoke(prompt)
        parsed = json.loads(result)
        
        if parsed['best_match']:
            return {
                'old': old_field,
                'new': parsed['best_match'],
                'confidence': parsed['confidence'],
                'type': 'semantic_match',
                'reasoning': parsed['reasoning']
            }
        return None
```

#### 5.3.2 映射可视化界面

```
┌────────────────────────────────────────────────────────────────┐
│ 🔍 数据结构映射                                                 │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  旧函数: magic_pdf.parse()        新函数: _call_mineru_api()  │
│  ┌──────────────────────┐         ┌──────────────────────┐   │
│  │ Dict[str, List]      │         │ Dict[str, Any]       │   │
│  ├──────────────────────┤         ├──────────────────────┤   │
│  │                      │         │                      │   │
│  │ "text": [            │ ════╗   │ "content_list": [    │   │
│  │   {                  │     ║   │   {                  │   │
│  │     "content": str ──┼─────╫──→│     "text": str      │   │ ✓ 95%
│  │     "bbox": [float]──┼─ ✗  ║   │     "type": str      │   │
│  │     "page": int    ──┼─────╫──→│     "page_idx": int  │   │ ⚠️ 需转换
│  │   }                  │     ║   │   }                  │   │
│  │ ]                    │     ║   │ ]                    │   │
│  │                      │     ║   │                      │   │
│  │ "images": [...]      │ ════╝   │ (type="image")       │   │ ✓ 结构匹配
│  │ "tables": [...]      │ ════════→│ (type="table")       │   │ ✓ 结构匹配
│  │                      │         │                      │   │
│  └──────────────────────┘         └──────────────────────┘   │
│                                                                │
│  ─────────────────────────────────────────────────────────   │
│                                                                │
│  📊 映射统计                                                   │
│  • 精确匹配: 0个                                               │
│  • 语义匹配: 1个 (content→text, 95%置信度)                    │
│  • 结构匹配: 2个 (images/tables→content_list)                 │
│  • 需转换: 1个 (page→page_idx+1)                              │
│  • 缺失字段: 1个 (bbox)                                        │
│                                                                │
│  [✏️ 手动调整] [💾 确认映射] [🔄 重新分析]                      │
└────────────────────────────────────────────────────────────────┘
```

------

### 5.4 缺失字段处理（逐个询问）

#### 5.4.1 处理流程

~~~python
class MissingFieldHandler:
    def handle_missing_fields(self, missing_fields, original_usage):
        """
        逐个处理缺失字段
        """
        user_decisions = {}
        
        for field in missing_fields:
            # 分析字段在原代码中的用途
            usage_analysis = self._analyze_field_usage(
                field, 
                original_usage
            )
            
            # 生成AI建议
            ai_suggestion = self._generate_suggestion(
                field,
                usage_analysis
            )
            
            # 询问用户
            user_choice = self._ask_user(
                field,
                usage_analysis,
                ai_suggestion
            )
            
            user_decisions[field] = user_choice
        
        return user_decisions
    
    def _analyze_field_usage(self, field_name, code):
        """
        分析字段在原代码中如何被使用
        """
        prompt = f"""
分析字段 "{field_name}" 在代码中的使用情况：

```python
{code}
~~~

返回JSON: {{ "usage_count": 使用次数, "usage_locations": ["位置描述"], "usage_patterns": ["使用模式"], "is_critical": true/false, "impact_if_missing": "影响描述" }} """ result = llm.invoke(prompt) return json.loads(result)

```
#### 5.4.2 单个字段询问界面


┌─────────────────────────────────────────────┐ 
│ ⚠️ 缺失字段 1/3: "bbox"                      │ 
├─────────────────────────────────────────────┤ 
│                                             │ 
│ 📋 字段信息                                  │ 
│ • 字段名: bbox                               │ 
│ • 原类型: List[float] (4个元素)             │ 
│ • 含义: 文本/图片在PDF中的坐标 (x1,y1,x2,y2)│ 
│                                             │ 
│ 🔍 原代码使用分析                            │ 
│ • 使用次数: 35次                             │ 
│ • 主要用途:                                  │ 
│   1. 创建KnowDataObject时设置坐标 (30次)    │ 
│   2. 判断文本是否重叠 (3次)                  │ 
│   3. 计算布局位置 (2次)                      │ 
│ • 关键性: 高 (影响布局分析)                  │ 
│                                             │ 
│ 💡 新API情况                                 │ 
│ • MinerU API 不提供等效字段                 │ 
│ • content_list只有page_idx，无坐标信息      │ 
│                                             │ 
│ ─────────────────────────────────────────  │ 
│                                             │ 
│ 🤖 AI 建议                                   │ 
│                                             │ 
│ 由于坐标信息缺失，建议:                      │ 
│ 1. 如果不需要精确定位，使用默认值            │ 
│ 2. 如果需要精确定位，考虑:                   │ 
│    • 使用PyMuPDF补充坐标计算                 │ 
│    • 要求MinerU添加坐标支持                  │ 
│                                             │ 
│ 推荐: 使用默认值 [0.0, 0.0, 0.0, 0.0]       │ 
│ 原因: 最小化改动，后续可补充                 │ 
│                                             │ 
│ ─────────────────────────────────────────  │ 
│                                             │ 
│ 🎯 您的选择                                  │ 
│                                             │ 
│ ○ 使用 None                                 │ 
│   影响: 访问bbox[0]会报TypeError            │ 
│   需要: 同时修改使用bbox的代码 (35处)        │ 
│                                             │ 
│ ● 使用默认值 [0.0, 0.0, 0.0, 0.0] ← 推荐   │ 
│   影响: 所有元素位置为(0,0)                  │ 
│   优点: 不会报错，改动最小                   │ 
│   缺点: 丢失位置信息                         │ 
│                                             │ 
│ ○ 跳过此字段                                │ 
│   影响: KnowDataObject缺少必填字段           │ 
│   风险: 可能导致运行时错误                   │ 
│                                             │ 
│ ○ 自定义默认值                              │ 
│   x1: [***\*] y1: [\****]                     │ 
│   x2: [***\*] y2: [\****]                     │ 
│                                             │ 
│ ─────────────────────────────────────────  │ 
│                                             │ 
│ 📌 备注 (可选)                               │ 
│ ┌───────────────────────────────────────┐  │ 
│ │ 暂时使用默认值，后续考虑用PyMuPDF补充      │  │ 
│ │ 坐标计算逻辑                            │  │ 
│ └───────────────────────────────────────┘  │ 
│                                             │ 
│ [💾 确认选择] [📋 查看受影响代码] [⏭️ 跳过]  │ 
└─────────────────────────────────────────────┘

```
#### 5.4.3 批量预览
```

┌─────────────────────────────────────────────┐ 
│ 📊 缺失字段处理总结                           │ 
├─────────────────────────────────────────────┤ 
│                                             │ 
│ 已处理 3/3 个缺失字段                        │ 
│                                             │ 
│ 1. bbox → 默认值 [0.0, 0.0, 0.0, 0.0]      │ 
│    备注: 后续补充PyMuPDF计算                 │ 
│                                             │ 
│ 2. metadata → 跳过                          │ 
│    备注: 旧API特有，新API不需要              │ 
│                                             │ 
│ 3. version → 自定义 "1.0"                   │ 
│    备注: 固定版本号                          │ 
│                                             │ 
│ ─────────────────────────────────────────  │ 
│                                             │ 
│ 💡 影响分析                                  │ 
│ • 将影响 45 处代码                           │ 
│ • 需要生成 1 个适配函数                      │ 
│ • 预计增加 ~80 行代码                        │ 
│                                             │ 
│ [✅ 生成适配函数] [✏️ 修改选择] [❌ 取消]     │ 
└─────────────────────────────────────────────┘

```
---

### 5.5 适配函数生成（模拟原函数）

#### 5.5.1 核心生成逻辑
```python
class AdapterGenerator:
    def generate_adapter(
        self,
        old_function,
        new_function,
        mappings,
        missing_field_decisions,
        original_usage_code
    ):
        """
        生成适配器函数，模拟原函数的处理方式
        """
        # 1. 分析原函数的处理模式
        patterns = self._analyze_processing_patterns(original_usage_code)
        
        # 2. 构建prompt
        prompt = self._build_adapter_prompt(
            old_function,
            new_function,
            mappings,
            missing_field_decisions,
            patterns
        )
        
        # 3. 调用LLM生成
        adapter_code = llm.invoke(prompt)
        
        # 4. 验证生成的代码
        validated = self._validate_adapter(adapter_code, patterns)
        
        return validated
    
    def _analyze_processing_patterns(self, code):
        """
        分析原代码的处理模式
        """
        return {
            'loops': self._extract_loop_patterns(code),
            'error_handling': self._extract_error_patterns(code),
            'data_validation': self._extract_validation_patterns(code),
            'logging': self._extract_logging_patterns(code),
            'schemas': self._extract_schema_usage(code)
        }
```

#### 5.5.2 生成Prompt模板

~~~python
ADAPTER_GENERATION_PROMPT = """
你是Python重构专家。用户正在将API A替换为API B，需要你生成适配器函数。

## 任务
生成适配函数，将新API的返回值转换为旧API的格式，**关键是模拟原函数的处理方式**。

## 原函数 (API A)
```python
{old_function_code}
~~~

返回值结构: {old_return_structure}

## 新函数 (API B)

```python
{new_function_code}
```

返回值结构: {new_return_structure}

## 字段映射关系

{field_mappings}

## 缺失字段处理 (用户决策)

{missing_field_decisions}

## 原代码使用方式 (重要 - 需要模拟)

```python
{original_usage_code}
```

处理模式分析: {processing_patterns}

## 要求

1. **模拟原有处理方式**:
   - 保持相同的循环结构 (for/while)
   - 保留错误处理逻辑 (try/except)
   - 保留数据验证步骤
   - 保留日志记录方式
   - 使用相同的Schema/数据类
2. **严格遵守映射规则**:
   - 对于语义匹配的字段，添加注释说明映射关系
   - 对于需要转换的字段 (如page_idx+1)，明确转换逻辑
   - 对于缺失字段，严格按用户选择处理，并添加警告注释
3. **代码质量**:
   - 添加详细的docstring
   - 添加类型注解
   - 每个关键步骤添加注释
   - 保持原有的代码风格
4. **命名规范**:
   - 函数名: `_adapt_{new_api_name}_to_{old_api_name}_format`
   - 参数名: 与新API返回值一致
   - 返回值: 与旧API返回值一致

## 输出

只输出完整的适配函数代码，不要解释。

```python
# 你的代码
```

"""

```
#### 5.5.3 生成示例
**输入：**
- 旧函数: `magic_pdf.parse()`
- 新函数: `_call_mineru_api()`
- 缺失字段: `bbox` → 用户选择默认值 `[0.0, 0.0, 0.0, 0.0]`

**生成的适配函数：**
```python
async def _adapt_mineru_to_magic_pdf_format(
    mineru_result: dict,
    knowledge_id: str,
    bbox_default: List[float] = None
) -> Tuple[List[KnowDataObject], List[KnowDataObject]]:
    """
    适配 MinerU API 返回值为 magic_pdf 格式
    
    模拟原函数 default_pdf_analyzer() 的处理方式:
    - 循环遍历结果列表
    - 按类型分类 (text/image/table)
    - 创建 KnowDataObject 实例
    - 错误处理：单个item失败不影响其他
    
    Args:
        mineru_result: MinerU API 返回的原始数据
            格式: {"content_list": [...], "job_id": "..."}
        knowledge_id: 知识库ID
        bbox_default: bbox字段缺失时的默认值
            默认: [0.0, 0.0, 0.0, 0.0]
    
    Returns:
        Tuple[success_list, fail_list]
        - success_list: 成功解析的 KnowDataObject 列表
        - fail_list: 失败的 KnowDataObject 列表
    
    字段映射关系:
        - content → text (语义匹配, 95%置信度)
        - page → page_idx + 1 (0-based转1-based)
        - bbox → bbox_default (缺失字段，用户选择默认值)
        - images/tables → content_list (结构转换，按type过滤)
    """
    success_list = []
    fail_list = []
    
    # ⚠️ CodeFlow警告: bbox字段缺失
    # 原API (magic_pdf) 提供bbox，但MinerU不提供
    # 用户选择: 使用默认值 [0.0, 0.0, 0.0, 0.0]
    # 影响: 所有文本/图片位置信息丢失
    # 后续建议: 考虑用PyMuPDF补充坐标计算
    if bbox_default is None:
        logger.warning(
            "bbox field missing in MinerU response, "
            "using default value [0.0, 0.0, 0.0, 0.0]"
        )
        bbox_default = [0.0, 0.0, 0.0, 0.0]
    
    try:
        # 获取content_list (对应原来的text/images/tables)
        content_list = mineru_result.get("content_list", [])
        
        # 模拟原函数的循环处理逻辑
        for i, content_item in enumerate(content_list):
            try:
                # 获取类型 (原来通过不同的key区分，现在用type字段)
                content_type = content_item.get("type", "").lower()
                page_idx = content_item.get("page_idx", 0)
                
                # 处理TEXT类型 (模拟原来的text列表处理)
                if content_type == "text":
                    # 字段映射: text → raw_data
                    text_content = content_item.get("text", "")
                    text_level = content_item.get("text_level", 0)
                    
                    # 创建KnowDataObject (与原函数完全一致的方式)
                    data_obj = KnowDataObject(
                        data_type='TEXT',
                        raw_data=text_content,  # 映射: content→text
                        coord_x1=bbox_default[0],  # 缺失字段: 使用默认值
                        coord_y1=bbox_default[1],
                        coord_x2=bbox_default[2],
                        coord_y2=bbox_default[3],
                        page_start=page_idx + 1,  # 转换: 0-based → 1-based
                        page_end=page_idx + 1,
                        line_start=i + 1,
                        line_end=i + 1,
                        knowledge_id=knowledge_id,
                        data_tags=[f"level_{text_level}"] if text_level > 0 else []
                    )
                    success_list.append(data_obj)
                
                # 处理IMAGE类型 (模拟原来的images列表处理)
                elif content_type == "image":
                    img_path = content_item.get("img_path", "")
                    img_caption = content_item.get("img_caption", [])
                    img_footnote = content_item.get("img_footnote", [])
                    
                    # 模拟原函数的路径处理逻辑
                    local_img_path = img_path
                    if img_path.startswith("images/"):
                        images_dir = os.path.join(
                            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                            "images"
                        )
                        knowledge_images_dir = os.path.join(images_dir, knowledge_id)
                        local_img_path = os.path.join(
                            knowledge_images_dir,
                            os.path.basename(img_path)
                        )
                    
                    # 模拟原函数的caption合并逻辑
                    caption_text = " ".join(img_caption) if img_caption else ""
                    footnote_text = " ".join(img_footnote) if img_footnote else ""
                    combined_text = f"{caption_text} {footnote_text}".strip()
                    
                    data_obj = KnowDataObject(
                        data_type='IMAGE',
                        data_url=local_img_path,
                        raw_data=combined_text,
                        coord_x1=bbox_default[0],
                        coord_y1=bbox_default[1],
                        coord_x2=bbox_default[2],
                        coord_y2=bbox_default[3],
                        page_start=page_idx + 1,
                        page_end=page_idx + 1,
                        knowledge_id=knowledge_id,
                        data_tags=["image_caption"] if img_caption else [],
                        data_keywords=img_caption + img_footnote
                    )
                    success_list.append(data_obj)
                
                # 处理TABLE类型 (模拟原来的tables列表处理)
                elif content_type == "table":
                    table_text = content_item.get("text", "")
                    table_url = content_item.get("url", "")
                    
                    data_obj = KnowDataObject(
                        data_type='TABLE',
                        raw_data=table_text,
                        data_url=table_url,
                        coord_x1=bbox_default[0],
                        coord_y1=bbox_default[1],
                        coord_x2=bbox_default[2],
                        coord_y2=bbox_default[3],
                        page_start=page_idx + 1,
                        page_end=page_idx + 1,
                        knowledge_id=knowledge_id
                    )
                    success_list.append(data_obj)
                
                else:
                    # 模拟原函数的未知类型处理
                    logger.warning(f"Unknown content type: {content_type}")
                    fail_list.append(KnowDataObject(
                        data_type='TEXT',
                        raw_data=f'Unknown content type: {content_type}',
                        coord_x1=0.0,
                        coord_y1=0.0,
                        coord_x2=0.0,
                        coord_y2=0.0,
                        page_start=page_idx + 1,
                        page_end=page_idx + 1,
                        knowledge_id=knowledge_id
                    ))
            
            except Exception as e:
                # 模拟原函数的单item错误处理
                logger.error(f"Error parsing content item {i}: {str(e)}")
                fail_list.append(KnowDataObject(
                    data_type='TEXT',
                    raw_data='ERROR',
                    coord_x1=0.0,
                    coord_y1=0.0,
                    coord_x2=0.0,
                    coord_y2=0.0,
                    page_start=1,
                    page_end=1,
                    knowledge_id=knowledge_id
                ))
    
    except Exception as e:
        # 模拟原函数的全局错误处理
        logger.error(f"Error in MinerU result adaptation: {str(e)}")
        fail_list.append(KnowDataObject(
            data_type='TEXT',
            raw_data='ERROR',
            coord_x1=0.0,
            coord_y1=0.0,
            coord_x2=0.0,
            coord_y2=0.0,
            page_start=1,
            page_end=1,
            knowledge_id=knowledge_id
        ))
    
    return success_list, fail_list
```

------

## 6. 技术实现方案

### 6.1 技术栈

#### 6.1.1 前端技术栈

```typescript
{
  "核心框架": "React 18 + TypeScript",
  "可视化引擎": "React Flow v11",
  "状态管理": "Zustand",
  "代码编辑器": "Monaco Editor (VSCode kernel)",
  "Diff展示": "react-diff-viewer-continued",
  "UI组件库": "shadcn/ui + Tailwind CSS",
  "图形动画": "Framer Motion",
  "文件上传": "react-dropzone",
  "HTTP客户端": "axios",
  "构建工具": "Vite"
}
```

#### 6.1.2 后端技术栈

```python
{
    "Web框架": "FastAPI",
    "代码解析": {
        "AST解析": "ast (标准库)",
        "高级分析": "astroid",
        "类型推断": "mypy + typeshed",
        "代码格式化": "black"
    },
    "AI集成": {
        "LLM框架": "LangChain",
        "向量数据库": "Chroma (嵌入式)",
        "Embedding": "OpenAI text-embedding-3-small",
        "LLM": "Anthropic Claude Sonnet 4 / OpenAI GPT-4"
    },
    "图处理": "NetworkX",
    "Git集成": "gitpython",
    "并发": "asyncio + aiohttp"
}
```

------

### 6.2 系统架构图

```
┌─────────────────────────────────────────────────────┐
│                   浏览器端 (前端)                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │ React Flow  │  │Monaco Editor│  │  AI Chat    │ │
│  │  依赖图渲染  │  │  代码编辑   │  │   助手      │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘ │
│         │                │                │        │
│         └────────────────┴────────────────┘        │
│                        │                           │
│                 Zustand Store (状态)               │
│                        │                           │
└────────────────────────┼───────────────────────────┘
                         │ HTTP/WebSocket
                         │
┌────────────────────────▼───────────────────────────┐
│              FastAPI 后端 (Python)                  │
│  ┌──────────────────────────────────────────────┐  │
│  │          API层 (RESTful + WebSocket)         │  │
│  │  /parse  /analyze  /modify  /chat  /diff    │  │
│  └───────┬──────────────────────────────────────┘  │
│          │                                          │
│  ┌───────▼──────────┐  ┌─────────────────────┐    │
│  │  代码分析引擎     │  │   AI处理引擎        │    │
│  │  ┌─────────────┐ │  │  ┌───────────────┐  │    │
│  │  │AST Parser   │ │  │  │ LLM Orchestr. │  │    │
│  │  │Type Infer   │ │  │  │ Prompt Eng.   │  │    │
│  │  │Relation Ext.│ │  │  │ RAG (Chroma)  │  │    │
│  │  │Schema Detect│ │  │  │ Code Gen.     │  │    │
│  │  └─────────────┘ │  │  └───────────────┘  │    │
│  └──────────────────┘  └─────────────────────┘    │
│          │                        │                │
│  ┌───────▼────────────────────────▼──────┐         │
│  │      图数据结构 (NetworkX)            │         │
│  │  Nodes: {func, class, module}        │         │
│  │  Edges: {call, inherit, import}      │         │
│  │  Metadata: {async, schemas, types}   │         │
│  └──────────────────────────────────────┘         │
└────────────────────────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────┐
              │  本地文件系统     │
              │  • 上传的项目     │
              │  • 临时修改文件   │
              │  • 向量索引(Chroma)│
              └──────────────────┘
```

------

### 6.3 核心模块实现

#### 6.3.1 代码解析引擎

```python
# parser/analyzer.py
from ast import parse, NodeVisitor, AsyncFunctionDef, FunctionDef
from astroid import parse as astroid_parse
import networkx as nx
from typing import Dict, List, Tuple

class DependencyAnalyzer:
    def __init__(self, project_path: str):
        self.graph = nx.DiGraph()
        self.project_path = project_path
        self.schemas = {}  # 存储发现的数据结构
        self.type_hints = {}  # 存储类型注解
    
    def parse_project(self) -> dict:
        """解析整个项目，返回依赖图JSON"""
        # 1. 遍历所有.py文件
        for file_path in self._get_python_files():
            self._parse_file(file_path)
        
        # 2. 提取关系
        self._extract_calls()       # 函数调用
        self._extract_inheritance()  # 继承关系
        self._extract_imports()      # 导入关系
        
        # 3. 检测异步冲突
        self._detect_async_conflicts()
        
        # 4. 转换为前端格式
        return self._to_react_flow_format()
    
    def _parse_file(self, filepath: str):
        """解析单个文件"""
        with open(filepath) as f:
            source = f.read()
            tree = parse(source)
            
            # AST visitor
            visitor = CodeVisitor(filepath, self.graph)
            visitor.visit(tree)
            
            # Astroid分析（高级特性）
            astroid_tree = astroid_parse(source)
            self._analyze_with_astroid(astroid_tree, filepath)
    
    def _analyze_with_astroid(self, tree, filepath):
        """
        使用astroid进行高级分析
        - 类型推断
        - 调用图
        - 数据流
        """
        for node in tree.body:
            if isinstance(node, astroid.ClassDef):
                # 检测Pydantic模型、dataclass等
                if self._is_schema(node):
                    self.schemas[node.name] = self._extract_schema_structure(node)
            
            elif isinstance(node, astroid.FunctionDef):
                # 推断返回值类型
                try:
                    inferred_return = node.infer_return_value()
                    self.type_hints[node.name] = inferred_return
                except:
                    pass
    
    def _detect_async_conflicts(self):
        """检测同步/异步调用冲突"""
        for edge in self.graph.edges():
            source, target = edge
            source_node = self.graph.nodes[source]
            target_node = self.graph.nodes[target]
            
            # 同步函数调用异步函数
            if (not source_node.get('is_async', False) and 
                target_node.get('is_async', False)):
                self.graph.edges[edge]['conflict'] = 'async_mismatch'
                self.graph.edges[edge]['severity'] = 'high'
```

#### 6.3.2 异步影响链分析

```python
# analyzer/async_analyzer.py
class AsyncImpactAnalyzer:
    def __init__(self, graph: nx.DiGraph):
        self.graph = graph
        self.context_tracker = ContextWindowManager()
    
    def analyze_impact_chain(
        self, 
        modified_node_id: str
    ) -> Dict:
        """
        分析异步修改的影响链
        """
        impact_chain = []
        current_layer = 0
        current_nodes = [modified_node_id]
        analyzed_code = {}
        
        while current_nodes:
            # 检查上下文限制
            should_stop, reason = self.context_tracker.should_stop_tracing(
                impact_chain,
                analyzed_code
            )
            if should_stop:
                return {
                    'layers': impact_chain,
                    'stopped': True,
                    'reason': reason,
                    'suggestion': self._generate_batch_suggestion(impact_chain)
                }
            
            # 分析当前层
            layer_info = self._analyze_layer(
                current_layer,
                current_nodes,
                analyzed_code
            )
            impact_chain.append(layer_info)
            
            # 获取下一层（向上追溯调用者）
            next_nodes = self._get_callers(current_nodes)
            current_nodes = next_nodes
            current_layer += 1
        
        return {
            'layers': impact_chain,
            'stopped': False,
            'total_functions': sum(len(layer['nodes']) for layer in impact_chain)
        }
    
    def _analyze_layer(
        self,
        layer_num: int,
        nodes: List[str],
        analyzed_code: Dict
    ) -> Dict:
        """
        分析单层的影响
        """
        layer_nodes = []
        
        for node_id in nodes:
            node_data = self.graph.nodes[node_id]
            
            # 提取函数代码
            function_code = self._get_function_code(node_id)
            analyzed_code[node_id] = function_code
            
            # 评估风险
            risk_level, reasons = self._calculate_risk(node_id)
            
            # 检测特殊情况（循环调用等）
            special_cases = self._detect_special_cases(node_id, function_code)
            
            layer_nodes.append({
                'node_id': node_id,
                'name': node_data['name'],
                'file': node_data['file'],
                'line': node_data['line'],
                'risk_level': risk_level,  # AUTO/SUGGEST/CONFIRM
                'risk_reasons': reasons,
                'special_cases': special_cases,
                'code': function_code
            })
        
        return {
            'layer': layer_num,
            'nodes': layer_nodes,
            'auto_fix_count': sum(1 for n in layer_nodes if n['risk_level'] == 'AUTO'),
            'suggest_count': sum(1 for n in layer_nodes if n['risk_level'] == 'SUGGEST'),
            'confirm_count': sum(1 for n in layer_nodes if n['risk_level'] == 'CONFIRM')
        }
    
    def _detect_special_cases(self, node_id: str, code: str) -> List[Dict]:
        """
        检测特殊情况
        """
        cases = []
        tree = ast.parse(code)
        
        for node in ast.walk(tree):
            # 检测循环中调用
            if isinstance(node, (ast.For, ast.While)):
                loop_calls = self._find_calls_in_loop(node)
                if loop_calls:
                    cases.append({
                        'type': 'loop_async_call',
                        'calls': loop_calls,
                        'strategies': self._generate_loop_strategies(node, loop_calls)
                    })
            
            # 检测装饰器
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.decorator_list:
                    cases.append({
                        'type': 'has_decorators',
                        'decorators': [ast.unparse(d) for d in node.decorator_list]
                    })
        
        return cases
```

#### 6.3.3 数据结构适配器生成

```python
# generator/adapter_generator.py
class AdapterGenerator:
    def __init__(self, llm_client):
        self.llm = llm_client
        self.type_inferencer = TypeInferenceEngine()
        self.field_mapper = FieldMapper()
    
    async def generate_adapter(
        self,
        old_func_id: str,
        new_func_id: str,
        graph: nx.DiGraph
    ) -> Dict:
        """
        生成适配器函数
        """
        # 1. 提取返回值结构
        old_structure = await self._infer_return_structure(old_func_id, graph)
        new_structure = await self._infer_return_structure(new_func_id, graph)
        
        # 2. 智能映射字段
        mappings = await self.field_mapper.map_fields(
            old_structure,
            new_structure
        )
        
        # 3. 识别缺失字段
        missing_fields = [m for m in mappings if m['new'] is None]
        
        # 4. 逐个询问用户处理缺失字段
        missing_decisions = await self._handle_missing_fields(
            missing_fields,
            old_func_id,
            graph
        )
        
        # 5. 分析原函数处理模式
        patterns = await self._analyze_processing_patterns(
            old_func_id,
            graph
        )
        
        # 6. 生成适配函数
        adapter_code = await self._generate_adapter_code(
            old_func_id,
            new_func_id,
            mappings,
            missing_decisions,
            patterns
        )
        
        return {
            'adapter_code': adapter_code,
            'mappings': mappings,
            'missing_decisions': missing_decisions,
            'patterns': patterns
        }
    
    async def _handle_missing_fields(
        self,
        missing_fields: List[Dict],
        func_id: str,
        graph: nx.DiGraph
    ) -> Dict:
        """
        逐个处理缺失字段
        """
        decisions = {}
        
        for i, field in enumerate(missing_fields, 1):
            # 分析字段用途
            usage = await self._analyze_field_usage(
                field['old'],
                func_id,
                graph
            )
            
            # 生成AI建议
            suggestion = await self._generate_field_suggestion(
                field,
                usage
            )
            
            # 返回给前端，等待用户决策
            # (实际实现中通过WebSocket通信)
            user_choice = await self._wait_for_user_decision({
                'field_index': i,
                'total_fields': len(missing_fields),
                'field_info': field,
                'usage_analysis': usage,
                'ai_suggestion': suggestion
            })
            
            decisions[field['old']] = user_choice
        
        return decisions
    
    async def _generate_adapter_code(
        self,
        old_func_id: str,
        new_func_id: str,
        mappings: List[Dict],
        missing_decisions: Dict,
        patterns: Dict
    ) -> str:
        """
        调用LLM生成适配器代码
        """
        # 构建prompt
        prompt = ADAPTER_GENERATION_PROMPT.format(
            old_function_code=self._get_function_code(old_func_id),
            new_function_code=self._get_function_code(new_func_id),
            old_return_structure=json.dumps(mappings['old_structure'], indent=2),
            new_return_structure=json.dumps(mappings['new_structure'], indent=2),
            field_mappings=json.dumps(mappings, indent=2),
            missing_field_decisions=json.dumps(missing_decisions, indent=2),
            original_usage_code=patterns['usage_code'],
            processing_patterns=json.dumps(patterns, indent=2)
        )
        
        # 调用LLM
        response = await self.llm.ainvoke(prompt)
        
        # 提取代码
        code = self._extract_code_from_response(response)
        
        # 验证语法
        try:
            ast.parse(code)
        except SyntaxError as e:
            # 如果语法错误，重试
            code = await self._fix_syntax_error(code, str(e))
        
        return code
```

------

## 7. Demo Example

### 7.1 演示场景：magic_pdf → MinerU 迁移

#### 场景设置

```
项目: PrepKnow Knowledge Hub
文件: layout_service.py
任务: 将 magic_pdf 替换为 MinerU API
```

#### Step 1: 上传项目

```
用户操作:
1. 点击"上传项目"
2. 选择 layout_service.py
3. 系统自动解析

结果:
依赖图显示:
- 24个函数
- 6个类
- 3个主要模块
- 检测到1个async/sync冲突
```

#### Step 2: 查看依赖图

```
依赖图展示:

┌──────────────────────────┐
│ LayoutServiceManager     │
└────────┬─────────────────┘
         │
         ↓
┌──────────────────────────┐
│ default_analysis()       │
└────────┬─────────────────┘
         │
         ↓
┌──────────────────────────┐     ┌────────────────────┐
│ default_pdf_analyzer()   │     │ test_pdf_analyzer()│
└────────┬─────────────────┘     └────────────────────┘
         │
         ↓
┌──────────────────────────┐
│ magic_pdf.parse()        │ ← 要替换
└──────────────────────────┘
```

#### Step 3: 拖拽修改调用

```
用户操作:
1. 点击 default_pdf_analyzer() → magic_pdf.parse() 连接线
2. 拖拽断开
3. 拖拽连接到 _call_mineru_api()

系统响应:
⚠️ 检测到冲突！
- default_pdf_analyzer() 是同步函数
- _call_mineru_api() 是异步函数
```

#### Step 4: AI分析影响链

```
侧边栏显示:

🔼 影响链分析

Layer 1: default_pdf_analyzer() ✅
• 自动改为: async def
• 风险: 无

Layer 2: default_analysis() 🟢
• 需要改为: async def
• 风险: 低
• AI建议: 自动修复

⚠️ 上下文提示
建议先应用Layer 1-2，测试后再继续

[应用Layer 1-2] ← 用户点击
```

#### Step 5: 数据结构对比

```
系统自动弹出:

🔍 数据结构不匹配

旧API返回:
{
  "text": [{"content": str, "bbox": List[float], "page": int}],
  "images": [...],
  "tables": [...]
}

新API返回:
{
  "content_list": [{"type": str, "text": str, "page_idx": int}],
  "job_id": str
}

检测到1个缺失字段: bbox
```

#### Step 6: 处理缺失字段

```
⚠️ 缺失字段: bbox

原用途: 文本坐标定位 (使用35次)

您的选择:
● 使用默认值 [0.0, 0.0, 0.0, 0.0]

备注框:
[暂用默认值，后续补充PyMuPDF计算]

[确认] ← 用户点击
```

#### Step 7: 生成适配函数

```
🤖 正在生成适配函数...

✓ 已分析原函数处理模式
✓ 已生成适配函数 (87行)
✓ 已验证语法
✓ 已添加注释和警告

[查看生成的代码]
```

#### Step 8: 预览Diff
```
📝 预览修改 (2个文件)

layout_service.py:
- Line 77: def default_pdf_analyzer(...):
+ Line 77: async def default_pdf_analyzer(...):

- Line 210: result = magic_pdf.parse(file_path)
+ Line 210: result = await self._call_mineru_api(file_path)
+ Line 211: success_list, fail_list = await self._adapt_mineru_to_legacy_format(
+ Line 212:     result, knowledge_id, [0.0, 0.0, 0.0, 0.0]
+ Line 213: )

+ Line 420-506: [新增适配函数 _adapt_mineru_to_legacy_format]

🤖 AI分析:
✓ 无语法错误
⚠️ 1个警告: bbox字段使用默认值
影响: 2个函数，87行新增代码

[应用修改] [取消]
```

#### Step 9: 应用修改
```
用户点击[应用修改]

✓ 修改已应用
✓ 文件已更新
✓ 依赖图已刷新

建议:
1. 运行单元测试
2. 检查MinerU API连接
3. 验证坐标默认值影响

[查看修改后的代码] [运行测试]
```

---

### 7.2 关键交互演示脚本

#### 演示1: 异步冲突检测
```
场景: 用户拖拽连接异步函数

[屏幕录制要点]
1. 鼠标悬浮在 default_pdf_analyzer() 
   → 显示 tooltip: "同步函数"

2. 开始拖拽到 _call_mineru_api()
   → 连接线变橙色
   → 出现警告图标

3. 释放鼠标
   → 侧边栏弹出影响链分析
   → 依赖图高亮影响路径（绿色→黄色→红色）

4. 用户滚动侧边栏
   → 看到Layer 1-4的详细信息
   → 看到上下文限制提示

5. 用户选择"应用Layer 1-2"
   → 按钮变为loading状态
   → 2秒后完成，显示成功提示
```

#### 演示2: 缺失字段处理
```
场景: 处理bbox缺失字段

[屏幕录制要点]
1. 系统检测到缺失字段
   → 侧边栏弹出"缺失字段 1/3"

2. 显示字段信息
   → 用户阅读"使用35次"
   → 用户看到AI建议

3. 用户选择默认值选项
   → 选项高亮
   → 备注框变为可编辑

4. 用户输入备注
   → 实时保存
   → 显示字符计数

5. 用户点击"确认"
   → 进入下一个缺失字段（如果有）
   → 或显示"所有字段已处理"
```

#### 演示3: 适配器生成
```
场景: AI生成适配函数

[屏幕录制要点]
1. 所有决策完成后
   → 显示"生成适配函数"按钮
   → 按钮带有闪烁动画

2. 用户点击按钮
   → 出现loading动画
   → 显示进度提示:
     "正在分析原函数..."
     "正在生成代码..."
     "正在验证语法..."

3. 生成完成
   → Monaco Editor显示生成的代码
   → 代码带有语法高亮
   → 关键行有注释标记

4. 用户滚动查看代码
   → 可以看到完整的适配逻辑
   → 可以看到警告注释

5. 用户点击"应用修改"
   → Diff视图展示
   → 红色删除、绿色新增
```

---

## 8. 开发计划

### 8.1 MVP开发时间线（10-12周）

#### Sprint 1: 基础架构 (2周)
**Week 1:**
- [ ] 前端脚手架搭建（Vite + React + TypeScript）
- [ ] 后端API框架（FastAPI + 基础路由）
- [ ] AST解析器核心功能
- [ ] 文件上传功能

**Week 2:**
- [ ] React Flow 集成
- [ ] 基础节点渲染（函数/类/模块）
- [ ] 基础连接线渲染
- [ ] /parse API endpoint

**验收标准:**
- ✅ 上传50行Python文件
- ✅ 正确识别函数、类、调用关系
- ✅ 依赖图正确渲染

---

#### Sprint 2: 异步检测 (3周)
**Week 3:**
- [ ] async/sync 检测逻辑
- [ ] 影响链追溯算法
- [ ] 依赖图高亮显示

**Week 4:**
- [ ] 侧边栏UI（影响链列表）
- [ ] Layer风险评估
- [ ] 上下文窗口管理
- [ ] 循环异步检测

**Week 5:**
- [ ] 循环异步方案生成（保守+优化）
- [ ] 用户选择界面
- [ ] /analyze API endpoint

**验收标准:**
- ✅ 检测异步调用冲突
- ✅ 正确显示影响链（4层以上）
- ✅ 生成两种循环处理方案
- ✅ 上下文限制提示工作

---

#### Sprint 3: 数据结构适配 (3周)
**Week 6:**
- [ ] 类型推断引擎（注解+AI）
- [ ] 字段映射算法（语义匹配）
- [ ] 映射可视化UI

**Week 7:**
- [ ] 缺失字段检测
- [ ] 逐个询问用户界面
- [ ] AI建议生成

**Week 8:**
- [ ] 适配器代码生成（LLM集成）
- [ ] 原函数模式分析
- [ ] /generate_adapter API

**验收标准:**
- ✅ 类型推断准确率>80%
- ✅ 字段映射置信度>85%
- ✅ 生成的适配函数语法正确
- ✅ 模拟原函数处理方式

---

#### Sprint 4: Diff与应用 (2周)
**Week 9:**
- [ ] Monaco Editor Diff集成
- [ ] 批量修改预览
- [ ] /modify/preview API

**Week 10:**
- [ ] 实际文件修改逻辑
- [ ] /modify/apply API
- [ ] 错误处理和回滚

**验收标准:**
- ✅ Diff正确显示
- ✅ 文件修改成功
- ✅ 支持撤销操作

---

#### Sprint 5: 集成与优化 (2周)
**Week 11:**
- [ ] AI助手聊天功能（WebSocket）
- [ ] 问题检测面板
- [ ] 端到端测试

**Week 12:**
- [ ] 性能优化（大项目解析）
- [ ] UI/UX抛光
- [ ] Bug修复
- [ ] 文档编写

**验收标准:**
- ✅ 完整流程跑通（上传→修改→应用）
- ✅ 支持100+函数的项目
- ✅ 用户体验流畅

---

### 8.2 后续功能路线图

#### Phase 2 (MVP后 1-2个月)
- [ ] 版本对比（Git集成）
- [ ] 多语言支持（JavaScript/TypeScript）
- [ ] 批量重构（一次修改多个调用）
- [ ] 单元测试自动更新

#### Phase 3 (3-4个月)
- [ ] 团队协作（用户系统）
- [ ] 云端存储
- [ ] 实时协作编辑
- [ ] 性能分析可视化

#### Phase 4 (商业化)
- [ ] IDE插件（VSCode）
- [ ] CI/CD集成
- [ ] 企业版功能
- [ ] SaaS部署

---

### 8.3 技术风险与应对

| 风险 | 概率 | 影响 | 应对方案 |
|------|------|------|---------|
| **LLM生成代码质量不稳定** | 高 | 高 | 1. 详细的prompt工程<br>2. 多轮验证<br>3. 用户可手动修改 |
| **大项目解析性能** | 中 | 中 | 1. 增量解析<br>2. Web Worker<br>3. 分页加载 |
| **类型推断准确率** | 中 | 中 | 1. 多种fallback策略<br>2. 用户提供示例<br>3. 置信度标注 |
| **上下文窗口限制** | 高 | 中 | 1. 分层处理<br>2. 智能边界检测<br>3. 批量应用 |
| **API成本** | 低 | 低 | 1. 本地缓存<br>2. 用户自带Key<br>3. 批量调用优化 |

---

## 9. 总结

### 9.1 核心创新点

1. **可视化优先**：用依赖图而非文本理解代码
2. **AI深度理解**：理解循环、调用、schemas、数据结构
3. **非阻断式交互**：侧边栏AI不打断工作流
4. **智能分层修复**：上下文感知的批量处理
5. **模拟原函数**：生成适配器保持原有处理逻辑

### 9.2 适用场景总结

✅ **最适合：**
- API迁移重构（如 magic_pdf → MinerU）
- 同步→异步转换
- 数据结构适配
- 大规模调用关系修改

⚠️ **需谨慎：**
- 超大项目（>1000函数）→ 建议分模块处理
- 复杂业务逻辑重构 → AI建议为主，人工审核为辅

❌ **不适合：**
- 算法优化（需要领域知识）
- 性能调优（需要profiling）

---

## 附录

### A. 关键Prompt模板

详见第5.5.2节和第4.3.2节

### B. API接口文档

详见之前版本技术文档的API设计部分（保持不变）

### C. 数据结构定义

```typescript
// 依赖图节点
interface DependencyNode {
  id: string;
  type: 'function' | 'class' | 'module';
  name: string;
  file: string;
  line: number;
  is_async: boolean;
  schemas: string[];  // 使用的数据结构
  return_type?: string;
}

// 连接线
interface DependencyEdge {
  id: string;
  source: string;
  target: string;
  type: 'call' | 'inherit' | 'import';
  conflict?: 'async_mismatch';
  severity?: 'high' | 'medium' | 'low';
}

// 影响链
interface ImpactLayer {
  layer: number;
  nodes: LayerNode[];
  auto_fix_count: number;
  suggest_count: number;
  confirm_count: number;
}

// 字段映射
interface FieldMapping {
  old: string;
  new: string | null;
  confidence: number;
  type: 'exact_match' | 'semantic_match' | 'missing';
  reasoning?: string;
}
```

---

**文档版本**: v3.0  
**最后更新**: 2026-01-21  
**作者**: Claude (Anthropic)  
**审核**: Victor (Product Owner)  
**核心更新**: 三层分离视图体系，泳道式函数调用可视化

---

Victor，这份完整的技术文档整合了：
1. ✅ 之前版本的所有核心设计
2. ✅ 异步检测的详细实现（理解循环、调用、schemas等）
3. ✅ 数据结构适配的完整流程（逐个询问缺失字段）
4. ✅ 上下文窗口管理（分层应用）
5. ✅ Demo Example（演示脚本）
6. ✅ 完整的开发计划

现在你可以：
1. 直接用这份文档开始开发
2. 拿给团队成员review
3. 用Demo Example准备展示材料

有任何需要调整或补充的地方，随时告诉我！🚀