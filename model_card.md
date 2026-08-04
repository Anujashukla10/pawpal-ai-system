# Model Card & Reflection — PawPal+ Rescheduling Agent

## What are the limitations or biases in your system?

**Scope limitation — no cross-pet resolution.** The `ReschedulingAgent` only resolves conflicts within a single pet's schedule. It cannot resolve cross-pet conflicts (e.g., the owner is scheduled to walk one pet while also scheduled to bathe another at the same time) — those are still detected by `check_cross_pet_conflicts()` and shown to the user, but no fix is attempted. A real deployment would need the agent to reason across all of an owner's schedulers at once, which introduces a much larger search space and was out of scope for this project's time budget.

**Priority bias inherited from the base scheduler.** `build_plan()` always schedules high-priority tasks first, regardless of duration or how many lower-priority tasks get bumped as a result. The agent inherits this bias — it fixes conflicts by moving times, not by reconsidering priority order, so a task the owner marked "low priority" can still get pushed later or skipped even if it was time-sensitive in a way priority alone doesn't capture (e.g., a vet appointment marked "low" because it's not urgent, but which actually has a fixed real-world time).

**No real-world calendar awareness.** The agent reasons purely from the numbers it's given (durations, budget, start time) — it has no concept of the owner's actual day (a real commute, a work meeting, an actual vet office's hours). Its "fixes" are only guaranteed to be internally consistent with the data it's given, not realistic for the pet owner's actual day.

## Could your AI be misused, and how would you prevent that?

The most plausible misuse is a garbage-in / garbage-out problem rather than malicious use: a user (or a bug elsewhere in the app) could feed the agent a large number of fake high-priority, short-duration tasks to manipulate the schedule in ways that crowd out real tasks. The guardrail (`_validate()`) prevents the agent from ever accepting a fix that leaves a conflict unresolved or exceeds the time budget, but it does not evaluate whether the *inputs* themselves are legitimate — that responsibility sits with `Task.__post_init__()`'s validation (rejecting bad priority/recurrence/duration values) and, ultimately, the user adding tasks in good faith.

A second, smaller risk: because the LLM sees the full task list and titles in its prompt, a user could put arbitrary text into a task title, which then gets sent to a third-party API (Groq). Nothing sensitive is collected in this app (no real names beyond a display name, no addresses, no health records beyond a task title like "Medication"), but a production version should document what's sent to a third-party model and avoid letting arbitrary free text reach the LLM prompt unsanitized.

## What surprised you while testing your AI's reliability?

Two concrete things came up during actual testing of this project:

1. **The LLM did not reliably follow "no markdown fences" instructions.** Even with an explicit "Respond with ONLY a JSON array, no prose, no markdown fences" instruction in the prompt, Llama 3.3 (via Groq) sometimes wrapped its JSON response in ` ```json ... ``` ` blocks anyway. This required adding `_extract_json()` as a guardrail step to strip fences before parsing — without it, a perfectly valid fix would have been rejected as malformed JSON purely because of formatting, not content.
2. **My own test assertion was wrong, not the code.** While writing `tests/test_agent.py`, a test asserted `len(agent.trace) == 3` after 3 failed attempts, expecting one trace entry per attempt. It actually failed with `6 == 3`, because the agent logs two entries per failed attempt (the prompt/response pair, and a separate parse-error entry). The agent's behavior was correct; my test's assumption about its own logging format was not. This was a useful reminder that when a test fails, the first question should be "is the test's assumption right?" before assuming the implementation is broken — and it directly informed the trade-off decision documented in the README about what to log.

## Describe your collaboration with AI during this project. Identify one instance when the AI gave a helpful suggestion and one instance where its suggestion was flawed or incorrect.

**Helpful suggestion:** When I didn't have an Anthropic API key, the AI assistant I used to plan this project suggested switching to Groq's free tier instead of blocking progress on getting paid API access, and adapted the agent code's client setup and `_call_llm()` method accordingly with minimal changes to the rest of the plan → act → check logic. This let the "substantial AI feature" requirement get met without any cost, and Groq's speed made iterating on the agent (running it 5–10 times while debugging) fast and free.

**Flawed suggestion:** The AI assistant initially wrote a test (`test_agent_raises_after_malformed_json_every_attempt`) asserting the trace would contain exactly 3 entries after 3 failed attempts. When I actually ran the test, it failed — the real trace had 6 entries, because the agent logs both a "prompt/response" entry and a separate "error" entry per failed attempt. The assistant's assumption about its own logging format was wrong. I caught this because I ran the test myself rather than assuming the generated code was correct, and the fix (checking `len([t for t in agent.trace if "prompt" in t])` instead of the raw trace length) was straightforward once the actual behavior was visible in the pytest failure output.

**Overall process:** I used AI assistance throughout — for the initial architecture (the plan/act/check loop design), for writing the mocked pytest tests and evaluation harness, and for drafting documentation. At every stage, I ran the actual code myself (`python ai_agent.py`, `python main.py`, `streamlit run app.py`, `pytest`) before accepting that something worked, and caught at least the two issues described above by doing so. The main lesson from this project is that an AI-generated plan → act → check pattern is only as trustworthy as the validation step actually is — writing `_validate()` to reuse the scheduler's own proven conflict/budget logic, rather than trusting the LLM's claim that its fix was correct, was the single most important design decision for making this system genuinely reliable rather than just appearing reliable.

## Future Improvements

If I extended this project further, I would prioritize:
1. **Cross-pet conflict resolution** — extending the agent to reason across all of an owner's schedulers at once, not just one pet at a time.
2. **Priority-aware rescheduling** — letting the agent suggest re-ranking a task's priority (not just its time) when a fixed real-world constraint (like a vet appointment) conflicts with the greedy scheduler's priority-first assumption.
3. **Persistent trace logging** — writing every agent run's trace to a timestamped file automatically, rather than only capturing traces manually during testing, so reliability could be monitored over many real days of use.