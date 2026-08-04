# AI Interactions Log

> **Stretch features only.** Only fill in the sections that apply to stretch features you attempted. If you did not attempt a stretch feature, leave its section blank or delete it. This file is not required for the core project.

---

## Agent Workflow (SF7)

> Document your experience using an AI agent (e.g., Cursor Agent, Claude, Copilot) to make multi-step changes autonomously.

**What task did you give the agent?**

<!-- Describe the goal you asked the agent to accomplish -->
The `ReschedulingAgent` (in `ai_agent.py`) is given the task of resolving same-pet scheduling conflicts and skipped tasks that the deterministic `Scheduler` couldn't handle on its own. When `Scheduler.check_conflicts()` finds an overlap (or `_skipped` is non-empty), the agent takes over: it must propose a new set of times that eliminates the conflict while keeping every task within the owner's time budget.

**What did the agent do?**

<!-- List the steps the agent took (files edited, commands run, etc.) -->
The agent runs a three-step plan → act → check loop:

1. **Plan** — it builds a prompt containing the owner's budget, the current plan, any skipped tasks, and the specific detected issues, then sends it to Groq's `llama-3.3-70b-versatile` model and asks for a JSON array of `{"title", "new_time"}` fixes.
2. **Act** — it applies those fixes to a deep copy of the plan (never touching the live plan directly).
3. **Check** — it re-runs the scheduler's own conflict-overlap formula and budget check against the candidate plan. If clean, the fix is committed to `self.scheduler.plan`. If not, the specific validation failure is fed back into the next prompt and the agent retries, up to 3 attempts total, before raising `AgentError` and falling back to the original (conflicted but at least known) plan.

**Real trace from a live run** (captured from the Streamlit UI, `Morning walk` and `eat` both forced to 08:30):

```json
{
  "attempt": 1,
  "prompt": "You are a scheduling assistant for a pet-care app.\n\nOwner budget: 120 minutes, starting 08:00.\n\nCurrent plan for Biscuit:\n- Morning walk @ 08:30 (30min, high)\n- eat @ 08:30 (30min, high)\n- walk @ 09:00 (40min, high)\n\nSkipped tasks (didn't fit):\nNone\n\nDetected issues:\n⚠️  CONFLICT on Biscuit: 'Morning walk' (08:30–09:00) overlaps 'eat' (08:30–09:00)\n\nRespond with ONLY a JSON array, no prose, no markdown fences. Each item:\n{\"title\": \"<task title>\", \"new_time\": \"HH:MM\"}\nKeep every task within the owner's budget window. This is attempt 1/3.",
  "response": "[{\"title\": \"Morning walk\", \"new_time\": \"08:00\"}, {\"title\": \"eat\", \"new_time\": \"08:30\"}, {\"title\": \"walk\", \"new_time\": \"09:00\"}]"
}
{
  "attempt": 1,
  "result": "accepted"
}
```

Resolved on the first attempt — no retry needed in this case. See `logs/agent_trace_bad_json.json` for an example of a run where the model returned malformed output and the agent had to retry through all 3 attempts before falling back safely.

**What did you have to verify or fix manually?**

<!-- Describe anything the agent got wrong or that required human review -->

- **Markdown fences:** despite the prompt explicitly saying "no markdown fences," Groq's Llama model sometimes wrapped its JSON response in ` ```json ... ``` ` anyway. I added a `_extract_json()` guardrail step using a regex to strip fences before parsing — without it, a genuinely valid fix would have been rejected as malformed JSON purely on formatting, not content.
- **Validation logic:** I did not trust the LLM's own claim that a fix "resolved" the conflict. `_validate()` independently re-runs the scheduler's proven overlap-detection formula (`a_start < b_end and b_start < a_end`) and budget math against the candidate plan before it's ever accepted — this is what actually caught cases where the model proposed a no-op fix (same time as before) or a fix that pushed a task past the owner's budget (both confirmed in `evaluate_agent.py`'s scenario tests).
- **Trace logging format:** I initially wrote a test assuming one trace entry per attempt; running it against the real agent showed each failed attempt actually logs two entries (prompt/response, then a separate parse error). I fixed the test's assertion rather than changing the logging, since the two-entry format is more useful for debugging (you can see both what was sent and specifically why it failed).

---

## Prompt Comparison (SF11)

> Compare two different prompts (or two different models) on the same task.

| | Option A | Option B |
|-|----------|----------|
| **Model / tool used** | | |
| **Prompt** | | |
| **Response summary** | | |
| **What was useful** | | |
| **Problems noticed** | | |
| **Decision** | | |

**Which approach did you use in your final implementation and why?**

<!-- Your conclusion -->
