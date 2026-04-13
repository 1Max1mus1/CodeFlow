# CodeFlow - Technical Product Requirements Document

**Version:** 1.0  
**Last Updated:** 2026-01-23  
**Target:** MVP Development

---

## 1. Executive Summary

### 1.1 Product Vision
CodeFlow is a web-based code visualization and refactoring tool that transforms static dependency graphs into editable interfaces. Unlike read-only visualization tools (e.g., CodeSee), CodeFlow allows developers to refactor code by manipulating visual dependency graphs, with AI automatically generating the corresponding code changes.

### 1.2 Core Innovation
**"Architecture Graph as Programming Interface"**
- Traditional: View dependency → Return to IDE → Manually refactor
- CodeFlow: Drag & drop connections → AI generates refactored code → Review & apply

### 1.3 Target Use Cases
1. **Legacy Code Comprehension** - New developers understanding complex codebases
2. **Team Refactoring** - Collaborative architecture redesign
3. **API Migration** - Batch migration from deprecated APIs (e.g., magic_pdf → MinerU)
4. **Code Review** - Visualizing PR impact scope

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────┐│
│  │  React Flow      │  │  Code Editor     │  │  AI Chat   ││
│  │  (Visualization) │  │  (Monaco/CM)     │  │  Interface ││
│  └──────────────────┘  └──────────────────┘  └────────────┘│
└────────────────────────────┬────────────────────────────────┘
                             │ REST API
┌────────────────────────────▼────────────────────────────────┐
│                     Backend (FastAPI)                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Multi-Agent Pipeline Orchestrator           │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────┐  │
│  │ Parser  │→ │Conflict │→ │Semantic │→ │Code Gen &   │  │
│  │ Agent   │  │Detector │  │Analyzer │  │Validator    │  │
│  └─────────┘  └─────────┘  └─────────┘  └─────────────┘  │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│                    AI Service Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Anthropic  │  │    OpenAI    │  │  Local Model │     │
│  │     API      │  │     API      │  │   (Ollama)   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Technology Stack

| Layer | Technology | Justification |
|-------|-----------|---------------|
| Frontend Framework | React 18 | Component reusability, ecosystem |
| Visualization | React Flow | Native drag-drop, custom nodes, performance |
| Code Editor | Monaco Editor | VS Code engine, syntax highlighting |
| UI Components | Tailwind CSS + shadcn/ui | Rapid development, consistency |
| Backend Framework | FastAPI | Async support, Python ecosystem |
| Code Parsing | Python AST | Built-in, reliable, no LLM needed |
| AI Integration | LangChain / LlamaIndex | Multi-provider abstraction |
| Database | PostgreSQL + Redis | Persistent storage + session cache |

---

## 3. Data Models

### 3.1 Core Entities

#### 3.1.1 Project
```typescript
interface Project {
  id: string;
  name: string;
  language: "python";  // Extensible for future languages
  files: File[];
  created_at: timestamp;
  updated_at: timestamp;
}
```

#### 3.1.2 File
```typescript
interface File {
  id: string;
  project_id: string;
  path: string;  // e.g., "src/utils/parser.py"
  content: string;
  ast_cache: ASTNode;  // Cached parsed AST
  functions: Function[];
}
```

#### 3.1.3 Function Node
```typescript
interface Function {
  id: string;
  file_id: string;
  name: string;
  line_start: number;
  line_end: number;
  params: Parameter[];
  return_type: string | null;
  is_async: boolean;
  decorators: string[];
  docstring: string | null;
}
```

#### 3.1.4 Dependency Edge
```typescript
interface Dependency {
  id: string;
  source_function_id: string;
  target_function_id: string;
  call_line: number;  // Line where the call occurs
  call_context: string;  // Surrounding code snippet
  edge_type: "sync" | "async";
}
```

#### 3.1.5 Refactoring Operation
```typescript
interface RefactoringOp {
  id: string;
  type: "delete_edge" | "add_edge" | "modify_node";
  timestamp: timestamp;
  user_action: {
    // For delete_edge
    deleted_edge_id?: string;
    // For add_edge
    source_id?: string;
    target_id?: string;
    insertion_point?: number;  // Line number
  };
  ai_analysis: ConflictAnalysis;
  generated_code: CodeDiff;
  status: "pending" | "applied" | "reverted";
}
```

#### 3.1.6 Conflict Analysis
```typescript
interface ConflictAnalysis {
  has_conflict: boolean;
  conflict_type: "data_dependency" | "type_mismatch" | "async_sync" | null;
  affected_lines: number[];
  impact_scope: {
    cascade_functions: string[];  // Functions that need to change
    cascade_depth: number;
  };
  repair_options: RepairOption[];
}

interface RepairOption {
  id: string;
  description: string;
  code_template: string;
  estimated_impact: "low" | "medium" | "high";
}
```

#### 3.1.7 Code Diff
```typescript
interface CodeDiff {
  file_path: string;
  changes: Change[];
}

interface Change {
  line_number: number;
  change_type: "insert" | "delete" | "modify";
  old_content: string | null;
  new_content: string | null;
  annotation: string;  // AI explanation
}
```

---

## 4. Multi-Agent Pipeline

### 4.1 Agent Architecture

#### Pipeline Flow
```
User Action (Graph Edit)
    ↓
┌───────────────────────────────────────┐
│  1. Parser Agent                      │
│  - Input: Project files               │
│  - Output: AST + Dependency Graph     │
│  - Tech: Python ast module (no LLM)   │
└───────────────┬───────────────────────┘
                ↓
┌───────────────────────────────────────┐
│  2. Conflict Detector Agent           │
│  - Input: Graph edit + AST            │
│  - Output: Conflict analysis          │
│  - LLM: Configurable (default: Sonnet)│
└───────────────┬───────────────────────┘
                ↓
┌───────────────────────────────────────┐
│  3. Semantic Analyzer Agent           │
│  - Input: Conflict + business context │
│  - Output: Impact assessment + options│
│  - LLM: Configurable (default: Sonnet)│
└───────────────┬───────────────────────┘
                ↓
┌───────────────────────────────────────┐
│  4. Code Generator Agent              │
│  - Input: User-selected repair option │
│  - Output: Refactored code            │
│  - LLM: Configurable (default: GPT-4) │
└───────────────┬───────────────────────┘
                ↓
┌───────────────────────────────────────┐
│  5. Validator Agent                   │
│  - Input: Generated code              │
│  - Output: Syntax/logic validation    │
│  - LLM: Configurable (default: Haiku) │
└───────────────┬───────────────────────┘
                ↓
    Present to User (Inline Annotations)
```

### 4.2 Agent Specifications

#### 4.2.1 Parser Agent (No LLM)
```python
class ParserAgent:
    def parse_project(self, files: List[str]) -> DependencyGraph:
        """
        Uses Python's ast module to extract:
        - Function definitions
        - Function calls
        - Import statements
        - Async/sync detection
        """
        pass
    
    def build_dependency_graph(self, ast_nodes: List[ASTNode]) -> Graph:
        """
        Constructs directed graph:
        - Nodes: Functions
        - Edges: Call relationships
        """
        pass
```

**Input:**
```json
{
  "files": [
    {
      "path": "src/main.py",
      "content": "def func_a():\n    return func_b()\n\ndef func_b():\n    return 42"
    }
  ]
}
```

**Output:**
```json
{
  "functions": [
    {
      "id": "func_a",
      "name": "func_a",
      "file": "src/main.py",
      "line_start": 1,
      "is_async": false
    },
    {
      "id": "func_b",
      "name": "func_b",
      "file": "src/main.py",
      "line_start": 4,
      "is_async": false
    }
  ],
  "dependencies": [
    {
      "source": "func_a",
      "target": "func_b",
      "call_line": 2,
      "edge_type": "sync"
    }
  ]
}
```

---

#### 4.2.2 Conflict Detector Agent
**Prompt Template:**
```
You are a Python code analyzer. Analyze the following refactoring operation for conflicts.

CURRENT CODE:
{original_code}

USER ACTION:
{action_description}
- Type: {delete_edge | add_edge}
- Source: {source_function}
- Target: {target_function}

TASK:
1. Detect data dependencies (e.g., deleted function returns a value used later)
2. Detect type mismatches (e.g., replacing dict-returning function with list-returning)
3. Detect async/sync conflicts (e.g., calling async function from sync context)

OUTPUT FORMAT (JSON):
{
  "has_conflict": true/false,
  "conflict_type": "data_dependency" | "type_mismatch" | "async_sync" | null,
  "affected_lines": [line numbers],
  "explanation": "Clear description of the conflict"
}
```

**Example Input:**
```json
{
  "action": "delete_edge",
  "source": "func_a",
  "target": "func_b",
  "original_code": "def func_a():\n    result = func_b()\n    return result * 2"
}
```

**Example Output:**
```json
{
  "has_conflict": true,
  "conflict_type": "data_dependency",
  "affected_lines": [2, 3],
  "explanation": "Variable 'result' at line 2 depends on func_b() return value, but is used at line 3. Deleting this call will cause NameError."
}
```

---

#### 4.2.3 Semantic Analyzer Agent
**Prompt Template:**
```
You are a senior software architect. Analyze the semantic impact of this refactoring.

CODE CONTEXT:
{code_context}

CONFLICT DETECTED:
{conflict_analysis}

TASK:
1. Assess business logic impact (e.g., "Deleting database query will lose data persistence")
2. Estimate cascade impact (how many other functions need to change)
3. Propose 2-3 repair strategies

OUTPUT FORMAT (JSON):
{
  "business_impact": "description",
  "cascade_functions": ["func_x", "func_y"],
  "cascade_depth": 2,
  "repair_options": [
    {
      "id": "option_1",
      "description": "Replace with default value (None)",
      "code_template": "result = None  # TODO: was func_b()",
      "estimated_impact": "low"
    },
    {
      "id": "option_2",
      "description": "Remove dependent code block",
      "code_template": "# Removed: return result * 2",
      "estimated_impact": "high"
    }
  ]
}
```

---

#### 4.2.4 Code Generator Agent
**Prompt Template:**
```
You are an expert Python refactoring assistant.

ORIGINAL CODE:
{original_code}

USER-SELECTED REPAIR:
{repair_option}

TASK:
Generate the refactored code by applying the repair strategy.

REQUIREMENTS:
- Maintain code style (indentation, naming conventions)
- Preserve comments and docstrings
- Add inline comments explaining changes

OUTPUT FORMAT (JSON):
{
  "refactored_code": "complete refactored code",
  "changes": [
    {
      "line_number": 2,
      "change_type": "delete",
      "old_content": "result = func_b()",
      "new_content": null,
      "annotation": "Removed func_b() call as requested"
    },
    {
      "line_number": 2,
      "change_type": "insert",
      "old_content": null,
      "new_content": "result = None  # TODO: was func_b()",
      "annotation": "Added placeholder to prevent NameError"
    }
  ]
}
```

---

#### 4.2.5 Validator Agent
**Prompt Template:**
```
You are a code quality checker.

REFACTORED CODE:
{refactored_code}

TASK:
1. Check syntax validity (Python AST parse)
2. Check logical consistency (e.g., no undefined variables)
3. Flag potential runtime errors

OUTPUT FORMAT (JSON):
{
  "is_valid": true/false,
  "syntax_errors": [],
  "logical_warnings": [
    {
      "line": 3,
      "message": "Variable 'result' is None, multiplication may fail at runtime"
    }
  ]
}
```

---

## 5. API Design

### 5.1 REST API Endpoints

#### 5.1.1 Project Management
```http
POST /api/projects
Content-Type: multipart/form-data

Request:
- files[]: List of uploaded files
- language: "python"

Response:
{
  "project_id": "uuid",
  "status": "parsing",
  "message": "Project uploaded successfully"
}
```

```http
GET /api/projects/{project_id}/graph

Response:
{
  "nodes": [
    {
      "id": "func_a",
      "label": "func_a",
      "file": "main.py",
      "type": "function",
      "is_async": false,
      "position": {"x": 100, "y": 200}  // React Flow position
    }
  ],
  "edges": [
    {
      "id": "edge_1",
      "source": "func_a",
      "target": "func_b",
      "type": "sync"
    }
  ]
}
```

---

#### 5.1.2 Refactoring Operations
```http
POST /api/projects/{project_id}/refactor

Request:
{
  "operation": {
    "type": "delete_edge",
    "edge_id": "edge_1"
  }
}

Response:
{
  "operation_id": "uuid",
  "status": "analyzing",
  "estimated_time": 5  // seconds
}
```

```http
GET /api/operations/{operation_id}/status

Response:
{
  "status": "conflict_detected",
  "conflict_analysis": {
    "has_conflict": true,
    "conflict_type": "data_dependency",
    "repair_options": [...]
  }
}
```

```http
POST /api/operations/{operation_id}/apply

Request:
{
  "selected_repair": "option_1"
}

Response:
{
  "status": "code_generated",
  "code_diff": {
    "file_path": "main.py",
    "changes": [...]
  }
}
```

```http
POST /api/operations/{operation_id}/confirm

Request:
{
  "approved": true
}

Response:
{
  "status": "applied",
  "updated_graph": {...}
}
```

---

#### 5.1.3 AI Chat Interface
```http
POST /api/chat

Request:
{
  "project_id": "uuid",
  "context": {
    "current_operation": "add_edge",
    "source": "func_a",
    "target": "func_c"
  },
  "message": "Where should I insert the func_c() call?"
}

Response:
{
  "suggestions": [
    {
      "location": "line 5",
      "reason": "After data validation, before processing",
      "code_preview": "    result = func_c(data)\n    return process(result)"
    }
  ]
}
```

---

### 5.2 WebSocket API (Real-time Updates)
```javascript
// Client connection
const ws = new WebSocket('ws://api.codeflow.dev/ws/{project_id}');

// Pipeline progress updates
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  /*
  {
    "type": "pipeline_progress",
    "stage": "conflict_detector",
    "progress": 60,
    "message": "Analyzing data dependencies..."
  }
  */
};
```

---

## 6. AI Model Configuration

### 6.1 Configuration Interface
```yaml
# config/ai_models.yaml
agents:
  conflict_detector:
    provider: "anthropic"
    model: "claude-sonnet-4-5-20250929"
    temperature: 0.2
    max_tokens: 2000
  
  semantic_analyzer:
    provider: "anthropic"
    model: "claude-sonnet-4-5-20250929"
    temperature: 0.3
    max_tokens: 3000
  
  code_generator:
    provider: "openai"
    model: "gpt-4-turbo-preview"
    temperature: 0.1
    max_tokens: 4000
  
  validator:
    provider: "anthropic"
    model: "claude-haiku-4-5-20251001"
    temperature: 0
    max_tokens: 1000

# Fallback configuration
fallback:
  enabled: true
  priority: ["anthropic", "openai", "local"]
  
# Rate limiting
rate_limits:
  requests_per_minute: 20
  tokens_per_hour: 100000
```

### 6.2 Provider Abstraction Layer
```python
from abc import ABC, abstractmethod

class LLMProvider(ABC):
    @abstractmethod
    def complete(self, prompt: str, config: dict) -> str:
        pass

class AnthropicProvider(LLMProvider):
    def complete(self, prompt: str, config: dict) -> str:
        # Anthropic API implementation
        pass

class OpenAIProvider(LLMProvider):
    def complete(self, prompt: str, config: dict) -> str:
        # OpenAI API implementation
        pass

class LocalProvider(LLMProvider):
    def complete(self, prompt: str, config: dict) -> str:
        # Ollama local model implementation
        pass

# Usage in agents
class ConflictDetectorAgent:
    def __init__(self, config: dict):
        self.provider = get_provider(config['provider'])
        self.model = config['model']
    
    def analyze(self, operation: RefactoringOp) -> ConflictAnalysis:
        prompt = self.build_prompt(operation)
        response = self.provider.complete(prompt, self.model)
        return self.parse_response(response)
```

---

## 7. Frontend Component Architecture

### 7.1 Component Hierarchy
```
App
├── ProjectUploader
├── MainWorkspace
│   ├── DependencyGraph (React Flow)
│   │   ├── FunctionNode (custom node)
│   │   ├── DependencyEdge (custom edge)
│   │   └── MiniMap
│   ├── CodeEditor (Monaco)
│   │   └── InlineAnnotations
│   └── ChatPanel
│       └── MessageList
├── ConflictModal
│   ├── ConflictDescription
│   ├── RepairOptionsList
│   └── ActionButtons
└── HistoryPanel (Undo/Redo)
```

### 7.2 State Management (Redux Toolkit)
```typescript
// store/slices/projectSlice.ts
interface ProjectState {
  currentProject: Project | null;
  dependencyGraph: {
    nodes: Node[];
    edges: Edge[];
  };
  selectedNodes: string[];
  operationHistory: RefactoringOp[];
  historyIndex: number;
}

// Actions
const projectSlice = createSlice({
  name: 'project',
  initialState,
  reducers: {
    setProject: (state, action) => { },
    updateGraph: (state, action) => { },
    addOperation: (state, action) => { },
    undo: (state) => {
      if (state.historyIndex > 0) {
        state.historyIndex--;
        // Restore previous state
      }
    },
    redo: (state) => { },
  }
});
```

### 7.3 Key UI Components

#### 7.3.1 FunctionNode (React Flow Custom Node)
```tsx
const FunctionNode: React.FC<NodeProps<FunctionNodeData>> = ({ data }) => {
  return (
    <div className="function-node">
      <Handle type="target" position={Position.Top} />
      
      <div className="node-header">
        {data.is_async && <Badge>async</Badge>}
        <span className="function-name">{data.name}</span>
      </div>
      
      <div className="node-body">
        <div className="params">
          {data.params.map(p => <Param key={p} name={p} />)}
        </div>
        <div className="file-path">{data.file}</div>
      </div>
      
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
};
```

#### 7.3.2 ConflictModal
```tsx
const ConflictModal: React.FC<ConflictModalProps> = ({ 
  conflict, 
  onSelectRepair, 
  onCancel 
}) => {
  return (
    <Dialog open={true}>
      <DialogTitle>
        <AlertCircle className="text-red-500" />
        Conflict Detected: {conflict.conflict_type}
      </DialogTitle>
      
      <DialogContent>
        <Alert variant="destructive">
          {conflict.explanation}
        </Alert>
        
        {conflict.impact_scope.cascade_functions.length > 0 && (
          <div className="cascade-warning">
            <p>This change will affect {conflict.impact_scope.cascade_functions.length} other functions:</p>
            <ul>
              {conflict.impact_scope.cascade_functions.map(f => (
                <li key={f}>{f}</li>
              ))}
            </ul>
          </div>
        )}
        
        <div className="repair-options">
          <h3>Suggested Solutions:</h3>
          {conflict.repair_options.map(option => (
            <RepairOptionCard 
              key={option.id}
              option={option}
              onSelect={() => onSelectRepair(option.id)}
            />
          ))}
        </div>
      </DialogContent>
      
      <DialogActions>
        <Button variant="outline" onClick={onCancel}>Cancel</Button>
      </DialogActions>
    </Dialog>
  );
};
```

#### 7.3.3 Code Editor with Inline Annotations
```tsx
const CodeEditorWithAnnotations: React.FC = () => {
  const [decorations, setDecorations] = useState<monaco.editor.IModelDeltaDecoration[]>([]);
  
  const applyChanges = (changes: Change[]) => {
    const newDecorations = changes.map(change => ({
      range: new monaco.Range(change.line_number, 1, change.line_number, 1),
      options: {
        isWholeLine: true,
        className: change.change_type === 'insert' ? 'code-insert' :
                   change.change_type === 'delete' ? 'code-delete' :
                   'code-modify',
        glyphMarginClassName: 'change-glyph',
        hoverMessage: { value: change.annotation }
      }
    }));
    setDecorations(newDecorations);
  };
  
  return (
    <Editor
      height="100%"
      language="python"
      theme="vs-dark"
      options={{
        readOnly: false,
        minimap: { enabled: true },
        lineNumbers: 'on'
      }}
      onMount={(editor) => {
        editor.deltaDecorations([], decorations);
      }}
    />
  );
};
```

---

## 8. Conflict Detection Algorithms

### 8.1 Data Dependency Analysis
```python
def detect_data_dependency_conflict(
    deleted_call: str,
    ast_node: ast.FunctionDef
) -> ConflictAnalysis:
    """
    Analyzes if deleting a function call breaks data flow.
    
    Algorithm:
    1. Find the assignment node for the deleted call
    2. Check if the assigned variable is used later
    3. Trace usage through the function body
    """
    
    # Example: result = func_b()
    assignment_node = find_assignment(ast_node, deleted_call)
    if not assignment_node:
        return ConflictAnalysis(has_conflict=False)
    
    variable_name = assignment_node.target.id
    
    # Check if variable is used after the call
    subsequent_usage = find_variable_usage(
        ast_node,
        variable_name,
        after_line=assignment_node.lineno
    )
    
    if subsequent_usage:
        return ConflictAnalysis(
            has_conflict=True,
            conflict_type="data_dependency",
            affected_lines=[usage.lineno for usage in subsequent_usage],
            explanation=f"Variable '{variable_name}' is used at lines {subsequent_usage} but will be undefined after deleting the call"
        )
    
    return ConflictAnalysis(has_conflict=False)
```

### 8.2 Type Mismatch Detection
```python
def detect_type_mismatch(
    old_function: Function,
    new_function: Function,
    usage_context: List[ast.stmt]
) -> ConflictAnalysis:
    """
    Detects if replacing func_a with func_b causes type issues.
    
    Uses LLM to infer return types from:
    1. Type hints (if available)
    2. Return statements
    3. Function docstrings
    """
    
    old_type = infer_return_type(old_function)
    new_type = infer_return_type(new_function)
    
    if old_type != new_type:
        # Analyze how the return value is used
        usage_patterns = analyze_usage_patterns(usage_context)
        
        # Generate conversion options
        repair_options = generate_type_adapters(old_type, new_type, usage_patterns)
        
        return ConflictAnalysis(
            has_conflict=True,
            conflict_type="type_mismatch",
            explanation=f"Return type changes from {old_type} to {new_type}",
            repair_options=repair_options
        )
    
    return ConflictAnalysis(has_conflict=False)

def generate_type_adapters(
    old_type: str,
    new_type: str,
    usage_patterns: List[str]
) -> List[RepairOption]:
    """
    Example: dict -> list conversion
    """
    if old_type == "dict" and new_type == "list":
        if "key_access" in usage_patterns:  # e.g., result['key']
            return [
                RepairOption(
                    description="Convert list to dict with enumerate",
                    code_template="result = {i: v for i, v in enumerate(result)}",
                    estimated_impact="low"
                )
            ]
    # More conversion strategies...
```

### 8.3 Async/Sync Conflict Detection
```python
def detect_async_sync_conflict(
    caller: Function,
    new_callee: Function
) -> ConflictAnalysis:
    """
    Detects if sync function tries to call async function (or vice versa).
    """
    
    if not caller.is_async and new_callee.is_async:
        # Need to convert caller to async
        cascade_impact = find_all_callers(caller)
        
        return ConflictAnalysis(
            has_conflict=True,
            conflict_type="async_sync",
            impact_scope={
                "cascade_functions": [f.name for f in cascade_impact],
                "cascade_depth": calculate_call_depth(cascade_impact)
            },
            explanation=f"Calling async function '{new_callee.name}' from sync function '{caller.name}' requires converting '{caller.name}' to async",
            repair_options=[
                RepairOption(
                    description=f"Convert {caller.name} to async (affects {len(cascade_impact)} callers)",
                    code_template=f"async def {caller.name}(...):\n    result = await {new_callee.name}(...)",
                    estimated_impact="high" if len(cascade_impact) > 5 else "medium"
                ),
                RepairOption(
                    description="Wrap with asyncio.run() (may impact performance)",
                    code_template=f"result = asyncio.run({new_callee.name}(...))",
                    estimated_impact="low"
                )
            ]
        )
    
    return ConflictAnalysis(has_conflict=False)
```

---

## 9. MVP Implementation Roadmap

### Phase 1: Core Infrastructure (Weeks 1-2)
**Deliverables:**
- [ ] FastAPI backend scaffolding
- [ ] React + React Flow frontend setup
- [ ] Parser Agent (Python AST extraction)
- [ ] Basic dependency graph visualization
- [ ] File upload and project management

**Success Criteria:**
- Upload a Python file, see function nodes connected by edges

---

### Phase 2: Read-Only Visualization (Week 3)
**Deliverables:**
- [ ] Custom React Flow nodes (function cards with metadata)
- [ ] Edge styling (sync/async differentiation)
- [ ] Zoom/pan/filter controls
- [ ] File tree sidebar
- [ ] Basic code viewer (Monaco integration)

**Success Criteria:**
- Replicate CodeSee's visualization UX for a 50-line Python script

---

### Phase 3: Multi-Agent Pipeline (Weeks 4-5)
**Deliverables:**
- [ ] AI model configuration system
- [ ] Conflict Detector Agent
- [ ] Semantic Analyzer Agent
- [ ] Code Generator Agent
- [ ] Validator Agent
- [ ] Pipeline orchestrator with progress tracking

**Success Criteria:**
- Delete an edge → AI detects conflict → Shows repair options

---

### Phase 4: Interactive Refactoring (Week 6)
**Deliverables:**
- [ ] Edge deletion with conflict modal
- [ ] Repair option selection UI
- [ ] Code diff preview (inline annotations)
- [ ] Apply/revert changes
- [ ] Undo/redo stack

**Success Criteria:**
- Complete refactoring workflow: drag → conflict → repair → apply → see updated code

---

### Phase 5: Edge Addition & Chat (Week 7)
**Deliverables:**
- [ ] Add new edge by dragging from node handle
- [ ] AI chat interface for insertion point suggestion
- [ ] Manual insertion point selection in code editor
- [ ] Parameter adaptation for new function calls

**Success Criteria:**
- Add A→C edge → AI suggests where to insert call → Apply → Code updated

---

### Phase 6: Demo Example Project (Week 8)
**Deliverables:**
- [ ] Curated example project (API migration scenario)
- [ ] Guided refactoring tasks with annotations
- [ ] Demo video showcasing workflow
- [ ] Documentation for first-time users

**Success Criteria:**
- New user can complete example refactoring in < 5 minutes

---

## 10. Non-Functional Requirements

### 10.1 Performance
- **Graph Rendering:** Support up to 100 nodes/200 edges without lag
- **AI Response Time:** < 10 seconds for conflict detection
- **Code Parsing:** < 2 seconds for 10 files (5000 LOC total)

### 10.2 Security
- **Code Privacy:** No persistent storage of uploaded code (session-only)
- **API Keys:** User-provided or server-side encrypted storage
- **HTTPS Only:** All API communication encrypted

### 10.3 Scalability (Post-MVP)
- **Concurrent Users:** 10 users simultaneously
- **Project Size:** Up to 50 files / 10,000 LOC
- **Multi-language:** Extensible parser interface for JS/TypeScript

---

## 11. Testing Strategy

### 11.1 Unit Tests
```python
# tests/test_parser_agent.py
def test_function_extraction():
    code = """
def foo():
    return bar()
def bar():
    return 42
"""
    agent = ParserAgent()
    result = agent.parse_code(code)
    assert len(result.functions) == 2
    assert len(result.dependencies) == 1
    assert result.dependencies[0].source == "foo"

# tests/test_conflict_detector.py
def test_data_dependency_detection():
    operation = RefactoringOp(type="delete_edge", ...)
    agent = ConflictDetectorAgent(mock_llm)
    analysis = agent.analyze(operation)
    assert analysis.has_conflict == True
    assert analysis.conflict_type == "data_dependency"
```

### 11.2 Integration Tests
```python
# tests/test_refactoring_pipeline.py
@pytest.mark.asyncio
async def test_full_refactoring_workflow():
    # Upload project
    project = await upload_test_project()
    
    # Trigger deletion
    operation = await delete_edge(project.id, "edge_1")
    
    # Wait for pipeline
    result = await poll_operation_status(operation.id)
    
    # Verify conflict detected
    assert result.status == "conflict_detected"
    assert len(result.repair_options) > 0
    
    # Apply repair
    final_code = await apply_repair(operation.id, "option_1")
    
    # Verify code validity
    ast.parse(final_code)  # Should not raise
```

### 11.3 E2E Tests (Playwright)
```typescript
// e2e/refactoring.spec.ts
test('delete edge with conflict resolution', async ({ page }) => {
  await page.goto('/projects/demo');
  
  // Click on an edge
  await page.click('[data-edge-id="edge_1"]');
  await page.click('button:has-text("Delete")');
  
  // Conflict modal should appear
  await expect(page.locator('.conflict-modal')).toBeVisible();
  
  // Select repair option
  await page.click('[data-option-id="option_1"]');
  await page.click('button:has-text("Apply")');
  
  // Code should update
  await expect(page.locator('.code-editor')).toContainText('result = None');
});
```

---

## 12. Future Enhancements (Post-MVP)

### 12.1 Advanced Features
- **Multi-language Support** (JavaScript/TypeScript, Java)
- **Team Collaboration** (Real-time multi-user editing)
- **Version Control Integration** (Git branch diffing)
- **Test Coverage Visualization** (Show which functions have tests)
- **Performance Profiling** (Highlight slow functions)

### 12.2 AI Enhancements
- **Batch Refactoring** (Apply same change to multiple similar patterns)
- **Intelligent Suggestions** (Proactive architecture improvements)
- **Natural Language Refactoring** ("Move all database calls to a service layer")

### 12.3 Enterprise Features
- **Self-hosted Deployment**
- **SSO Integration**
- **Audit Logs**
- **Custom AI Model Training** (Fine-tuned on company codebases)

---

## 13. Appendix

### 13.1 Example Refactoring Scenarios

#### Scenario 1: Delete Edge with Data Dependency
**Before:**
```python
def process_data(file_path):
    data = read_file(file_path)  # User deletes this edge
    cleaned = clean_data(data)
    return cleaned
```

**AI Analysis:**
```json
{
  "has_conflict": true,
  "conflict_type": "data_dependency",
  "affected_lines": [3],
  "repair_options": [
    {
      "description": "Use empty data",
      "code": "data = []"
    },
    {
      "description": "Remove dependent operations",
      "code": "# Removed: cleaned = clean_data(data)\nreturn None"
    }
  ]
}
```

---

#### Scenario 2: Add Edge with Type Mismatch
**Before:**
```python
def analyze():
    result = fetch_dict()  # Returns {'key': 'value'}
    return result['key']
```

**User Action:** Replace `fetch_dict()` with `fetch_list()` (returns `['value']`)

**AI Analysis:**
```json
{
  "has_conflict": true,
  "conflict_type": "type_mismatch",
  "repair_options": [
    {
      "description": "Convert list to dict",
      "code": "result = {i: v for i, v in enumerate(fetch_list())}"
    },
    {
      "description": "Use list indexing",
      "code": "result = fetch_list()\nreturn result[0]"
    }
  ]
}
```

---

#### Scenario 3: Async/Sync Cascade
**Before:**
```python
def main():
    result = helper()  # Sync
    return process(result)

def helper():
    return fetch_sync()  # User wants to replace with async fetch_async()
```

**AI Analysis:**
```json
{
  "has_conflict": true,
  "conflict_type": "async_sync",
  "impact_scope": {
    "cascade_functions": ["main", "helper"],
    "cascade_depth": 2
  },
  "repair_options": [
    {
      "description": "Convert entire call chain to async",
      "affected_functions": ["main", "helper"],
      "code": "async def main():\n    result = await helper()\n    return process(result)\n\nasync def helper():\n    return await fetch_async()"
    }
  ]
}
```

---

### 13.2 Technology Alternatives Considered

| Component | Chosen | Alternatives | Reason |
|-----------|--------|--------------|---------|
| Frontend Graph | React Flow | D3.js, Cytoscape.js | Built-in drag-drop, React integration |
| Code Editor | Monaco | CodeMirror 6 | VS Code engine, better LSP support |
| Backend | FastAPI | Flask, Django | Async support, auto OpenAPI docs |
| AI Framework | LangChain | Direct API calls | Multi-provider abstraction |
| State Management | Redux Toolkit | Zustand, Jotai | Complex state, time-travel debugging |

---

### 13.3 Cost Estimation (Monthly, MVP)

| Item | Cost | Notes |
|------|------|-------|
| **AI API Calls** | $150-300 | ~10K operations @ $0.015-0.03 per operation |
| **Server Hosting** | $50 | AWS t3.medium or equivalent |
| **Database** | $20 | Managed PostgreSQL |
| **CDN/Storage** | $10 | Cached assets |
| **Development** | N/A | Solo developer |
| **Total** | **$230-380** | Scales with user adoption |

---

### 13.4 Key Metrics to Track

**User Engagement:**
- Time to first refactoring operation
- Average operations per session
- Conflict resolution success rate

**Technical Performance:**
- AI response latency (p50, p95, p99)
- Graph rendering FPS
- Parser accuracy (false positive conflicts)

**Business Metrics:**
- User retention (Day 1, Day 7, Day 30)
- Conversion rate (demo → signup)
- NPS score from beta users

---

## 14. Risk Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| AI hallucinations in code generation | High | Medium | Validator Agent + user review before apply |
| Complex refactorings breaking logic | High | Medium | Sandbox testing environment (future) |
| Slow AI response times | Medium | Low | Cache common patterns, optimize prompts |
| User confusion with conflict modals | Medium | High | User testing, simplified explanations |
| Python AST parsing edge cases | Low | Medium | Fallback to syntax-only analysis |

---

## 15. Success Criteria for MVP

**Must Have:**
1. ✅ Parse Python project → Generate dependency graph
2. ✅ Delete edge → Detect conflict → Show repair options
3. ✅ Add edge → AI suggests insertion point → User confirms
4. ✅ Apply changes → See inline code annotations
5. ✅ Undo/redo operations

**Nice to Have:**
- Async/sync conflict handling
- Type mismatch adapters
- Demo example project with guided tasks

**MVP Launch Ready When:**
- [ ] User can complete a simple refactoring in < 2 minutes
- [ ] No critical bugs in core pipeline
- [ ] AI accuracy >80% on common conflicts
- [ ] Documentation for developers and end-users

---

## Document Change Log

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-01-23 | Initial technical PRD | Victor |

---

**Next Steps:**
1. Set up development environment (FastAPI + React boilerplate)
2. Implement Parser Agent (Python AST extraction)
3. Build basic React Flow visualization
4. Integrate first AI agent (Conflict Detector)

**Contact:**
For questions or clarifications, reach out via project documentation or team chat.
