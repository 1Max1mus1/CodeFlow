# Codeflow Acceptance Plan

**Version:** 1.0  
**Date:** 2026-04-12  
**Tester:** User (Trial Official)  
**Reviewer:** Claude (AI Assistant)

---

## Overview

This document guides the Human-in-the-Loop acceptance process for Codeflow Phases 1–6.  
The app is running at:
- Frontend: http://localhost:5173
- Backend: http://localhost:8000

For each scenario, perform the steps, then report back one of:
- **PASS** – works exactly as described
- **FAIL [description]** – something went wrong
- **PARTIAL [description]** – mostly works but has issues

---

## Scenario 1 — Project Load & Graph Display

**Goal:** Verify that the app loads a project and renders the call graph correctly.

**Steps:**
1. Open http://localhost:5173 in your browser
2. The left sidebar should show a "Parse Project" button or path input — enter the path to `Codeflow\example\TestProject` (absolute path on your machine, e.g. `C:\Users\YourUserName\Desktop\Codeflow\example\TestProject`)
3. Click **Parse**
4. The graph canvas should appear with colored nodes:
   - Blue nodes = Python functions
   - Orange nodes = schemas
   - Purple nodes = external APIs (none initially)
5. You should see function nodes including `create_job`, `get_job`, `_update_job_status`
6. Blue arrows (call edges) should connect them

**Report:** PASS / FAIL / PARTIAL

---

## Scenario 2 — Session Creation

**Goal:** Verify session is created when an entry point is selected.

**Steps:**
1. After parsing, the left sidebar should list entry points
2. Click the entry point for `create_job` (or whichever is shown)
3. The sidebar should update and show the session is active
4. The "+ Import External API" button at the bottom of the sidebar should become enabled

**Report:** PASS / FAIL / PARTIAL

---

## Scenario 3 — Delete Operation (no AI needed)

**Goal:** Verify delete operation flow works end-to-end without AI.

**Steps:**
1. Click on a function node in the graph (e.g., `_update_job_status`)
2. The right panel should show details for that function
3. Press the **Delete** key on your keyboard
4. A confirmation question should appear in the right panel: "What should happen at those call sites after deletion?"
5. Select an option (e.g., "Skip the calls")
6. The diff preview should appear showing the code changes
7. Click **Apply** — the status should change to "applied"

**Report:** PASS / FAIL / PARTIAL

---

## Scenario 4 — Import External API

**Goal:** Verify that an external API node can be imported.

**Steps:**
1. Click "+ Import External API" in the left sidebar (must have an active session)
2. A modal should appear with fields: Name, Endpoint, Method (dropdown), Description, Output Schema
3. Fill in:
   - Name: `StatusAPI`
   - Endpoint: `/status`
   - Method: `GET`
   - Add one schema field: name=`status`, type=`str`
4. Click **Confirm**
5. A purple "StatusAPI" node should appear on the graph canvas

**Report:** PASS / FAIL / PARTIAL

---

## Scenario 5 — Replace Operation (drag gesture)

**Goal:** Verify that dragging an ExternalAPI node onto a function triggers replace.

**Prerequisites:** Scenario 4 completed (purple node visible)

**Steps:**
1. Click and drag the purple `StatusAPI` node onto a blue function node (e.g., `get_job`)
2. A confirmation dialog should appear: "Replace `get_job` with `StatusAPI`?"
3. Click **Confirm**
4. The right panel should show questions about schema compatibility
5. Answer one question, or type "cancel" and hit Enter
6. After answering, a diff preview should appear

**Report:** PASS / FAIL / PARTIAL

---

## Scenario 6 — Add Insert (edge click)

**Goal:** Verify that clicking a call edge triggers the add_insert flow.

**Steps:**
1. Ensure no active operation (refresh if needed, re-parse project)
2. Create a session again (click entry point)
3. Click on a **blue call edge** (the arrow between two function nodes, e.g., between `create_job` and `_update_job_status`)
4. A dialog should appear: "Insert a new function between X and Y?"
5. Click **Confirm**
6. The right panel should show one free-text question describing what the new function should do
7. The question should mention both function names and their types
8. Type "cancel" and press Enter — the status should change to "ready" immediately (no AI call)
9. A (empty) diff preview should appear

**Report:** PASS / FAIL / PARTIAL

---

## Scenario 7 — Add Branch (button click)

**Goal:** Verify that clicking "Add Branch Function" on a selected function works.

**Steps:**
1. Click on a function node (e.g., `create_job`)
2. The right panel should show the function's name and an "Add Branch Function" button
3. Click **Add Branch Function**
4. The right panel should show 2 questions:
   - Q1: What condition should trigger the new branch? (Python expression)
   - Q2: What should the new branch function do?
5. Answer Q1 with "cancel" — the operation should jump to "ready" immediately
6. A diff preview should appear

**Report:** PASS / FAIL / PARTIAL

---

## Scenario 8 — Revert Operation

**Goal:** Verify that a "ready" operation can be reverted.

**Steps:**
1. Get any operation to "ready" state (e.g., delete with "cancel" answer)
2. In the diff preview, click **Revert**
3. The operation status should change to "reverted"
4. The right panel should clear the diff view

**Report:** PASS / FAIL / PARTIAL

---

## Scoring

| Scenario | Description | Result |
|----------|-------------|--------|
| 1 | Project Load & Graph Display | |
| 2 | Session Creation | |
| 3 | Delete Operation | |
| 4 | Import External API | |
| 5 | Replace (drag gesture) | |
| 6 | Add Insert (edge click) | |
| 7 | Add Branch (button) | |
| 8 | Revert Operation | |

**Pass threshold:** 7/8 scenarios PASS or PARTIAL  
**AI scenarios** (5, 6 full diff, 7 full diff): require `MOONSHOT_API_KEY` in `backend/.env`

---

## How to Report

After trying each scenario, reply with one of:
- Scenario number + PASS/FAIL/PARTIAL
- Any error messages or unexpected behavior you saw
- Screenshots if helpful (paste as text description)

I will adjust the code based on your feedback and re-test.
