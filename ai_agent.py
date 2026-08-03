"""
PawPal+ — AI Rescheduling Agent
Adds a real AI feature on top of the deterministic scheduler:
  PLAN  — ask an LLM (via Groq) to propose fixes for conflicts/skipped tasks
  ACT   — apply those fixes to a candidate plan
  CHECK — re-run the scheduler's own guardrails; retry or fall back
"""

import os
import json
import re
import copy
from dotenv import load_dotenv
from groq import Groq
from pawpal_system import Scheduler, Task

load_dotenv()  # reads .env and sets GROQ_API_KEY into the environment

MAX_ATTEMPTS = 3
MODEL = "llama-3.3-70b-versatile"


class AgentError(Exception):
    """Raised when the agent cannot produce a valid fix after MAX_ATTEMPTS."""


class ReschedulingAgent:
    def __init__(self, scheduler: Scheduler, client: Groq | None = None):
        self.scheduler = scheduler
        self.client = client or Groq(api_key=os.environ.get("GROQ_API_KEY"))
        self.trace: list[dict] = []

    def _build_prompt(self, issues, attempt, feedback=""):
        plan_desc = "\n".join(
            f"- {t.title} @ {t.scheduled_time} ({t.duration_minutes}min, {t.priority})"
            for t in self.scheduler.plan
        )
        skipped_desc = "\n".join(
            f"- {t.title} ({t.duration_minutes}min, {t.priority})"
            for t in self.scheduler._skipped
        ) or "None"
        return f"""You are a scheduling assistant for a pet-care app.

Owner budget: {self.scheduler.owner.available_minutes} minutes, starting {self.scheduler.start_time}.

Current plan for {self.scheduler.pet.name}:
{plan_desc}

Skipped tasks (didn't fit):
{skipped_desc}

Detected issues:
{chr(10).join(issues)}

{"Previous attempt failed validation: " + feedback if feedback else ""}

Respond with ONLY a JSON array, no prose, no markdown fences. Each item:
{{"title": "<task title>", "new_time": "HH:MM"}}
Keep every task within the owner's budget window. This is attempt {attempt}/{MAX_ATTEMPTS}."""

    def _call_llm(self, prompt: str) -> str:
        resp = self.client.chat.completions.create(
            model=MODEL,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content

    @staticmethod
    def _extract_json(raw: str) -> str:
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", raw, re.DOTALL)
        return match.group(1) if match else raw.strip()

    def _apply_fixes(self, fixes):
        working_plan = copy.deepcopy(self.scheduler.plan)
        by_title = {t.title.lower(): t for t in working_plan}
        for fix in fixes:
            task = by_title.get(fix.get("title", "").lower())
            if task and fix.get("new_time"):
                task.scheduled_time = fix["new_time"]
        return working_plan

    def _validate(self, plan):
        problems = []
        for i, a in enumerate(plan):
            for b in plan[i + 1:]:
                a_start = Scheduler._to_minutes(a.scheduled_time)
                a_end = a_start + a.duration_minutes
                b_start = Scheduler._to_minutes(b.scheduled_time)
                b_end = b_start + b.duration_minutes
                if a_start < b_end and b_start < a_end:
                    problems.append(f"CONFLICT: {a.title} overlaps {b.title}")
        start = Scheduler._to_minutes(self.scheduler.start_time)
        for t in plan:
            end = Scheduler._to_minutes(t.scheduled_time) + t.duration_minutes
            if end - start > self.scheduler.owner.available_minutes:
                problems.append(f"BUDGET: {t.title} ends outside available_minutes")
        return problems

    def resolve(self):
        issues = [w for w in self.scheduler.check_conflicts() if "CONFLICT" in w]
        if self.scheduler._skipped:
            issues.append(f"{len(self.scheduler._skipped)} task(s) skipped due to budget.")
        if not issues:
            self.trace.append({"attempt": 0, "note": "No issues found — agent not needed."})
            return self.scheduler.plan

        feedback = ""
        for attempt in range(1, MAX_ATTEMPTS + 1):
            prompt = self._build_prompt(issues, attempt, feedback)
            raw = self._call_llm(prompt)
            cleaned = self._extract_json(raw)
            self.trace.append({"attempt": attempt, "prompt": prompt, "response": raw})

            try:
                fixes = json.loads(cleaned)
            except json.JSONDecodeError:
                feedback = "Response was not valid JSON."
                self.trace.append({"attempt": attempt, "error": feedback})
                continue

            candidate = self._apply_fixes(fixes)
            problems = self._validate(candidate)
            if not problems:
                self.scheduler.plan = candidate
                self.trace.append({"attempt": attempt, "result": "accepted"})
                return candidate

            feedback = "; ".join(problems)
            self.trace.append({"attempt": attempt, "result": "rejected", "problems": problems})

        raise AgentError(f"Agent could not resolve issues after {MAX_ATTEMPTS} attempts: {feedback}")


if __name__ == "__main__":
    # Quick standalone smoke test — run: python ai_agent.py
    from pawpal_system import Owner, Pet, Task, Scheduler

    owner = Owner(name="Jordan", available_minutes=60, preferred_start="08:00")
    pet = Pet(name="Biscuit", species="dog")
    owner.add_pet(pet)
    sched = Scheduler(owner=owner, pet=pet)
    sched.plan = [
        Task("Walk", 30, "high", scheduled_time="08:00"),
        Task("Feed", 10, "high", scheduled_time="08:00"),
    ]

    agent = ReschedulingAgent(sched)
    try:
        agent.resolve()
        print("✅ Agent resolved the conflict. Final plan:")
        for t in sched.plan:
            print(f"  {t.scheduled_time} — {t.title}")
    except AgentError as e:
        print(f"⚠️ {e}")