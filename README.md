# CodeFlow

**An AI-powered Python codebase visualiser with live graph editing.**

CodeFlow parses your Python project into an interactive call-graph, lets you explore function relationships visually, and uses an LLM to perform structural code changes — delete functions, branch logic, insert intermediaries, or replace implementations with external APIs — all with diff preview and one-click apply/undo.

> **Built entirely with AI-assisted engineering via the Claude Code CLI (Anthropic Harness Engineering).** Every feature — from the AST parser to the ReactFlow graph, AI prompts, and operation pipeline — was designed, implemented, debugged, and acceptance-tested through natural-language conversation with Claude Code. No boilerplate was written by hand.

---

## What it does

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

---

## Tech stack

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

---

## Getting started

### Prerequisites

- Python 3.11+
- Node.js 18+
- A [Moonshot API key](https://platform.moonshot.cn/) (Kimi)

### 1 — Clone

```bash
git clone https://github.com/1Max1mus1/CodeFlow.git
cd CodeFlow
```

### 2 — Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env and paste your Moonshot API key:
# MOONSHOT_API_KEY=sk-...
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### 3 — Frontend

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173
```

### 4 — Load a project

1. Open `http://localhost:5173`
2. Enter the **absolute path** to any Python project in the sidebar (e.g. `C:\Users\you\my_project`)
3. Click **Load** — CodeFlow parses the project and renders the call graph
4. Select an entry point from the sidebar to filter the graph
5. Right-click any function node to start an AI operation

An example project is included at `example/TestProject/` to try immediately.

---

## AI operations walkthrough

### Delete a function
Right-click → **Delete** → confirm → AI asks how to handle call sites → review diff → Apply

### Add a branch
Right-click → **Add Branch** on any function → fill in:
1. The Python condition expression
2. What the new branch function should do
3. Which file to place the new function in

### Insert an intermediate function
Click any **call edge** between two functions → confirm → fill in:
1. What the new function should do
2. Which file to place it in

### Replace with external API
Import an API via the toolbar → drag the API node onto a function → AI maps schemas → review diff → Apply

---

## Project structure

```
CodeFlow/
├── backend/
│   ├── src/
│   │   ├── main.py               # FastAPI app entry
│   │   ├── models/domain.py      # Pydantic domain models
│   │   ├── routers/              # REST endpoints (project, session, operation)
│   │   └── services/
│   │       ├── parser.py         # astroid-based Python AST parser
│   │       ├── session.py        # in-memory store
│   │       └── ai/
│   │           ├── analyzer.py   # Programmatic question generation
│   │           ├── generator.py  # Moonshot API → FileDiff generation
│   │           └── prompts.py    # All LLM prompt templates
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.tsx               # Root component, event wiring
│   │   ├── components/           # ReactFlow nodes, edges, panels, IDE view
│   │   ├── hooks/                # useOperation, useProject, useSession
│   │   ├── services/api.ts       # HTTP client for backend
│   │   ├── store/                # Zustand global state
│   │   └── utils/projectToFlow.ts# Project → ReactFlow nodes/edges
│   └── package.json
├── tests/                        # Backend integration tests (phase 0–6)
└── example/TestProject/          # Sample Python project for testing
```

---

## What makes it different

**Most code-visualisation tools are read-only.** CodeFlow closes the loop: parse → visualise → edit → apply — all in one interface, with an LLM doing the heavy lifting for the refactoring.

**Structured AI operations, not a chat box.** Instead of a free-form chat, every operation is a typed workflow (delete / add_branch / add_insert / replace) with programmatically-generated clarifying questions. The AI only writes code after the user has answered every question — reducing hallucination and keeping diffs minimal.

**Cross-file generation.** When adding a new function the user picks the destination file. For cross-file placements, CodeFlow runs two sequential Moonshot calls: one to write the new function, one to add the import and call-site update to the original file — automatically deriving the new function name by diffing `def` statements.

**Session-resilient operations.** Operations store `project_id` directly, so applied/rolled-back operations survive backend restarts without losing context.

**Built with Harness Engineering.** This entire project — architecture, implementation, testing, and iteration — was completed through Claude Code (Anthropic's agentic CLI). The codebase represents what AI-assisted engineering can produce end-to-end: from initial PRD through to a working, tested product.

---

## Running tests

```bash
# From project root
pytest tests/ -v
```

Tests cover parsing, session management, operation lifecycle, diff generation, and apply/rollback.

---

## Environment variables

| Variable | Description |
|---|---|
| `MOONSHOT_API_KEY` | Your Moonshot (Kimi) API key — required for all AI operations |

---

## License

MIT
