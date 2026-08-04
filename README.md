# PawPal+ (Applied AI System Final Project)

## Base Project

This project extends **PawPal+** (Module 2), an object-oriented pet-care scheduler built with Python dataclasses. The original system let an owner register pets, add care tasks (feeding, walks, meds, grooming), and generate a daily schedule using a greedy priority-based algorithm — with sorting, filtering, recurring-task logic, and conflict detection, but no AI/LLM component of any kind.

## New AI Feature: Rescheduling Agent

This final project adds a genuine AI capability on top of that deterministic system: a **`ReschedulingAgent`** (`ai_agent.py`) that runs a plan → act → check loop using an LLM (Groq, `llama-3.3-70b-versatile`) whenever the scheduler detects a same-pet conflict or a skipped task.

1. **Plan** — the agent sends the current schedule, conflicts, and skipped tasks to the LLM and asks for a JSON array of time fixes.
2. **Act** — it applies those fixes to a candidate copy of the plan.
3. **Check** — it re-runs the scheduler's own conflict and budget rules as a guardrail. If the fix is invalid, the failure is fed back to the LLM and it retries (up to 3 attempts) before falling back to the original plan with a warning.

The agent is wired into both `main.py` (CLI) and `app.py` (Streamlit — see the "🤖 Ask AI to resolve conflicts" button that appears next to any conflict warning). See `diagrams/architecture.mmd` for the full data-flow diagram, and `diagrams/uml_final.mmd` for the class structure.

## Architecture Overview

`diagrams/architecture.mmd` shows the data flow: owner/pet/task data feeds into `Scheduler.build_plan()`, which checks for conflicts or skipped tasks. If none are found, the plan goes straight to the user. If issues exist, the `ReschedulingAgent` takes over — it asks the LLM to propose fixes (plan), applies them to a candidate schedule (act), and re-checks that candidate against the scheduler's own conflict/budget rules (check). A valid fix is accepted and shown to the user; an invalid one triggers a retry (up to 3 attempts) with the failure reason fed back to the LLM; if all retries fail, the system falls back to the original plan with a warning rather than showing a broken schedule. `diagrams/uml_final.mmd` shows the underlying class structure — `Owner` owns `Pet`s, each `Pet` owns `Task`s, and `Scheduler` is injected with both to read, sort, and schedule tasks; `ReschedulingAgent` sits alongside `Scheduler`, reading and mutating its `plan` without needing changes to the original classes.

## Design Decisions

- **The agent only touches same-pet conflicts, not cross-pet ones.** Cross-pet conflicts (e.g., Jordan can't walk one pet while bathing another) are still detected and shown, but resolving them would require coordinating multiple schedulers at once, which was out of scope for this iteration. This is a deliberate trade-off to keep the agent's responsibility narrow and its guardrail logic easy to verify.
- **The agent never edits the live plan directly.** `_apply_fixes()` works on a deep copy, and only `resolve()` commits the result back to `self.scheduler.plan`, and only after `_validate()` passes. This means a failed or malicious-looking LLM response can never corrupt the real schedule mid-attempt.
- **Bounded retries (3) instead of unlimited.** An LLM that keeps failing validation could loop forever; capping attempts and falling back to the original (safe, if imperfect) plan was chosen over either infinite retries or immediately giving up on attempt 1.
- **Groq over a paid API.** The project needed a real LLM call for the "substantial AI feature" requirement without a $-cost dependency for grading; Groq's free tier meets that while still requiring genuine prompt engineering and JSON-reliability handling (see the code-fence-stripping logic in `_extract_json()`, added after testing showed Llama models sometimes wrap JSON in markdown fences despite instructions not to).

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan
- Automatically resolve scheduling conflicts using AI, with a safety check before any fix is applied

## What this system does

- Lets a user enter basic owner + pet info
- Lets a user add/edit tasks (duration + priority at minimum)
- Generates a daily schedule/plan based on constraints and priorities
- Displays the plan clearly and explains the reasoning
- Detects same-pet and cross-pet scheduling conflicts
- Runs an AI agent that proposes, applies, and validates fixes for same-pet conflicts
- Includes automated tests and an evaluation harness for both the scheduler and the agent

## Getting started

### Setup
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install tabulate groq python-dotenv
```

### AI Agent Setup

The rescheduling agent needs a free Groq API key:

1. Get one at [console.groq.com](https://console.groq.com) → API Keys → Create API Key (no billing info required)
2. Create a `.env` file in the project root containing:
   ```
   GROQ_API_KEY=gsk_your_actual_key_here
   ```
3. `.env` is already listed in `.gitignore` — it is never committed. If the key is missing, `ai_agent.py` will raise an authentication error when it tries to contact Groq; the rest of the app (scheduling, sorting, conflict detection) still works without it.

### Run the app
```bash
streamlit run app.py
```

### Run from the terminal
```bash
python main.py
```

### Run the test suites
```bash
python -m pytest -v              # scheduler tests
python -m pytest tests/test_agent.py -v   # AI agent tests
python evaluate_agent.py         # AI agent evaluation harness
```

## 🖥️ Sample Output

```
════════════════════════════════════════════════════════════
               🐾  PawPal+ — Today's Schedule
════════════════════════════════════════════════════════════
  📅  Monday, August 03 2026

  Owner:  Jordan
  Budget: 120 min  │  Start: 08:00
════════════════════════════════════════════════════════════

🐕 Biscuit (Golden Retriever)
────────────────────────────────────────────────────────────
╭─────────────┬──────────────────┬────────────┬────────────┬──────────────╮
│ Time        │ Task             │   Duration │ Priority   │ Recurrence   │
├─────────────┼──────────────────┼────────────┼────────────┼──────────────┤
│ 08:05–08:10 │ 💊 Medication     │      5 min │ ● HIGH     │ 📅 daily      │
│ 08:05–08:15 │ 🍽 Feeding        │     10 min │ ● HIGH     │ 📅 daily      │
│ 08:15–08:45 │ 🚶 Morning walk   │     30 min │ ● HIGH     │ 📅 daily      │
│ 08:45–08:55 │ 🛁 Teeth brushing │     10 min │ ● MED      │ 📅 daily      │
│ 08:55–09:10 │ 🎾 Enrichment toy │     15 min │ ● MED      │ 📅 daily      │
│ 09:10–09:50 │ 🛁 Bath           │     40 min │ ● LOW      │ 📆 weekly     │
╰─────────────┴──────────────────┴────────────┴────────────┴──────────────╯

  Time used: [███████████████████████████░░░] 110/120 min

🤖 AI Rescheduling Agent — Biscuit
────────────────────────────────────────────────────────────
  ✅ Agent resolved conflicts. Updated plan:
    08:00 — Medication
    08:05 — Feeding
    08:15 — Morning walk
    08:45 — Teeth brushing
    08:55 — Enrichment toy
    09:10 — Bath

  Progress: 0/6 tasks complete (0%)
  Still to do:
    ○  💊 Medication  @ 08:00
    ○  🍽 Feeding  @ 08:05
    ○  🚶 Morning walk  @ 08:15
    ○  🛁 Teeth brushing  @ 08:45
    ○  🎾 Enrichment toy  @ 08:55
    ○  🛁 Bath  @ 09:10

🐈 Mochi (Siamese)
────────────────────────────────────────────────────────────
╭─────────────┬────────────────┬────────────┬────────────┬──────────────╮
│ Time        │ Task           │   Duration │ Priority   │ Recurrence   │
├─────────────┼────────────────┼────────────┼────────────┼──────────────┤
│ 08:00–08:05 │ 🧹 Litter box   │      5 min │ ● HIGH     │ 📅 daily      │
│ 08:05–08:15 │ 🍽 Feeding      │     10 min │ ● HIGH     │ 📅 daily      │
│ 08:15–08:25 │ 🛁 Brush coat   │     10 min │ ● MED      │ 📆 weekly     │
│ 08:25–08:40 │ 🎾 Playtime     │     15 min │ ● MED      │ 📅 daily      │
│ 08:40–09:10 │ 🏥 Vet check-up │     30 min │ ● LOW      │ 🔔 as needed  │
╰─────────────┴────────────────┴────────────┴────────────┴──────────────╯

  Time used: [█████████████████░░░░░░░░░░░░░] 70/120 min

  Progress: 0/5 tasks complete (0%)
  Still to do:
    ○  🧹 Litter box  @ 08:00
    ○  🍽 Feeding  @ 08:05
    ○  🛁 Brush coat  @ 08:15
    ○  🎾 Playtime  @ 08:25
    ○  🏥 Vet check-up  @ 08:40

⚠️  Conflict Check
────────────────────────────────────────────────────────────
  ⚠️  CROSS-PET CONFLICT: Biscuit·'Medication' (08:00–08:05) overlaps Mochi·'Litter box' (08:00–08:05)
  ⚠️  CROSS-PET CONFLICT: Biscuit·'Feeding' (08:05–08:15) overlaps Mochi·'Feeding' (08:05–08:15)
  ⚠️  CROSS-PET CONFLICT: Biscuit·'Morning walk' (08:15–08:45) overlaps Mochi·'Brush coat' (08:15–08:25)
  ⚠️  CROSS-PET CONFLICT: Biscuit·'Morning walk' (08:15–08:45) overlaps Mochi·'Playtime' (08:25–08:40)
  ⚠️  CROSS-PET CONFLICT: Biscuit·'Morning walk' (08:15–08:45) overlaps Mochi·'Vet check-up' (08:40–09:10)
  ⚠️  CROSS-PET CONFLICT: Biscuit·'Teeth brushing' (08:45–08:55) overlaps Mochi·'Vet check-up' (08:40–09:10)
  ⚠️  CROSS-PET CONFLICT: Biscuit·'Enrichment toy' (08:55–09:10) overlaps Mochi·'Vet check-up' (08:40–09:10)

💡 Why was this plan chosen?
────────────────────────────────────────────────────────────
Plan explanation for Biscuit (Jordan, 120 min available):

  ✓ Medication: scheduled first — highest priority
  ✓ Feeding: scheduled first — highest priority
  ✓ Morning walk: scheduled first — highest priority
  ✓ Teeth brushing: included — fits within remaining time (priority: medium)
  ✓ Enrichment toy: included — fits within remaining time (priority: medium)
  ✓ Bath: included — fits within remaining time (priority: low)

Plan explanation for Mochi (Jordan, 120 min available):

  ✓ Litter box: scheduled first — highest priority
  ✓ Feeding: scheduled first — highest priority
  ✓ Brush coat: included — fits within remaining time (priority: medium)
  ✓ Playtime: included — fits within remaining time (priority: medium)
  ✓ Vet check-up: included — fits within remaining time (priority: low)

════════════════════════════════════════════════════════════
  All schedules generated.  11 tasks · 180 min planned  🐶🐱
════════════════════════════════════════════════════════════
```

*Note: Biscuit's `Medication`/`Feeding` conflict above was forced on purpose in `main.py` so the AI agent's behavior is visible end-to-end in this demo run. The cross-pet conflicts below are detected but intentionally left unresolved — the agent is scoped to one pet's own schedule; see Limitations in `model_card.md`.*

## 📐 Smarter Scheduling

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| **Task sorting** | `sort_tasks()`, `sort_by_time()` | `sort_tasks()` orders by priority score descending (high=3, medium=2, low=1), then duration ascending as a tiebreaker. `sort_by_time()` re-orders the built plan chronologically using zero-padded `"HH:MM"` string comparison. |
| **Filtering** | `filter_by_priority()`, `filter_by_recurrence()`, `filter_by_status()`, `filter_by_pet()` | Filters tasks by priority level, recurrence pattern, completion status, or pet name. `filter_by_status()` drives the to-do/done metric tiles in the UI. |
| **Conflict handling** | `check_conflicts()`, `check_cross_pet_conflicts()` | Detects overlapping tasks using the interval overlap formula `a_start < b_end and b_start < a_end`. Returns plain warning strings — never raises. Cross-pet detection catches cases where one owner cannot do two things simultaneously. |
| **Recurring tasks** | `next_occurrence()`, `mark_task_complete()` | Uses `datetime.timedelta` to compute next due dates (`+1 day` daily, `+7 days` weekly). Auto-registers the next occurrence in `pet._tasks` when a task is marked complete. `as_needed` tasks return `None`. |
| **Greedy scheduling** | `build_plan()` | Iterates sorted tasks and fits each one into the time budget. Skipped tasks are stored in `self._skipped` with a reason. Elapsed time is derived from `current_minutes - start_minutes` — no separate counter needed. |
| **Plan explanation** | `explain_plan()` | Returns a plain-English reason for every scheduled and skipped task. Displayed as a collapsible expander in the UI. |
| **Progress tracking** | `progress_report()`, `filter_by_status()` | Tracks done vs remaining tasks per pet. Feeds `st.metric` tiles and the `st.progress` budget bar in the Streamlit UI. |
| **Input validation** | `Task.__post_init__()` | Rejects invalid priority/recurrence values and non-positive durations at object creation time, before any scheduling runs. |
| **AI rescheduling agent** | `ReschedulingAgent.resolve()` (`ai_agent.py`) | Runs a plan → act → check loop: an LLM (Groq) proposes time fixes for same-pet conflicts, fixes are applied to a candidate plan, then re-validated against the scheduler's own conflict/budget rules before being accepted. Retries up to 3 times, then falls back safely with a warning. |

## 📸 Demo Walkthrough

### Streamlit UI (`streamlit run app.py`)

The app has four numbered sections that guide the user from setup to schedule:

**Section 1 — Owner Info**
Enter your name, total daily time budget (in minutes), and preferred start time (`HH:MM`). Click **Save owner**. A green success banner confirms the owner is saved. The owner info bar persists at the top of every section below — Streamlit's `session_state` keeps it alive across interactions.

**Section 2 — Add a Pet**
Enter a pet name, species, breed, and age, then click **Add pet**. The pet is registered with the owner and a `Scheduler` is created for it immediately. Registered pets are listed inline. You can add multiple pets — each gets its own scheduler.

**Section 3 — Add Tasks**
Select which pet the task belongs to, then fill in a title, duration, priority (`high / medium / low`), and recurrence (`daily / weekly / as_needed`). Click **Add task**. Each pet's current task library is visible in a collapsible expander. Adding a task marks any existing plan as stale.

**Section 4 — Today's Schedule**
Click **🗓️ Build Today's Schedule**. The scheduler runs `build_plan()` for every pet and displays:
- A schedule table sorted chronologically via `sort_by_time()`, with priority colour-coded (🔴 high, 🟡 medium, 🟢 low)
- A `st.progress` bar showing time used vs total budget
- A skipped-tasks expander listing anything that didn't fit
- Two `st.metric` tiles — "Tasks to do" and "Completed" — from `filter_by_status()`
- A **"Why was this plan chosen?"** expander with `explain_plan()` output
- If two tasks overlap, a `st.warning` banner appears above the table with a **"Show conflicts"** expander for details, plus a **🤖 Ask AI to resolve conflicts** button that triggers `ReschedulingAgent.resolve()` live and shows a **🧠 Agent reasoning trace** expander with the actual prompt/response/validation steps
- If two pets' plans overlap (Jordan can't do two things at once), a cross-pet warning banner appears at the top of the section

### Example workflow

```
1. Enter name: Jordan | Budget: 120 min | Start: 08:00 → Save owner
2. Add pet: Biscuit (dog, Golden Retriever, age 3) → Add pet
3. Add tasks to Biscuit:
     Morning walk   30 min  high    daily
     Feeding        10 min  high    daily
     Medication      5 min  high    daily
     Teeth brushing 10 min  medium  daily
     Bath           40 min  low     weekly
4. Click: Build Today's Schedule
5. View sorted table, time budget bar, and explanation panel
6. If a conflict is detected, click "🤖 Ask AI to resolve conflicts" and review the reasoning trace
7. Expand "Why was this plan chosen?" to read per-task reasoning
```

### Key scheduler behaviors shown in the UI

| Behavior | Where you see it |
|---|---|
| Priority sort | High tasks always appear first in the schedule table |
| Chronological sort | Table rows are in `HH:MM` order via `sort_by_time()` |
| Time budget | Progress bar fills proportionally; skipped tasks listed separately |
| Conflict warning | `st.warning` banner + expandable detail if tasks overlap |
| AI conflict resolution | "🤖 Ask AI to resolve conflicts" button + live reasoning trace expander |
| Plan reasoning | Collapsible `explain_plan()` panel per pet |
| Progress tracking | "Tasks to do" / "Completed" metric tiles |

### Live AI agent run (captured from the Streamlit UI)

```
⚠️ 1 conflict(s) detected for Biscuit. Two or more tasks overlap. Review and adjust times.

Show Biscuit's conflicts
  ⚠️ CONFLICT on Biscuit: 'Morning walk' (08:30–09:00) overlaps 'eat' (08:30–09:00)

✅ AI agent resolved the conflict(s) for Biscuit.

🧠 Agent reasoning trace
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

Resulting table after the fix:

```
08:00  Morning walk   30 min  🔴 high  daily
08:30  eat            30 min  🔴 high  daily
09:00  walk           40 min  🔴 high  daily
⏱ Time used: 100 / 120 min
```

### CLI output (`python main.py`)

See the full "🖥️ Sample Output" section above — it now includes the "🤖 AI Rescheduling Agent — Biscuit" block showing the same plan → act → check cycle running end-to-end from the terminal.

## 🎨 Formatting Features

### CLI (`main.py`)

| Feature | Implementation | Where you see it |
|---|---|---|
| **Structured tables** | `tabulate` library, `rounded_outline` style | Schedule printed as a box-drawn table with aligned columns |
| **ANSI colour-coded priority** | `\033[91m` red / `\033[93m` yellow / `\033[92m` green + `\033[0m` reset | `● HIGH` in red, `● MED` in yellow, `● LOW` in green in the Priority column |
| **Task-type emoji icons** | `task_icon()` keyword matcher in `main.py` | 🚶 walks, 🍽 feeding, 💊 medication, 🛁 grooming, 🎾 enrichment, 🏥 vet, 🧹 litter |
| **Recurrence badges** | `recurrence_badge()` in `main.py` | 📅 daily, 📆 weekly, 🔔 as needed |
| **ASCII progress bar** | Inline string — `█` filled, `░` empty, coloured by % used | `[███████████░░░░░]  110/120 min` — yellow if >85%, red if over budget |
| **Section headers** | `print_section()` with ANSI bold + cyan + dim divider | Cyan bold labels between each output block, including the AI agent section |
| **Conflict warnings** | Red ANSI on `⚠️ CONFLICT` lines | Conflict lines printed in red; clean result printed in green |

### Streamlit UI (`app.py`)

| Feature | Component | Where you see it |
|---|---|---|
| **Priority colour dots** | `PRIORITY_EMOJI` dict — 🔴 🟡 🟢 | Priority column in every schedule table |
| **Time budget bar** | `st.progress(pct, text=...)` | Fills proportionally; label shows `used / total min` |
| **Conflict banners** | `st.warning(...)` + `st.expander(...)` | Yellow banner above the table; expandable detail list |
| **AI agent button + trace** | `st.button(...)`, `st.spinner(...)`, `st.json(...)` | "🤖 Ask AI to resolve conflicts" button next to conflict warnings; reasoning trace shown as a collapsible JSON expander |
| **Progress tiles** | `st.metric("Tasks to do", n)` | Two side-by-side metric cards below each schedule |
| **Skipped tasks** | `st.expander("⏭ Skipped tasks...")` | Collapsible block listing tasks that didn't fit |
| **Reasoning panel** | `st.expander("💡 Why was this plan chosen?")` | Collapsible `explain_plan()` output per pet |

### Libraries used

```bash
pip install tabulate groq python-dotenv
# streamlit            # already in requirements.txt
```

`tabulate` is a lightweight library with no dependencies used for CLI table formatting. `groq` is the client SDK for the Groq LLM API used by the rescheduling agent. `python-dotenv` loads the `GROQ_API_KEY` from a local `.env` file so the key is never hardcoded or committed. ANSI colours are built into Python's string literals and need no extra library.

## 🧪 Testing PawPal+

```bash
# Run the full scheduler test suite
python -m pytest

# Run with verbose output (shows each test name)
python -m pytest -v

# Run with coverage report
python -m pytest --cov
```

### What the scheduler tests cover

The suite has 11 tests split into happy paths and edge cases:

**Happy paths** — normal usage that must always work:
- `test_mark_complete_changes_status` — `Task.mark_complete()` flips `completed` from `False` to `True`
- `test_add_task_increases_pet_task_count` — `Pet.add_task()` correctly grows the task list
- `test_build_plan_orders_high_priority_first` — tasks added out of order are sorted by priority before scheduling

**Sorting correctness:**
- `test_sort_by_time_returns_chronological_order` — `sort_by_time()` returns the built plan in `HH:MM` order regardless of insertion order

**Recurrence logic:**
- `test_daily_task_creates_next_occurrence_tomorrow` — completing a `daily` task creates a new one with `due_date = today + 1 day`
- `test_weekly_task_creates_next_occurrence_in_seven_days` — completing a `weekly` task creates a new one with `due_date = today + 7 days`
- `test_as_needed_task_returns_no_next_occurrence` — completing an `as_needed` task returns `None`

**Conflict detection:**
- `test_check_conflicts_detects_overlapping_tasks` — two tasks manually set to `08:00` trigger a `CONFLICT` warning
- `test_check_conflicts_returns_clean_on_sequential_plan` — a normally built plan produces no conflict warnings

**Edge cases:**
- `test_build_plan_with_no_tasks_returns_empty` — a pet with no tasks returns `[]` without crashing
- `test_task_exceeding_budget_is_skipped` — a 90-min task with a 60-min budget lands in `_skipped`; smaller tasks still schedule

### Scheduler test run output

```
====================================================================== test session starts =======================================================================
platform win32 -- Python 3.14.5, pytest-9.0.3, pluggy-1.6.0
rootdir: C:\Users\anuja\ai110-module2show-pawpal-starter
plugins: anyio-4.13.0
collected 11 items

tests\test_pawpal.py ...........                                                                                                                            [100%]

======================================================================= 11 passed in 0.27s =======================================================================
```

## 🛡️ Agent Reliability & Evaluation

The `ReschedulingAgent` includes a built-in guardrail: every LLM-proposed fix is re-validated against the scheduler's own conflict-detection and budget rules before being accepted. Invalid fixes are rejected and retried (up to 3 attempts) rather than applied blindly.

### Automated agent tests (`tests/test_agent.py`)

Six tests mock the LLM call so results are deterministic, free, and don't depend on Groq being reachable during grading:

```
python -m pytest tests/test_agent.py -v

tests/test_agent.py::test_agent_accepts_valid_llm_fix PASSED                        [ 16%]
tests/test_agent.py::test_agent_skips_work_when_no_conflicts PASSED                 [ 33%]
tests/test_agent.py::test_agent_raises_after_malformed_json_every_attempt PASSED    [ 50%]
tests/test_agent.py::test_agent_strips_markdown_code_fences PASSED                  [ 66%]
tests/test_agent.py::test_agent_rejects_fix_that_still_conflicts PASSED             [ 83%]
tests/test_agent.py::test_agent_rejects_fix_exceeding_budget PASSED                  [100%]

6 passed in 0.32s
```

### Evaluation harness (`evaluate_agent.py`)

A test harness runs the agent against 5 predefined scenarios and prints a pass/fail summary:

```
python evaluate_agent.py

Scenario                                      Resolved   Expected   Attempts   Result
------------------------------------------------------------------------------------------
Valid fix resolves conflict                   True       True       2          PASS
Malformed JSON is rejected gracefully         False      False      6          PASS
Markdown-fenced JSON is still parsed          True       True       2          PASS
No-op fix (still conflicting) is rejected     False      False      6          PASS
Fix that exceeds budget is rejected           False      False      6          PASS
------------------------------------------------------------------------------------------

5/5 scenarios behaved as expected.
```

### Guardrail behavior summary

| Test Input | Evaluation Criteria | Result |
|---|---|---|
| Two tasks forced to the same time slot | LLM proposes a valid fix | Agent resolves in 1 attempt, no conflicts remain — Pass |
| LLM returns non-JSON prose | Agent doesn't crash | `AgentError` raised after 3 retries, original plan kept — Pass |
| LLM wraps JSON in code fences | Agent still parses correctly | Fix applied successfully — Pass |
| LLM proposes a fix that doesn't actually resolve the conflict | Guardrail rejects it | Retried and eventually falls back safely — Pass |
| LLM proposes a fix that exceeds the owner's time budget | Guardrail rejects it | Retried and eventually falls back safely — Pass |

### Confidence Level

⭐⭐⭐⭐⭐ 5 / 5

All 11 scheduler tests, all 6 agent tests, and all 5 evaluation scenarios pass. The guardrail correctly distinguishes valid fixes from invalid ones in every tested case, and the agent never applies an unvalidated change to the live schedule. See `model_card.md` for known limitations (e.g., the agent does not currently resolve cross-pet conflicts).