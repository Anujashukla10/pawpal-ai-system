"""
PawPal+ — Agent Evaluation Harness
Runs the ReschedulingAgent against predefined scenarios (mocked LLM
responses) and prints a pass/fail summary. This is a stretch feature
demonstrating structured, repeatable evaluation of AI behavior.

Run with: python evaluate_agent.py
"""

import json
from unittest.mock import patch
from pawpal_system import Owner, Pet, Task, Scheduler
from ai_agent import ReschedulingAgent, AgentError


def build_scheduler(plan):
    owner = Owner(name="Jordan", available_minutes=60, preferred_start="08:00")
    pet = Pet(name="Biscuit", species="dog")
    owner.add_pet(pet)
    sched = Scheduler(owner=owner, pet=pet)
    sched.plan = plan
    return sched


CONFLICT_PLAN = [
    Task("Walk", 30, "high", scheduled_time="08:00"),
    Task("Feed", 10, "high", scheduled_time="08:00"),
]

SCENARIOS = [
    {
        "name": "Valid fix resolves conflict",
        "plan": CONFLICT_PLAN,
        "mock_response": json.dumps([{"title": "Feed", "new_time": "08:30"}]),
        "expect_resolved": True,
    },
    {
        "name": "Malformed JSON is rejected gracefully",
        "plan": CONFLICT_PLAN,
        "mock_response": "not valid json at all",
        "expect_resolved": False,
    },
    {
        "name": "Markdown-fenced JSON is still parsed",
        "plan": CONFLICT_PLAN,
        "mock_response": '```json\n[{"title": "Feed", "new_time": "08:30"}]\n```',
        "expect_resolved": True,
    },
    {
        "name": "No-op fix (still conflicting) is rejected",
        "plan": CONFLICT_PLAN,
        "mock_response": json.dumps([{"title": "Feed", "new_time": "08:00"}]),
        "expect_resolved": False,
    },
    {
        "name": "Fix that exceeds budget is rejected",
        "plan": CONFLICT_PLAN,
        "mock_response": json.dumps([{"title": "Feed", "new_time": "09:00"}]),
        "expect_resolved": False,
    },
]


def run():
    results = []
    for scenario in SCENARIOS:
        sched = build_scheduler(scenario["plan"])
        agent = ReschedulingAgent(sched, client=object())

        with patch.object(agent, "_call_llm", return_value=scenario["mock_response"]):
            try:
                agent.resolve()
                resolved = True
            except AgentError:
                resolved = False

        passed = resolved == scenario["expect_resolved"]
        results.append({
            "name": scenario["name"],
            "resolved": resolved,
            "expected": scenario["expect_resolved"],
            "passed": passed,
            "attempts": len(agent.trace),
        })

    # ── Print summary table ─────────────────────────────────────────
    print(f"\n{'Scenario':<45} {'Resolved':<10} {'Expected':<10} {'Attempts':<10} {'Result'}")
    print("-" * 90)
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"{r['name']:<45} {str(r['resolved']):<10} {str(r['expected']):<10} "
              f"{r['attempts']:<10} {status}")

    total = len(results)
    passed_count = sum(r["passed"] for r in results)
    print("-" * 90)
    print(f"\n{passed_count}/{total} scenarios behaved as expected.\n")

    return results


if __name__ == "__main__":
    run()