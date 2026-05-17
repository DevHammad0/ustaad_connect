---
name: openai-agents-sdk
description: Builds OpenAI Agents SDK (Python) agents with tools, streaming, sessions/memory, handoffs (multi-agent), guardrails, tracing, and consuming MCP tools (Model Context Protocol). Use when the user mentions OpenAI Agents SDK, openai-agents, agents, tool calling, streaming events, sessions, memory, handoffs, guardrails, tracing/spans, or MCP.
---

# OpenAI Agents SDK (Python)

Build reliable agentic features using **OpenAI Agents SDK**. Keep implementation minimal, follow defaults, and validate with the evaluations.

## Navigation (read only what you need)

- **Quickstart (fastest path to working code)**: See `references/patterns.md` → “Agent setup”, “Tools”, “Running”, then copy templates from `assets/templates/`.
- **Evaluate the Skill**: See [`references/evaluations.md`](references/evaluations.md)
- **Authoritative docs index**: See [`references/docs-map.md`](references/docs-map.md)
- **Recommended patterns (defaults + escape hatches)**: See [`references/patterns.md`](references/patterns.md)
- **Build/review checklists + common failures**: See [`references/checklists.md`](references/checklists.md)
- **Copy/paste templates** (minimal scaffolding):
  - **Core**:
    - `assets/templates/agent.py`
    - `assets/templates/tools.py`
    - `assets/templates/runner.py`
  - **Optional (only if needed)**:
    - `assets/templates/sessions.py`
    - `assets/templates/handoffs.py`
    - `assets/templates/guardrails.py`
    - `assets/templates/tracing.py`
    - `assets/templates/mcp_consume.py`

## Workflow (default)

1. **Clarify the target**
   - What is the agent’s job?
   - What tools does it need (inputs/outputs)? Any external systems?
   - Does it need **streaming**? **sessions/memory**? **handoffs**? **guardrails**? **tracing**?
   - If MCP is mentioned: which MCP servers/tools are being consumed and what auth/tenancy context is required?

2. **Pick the smallest pattern**
   - Start with **one agent + a few tools** (E1).
   - Add **streaming** (E2) only if needed.
   - Add **sessions/memory** (E3) only if persistence is required.
   - Add **handoffs** (E4) only if you truly need multiple roles.
   - Add **guardrails + tracing** (E5) when correctness/safety/observability matters.

3. **Scaffold using templates**
   - Copy the minimal templates from `assets/templates/` into the codebase and rename as needed.
   - Keep functions small and typed; design tools first.

4. **Implement → validate → iterate**
   - Validate with the evaluation prompts in `references/evaluations.md`.
   - Keep a tight feedback loop: run → inspect output/events → fix → rerun.

## Validate loop (project)

1. Run Skill validation:

```bash
.claude/skills/skill-creator/scripts/quick_validate.py .claude/skills/openai-agents-sdk
```

2. Run E1–E5 prompts from `references/evaluations.md` and iterate until they pass.
   - “Pass” means the output matches the **Expected behavior** bullets for each evaluation.


