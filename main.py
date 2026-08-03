"""
PawPal+ — main.py (v7)
Professional CLI formatting:
  - tabulate: structured tables for schedule, tasks, and progress
  - Color-coded ANSI priority badges (high=red, medium=yellow, low=green)
  - Emoji task-type icons (🚶 walk, 🍽 feed, 💊 meds, 🛁 groom, 🎾 enrichment)
  - Conflict warning banners with divider lines
  - AI Rescheduling Agent (Groq) for resolving same-pet conflicts
"""

import copy
import datetime
from tabulate import tabulate
from pawpal_system import Owner, Pet, Task, Scheduler
from ai_agent import ReschedulingAgent, AgentError


# ─────────────────────────────────────────────
# ANSI color helpers
# ─────────────────────────────────────────────

RESET  = "\033[0m"
RED    = "\033[91m"
YELLOW = "\033[93m"
GREEN  = "\033[92m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"

def priority_badge(priority: str) -> str:
    """Return a colour-coded priority label for terminal output."""
    colors = {"high": RED, "medium": YELLOW, "low": GREEN}
    labels = {"high": "● HIGH", "medium": "● MED ", "low": "● LOW "}
    color = colors.get(priority, RESET)
    label = labels.get(priority, priority.upper())
    return f"{color}{label}{RESET}"


def task_icon(title: str) -> str:
    """Return an emoji icon based on common task-title keywords."""
    t = title.lower()
    if any(w in t for w in ["walk", "run", "exercise", "hike"]):
        return "🚶"
    if any(w in t for w in ["feed", "food", "meal", "treat"]):
        return "🍽"
    if any(w in t for w in ["med", "pill", "tablet", "injection"]):
        return "💊"
    if any(w in t for w in ["bath", "groom", "brush", "teeth"]):
        return "🛁"
    if any(w in t for w in ["play", "enrich", "toy", "training"]):
        return "🎾"
    if any(w in t for w in ["vet", "check", "appointment"]):
        return "🏥"
    if any(w in t for w in ["litter", "clean"]):
        return "🧹"
    return "📋"


def recurrence_badge(recurrence: str) -> str:
    """Return a short label for recurrence."""
    return {"daily": "📅 daily", "weekly": "📆 weekly", "as_needed": "🔔 as needed"}.get(
        recurrence, recurrence
    )


def print_section(title: str, char: str = "─", width: int = 60) -> None:
    """Print a styled section header."""
    print(f"\n{BOLD}{CYAN}{title}{RESET}")
    print(DIM + char * width + RESET)


def print_warnings(warnings: list[str], label: str) -> None:
    """Print a labelled conflict block."""
    print(f"\n{DIM}{'─' * 54}{RESET}")
    print(f"  {BOLD}{label}{RESET}")
    print(DIM + "─" * 54 + RESET)
    real = [w for w in warnings if "CONFLICT" in w]
    if real:
        for w in real:
            print(f"  {RED}{w}{RESET}")
    else:
        print(f"  {GREEN}✅  No conflicts detected.{RESET}")


def render_schedule_table(sched: Scheduler, pet_name: str) -> None:
    """Print the plan as a formatted tabulate table with colour and icons."""
    if not sched.plan:
        print(f"  {DIM}No tasks scheduled.{RESET}")
        return

    rows = []
    for t in sched.sort_by_time():
        end_min = Scheduler._to_minutes(t.scheduled_time) + t.duration_minutes
        end_str = Scheduler._minutes_to_time(end_min)
        rows.append([
            f"{t.scheduled_time}–{end_str}",
            f"{task_icon(t.title)} {t.title}",
            f"{t.duration_minutes} min",
            priority_badge(t.priority),
            recurrence_badge(t.recurrence),
        ])

    print(tabulate(
        rows,
        headers=["Time", "Task", "Duration", "Priority", "Recurrence"],
        tablefmt="rounded_outline",
        colalign=("left", "left", "right", "left", "left"),
    ))

    used  = sum(t.duration_minutes for t in sched.plan)
    total = sched.owner.available_minutes
    bar_width = 30
    filled = int(bar_width * used / total)
    bar = f"[{'█' * filled}{'░' * (bar_width - filled)}]"
    color = GREEN if used / total < 0.85 else YELLOW if used / total < 1.0 else RED
    print(f"\n  {BOLD}Time used:{RESET} {color}{bar}{RESET} {used}/{total} min")

    if sched._skipped:
        print(f"\n  {YELLOW}⏭  Skipped — not enough time:{RESET}")
        skipped_rows = [[
            f"{task_icon(t.title)} {t.title}",
            f"{t.duration_minutes} min",
            priority_badge(t.priority),
        ] for t in sched._skipped]
        print(tabulate(skipped_rows, headers=["Task", "Duration", "Priority"],
                       tablefmt="simple", colalign=("left", "right", "left")))


def render_progress(sched: Scheduler) -> None:
    """Print a done/remaining progress summary."""
    done      = sched.filter_by_status(completed=True)
    remaining = sched.filter_by_status(completed=False)
    total     = len(sched.plan)
    pct       = int(100 * len(done) / total) if total else 0
    color     = GREEN if pct == 100 else YELLOW if pct > 0 else DIM
    print(f"\n  {BOLD}Progress:{RESET} {color}{len(done)}/{total} tasks complete ({pct}%){RESET}")
    if remaining:
        print(f"  {DIM}Still to do:{RESET}")
        for t in remaining:
            print(f"    ○  {task_icon(t.title)} {t.title}  {DIM}@ {t.scheduled_time}{RESET}")


def run_agent_section(sched: Scheduler, pet_name: str) -> ReschedulingAgent:
    """Run the AI rescheduling agent on a scheduler and print what happened."""
    print_section(f"🤖 AI Rescheduling Agent — {pet_name}")
    agent = ReschedulingAgent(sched)
    try:
        agent.resolve()
        if agent.trace and agent.trace[0].get("note"):
            print(f"  {GREEN}✅ {agent.trace[0]['note']}{RESET}")
        else:
            print(f"  {GREEN}✅ Agent resolved conflicts. Updated plan:{RESET}")
            for t in sorted(sched.plan, key=lambda t: t.scheduled_time):
                print(f"    {t.scheduled_time} — {t.title}")
    except AgentError as e:
        print(f"  {YELLOW}⚠️  {e}{RESET}")
        print(f"  {DIM}Falling back to original plan.{RESET}")
    return agent


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    today = datetime.date.today()
    W = 60

    print(f"\n{BOLD}{'═' * W}{RESET}")
    print(f"{BOLD}{'🐾  PawPal+ — Today\'s Schedule':^{W}}{RESET}")
    print(f"{BOLD}{'═' * W}{RESET}")
    print(f"  📅  {today.strftime('%A, %B %d %Y')}")

    # ── Setup ─────────────────────────────────────────────────────────
    owner = Owner(name="Jordan", available_minutes=120, preferred_start="08:00")
    dog   = Pet(name="Biscuit", species="dog", breed="Golden Retriever", age=3)
    cat   = Pet(name="Mochi",   species="cat", breed="Siamese",          age=5)
    owner.add_pet(dog)
    owner.add_pet(cat)

    print(f"\n  {BOLD}Owner:{RESET}  {owner.name}")
    print(f"  {BOLD}Budget:{RESET} {owner.available_minutes} min  │  "
          f"{BOLD}Start:{RESET} {owner.preferred_start}")
    print(f"{BOLD}{'═' * W}{RESET}")

    # ── Biscuit ───────────────────────────────────────────────────────
    dog_sched = Scheduler(owner=owner, pet=dog)
    dog_sched.add_task(Task("Morning walk",   30, "high",   recurrence="daily"))
    dog_sched.add_task(Task("Feeding",        10, "high",   recurrence="daily"))
    dog_sched.add_task(Task("Medication",      5, "high",   recurrence="daily"))
    dog_sched.add_task(Task("Teeth brushing", 10, "medium", recurrence="daily"))
    dog_sched.add_task(Task("Enrichment toy", 15, "medium", recurrence="daily"))
    dog_sched.add_task(Task("Bath",           40, "low",    recurrence="weekly"))
    dog_sched.build_plan()

    # Force a conflict on purpose so the AI agent demo has something to fix
    dog_sched.plan[0].scheduled_time = dog_sched.plan[1].scheduled_time

    print_section(f"🐕 Biscuit ({dog.breed})")
    render_schedule_table(dog_sched, dog.name)
    run_agent_section(dog_sched, dog.name)
    render_progress(dog_sched)

    # ── Mochi ─────────────────────────────────────────────────────────
    cat_sched = Scheduler(owner=owner, pet=cat)
    cat_sched.add_task(Task("Feeding",    10, "high",   recurrence="daily"))
    cat_sched.add_task(Task("Litter box",  5, "high",   recurrence="daily"))
    cat_sched.add_task(Task("Playtime",   15, "medium", recurrence="daily"))
    cat_sched.add_task(Task("Brush coat", 10, "medium", recurrence="weekly"))
    cat_sched.add_task(Task("Vet check-up",30,"low",    recurrence="as_needed"))
    cat_sched.build_plan()

    print_section(f"🐈 Mochi ({cat.breed})")
    render_schedule_table(cat_sched, cat.name)
    render_progress(cat_sched)

    # ── Conflict detection ────────────────────────────────────────────
    print_section("⚠️  Conflict Check")

    same_dog = [w for w in dog_sched.check_conflicts() if "CONFLICT" in w]
    same_cat = [w for w in cat_sched.check_conflicts() if "CONFLICT" in w]
    cross    = [w for w in Scheduler.check_cross_pet_conflicts(
                    [dog_sched, cat_sched]) if "CONFLICT" in w]

    if not same_dog and not same_cat and not cross:
        print(f"  {GREEN}✅  No conflicts detected across all pets.{RESET}")
    for w in same_dog + same_cat + cross:
        print(f"  {RED}{w}{RESET}")

    # ── Plan explanations ─────────────────────────────────────────────
    print_section("💡 Why was this plan chosen?")
    print(dog_sched.explain_plan())
    print()
    print(cat_sched.explain_plan())

    # ── Summary ───────────────────────────────────────────────────────
    total_tasks = len(dog_sched.plan) + len(cat_sched.plan)
    total_mins  = (sum(t.duration_minutes for t in dog_sched.plan)
                 + sum(t.duration_minutes for t in cat_sched.plan))
    print(f"\n{BOLD}{'═' * W}{RESET}")
    print(f"  {BOLD}All schedules generated.{RESET}  "
          f"{total_tasks} tasks · {total_mins} min planned  🐶🐱")
    print(f"{BOLD}{'═' * W}{RESET}\n")


if __name__ == "__main__":
    main()