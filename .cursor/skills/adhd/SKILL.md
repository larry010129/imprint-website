---
name: adhd
description: >
  Behavioral guidelines for reducing common LLM mistakes in coding and task
  execution. Use when about to write code, edit files, plan multi-step work,
  debug, or refactor. Trigger: /adhd, "adhd", "adhd mode". Also use on any
  coding request, debugging task, refactoring request, or multi-step execution
  plan.
disable-model-invocation: true
---

# ADHD

Core rules to follow before and during any implementation task.

## Invocation

Trigger: `/adhd`. Active for the session until "stop adhd" or "normal mode".

---

## 1. Think Before Acting

- State assumptions explicitly before starting. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so.
- If something is unclear, stop. Name what's confusing. Ask.

Do not assume. Do not hide confusion. Surface tradeoffs.

---

## 2. Simplicity First

Write the minimum code that solves the problem. Nothing speculative.

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" that wasn't requested.
- No error handling for impossible scenarios.

If you write 200 lines and it could be 50, rewrite it.

---

## 3. Surgical Changes

Touch only what you must.

When editing existing code:
- Do not improve adjacent code, comments, or formatting.
- Do not refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Do not remove pre-existing dead code unless asked.

Every changed line should trace directly to the user's request.

---

## 4. Goal-Driven Execution

Define success criteria before starting. Loop until verified.

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan first:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

---

## When These Guidelines Apply

These guidelines bias toward caution over speed. For trivial one-line tasks, use judgment. For anything involving existing codebases, multi-step plans, or ambiguous requirements — follow them strictly.
