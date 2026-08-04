"""
PawPal+ — AI Rescheduling Agent test suite
Run with: python -m pytest tests/test_agent.py -v

All tests mock _call_llm so they are deterministic, free, and don't
depend on Groq's API being reachable during grading.
"""

import json
from unittest.mock import patch
import pytest
from pawpal_system import Owner, Pet, Task, Scheduler
from ai_agent import ReschedulingAgent, AgentError


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def conflicted_scheduler():
    """A scheduler with two tasks manually forced onto the same time slot."""
    owner = Owner(name="Jordan", available_minutes=60, preferred_start="08:00")
    pet = Pet(name="Biscuit", species="dog")
    owner.add_pet(pet)
    sched = Scheduler(owner=owner, pet=pet)
    sched.plan = [
        Task("Walk", 30, "high", scheduled_time="08:00"),
        Task("Feed", 10, "high", scheduled_time="08:00"),
    ]
    return sched


@pytest.fixture
def clean_scheduler():
    """A scheduler with a valid, non-conflicting plan already built."""
    owner = Owner(name="Jordan", available_minutes=60, preferred_start="08:00")
    pet = Pet(name="Biscuit", species="dog")
    owner.add_pet(pet)
    sched = Scheduler(owner=owner, pet=pet)
    sched.add_task(Task("Walk", 30, "high", recurrence="daily"))
    sched.add_task(Task("Feed", 10, "high", recurrence="daily"))
    sched.build_plan()
    return sched


def make_agent(sched):
    """Build an agent without needing a real Groq client."""
    return ReschedulingAgent(sched, client=object())


# ─────────────────────────────────────────────
# HAPPY PATH — agent resolves a real conflict
# ─────────────────────────────────────────────

def test_agent_accepts_valid_llm_fix(conflicted_scheduler):
    """A correctly-formatted, non-conflicting LLM fix should be accepted on attempt 1."""
    agent = make_agent(conflicted_scheduler)
    mock_response = json.dumps([{"title": "Feed", "new_time": "08:30"}])

    with patch.object(agent, "_call_llm", return_value=mock_response):
        result = agent.resolve()

    assert not agent._validate(result)
    assert agent.trace[-1]["result"] == "accepted"


def test_agent_skips_work_when_no_conflicts(clean_scheduler):
    """If the plan is already valid, the agent should not call the LLM at all."""
    agent = make_agent(clean_scheduler)

    with patch.object(agent, "_call_llm") as mock_call:
        result = agent.resolve()
        mock_call.assert_not_called()

    assert result == clean_scheduler.plan
    assert agent.trace[0]["note"].startswith("No issues found")


# ─────────────────────────────────────────────
# GUARDRAIL — malformed or invalid LLM output
# ─────────────────────────────────────────────

def test_agent_raises_after_malformed_json_every_attempt(conflicted_scheduler):
    """Non-JSON responses on every attempt should raise AgentError, not crash."""
    agent = make_agent(conflicted_scheduler)

    with patch.object(agent, "_call_llm", return_value="Sure, here's a plan: not json"):
        with pytest.raises(AgentError):
            agent.resolve()

    # Each failed attempt logs 2 entries (prompt/response, then the parse error)
    attempts_made = len([t for t in agent.trace if "prompt" in t])
    assert attempts_made == 3   # confirms it actually retried MAX_ATTEMPTS times


def test_agent_strips_markdown_code_fences(conflicted_scheduler):
    """A response wrapped in ```json fences should still parse correctly."""
    agent = make_agent(conflicted_scheduler)
    fenced = '```json\n[{"title": "Feed", "new_time": "08:30"}]\n```'

    with patch.object(agent, "_call_llm", return_value=fenced):
        result = agent.resolve()

    assert not agent._validate(result)


def test_agent_rejects_fix_that_still_conflicts(conflicted_scheduler):
    """If the LLM's fix doesn't actually resolve the conflict, validation should reject it and retry."""
    agent = make_agent(conflicted_scheduler)
    # Bad fix: moves Feed to overlap with Walk's new duration-adjusted window
    bad_fix = json.dumps([{"title": "Feed", "new_time": "08:00"}])  # no change at all

    with patch.object(agent, "_call_llm", return_value=bad_fix):
        with pytest.raises(AgentError):
            agent.resolve()

    rejected_attempts = [t for t in agent.trace if t.get("result") == "rejected"]
    assert len(rejected_attempts) == 3


def test_agent_rejects_fix_exceeding_budget(conflicted_scheduler):
    """A fix that pushes a task past the owner's available_minutes should be rejected."""
    agent = make_agent(conflicted_scheduler)
    # Owner only has 60 min budget; this pushes Feed's end time past it
    overbudget_fix = json.dumps([{"title": "Feed", "new_time": "09:00"}])

    with patch.object(agent, "_call_llm", return_value=overbudget_fix):
        with pytest.raises(AgentError):
            agent.resolve()