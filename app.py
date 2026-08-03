"""
PawPal+ — app.py (final)
All Phase 3 features wired to the UI:
  - sort_by_time()              → schedule table in chronological order
  - filter_by_status()          → to-do / done progress view
  - check_conflicts()           → st.warning banners per pet
  - check_cross_pet_conflicts() → cross-pet warning banner
  - explain_plan()              → collapsible reasoning panel
  - progress_report()           → live completion tracker
"""

import streamlit as st
from pawpal_system import Owner, Pet, Task, Scheduler
from ai_agent import ReschedulingAgent, AgentError

# ─────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")
st.caption("A daily care planner for your pets.")

# ─────────────────────────────────────────────
# Session state bootstrap
# ─────────────────────────────────────────────

if "owner"      not in st.session_state: st.session_state.owner      = None
if "schedulers" not in st.session_state: st.session_state.schedulers = {}
if "plan_built" not in st.session_state: st.session_state.plan_built = False

# ─────────────────────────────────────────────
# Section 1 — Owner info
# ─────────────────────────────────────────────

st.header("1 · Owner Info")

with st.form("owner_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        owner_name = st.text_input("Your name", value="Jordan")
    with col2:
        available_minutes = st.number_input(
            "Time available today (min)", min_value=10, max_value=480, value=120
        )
    with col3:
        preferred_start = st.text_input("Start time (HH:MM)", value="08:00")
    submitted_owner = st.form_submit_button("Save owner")

if submitted_owner:
    st.session_state.owner      = Owner(
        name=owner_name,
        available_minutes=int(available_minutes),
        preferred_start=preferred_start,
    )
    st.session_state.schedulers = {}
    st.session_state.plan_built = False
    st.success(f"✅ Owner **{owner_name}** saved — {available_minutes} min starting {preferred_start}.")

if st.session_state.owner:
    o = st.session_state.owner
    st.info(f"👤 **{o.name}** · {o.available_minutes} min/day · starts {o.preferred_start}")
else:
    st.warning("Fill in owner info above to get started.")
    st.stop()

# ─────────────────────────────────────────────
# Section 2 — Add a pet
# ─────────────────────────────────────────────

st.divider()
st.header("2 · Add a Pet")

with st.form("pet_form"):
    col1, col2, col3, col4 = st.columns(4)
    with col1: pet_name = st.text_input("Pet name", value="Biscuit")
    with col2: species  = st.selectbox("Species", ["dog", "cat", "other"])
    with col3: breed    = st.text_input("Breed (optional)", value="")
    with col4: age      = st.number_input("Age", min_value=0, max_value=30, value=0)
    submitted_pet = st.form_submit_button("Add pet")

if submitted_pet:
    owner = st.session_state.owner
    existing = [p.name.lower() for p in owner.get_pets()]
    if pet_name.lower() in existing:
        st.warning(f"A pet named **{pet_name}** is already registered.")
    else:
        new_pet = Pet(name=pet_name, species=species, breed=breed, age=int(age))
        owner.add_pet(new_pet)
        st.session_state.schedulers[pet_name] = Scheduler(owner=owner, pet=new_pet)
        st.session_state.plan_built = False
        st.success(f"🐾 **{pet_name}** the {species} added!")

pets = st.session_state.owner.get_pets()
if pets:
    st.write("**Registered pets:**", ", ".join(p.name for p in pets))
else:
    st.info("No pets yet — add one above.")

# ─────────────────────────────────────────────
# Section 3 — Add tasks
# ─────────────────────────────────────────────

st.divider()
st.header("3 · Add Tasks")

if not pets:
    st.info("Add a pet first before adding tasks.")
else:
    with st.form("task_form"):
        col1, col2 = st.columns(2)
        with col1: selected_pet = st.selectbox("Pet", [p.name for p in pets])
        with col2: task_title   = st.text_input("Task title", value="Morning walk")

        col3, col4, col5 = st.columns(3)
        with col3: duration   = st.number_input("Duration (min)", min_value=1, max_value=240, value=30)
        with col4: priority   = st.selectbox("Priority", ["high", "medium", "low"])
        with col5: recurrence = st.selectbox("Recurrence", ["daily", "weekly", "as_needed"])
        submitted_task = st.form_submit_button("Add task")

    if submitted_task:
        sched = st.session_state.schedulers.get(selected_pet)
        if sched is None:
            st.error(f"No scheduler found for **{selected_pet}**. Try re-adding the pet.")
        else:
            try:
                sched.add_task(Task(
                    title=task_title,
                    duration_minutes=int(duration),
                    priority=priority,
                    recurrence=recurrence,
                ))
                st.session_state.plan_built = False   # plan is stale after adding
                st.success(f"✅ Added **{task_title}** to {selected_pet}.")
            except ValueError as e:
                st.warning(str(e))

    # Task library per pet
    for pet in pets:
        tasks = pet.get_tasks()
        if tasks:
            with st.expander(f"🐾 {pet.name}'s tasks ({len(tasks)})", expanded=False):
                st.table([{
                    "Task":          t.title,
                    "Duration (min)": t.duration_minutes,
                    "Priority":      t.priority,
                    "Recurrence":    t.recurrence,
                } for t in tasks])

# ─────────────────────────────────────────────
# Section 4 — Generate & display schedule
# ─────────────────────────────────────────────

st.divider()
st.header("4 · Today's Schedule")

if not pets:
    st.info("Add a pet and some tasks first.")
else:
    if st.button("🗓️ Build Today's Schedule", type="primary"):
        has_tasks = any(len(p.get_tasks()) > 0 for p in pets)
        if not has_tasks:
            st.warning("No tasks found. Add tasks in Step 3 first.")
        else:
            for pet in pets:
                sched = st.session_state.schedulers.get(pet.name)
                if sched is None or len(pet.get_tasks()) == 0:
                    continue
                sched.build_plan()
            st.session_state.plan_built = True

    # ── Display results (persists across reruns) ──────────────────────
    if st.session_state.plan_built:

        all_schedulers = [
            s for s in st.session_state.schedulers.values()
            if s.plan
        ]

        # ── Cross-pet conflict banner (shown once at the top) ─────────
        if len(all_schedulers) > 1:
            cross_warnings = Scheduler.check_cross_pet_conflicts(all_schedulers)
            real_cross = [w for w in cross_warnings if "CONFLICT" in w]
            if real_cross:
                st.warning(
                    "⚠️ **Scheduling conflict detected across pets.** "
                    "Jordan cannot do two things at once — consider adjusting start times."
                )
                with st.expander("Show cross-pet conflicts"):
                    for w in real_cross:
                        st.markdown(f"- {w}")

        # ── Per-pet schedule ──────────────────────────────────────────
        for pet in pets:
            sched = st.session_state.schedulers.get(pet.name)
            if sched is None or not sched.plan:
                continue

            st.subheader(f"🐾 {pet.name} ({pet.species})")

            # ── Same-pet conflict warning + AI agent ──────────────────
            same_warnings = [w for w in sched.check_conflicts() if "CONFLICT" in w]
            if same_warnings:
                st.warning(
                    f"⚠️ **{len(same_warnings)} conflict(s) detected for {pet.name}.** "
                    "Two or more tasks overlap. Review and adjust times."
                )
                with st.expander(f"Show {pet.name}'s conflicts"):
                    for w in same_warnings:
                        st.markdown(f"- {w}")

                if st.button(f"🤖 Ask AI to resolve {pet.name}'s conflicts", key=f"agent_{pet.name}"):
                    agent = ReschedulingAgent(sched)
                    try:
                        with st.spinner("Agent is reasoning about the schedule..."):
                            agent.resolve()
                        st.success(f"✅ AI agent resolved the conflict(s) for {pet.name}.")
                        st.session_state[f"agent_trace_{pet.name}"] = agent.trace
                    except AgentError as e:
                        st.error(f"⚠️ Agent couldn't resolve this: {e}")

                trace = st.session_state.get(f"agent_trace_{pet.name}")
                if trace:
                    with st.expander("🧠 Agent reasoning trace"):
                        for entry in trace:
                            st.json(entry)

            # ── Schedule table — sorted chronologically ───────────────
            sorted_plan = sched.sort_by_time()
            PRIORITY_EMOJI = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            st.table([{
                "Time":           t.scheduled_time,
                "Task":           t.title,
                "Duration (min)": t.duration_minutes,
                "Priority":       f"{PRIORITY_EMOJI.get(t.priority, '')} {t.priority}",
                "Recurrence":     t.recurrence,
            } for t in sorted_plan])

            # ── Time budget bar ───────────────────────────────────────
            used  = sum(t.duration_minutes for t in sched.plan)
            total = st.session_state.owner.available_minutes
            pct   = min(used / total, 1.0)
            st.progress(pct, text=f"⏱ Time used: {used} / {total} min")

            # ── Skipped tasks ─────────────────────────────────────────
            if sched._skipped:
                with st.expander(f"⏭ Skipped tasks ({len(sched._skipped)}) — not enough time"):
                    st.table([{
                        "Task":           t.title,
                        "Duration (min)": t.duration_minutes,
                        "Priority":       t.priority,
                    } for t in sched._skipped])

            # ── Filter view: incomplete tasks ─────────────────────────
            todo = sched.filter_by_status(completed=False)
            done = sched.filter_by_status(completed=True)

            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Tasks to do", len(todo))
            with col_b:
                st.metric("Completed", len(done))

            # ── Why was this plan chosen? ─────────────────────────────
            with st.expander("💡 Why was this plan chosen?"):
                st.text(sched.explain_plan())

            st.divider()