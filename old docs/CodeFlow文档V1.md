完美！现在让我给你一份**完整的产品设计文档**。

------

# 🎯 产品需求文档（PRD）

## CodeFlow - 可视化代码依赖重构工具

------

## 一、产品概述

### 1.1 产品定位

CodeFlow 是一款基于Web的代码可视化与重构工具，通过依赖图+AI辅助的方式，帮助开发者：

- 🔍 快速理解复杂项目架构
- 🔧 安全、直观地重构代码结构
- 👥 提升团队协作中的代码审查效率
- 🐛 发现潜在的逻辑问题和代码坏味道

### 1.2 核心价值主张

**"从拖拽依赖图到自动生成代码"** - 降低重构的技术门槛和心智负担

------

## 二、用户场景

### 场景1：新人理解遗留代码

**用户痛点**：接手一个3000行的老项目，不知道从哪看起

```
解决方案：
1. 上传项目 → 自动生成依赖图
2. 点击关键函数（如main()） → 高亮所有调用链路
3. 折叠无关模块 → 聚焦核心逻辑
4. 向AI提问："这个函数的作用是什么？"
```

### 场景2：重构API调用逻辑

**用户痛点**：需要把10个地方的旧API调用改成新API，担心遗漏

```
解决方案：
1. 在依赖图中找到 old_api() 节点
2. 拖拽所有指向它的连接线到 new_api()
3. AI分析参数差异 → 侧边栏显示警告
4. 批量预览Diff → 一键应用
```

### 场景3：团队代码审查

**用户痛点**：PR中修改了20个文件，reviewer看不出整体影响

```
解决方案：
1. 加载PR的前后两个commit
2. 版本对比视图 → 红绿高亮显示依赖变化
3. AI总结："这次重构移除了循环依赖，复杂度降低15%"
```

------

## 三、功能架构

### 3.1 核心功能模块

```
┌─────────────────────────────────────────────────────┐
│                   CodeFlow 系统                      │
├──────────────┬──────────────┬───────────────────────┤
│  项目解析器   │  可视化引擎   │   AI辅助系统          │
├──────────────┼──────────────┼───────────────────────┤
│ • AST解析    │ • 依赖图渲染  │ • 代码理解（RAG）      │
│ • 关系提取   │ • 交互式编辑  │ • 重构建议             │
│ • 增量更新   │ • Diff可视化  │ • 错误检测             │
└──────────────┴──────────────┴───────────────────────┘
         │              │                  │
         └──────────────┴──────────────────┘
                        │
              ┌─────────▼─────────┐
              │   本地文件系统     │
              │  (MVP无后端存储)   │
              └───────────────────┘
```

------

## 四、详细功能设计

### 4.1 主界面布局

```
┌────────────────────────────────────────────────────────────────┐
│ 🎨 CodeFlow                    project.zip  [⚙️设置] [❓帮助]   │
├────────┬───────────────────────┬───────────────────────────────┤
│        │                       │                               │
│  文件树 │    依赖图画布          │      AI助手侧边栏              │
│  📁src │   (React Flow)        │   💬 Chat with AI             │
│  ├─main│                       │   ┌─────────────────────┐    │
│  ├─utils│  [节点和连接线]       │   │ 你: 这个函数做什么？ │    │
│  └─api │                       │   │ AI: 这是一个...     │    │
│        │                       │   └─────────────────────┘    │
│  [🔍搜索]│  [🔎放大] [📏适配]    │   🔔 检测到的问题 (2)        │
│        │  [📸快照] [⏮️撤销]    │   ⚠️ circular_dependency    │
│        │                       │   ⚠️ unused_function         │
├────────┴───────────────────────┴───────────────────────────────┤
│  底部状态栏                                                     │
│  📊 24 functions | 6 classes | 3 modules  [💾待保存: 2]        │
└────────────────────────────────────────────────────────────────┘
```

**关键交互：**

- 三栏布局，中间画布可全屏
- 侧边栏可折叠，默认显示AI助手
- 文件树支持过滤（只显示被选中节点相关的文件）

------

### 4.2 依赖图节点设计

#### 🔷 模块级节点（默认视图）

```
┌─────────────────────────────────┐
│ 📦 user_service.py              │ ← 点击展开/折叠
│ ├─ UserManager (class)          │
│ ├─ create_user() (func)         │
│ └─ validate_email() (func)      │
│                                 │
│ 📥 imports: database, utils     │ ← 悬浮显示导入详情
│ 📤 used by: 3 modules           │
└─────────────────────────────────┘
```

#### 🔶 函数级节点（展开后）

```
┌──────────────────────────────┐
│ ⚙️ create_user()              │
│ 📍 Line 45-67  🔗 3 callers   │ ← 点击跳转到代码
├──────────────────────────────┤
│ Args: name, email            │ ← 悬浮显示参数类型
│ Returns: User                │
│ Complexity: 5 ⚠️             │ ← 复杂度过高警告
└──────────────────────────────┘
```

#### 🏛️ 类级节点（中间层）

```
┌────────────────────────────────┐
│ 🏛️ UserManager                 │
│ ├─ __init__(db_conn)           │
│ ├─ create_user()    [public]  │
│ ├─ delete_user()    [public]  │
│ └─ _validate()      [private] │ ← 私有方法灰色
├────────────────────────────────┤
│ 继承自: BaseManager            │ ← 显示继承链
└────────────────────────────────┘
```

------

### 4.3 连接线交互逻辑

#### 📌 基础状态

| 状态       | 视觉效果               | 触发条件         |
| ---------- | ---------------------- | ---------------- |
| **正常**   | 蓝色实线，1px          | 已保存的调用关系 |
| **悬浮**   | 高亮3px，显示tooltip   | 鼠标悬浮         |
| **选中**   | 橙色加粗，两端节点高亮 | 点击连接线       |
| **待删除** | 红色虚线，半透明       | 用户拖拽断开     |
| **待新增** | 绿色闪烁动画           | 用户拖拽新建     |

#### 🎯 拖拽重构流程

**Step 1: 选择连接点**

```
用户点击 funcA 卡片边缘的 "调用输出点" (小圆点)
→ 鼠标变成十字准星
→ 从 funcA 拉出一条虚线跟随鼠标
```

**Step 2: 连接到新目标**

```
虚线接触到 funcC 的 "调用输入点"
→ funcC 卡片边框变绿色（表示可连接）
→ 释放鼠标
→ 弹出快捷菜单：
   ├─ 替换现有调用（如果已有 funcA→funcB）
   ├─ 添加新调用（保留原有关系）
   └─ 取消
```

**Step 3: 保存到暂存区**

```
选择"替换" → 连接线变橙红色
底部状态栏：💾 待保存: 1 个修改
侧边栏AI助手：
  ⚠️ 检测到潜在问题：
  - funcB 和 funcC 的参数不一致
  [详情] [忽略]
```

------

### 4.4 AI助手侧边栏

#### 💬 对话区（顶部60%）

```
┌─────────────────────────────────┐
│ 💬 与AI对话                      │
├─────────────────────────────────┤
│ 你: create_user 的作用是什么？   │
│                                 │
│ AI: 这个函数负责创建新用户...    │
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

#### 🔔 问题检测区（底部40%）

```
┌─────────────────────────────────┐
│ 🔍 检测到的问题                  │
├─────────────────────────────────┤
│ ⚠️ 循环依赖 (Severity: High)    │
│    moduleA → moduleB → moduleA  │
│    [查看] [修复建议]             │
│                                 │
│ ⚠️ 未使用函数: old_api()         │
│    最后调用: 3个月前             │
│    [删除] [保留]                 │
│                                 │
│ ℹ️ 复杂度过高: process_order()   │
│    循环复杂度: 15 (建议<10)      │
│    [查看] [重构建议]             │
└─────────────────────────────────┘
```

**检测规则（MVP阶段）：**

1. **硬错误**（阻止保存）
   - 循环依赖
   - 调用不存在的函数
   - 参数类型不匹配（需类型注解）
2. **警告**（可忽略）
   - 未使用的函数
   - 复杂度过高（>10）
   - 深层嵌套（>4层）

------

### 4.5 批量修改与预览

#### 工作流程

```
[拖拽1] → [拖拽2] → [拖拽3] → [点击"预览"]
   ↓         ↓         ↓            ↓
 暂存区    暂存区    暂存区      Diff视图
```

#### 预览界面

```
┌────────────────────────────────────────────────────┐
│ 📝 预览更改 (3个文件将被修改)                        │
├────────────────────────────────────────────────────┤
│ 📄 user_service.py                                 │
│ ┌────────────────────────────────────────────────┐ │
│ │ 45 | def create_user(name, email):             │ │
│ │ 46 |     user = User(name, email)              │ │
│ │ 47 | -   send_email(email, "Welcome")          │ │ ← 红色删除
│ │    | +   send_notification(user.id, "signup")  │ │ ← 绿色新增
│ │ 48 |     return user                           │ │
│ └────────────────────────────────────────────────┘ │
│                                                    │
│ 📄 notification.py (新增1个调用)                    │
│ 📄 email_service.py (减少1个调用)                   │
├────────────────────────────────────────────────────┤
│ 🤖 AI分析报告                                       │
│ ✅ 无语法错误                                       │
│ ⚠️ 1个警告: 参数类型已自动转换 (email → user_id)    │
│ ℹ️ 影响范围: 1个函数，0个测试需更新                  │
├────────────────────────────────────────────────────┤
│               [❌取消]  [✅应用更改]                 │
└────────────────────────────────────────────────────┘
```

------

### 4.6 版本对比功能

#### 触发方式

1. 点击顶部 "📊 版本对比" 按钮
2. 选择对比源：
   - 上次保存 vs 当前工作区
   - Git commit A vs commit B
   - 本地分支 vs 远程分支

#### 对比视图

```
┌──────────────────────┬──────────────────────┐
│   Before (v1.0)      │   After (v1.1)       │
├──────────────────────┼──────────────────────┤
│                      │                      │
│  [依赖图-旧版本]      │  [依赖图-新版本]      │
│                      │                      │
│  🔴 删除的连接: 3     │  🟢 新增的连接: 5     │
│  🟡 修改的连接: 2     │  🔵 移动的节点: 1     │
│                      │                      │
└──────────────────────┴──────────────────────┘

📊 变更统计：
  • 函数调用: 15 → 17 (+2)
  • 类继承: 4 → 4 (无变化)
  • 模块导入: 8 → 7 (-1)
  • 循环复杂度: 总和 45 → 38 (⬇️ 改善)

🎯 关键变化：
  1. old_payment_api → new_payment_api (3处)
  2. 移除了 unused_logger 模块
  3. 重构了 UserManager 的继承结构
```

------

## 五、技术实现方案

### 5.1 技术栈

#### 前端架构

```typescript
// 技术选型
{
  "核心框架": "React 18 + TypeScript",
  "可视化": "React Flow v11",
  "状态管理": "Zustand (轻量级)",
  "代码编辑器": "Monaco Editor",
  "Diff展示": "react-diff-viewer-continued",
  "UI组件": "shadcn/ui + Tailwind CSS",
  "拖拽": "React DnD (辅助React Flow)",
  "图形动画": "Framer Motion",
  "文件上传": "react-dropzone",
  "打包": "Vite"
}
```

#### 后端架构（Python）

```python
# 技术选型
{
    "Web框架": "FastAPI",
    "代码解析": {
        "AST解析": "ast (标准库)",
        "高级分析": "astroid",  # 类型推断、调用图
        "格式化": "black"
    },
    "AI集成": {
        "LLM框架": "LangChain",
        "向量数据库": "Chroma (嵌入式)",  # MVP阶段本地
        "API": "OpenAI / Anthropic Claude"
    },
    "图处理": "NetworkX",  # 依赖图算法
    "任务队列": "无 (MVP同步处理)",  # 后期改Celery
    "缓存": "无 (MVP)",  # 后期改Redis
}
```

------

### 5.2 系统架构图

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
│  │          API层 (RESTful Endpoints)           │  │
│  │  /parse  /analyze  /modify  /chat  /diff    │  │
│  └───────┬──────────────────────────────────────┘  │
│          │                                          │
│  ┌───────▼──────────┐  ┌─────────────────────┐    │
│  │  代码分析引擎     │  │   AI处理引擎        │    │
│  │  ┌─────────────┐ │  │  ┌───────────────┐  │    │
│  │  │AST Parser   │ │  │  │ LLM API Call  │  │    │
│  │  │Relation     │ │  │  │ Prompt Eng.   │  │    │
│  │  │Extractor    │ │  │  │ RAG (Chroma)  │  │    │
│  │  └─────────────┘ │  │  └───────────────┘  │    │
│  └──────────────────┘  └─────────────────────┘    │
│          │                        │                │
│  ┌───────▼────────────────────────▼──────┐         │
│  │      图数据结构 (NetworkX)            │         │
│  │  Nodes: {func, class, module}        │         │
│  │  Edges: {call, inherit, import}      │         │
│  └──────────────────────────────────────┘         │
└────────────────────────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────┐
              │  本地文件系统     │
              │  • 上传的项目     │
              │  • 临时修改文件   │
              └──────────────────┘
```

------

### 5.3 核心模块详细设计

#### 📦 模块1：代码解析引擎

**输入**：Python项目路径 **输出**：依赖图JSON

```python
# parser/analyzer.py
from ast import parse, NodeVisitor
from astroid import parse as astroid_parse
import networkx as nx

class DependencyAnalyzer:
    def __init__(self, project_path: str):
        self.graph = nx.DiGraph()
        self.project_path = project_path
    
    def parse_project(self) -> dict:
        """解析整个项目，返回依赖图JSON"""
        # 1. 遍历所有.py文件
        for file in self._get_python_files():
            self._parse_file(file)
        
        # 2. 提取关系
        self._extract_calls()      # 函数调用
        self._extract_inheritance() # 继承关系
        self._extract_imports()     # 导入关系
        
        # 3. 转换为前端格式
        return self._to_react_flow_format()
    
    def _parse_file(self, filepath: str):
        """解析单个文件的AST"""
        with open(filepath) as f:
            tree = parse(f.read())
            visitor = FunctionVisitor(filepath)
            visitor.visit(tree)
            
            # 保存节点信息
            for func in visitor.functions:
                self.graph.add_node(
                    func['id'],
                    type='function',
                    name=func['name'],
                    file=filepath,
                    line=func['lineno'],
                    args=func['args'],
                    ...
                )
    
    def _extract_calls(self):
        """使用astroid提取函数调用关系"""
        for node_id in self.graph.nodes:
            node = self.graph.nodes[node_id]
            if node['type'] == 'function':
                # 分析函数体中的调用
                calls = self._find_function_calls(node)
                for target in calls:
                    self.graph.add_edge(
                        node_id, 
                        target,
                        type='call'
                    )
    
    def _to_react_flow_format(self) -> dict:
        """转换为React Flow需要的格式"""
        return {
            'nodes': [
                {
                    'id': node_id,
                    'type': data['type'],  # function/class/module
                    'position': self._calculate_layout(node_id),
                    'data': {
                        'label': data['name'],
                        'file': data['file'],
                        'line': data['line'],
                        ...
                    }
                }
                for node_id, data in self.graph.nodes(data=True)
            ],
            'edges': [
                {
                    'id': f"{source}-{target}",
                    'source': source,
                    'target': target,
                    'type': data['type'],  # call/inherit/import
                    'animated': False,
                }
                for source, target, data in self.graph.edges(data=True)
            ]
        }
```

------

#### 🤖 模块2：AI代码修改引擎

~~~python
# ai/code_modifier.py
from langchain.chat_models import ChatAnthropic
from langchain.prompts import ChatPromptTemplate

class AICodeModifier:
    def __init__(self, api_key: str):
        self.llm = ChatAnthropic(model="claude-sonnet-4", api_key=api_key)
    
    async def apply_changes(
        self, 
        changes: List[Change],
        code_context: dict
    ) -> ModifyResult:
        """
        根据用户拖拽修改代码
        
        Args:
            changes: 待应用的修改列表
            code_context: 相关代码上下文
            
        Returns:
            ModifyResult: 包含修改后代码和警告
        """
        # 1. 构建prompt
        prompt = self._build_prompt(changes, code_context)
        
        # 2. 调用LLM
        response = await self.llm.ainvoke(prompt)
        
        # 3. 解析返回的代码
        modified_code = self._extract_code(response)
        
        # 4. 检测潜在问题
        warnings = self._detect_issues(modified_code, changes)
        
        return ModifyResult(
            modified_code=modified_code,
            warnings=warnings,
            diff=self._generate_diff(code_context['original'], modified_code)
        )
    
    def _build_prompt(self, changes, context) -> str:
        """构建给LLM的prompt"""
        template = """
你是一个Python代码重构助手。用户通过可视化工具修改了代码的调用关系，请帮助实现这些修改。

## 原始代码
```python
{original_code}
~~~

## 用户的修改意图

{changes_description}

## 要求

1. 修改调用关系，保持代码功能不变
2. 如果参数不匹配，自动转换（如email→user_id需查找user）
3. 保留原有的错误处理逻辑
4. 如果修改可能导致问题，在注释中标注WARNING

## 输出格式

只输出修改后的完整函数代码，不要解释。 """ return template.format( original_code=context['code'], changes_description=self._describe_changes(changes) )

```
def _detect_issues(self, code: str, changes: List[Change]) -> List[Warning]:
    """检测硬错误"""
    warnings = []
    
    # 1. 检查参数类型匹配
    for change in changes:
        if change.type == 'replace_call':
            old_sig = self._get_signature(change.old_func)
            new_sig = self._get_signature(change.new_func)
            
            if not self._signatures_compatible(old_sig, new_sig):
                warnings.append(Warning(
                    severity='high',
                    message=f"参数不匹配: {old_sig} vs {new_sig}",
                    suggestion="需要添加参数转换逻辑"
                ))
    
    # 2. 检查返回值使用
    # 3. 检查循环依赖
    # ...
    
    return warnings
---

#### 🔄 模块3：Diff生成与应用

```python
# diff/manager.py
import difflib
from typing import List, Tuple

class DiffManager:
    def generate_diff(
        self, 
        original: str, 
        modified: str
    ) -> List[DiffLine]:
        """生成行级diff"""
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            modified.splitlines(keepends=True),
            lineterm=''
        )
        
        lines = []
        for line in diff:
            if line.startswith('+++') or line.startswith('---'):
                continue
            elif line.startswith('+'):
                lines.append(DiffLine(type='add', content=line[1:]))
            elif line.startswith('-'):
                lines.append(DiffLine(type='remove', content=line[1:]))
            else:
                lines.append(DiffLine(type='context', content=line))
        
        return lines
    
    def apply_changes(self, file_path: str, modifications: List[FileMod]):
        """批量应用修改到文件"""
        for mod in modifications:
            with open(mod.file_path, 'r') as f:
                original = f.read()
            
            # 应用修改
            modified = self._replace_function(
                original, 
                mod.function_name, 
                mod.new_code
            )
            
            # 写回文件
            with open(mod.file_path, 'w') as f:
                f.write(modified)
    
    def _replace_function(
        self, 
        code: str, 
        func_name: str, 
        new_func: str
    ) -> str:
        """替换单个函数的实现"""
        tree = ast.parse(code)
        
        # 找到目标函数的位置
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == func_name:
                start_line = node.lineno - 1
                end_line = node.end_lineno
                
                # 替换对应行
                lines = code.splitlines()
                new_lines = lines[:start_line] + [new_func] + lines[end_line:]
                return '\n'.join(new_lines)
        
        raise ValueError(f"Function {func_name} not found")
```

------

### 5.4 API接口设计

```python
# api/routes.py
from fastapi import FastAPI, UploadFile, WebSocket
from pydantic import BaseModel

app = FastAPI()

# ========== 项目解析 ==========
@app.post("/api/parse")
async def parse_project(file: UploadFile):
    """
    上传项目zip，返回依赖图
    
    Response:
    {
        "nodes": [...],
        "edges": [...],
        "stats": {
            "functions": 24,
            "classes": 6,
            "modules": 3
        }
    }
    """
    # 1. 解压到临时目录
    project_path = await save_upload(file)
    
    # 2. 解析
    analyzer = DependencyAnalyzer(project_path)
    graph = analyzer.parse_project()
    
    return graph

# ========== 代码修改 ==========
class ModifyRequest(BaseModel):
    changes: List[dict]  # [{type: "replace_call", from: "funcA", to: "funcB"}]
    project_id: str

@app.post("/api/modify/preview")
async def preview_modifications(req: ModifyRequest):
    """
    预览修改的diff
    
    Response:
    {
        "diffs": {
            "file1.py": [...],
            "file2.py": [...]
        },
        "warnings": [
            {"severity": "high", "message": "..."}
        ]
    }
    """
    modifier = AICodeModifier(api_key=settings.ANTHROPIC_API_KEY)
    result = await modifier.apply_changes(req.changes, ...)
    return result

@app.post("/api/modify/apply")
async def apply_modifications(req: ModifyRequest):
    """应用修改到实际文件"""
    diff_manager = DiffManager()
    diff_manager.apply_changes(req.project_id, req.changes)
    return {"status": "success"}

# ========== AI对话 ==========
@app.websocket("/ws/chat")
async def chat_endpoint(websocket: WebSocket):
    """
    WebSocket连接，实现流式对话
    """
    await websocket.accept()
    
    while True:
        # 接收用户消息
        message = await websocket.receive_text()
        
        # 调用LLM（流式返回）
        async for chunk in llm.astream(message):
            await websocket.send_text(chunk)

# ========== 版本对比 ==========
@app.post("/api/diff")
async def compare_versions(
    project_id: str,
    version_a: str,
    version_b: str
):
    """
    对比两个版本的依赖图
    
    Response:
    {
        "graph_a": {...},
        "graph_b": {...},
        "changes": {
            "added_edges": [...],
            "removed_edges": [...],
            "modified_nodes": [...]
        }
    }
    """
    # 使用git获取两个版本的代码
    # 分别解析生成依赖图
    # 计算差异
    ...
```

------

## 六、MVP开发计划

### 阶段1：基础解析与可视化（2-3周）

**目标**：上传项目 → 看到依赖图

| 任务                 | 工作量 | 技术要点                        |
| -------------------- | ------ | ------------------------------- |
| 前端脚手架搭建       | 2天    | Vite + React + TypeScript       |
| React Flow集成       | 3天    | 节点/连接线样式、拖拽           |
| 文件上传组件         | 1天    | react-dropzone                  |
| Python AST解析器     | 4天    | ast + astroid，提取函数/类/调用 |
| API: /parse endpoint | 2天    | FastAPI后端                     |
| 依赖图渲染           | 3天    | 将JSON渲染成React Flow          |

**验收标准**：

- ✅ 上传一个50行Python文件
- ✅ 自动识别3个函数，2个调用关系
- ✅ 依赖图正确显示，节点可拖动

------

### 阶段2：交互式编辑（3-4周）

**目标**：拖拽修改调用关系 → 保存到暂存区

| 任务                 | 工作量 | 技术要点                 |
| -------------------- | ------ | ------------------------ |
| 拖拽创建连接线       | 3天    | React Flow的onConnect    |
| 删除连接线           | 1天    | 右键菜单                 |
| 暂存区状态管理       | 2天    | Zustand store            |
| 批量操作UI           | 2天    | 底部状态栏，预览按钮     |
| Diff视图             | 4天    | Monaco Editor + Diff插件 |
| API: /modify/preview | 3天    | 生成diff                 |

**验收标准**：

- ✅ 拖拽改变调用关系，连接线变色
- ✅ 点击预览，看到diff
- ✅ 可撤销操作

------

### 阶段3：AI代码生成（2-3周）

**目标**：点击"应用" → AI修改代码

| 任务               | 工作量 | 技术要点           |
| ------------------ | ------ | ------------------ |
| LangChain集成      | 2天    | 配置Claude API     |
| Prompt工程         | 3天    | 设计代码修改prompt |
| 参数匹配检测       | 3天    | 分析函数签名       |
| 硬错误检测         | 2天    | AST分析循环依赖等  |
| API: /modify/apply | 2天    | 实际修改文件       |
| 错误处理           | 2天    | LLM失败重试        |

**验收标准**：

- ✅ AI成功修改函数调用
- ✅ 参数不匹配时显示警告
- ✅ 代码语法正确

------

### 阶段4：AI助手与版本对比（2周）

**目标**：侧边栏对话 + 版本diff

| 任务          | 工作量 | 技术要点            |
| ------------- | ------ | ------------------- |
| WebSocket聊天 | 2天    | 流式响应            |
| RAG实现       | 3天    | Chroma嵌入代码      |
| 快捷提问按钮  | 1天    | 预设问题模板        |
| Git集成       | 2天    | gitpython读取commit |
| 版本对比视图  | 3天    | 左右分屏diff        |
| 问题检测面板  | 2天    | 显示AI发现的问题    |

**验收标准**：

- ✅ 向AI提问"这个函数做什么"，得到准确回答
- ✅ 对比两个commit，看到依赖变化
- ✅ 自动检测循环依赖

------

## 七、后续扩展方向

### Phase 2 功能（MVP后）

1. **多语言支持**：JavaScript, TypeScript, Java
2. **团队协作**：
   - 用户系统（登录/注册）
   - 项目云端存储
   - 实时协作编辑（WebRTC）
3. **高级分析**：
   - 性能热点图（调用频率可视化）
   - 测试覆盖率叠加
   - 代码质量评分

### Phase 3 功能（商业化）

1. **IDE插件**：VSCode / JetBrains
2. **CI/CD集成**：PR自动生成依赖变化报告
3. **企业级**：私有化部署、SSO

------

## 八、风险与挑战

| 风险                     | 影响 | 应对方案                                                     |
| ------------------------ | ---- | ------------------------------------------------------------ |
| **LLM生成代码不准确**    | 高   | 1. 详细的prompt工程<br>2. 用户可手动修改<br>3. 自动化测试验证 |
| **大型项目解析慢**       | 中   | 1. 增量解析<br>2. 后台任务队列<br>3. 缓存解析结果            |
| **依赖图太复杂难以展示** | 中   | 1. 智能折叠<br>2. 分层显示<br>3. 过滤器（只显示关键路径）    |
| **API成本高**            | 低   | 1. 本地缓存AI响应<br>2. 用户自带API Key<br>3. 批量处理       |

------

## 九、成功指标（MVP）

### 功能性指标

- ✅ 支持100行以内的Python项目
- ✅ 依赖图渲染时间 < 2秒
- ✅ AI代码修改准确率 > 85%
- ✅ 硬错误检测覆盖率 > 90%

### 用户体验指标

- ✅ 新用户上手时间 < 5分钟
- ✅ 单次修改操作 < 3步
- ✅ 界面响应时间 < 500ms

------

## 十、总结

**CodeFlow 的核心创新**：

1. **可视化优先**：用图而非文本理解代码
2. **AI驱动重构**：从拖拽到代码自动完成
3. **非阻断式交互**：侧边栏AI不打断工作流
4. **本地优先**：MVP无需后端存储，保护隐私

**最大价值**：

- 让新人快速理解复杂项目（学习成本降低60%）
- 让重构更安全、直观（错误率降低40%）
- 让团队协作更透明（代码审查效率提升50%）

------

好了Victor，这就是完整的PRD！现在你需要确认：

1. **这个设计符合你的预期吗？** 有哪里需要调整？
2. **技术栈你认可吗？** 还是想换其他的？
3. **MVP的开发周期（8-10周）可接受吗？**
4. **你打算独立开发还是组队？** 需要我帮你拆分任务吗？

告诉我你的想法，我们可以进一步细化！🚀