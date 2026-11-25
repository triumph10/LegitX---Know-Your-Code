import html
from pathlib import Path

import streamlit as st

from scanner import scan_project
from question_generator import generate_question
from evaluator import evaluate_answer
from adaptive_learning import choose_next_action, create_retry_prompt

from database import (
    initialize_database,
    save_evaluation,
    get_overall_stats,
    get_function_progress,
    get_recent_evaluations
)


st.set_page_config(
    page_title="LegitX",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ---------------------------------------------------------------- styling

CUSTOM_CSS = """
<style>
    .block-container { padding-top: 2rem; max-width: 1200px; }

    .hero {
        padding: 1.6rem 1.8rem;
        border-radius: 16px;
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 55%, #db2777 100%);
        color: #fff;
        margin-bottom: 1.2rem;
        box-shadow: 0 8px 24px rgba(79, 70, 229, 0.25);
    }
    .hero h1 { margin: 0; font-size: 2.1rem; color: #fff; padding: 0; }
    .hero p  { margin: .25rem 0 0 0; opacity: .92; font-size: 1.02rem; }

    .stepper { display: flex; gap: .5rem; margin: .4rem 0 1.2rem 0; flex-wrap: wrap; }
    .step {
        flex: 1; min-width: 130px; padding: .55rem .8rem; border-radius: 10px;
        font-size: .85rem; font-weight: 600; text-align: center;
        border: 1px solid rgba(128,128,128,.25);
        background: rgba(128,128,128,.07); opacity: .65;
    }
    .step.done   { background: rgba(34,197,94,.14); border-color: rgba(34,197,94,.45); opacity: 1; }
    .step.active { background: rgba(99,102,241,.18); border-color: #6366f1; opacity: 1; }

    .badge {
        display: inline-block; padding: .15rem .65rem; border-radius: 999px;
        font-size: .78rem; font-weight: 600; margin-right: .4rem;
        background: rgba(99,102,241,.16); border: 1px solid rgba(99,102,241,.4);
    }
    .badge.easy   { background: rgba(34,197,94,.16);  border-color: rgba(34,197,94,.5); }
    .badge.medium { background: rgba(245,158,11,.16); border-color: rgba(245,158,11,.55); }
    .badge.hard   { background: rgba(239,68,68,.16);  border-color: rgba(239,68,68,.5); }

    .question-card {
        padding: 1.1rem 1.3rem; border-radius: 12px;
        border-left: 5px solid #6366f1;
        background: rgba(99,102,241,.08);
        font-size: 1.05rem; line-height: 1.55; margin: .5rem 0 1rem 0;
    }

    .score-card {
        padding: 1.2rem 1.4rem; border-radius: 14px; text-align: center;
        border: 1px solid rgba(128,128,128,.25);
    }
    .score-card .big   { font-size: 3rem; font-weight: 800; line-height: 1.1; }
    .score-card .label { font-size: .85rem; opacity: .75; text-transform: uppercase; letter-spacing: .06em; }
    .score-card.good { background: rgba(34,197,94,.12);  border-color: rgba(34,197,94,.5); }
    .score-card.good .big { color: #16a34a; }
    .score-card.mid  { background: rgba(245,158,11,.12); border-color: rgba(245,158,11,.55); }
    .score-card.mid .big  { color: #d97706; }
    .score-card.low  { background: rgba(239,68,68,.12);  border-color: rgba(239,68,68,.5); }
    .score-card.low .big  { color: #dc2626; }

    div[data-testid="stMetric"] {
        background: rgba(128,128,128,.07);
        border: 1px solid rgba(128,128,128,.2);
        padding: .8rem 1rem; border-radius: 12px;
    }

    .pill-list { margin: 0; padding: 0; list-style: none; }
    .pill-list li {
        padding: .45rem .75rem; margin-bottom: .4rem; border-radius: 8px;
        font-size: .93rem;
    }
    .pill-list.good li { background: rgba(34,197,94,.12);  border-left: 4px solid #22c55e; }
    .pill-list.gap  li { background: rgba(245,158,11,.12); border-left: 4px solid #f59e0b; }

    section[data-testid="stSidebar"] .stButton > button { width: 100%; }
    #MainMenu, footer { visibility: hidden; }
</style>
"""


# ---------------------------------------------------------------- helpers

def initialize_session():
    defaults = {
        "scan_result": None,
        "functions": [],
        "question_data": None,
        "evaluation": None,
        "first_evaluation": None,
        "retry_count": 0,
        "active_function": None
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_attempt():
    st.session_state.question_data = None
    st.session_state.evaluation = None
    st.session_state.first_evaluation = None
    st.session_state.retry_count = 0


def score_tone(score):
    if score >= 80:
        return "good"
    if score >= 50:
        return "mid"
    return "low"


def score_message(score):
    if score >= 80:
        return "Strong understanding"
    if score >= 50:
        return "Getting there"
    return "Needs more work"


def render_hero():
    st.markdown(
        """
        <div class="hero">
            <h1>🧠 LegitX</h1>
            <p><b>Know Your Code. Own Your Skills.</b>
            &nbsp;·&nbsp; Don't just write code. Understand it.</p>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_stepper(step):
    labels = ["1 · Scan", "2 · Choose", "3 · Challenge", "4 · Evaluate"]
    parts = []

    for i, label in enumerate(labels, start=1):
        if i < step:
            css = "step done"
            label = "✓ " + label
        elif i == step:
            css = "step active"
        else:
            css = "step"
        parts.append(f'<div class="{css}">{label}</div>')

    st.markdown(
        f'<div class="stepper">{"".join(parts)}</div>',
        unsafe_allow_html=True
    )


def render_pill_list(items, kind, empty_text):
    if not items:
        st.caption(empty_text)
        return

    rows = "".join(f"<li>{html.escape(str(i))}</li>" for i in items)
    st.markdown(
        f'<ul class="pill-list {kind}">{rows}</ul>',
        unsafe_allow_html=True
    )


def difficulty_badge(difficulty):
    level = str(difficulty).strip().lower()
    css = level if level in ("easy", "medium", "hard") else ""
    return (
        f'<span class="badge {css}">'
        f'Difficulty: {html.escape(str(difficulty))}</span>'
    )


# ---------------------------------------------------------------- sidebar

def render_sidebar():
    with st.sidebar:
        st.markdown("## 🧠 LegitX")
        st.caption("Practice explaining your own code.")
        st.divider()

        st.markdown("### 📁 Project")

        project_path = st.text_input(
            "Python project folder",
            placeholder=r"C:\Users\YourName\Projects\MyProject",
            help="Full path to the folder containing your .py files."
        )

        if st.button("Scan Project", type="primary"):
            path = project_path.strip()

            if not path:
                st.error("Enter a project folder path.")

            elif not Path(path).expanduser().is_dir():
                st.error("That folder does not exist. Check the path.")

            else:
                try:
                    with st.spinner("Scanning your project..."):
                        result = scan_project(path)

                    st.session_state.scan_result = result
                    st.session_state.functions = result["functions"]
                    st.session_state.active_function = None
                    reset_attempt()

                    st.toast("Project scanned successfully!", icon="✅")

                except Exception as error:
                    st.error(f"Scanning failed: {error}")

        result = st.session_state.scan_result

        if result:
            st.divider()
            st.markdown("### 📊 Scan Summary")
            st.markdown(f"**{html.escape(str(result['project']))}**")
            c1, c2 = st.columns(2)
            c1.metric("Files", result["total_files"])
            c2.metric("Functions", result["total_functions"])

        st.divider()
        st.markdown("### 🏆 Your Progress")

        total_attempts, average_score, functions_practiced = (
            get_overall_stats()
        )
        average_score = average_score or 0

        c1, c2 = st.columns(2)
        c1.metric("Attempts", total_attempts)
        c2.metric("Avg Score", f"{average_score:.0f}%")
        st.metric("Functions Practised", functions_practiced)


# ---------------------------------------------------------------- sections

def render_function_picker(functions):
    st.subheader("Choose a function")

    files = sorted({f["file"] for f in functions})

    col_a, col_b = st.columns([1, 1])

    with col_a:
        file_filter = st.selectbox(
            "Filter by file",
            options=["All files"] + files
        )

    with col_b:
        search = st.text_input(
            "Search by name",
            placeholder="e.g. parse, load, save…"
        ).strip().lower()

    visible = [
        i for i, f in enumerate(functions)
        if (file_filter == "All files" or f["file"] == file_filter)
        and search in f["qualified_name"].lower()
    ]

    if not visible:
        st.warning("No functions match your filters.")
        return None

    selected_index = st.selectbox(
        f"Select a function ({len(visible)} available)",
        options=visible,
        format_func=lambda i: (
            f"{functions[i]['qualified_name']}  ·  {functions[i]['file']}"
        ),
        key="function_selector"
    )

    selected = functions[selected_index]

    marker = (selected["qualified_name"], selected["file"])

    if st.session_state.active_function != marker:
        st.session_state.active_function = marker
        reset_attempt()

    with st.expander("📄 View source code", expanded=False):
        st.code(selected.get("source_code", ""), language="python")

    return selected


def render_question(selected_function):
    st.subheader("Your challenge")

    if st.button("✨ Generate Question", type="primary"):
        try:
            with st.spinner("Generating your challenge..."):
                question = generate_question(selected_function)

            reset_attempt()
            st.session_state.question_data = question

        except Exception as error:
            st.error(f"Question generation failed: {error}")

    question_data = st.session_state.question_data

    if not question_data:
        st.caption(
            "Click **Generate Question** to get a challenge about this function."
        )
        return

    st.markdown(
        difficulty_badge(question_data["difficulty"])
        + f'<span class="badge">Type: '
          f'{html.escape(str(question_data["question_type"]))}</span>',
        unsafe_allow_html=True
    )

    st.markdown(
        f'<div class="question-card">'
        f'{html.escape(str(question_data["question"]))}</div>',
        unsafe_allow_html=True
    )

    if st.session_state.evaluation is None:
        with st.form("answer_form"):
            answer = st.text_area(
                "Explain this function in your own words",
                height=180,
                placeholder="What does it do? What are the inputs, outputs, "
                            "and edge cases? Why is it written this way?"
            )

            submitted = st.form_submit_button(
                "Submit Answer", type="primary"
            )

        if submitted:
            if not answer.strip():
                st.warning("Please enter an answer.")
            else:
                try:
                    with st.spinner("Evaluating your answer..."):
                        evaluation = evaluate_answer(
                            selected_function,
                            question_data,
                            answer
                        )

                        save_evaluation(
                            selected_function["qualified_name"],
                            selected_function["file"],
                            question_data["question"],
                            evaluation
                        )

                    st.session_state.evaluation = evaluation
                    st.session_state.first_evaluation = evaluation
                    st.session_state.retry_count = 0
                    st.rerun()

                except Exception as error:
                    st.error(f"Evaluation failed: {error}")


def render_evaluation(evaluation):
    score = evaluation["percentage"]
    tone = score_tone(score)

    left, right = st.columns([1, 2])

    with left:
        st.markdown(
            f"""
            <div class="score-card {tone}">
                <div class="label">Understanding Score</div>
                <div class="big">{score:.0f}%</div>
                <div>{score_message(score)}</div>
                <div class="label" style="margin-top:.5rem">
                    {evaluation['total_score']} / {evaluation['maximum_score']} points
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        first = st.session_state.first_evaluation
        if first is not None and st.session_state.retry_count > 0:
            st.metric(
                "Improvement since first attempt",
                f"{score:.0f}%",
                delta=f"{score - first['percentage']:+.0f}%"
            )

    with right:
        st.markdown("#### Criterion breakdown")

        for item in evaluation.get("criterion_results", []):
            points = item["score"]
            icon = "🟢" if points >= 2 else "🟡" if points == 1 else "🔴"

            with st.expander(
                f"{icon} {item['criterion']} — {points}/2"
            ):
                st.markdown(f"**Feedback:** {item['feedback']}")
                st.markdown(f"**Evidence:** {item['evidence']}")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### ✅ Strengths")
        render_pill_list(
            evaluation.get("strengths", []), "good",
            "No strengths recorded."
        )

    with col2:
        st.markdown("#### 📌 Knowledge gaps")
        render_pill_list(
            evaluation.get("knowledge_gaps", []), "gap",
            "No gaps found — nice work!"
        )

    overall = evaluation.get("overall_feedback", "")
    if overall:
        st.markdown("#### 💬 Overall feedback")
        st.info(overall)

    with st.expander("💡 View suggested answer"):
        st.write(evaluation.get("suggested_answer", ""))


def render_next_step(selected_function, question_data, evaluation):
    next_action = choose_next_action(evaluation)

    st.markdown("#### 🎯 Your next step")
    st.info(next_action["message"])

    if next_action["action"] in ("retry", "practice"):
        retry_prompt = create_retry_prompt(question_data, evaluation)

        focus = next_action.get("focus_areas", [])
        if focus:
            st.markdown("**Focus areas**")
            render_pill_list(focus, "gap", "")

        st.write(retry_prompt)

        with st.form(f"retry_form_{st.session_state.retry_count}"):
            retry_answer = st.text_area(
                "Try explaining it again",
                height=160
            )

            retry_submitted = st.form_submit_button(
                "Submit Improved Answer", type="primary"
            )

        if retry_submitted:
            if not retry_answer.strip():
                st.warning("Please enter your answer.")
            else:
                try:
                    with st.spinner("Evaluating your retry..."):
                        retry_evaluation = evaluate_answer(
                            selected_function,
                            question_data,
                            retry_answer
                        )

                        save_evaluation(
                            selected_function["qualified_name"],
                            selected_function["file"],
                            question_data["question"],
                            retry_evaluation
                        )

                    old_score = evaluation["percentage"]
                    new_score = retry_evaluation["percentage"]

                    st.session_state.evaluation = retry_evaluation
                    st.session_state.retry_count += 1

                    st.toast(
                        f"Previous: {old_score:.0f}%  →  New: {new_score:.0f}%",
                        icon="📈"
                    )
                    st.rerun()

                except Exception as error:
                    st.error(f"Retry failed: {error}")

    elif next_action["action"] == "next":
        st.success(
            "🎉 You're ready to practise another function. "
            "Choose a different one above."
        )


def render_practice_tab():
    functions = st.session_state.functions

    if not st.session_state.scan_result:
        st.info(
            "👈 Start by entering your project folder in the sidebar "
            "and clicking **Scan Project**."
        )
        render_stepper(1)
        return

    if not functions:
        st.warning("No Python functions found in this project.")
        render_stepper(1)
        return

    question_data = st.session_state.question_data
    evaluation = st.session_state.evaluation

    if evaluation:
        step = 4
    elif question_data:
        step = 3
    else:
        step = 2

    render_stepper(step)

    selected_function = render_function_picker(functions)

    if selected_function is None:
        return

    st.divider()
    render_question(selected_function)

    question_data = st.session_state.question_data
    evaluation = st.session_state.evaluation

    if evaluation and question_data:
        st.divider()
        st.subheader("Evaluation results")
        render_evaluation(evaluation)

        st.divider()
        render_next_step(selected_function, question_data, evaluation)


def render_history_tab():
    total_attempts, average_score, functions_practiced = (
        get_overall_stats()
    )
    average_score = average_score or 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Attempts", total_attempts)
    col2.metric("Average Score", f"{average_score:.1f}%")
    col3.metric("Functions Practised", functions_practiced)

    progress = get_function_progress()

    if progress:
        st.subheader("Function-wise progress")

        st.dataframe(
            [
                {
                    "Function": row[0],
                    "Attempts": row[1],
                    "Average Score": round(row[2] or 0, 1),
                    "Best Score": round(row[3] or 0, 1)
                }
                for row in progress
            ],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Average Score": st.column_config.ProgressColumn(
                    "Average Score", min_value=0, max_value=100,
                    format="%.1f%%"
                ),
                "Best Score": st.column_config.ProgressColumn(
                    "Best Score", min_value=0, max_value=100,
                    format="%.1f%%"
                )
            }
        )

    recent = get_recent_evaluations()

    st.subheader("Recent evaluations")

    if recent:
        # Score trend (rows come newest-first, so reverse for the chart)
        trend = [row[4] for row in reversed(recent)]
        if len(trend) > 1:
            st.caption("Score trend (oldest → newest)")
            st.line_chart(trend, height=180)

        st.dataframe(
            [
                {
                    "Function": row[0],
                    "File": row[1],
                    "Score": f"{row[2]}/{row[3]}",
                    "Percentage": round(row[4], 1),
                    "Date": str(row[5])
                }
                for row in recent
            ],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Percentage": st.column_config.ProgressColumn(
                    "Percentage", min_value=0, max_value=100,
                    format="%.1f%%"
                )
            }
        )
    else:
        st.info("No evaluations yet. Complete a challenge to see your history.")


# ---------------------------------------------------------------- main

def main():
    initialize_database()
    initialize_session()

    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    render_sidebar()
    render_hero()

    practice_tab, history_tab = st.tabs(
        ["🎯 Practice", "📈 Learning History"]
    )

    with practice_tab:
        render_practice_tab()

    with history_tab:
        render_history_tab()


if __name__ == "__main__":
    main()