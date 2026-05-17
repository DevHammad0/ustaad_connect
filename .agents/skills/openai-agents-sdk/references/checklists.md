# Checklists + common failure modes

## Build checklist (copy/paste)

### Agent design
- [ ] Agent goal is one sentence (what it does).
- [ ] Constraints are explicit (what it must not do).
- [ ] Output shape is defined (plain text vs structured).
- [ ] Toolset is minimal (avoid dumping “everything” into one agent).

### Tools
- [ ] Tool signatures are typed and validated.
- [ ] Tool errors are deterministic and actionable.
- [ ] External calls have timeouts; retries are bounded.
- [ ] Tools enforce authZ/tenancy boundaries (never rely on the model).

### Sessions / memory
- [ ] Storage is external to the process (DB / durable store).
- [ ] History trimming strategy exists (token budget).
- [ ] Retention and deletion policy are defined.

### Streaming
- [ ] Streaming is only used when the UI needs it.
- [ ] Event loop renders partial output and tool progress.
- [ ] Cancellation/timeout behavior is defined.

### Guardrails
- [ ] Guardrails exist for high-risk inputs and boundaries (authZ, PII, cross-tenant).
- [ ] Guardrails can short-circuit and return a clear report.

### Tracing / observability
- [ ] Tracing enabled in prod.
- [ ] Metadata attached (`user_id`, `request_id`, `session_id`).
- [ ] Errors and tool failures are captured with enough detail to reproduce.

### MCP
- [ ] Decide: consuming MCP tools, hosting an MCP server, or both.
- [ ] Tenant/auth boundaries are enforced in the MCP layer.
- [ ] Tool schemas are stable and versioned if needed.

## Review checklist (before shipping)
- [ ] Run E1–E5 from `references/evaluations.md`.
- [ ] Confirm the Skill activates on phrases like “handoffs”, “guardrails”, “streaming events”, “MCP”.
- [ ] Confirm `SKILL.md` remains a thin hub (not a full docs dump).
- [ ] Confirm all deep details are one-level-deep under `references/`.

## Common failure modes

### “The agent didn’t call my tool”
- Tool name/description isn’t clear enough.
- Tool arguments are hard to infer (add types + examples).
- Too many tools; reduce toolset or split by handoffs.

### “The agent calls tools with invalid args”
- Add guardrails for input validation.
- Add tool-level validation with clear error messages.
- Provide a structured output schema the agent must follow.

### “Conversation context bloats / costs explode”
- Trim/prune history (token budget).
- Store only what you need (summaries or last N turns).
- Separate “working memory” from “audit log”.

### “Streaming UI is messy”
- Stream only what you need (text deltas + tool start/end).
- Ensure your event loop always ends with a final result.

### “Cross-user data leakage risk”
- Enforce tenancy in tools and storage queries.
- Add guardrails that reject cross-tenant operations.
- Include `user_id` in tracing metadata for audits.


