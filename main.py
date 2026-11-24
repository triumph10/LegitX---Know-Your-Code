
import streamlit as st
from pathlib import Path

from scanner import scan_project
from question_generator import generate_question
from evaluator import evaluate_answer
from adaptive_learning import (
    choose_next_action,
    create_retry_prompt
)
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
    layout="wide"
)


# ---------------- SESSION STATE ----------------

def initialize_session():
    defaults = {
        "scan_result": None,
        "functions": [],
        "question_data": None,
        "evaluation": None,
        "selected_function": None,
        "retry_count": 0,
        "project_path": ""
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ---------------- EVALUATION DISPLAY ----------------

def show_evaluation(evaluation):
    st.subheader("Your Evaluation")

    percentage = evaluation["percentage"]

    st.metric(
        "Understanding Score",
        f"{percentage}%"
    )

    st.progress(max(0, min(100, percentage)) / 100)

    st.write(
        f"**Points:** {evaluation['total_score']} / "
        f"{evaluation['maximum_score']}"
    )

    st.divider()

    st.subheader("Criterion Breakdown")

    for item in evaluation.get("criterion_results", []):
        with st.expander(
            f"{item['criterion']} — {item['score']}/2"
        ):
            st.write("**Feedback:**", item["feedback"])
            st.write("**Evidence:**", item["evidence"])

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Your Strengths")

        for strength in evaluation.get("strengths", []):
            st.write(f"✅ {strength}")

    with col2:
        st.subheader("Knowledge Gaps")

        for gap in evaluation.get("knowledge_gaps", []):
            st.write(f"📌 {gap}")

    st.divider()

    st.subheader("Overall Feedback")
    st.write(evaluation.get("overall_feedback", ""))

    with st.expander("View Suggested Answer"):
        st.write(evaluation.get("suggested_answer", ""))


# ---------------- MAIN APPLICATION ----------------

def main():

    initialize_database()
    initialize_session()

    st.title("🧠 LegitX")
    st.subheader("Know Your Code. Own Your Skills.")
    st.write(
        "Don't just write code. Understand it."
    )

    # PROJECT INPUT

    st.divider()
    st.header("1. Select Your Project")

    project_path = st.text_input(
        "Enter your Python project folder path",
        placeholder=r"C:\Users\YourName\Projects\MyProject",
        value=st.session_state.project_path
    )

    if st.button("🔍 Scan Project", type="primary"):

        if not project_path.strip():
            st.error("Please enter a project folder path.")

        elif not Path(project_path).expanduser().is_dir():
            st.error("The folder does not exist. Check the path.")

        else:
            try:
                with st.spinner("Scanning your project..."):

                    result = scan_project(project_path.strip())

                st.session_state.scan_result = result
                st.session_state.functions = result["functions"]
                st.session_state.project_path = project_path.strip()

                st.session_state.question_data = None
                st.session_state.evaluation = None
                st.session_state.selected_function = None
                st.session_state.retry_count = 0

                st.session_state.function_index = 0

                st.success("Project scanned successfully!")

            except Exception as error:
                st.error(f"Scanning failed: {error}")

    # SCAN RESULTS

    if st.session_state.scan_result:

        result = st.session_state.scan_result

        col1, col2, col3 = st.columns(3)

        col1.metric("Files Scanned", result["total_files"])
        col2.metric("Functions Found", result["total_functions"])
        col3.metric("Available Challenges", len(result["functions"]))

        if not st.session_state.functions:
            st.warning("No Python functions were found.")

        else:

            # FUNCTION SELECTION

            st.divider()
            st.header("2. Choose a Function")

            selected_index = st.selectbox(
                "Select a function to practise",
                options=range(len(st.session_state.functions)),
                format_func=lambda index: (
                    st.session_state.functions[index]["qualified_name"]
                    + " — "
                    + st.session_state.functions[index]["file"]
                ),
                key="function_index"
            )

            selected_function = st.session_state.functions[selected_index]

            function_id = (
                selected_function["qualified_name"],
                selected_function["file"]
            )

            if st.session_state.selected_function != function_id:

                st.session_state.selected_function = function_id
                st.session_state.question_data = None
                st.session_state.evaluation = None
                st.session_state.retry_count = 0

            with st.expander("View Function Source Code"):
                st.code(
                    selected_function.get("source_code", ""),
                    language="python"
                )

            # QUESTION GENERATION

            st.divider()
            st.header("3. Generate Your Challenge")

            if st.button("✨ Generate Question"):

                try:
                    with st.spinner("Generating your AI challenge..."):

                        question_data = generate_question(
                            selected_function
                        )

                    st.session_state.question_data = question_data
                    st.session_state.evaluation = None
                    st.session_state.retry_count = 0

                except Exception as error:
                    st.error(f"Question generation failed: {error}")

            # ANSWER SUBMISSION

            if st.session_state.question_data:

                question_data = st.session_state.question_data

                st.divider()
                st.header("4. Your Challenge")

                st.caption(
                    f"Difficulty: {question_data['difficulty']} | "
                    f"Type: {question_data['question_type']}"
                )

                st.info(question_data["question"])

                with st.form("answer_form"):

                    user_answer = st.text_area(
                        "Explain this function in your own words",
                        height=180,
                        placeholder="Write your explanation here..."
                    )

                    submitted = st.form_submit_button(
                        "Submit Answer",
                        type="primary"
                    )

                if submitted:

                    if not user_answer.strip():
                        st.warning("Please enter your explanation.")

                    else:
                        try:
                            with st.spinner(
                                "Evaluating your understanding..."
                            ):

                                evaluation = evaluate_answer(
                                    selected_function,
                                    question_data,
                                    user_answer
                                )

                                save_evaluation(
                                    selected_function["qualified_name"],
                                    selected_function["file"],
                                    question_data["question"],
                                    evaluation
                                )

                            st.session_state.evaluation = evaluation
                            st.session_state.retry_count = 0

                            st.success("Your evaluation is complete!")

                        except Exception as error:
                            st.error(f"Evaluation failed: {error}")

            # EVALUATION AND ADAPTIVE LEARNING

            if st.session_state.evaluation:

                evaluation = st.session_state.evaluation

                st.divider()
                st.header("5. Your Learning Results")

                show_evaluation(evaluation)

                next_action = choose_next_action(evaluation)

                st.divider()
                st.subheader("Your Next Step")

                st.info(next_action["message"])

                if next_action["action"] in ("retry", "practice"):

                    retry_prompt = create_retry_prompt(
                        question_data,
                        evaluation
                    )

                    st.subheader("Targeted Practice")

                    for gap in next_action["focus_areas"]:
                        st.write(f"📌 {gap}")

                    st.write(retry_prompt)

                    with st.form("retry_form"):

                        retry_answer = st.text_area(
                            "Try explaining it again",
                            height=150,
                            key=f"retry_answer_{st.session_state.retry_count}"
                        )

                        retry_submitted = st.form_submit_button(
                            "Submit Improved Answer"
                        )

                    if retry_submitted:

                        if not retry_answer.strip():
                            st.warning("Please enter your explanation.")

                        else:
                            try:
                                with st.spinner(
                                    "Evaluating your improved explanation..."
                                ):

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

                                st.success(
                                    f"Previous score: {old_score}% | "
                                    f"New score: {new_score}%"
                                )

                                st.rerun()

                            except Exception as error:
                                st.error(f"Retry evaluation failed: {error}")

                elif next_action["action"] == "next":

                    st.success(
                        "Great progress! Select another function "
                        "to explore a new challenge."
                    )

    # LEARNING HISTORY

    st.divider()
    st.header("6. Your Learning History")

    total_attempts, average_score, functions_practiced = (
        get_overall_stats()
    )

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Attempts", total_attempts)
    col2.metric("Average Score", f"{average_score:.1f}%")
    col3.metric("Functions Practised", functions_practiced)

    progress = get_function_progress()

    if progress:

        st.subheader("Function-wise Progress")

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
            hide_index=True
        )

    recent = get_recent_evaluations()

    st.subheader("Recent Evaluations")

    if recent:

        st.dataframe(
            [
                {
                    "Function": row[0],
                    "File": row[1],
                    "Score": f"{row[2]}/{row[3]}",
                    "Percentage": f"{row[4]:.1f}%",
                    "Date": str(row[5])
                }
                for row in recent
            ],
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("Your completed evaluations will appear here.")


if __name__ == "__main__":
    main()
