
import streamlit as st
from pathlib import Path

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
    layout="wide"
)


def initialize_session():
    defaults = {
        "scan_result": None,
        "functions": [],
        "selected_function_index": 0,
        "question_data": None,
        "evaluation": None,
        "retry_count": 0
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def show_evaluation(evaluation):
    st.subheader("Your Understanding Score")

    score = evaluation["percentage"]
    st.metric("Understanding Score", f"{score:.1f}%")
    st.progress(max(0, min(100, score)) / 100)

    st.write(
        f"Points: {evaluation['total_score']} / "
        f"{evaluation['maximum_score']}"
    )

    st.subheader("Criterion Breakdown")

    for item in evaluation.get("criterion_results", []):
        with st.expander(
            f"{item['criterion']} — {item['score']}/2"
        ):
            st.write("Feedback:", item["feedback"])
            st.write("Evidence:", item["evidence"])

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Strengths")
        for item in evaluation.get("strengths", []):
            st.write(f"✅ {item}")

    with col2:
        st.markdown("### Knowledge Gaps")
        for item in evaluation.get("knowledge_gaps", []):
            st.write(f"📌 {item}")

    st.markdown("### Overall Feedback")
    st.write(evaluation.get("overall_feedback", ""))

    with st.expander("View Suggested Answer"):
        st.write(evaluation.get("suggested_answer", ""))


def main():
    initialize_database()
    initialize_session()

    st.title("🧠 LegitX")
    st.subheader("Know Your Code. Own Your Skills.")
    st.write("Don't just write code. Understand it.")

    # 1. PROJECT SCANNING

    st.divider()
    st.header("1. Scan Your Project")

    project_path = st.text_input(
        "Enter your Python project folder path",
        placeholder=r"C:\Users\YourName\Projects\MyProject"
    )

    if st.button("Scan Project", type="primary"):

        if not project_path.strip():
            st.error("Enter a project folder path.")

        elif not Path(project_path.strip()).expanduser().is_dir():
            st.error("That folder does not exist. Check the path.")

        else:
            try:
                with st.spinner("Scanning your project..."):
                    result = scan_project(project_path.strip())

                st.session_state.scan_result = result
                st.session_state.functions = result["functions"]
                st.session_state.question_data = None
                st.session_state.evaluation = None
                st.session_state.retry_count = 0
                st.session_state.selected_function_index = 0

                st.success("Project scanned successfully!")

            except Exception as error:
                st.error(f"Scanning failed: {error}")

    # 2. SCAN RESULTS

    if st.session_state.scan_result:

        result = st.session_state.scan_result

        col1, col2, col3 = st.columns(3)
        col1.metric("Project", result["project"])
        col2.metric("Files Scanned", result["total_files"])
        col3.metric("Functions Found", result["total_functions"])

        functions = st.session_state.functions

        if not functions:
            st.warning("No Python functions found.")

        else:

            # 3. FUNCTION SELECTION

            st.divider()
            st.header("2. Choose a Function")

            selected_index = st.selectbox(
                "Select a function",
                options=range(len(functions)),
                format_func=lambda i: (
                    f"{functions[i]['qualified_name']} "
                    f"({functions[i]['file']})"
                ),
                key="function_selector"
            )

            selected_function = functions[selected_index]

            if st.session_state.get("active_function") != (
                selected_function["qualified_name"],
                selected_function["file"]
            ):
                st.session_state.active_function = (
                    selected_function["qualified_name"],
                    selected_function["file"]
                )
                st.session_state.question_data = None
                st.session_state.evaluation = None
                st.session_state.retry_count = 0

            with st.expander("View Source Code"):
                st.code(
                    selected_function.get("source_code", ""),
                    language="python"
                )

            # 4. QUESTION GENERATION

            st.divider()
            st.header("3. Generate a Challenge")

            if st.button("Generate Question"):

                try:
                    with st.spinner("Generating your challenge..."):
                        question = generate_question(selected_function)

                    st.session_state.question_data = question
                    st.session_state.evaluation = None
                    st.session_state.retry_count = 0

                except Exception as error:
                    st.error(f"Question generation failed: {error}")

            # 5. ANSWER SUBMISSION

            question_data = st.session_state.question_data

            if question_data:

                st.divider()
                st.header("4. Your Challenge")

                st.caption(
                    f"Difficulty: {question_data['difficulty']} | "
                    f"Type: {question_data['question_type']}"
                )

                st.info(question_data["question"])

                with st.form("answer_form"):
                    answer = st.text_area(
                        "Explain this function in your own words",
                        height=160,
                        placeholder="Write your explanation..."
                    )

                    submitted = st.form_submit_button("Submit Answer")

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
                            st.session_state.retry_count = 0

                            st.success("Evaluation completed!")
                            st.rerun()

                        except Exception as error:
                            st.error(f"Evaluation failed: {error}")

            # 6. EVALUATION AND RETRY

            evaluation = st.session_state.evaluation

            if evaluation:

                st.divider()
                st.header("5. Evaluation Results")

                show_evaluation(evaluation)

                next_action = choose_next_action(evaluation)

                st.subheader("Your Next Step")
                st.info(next_action["message"])

                if next_action["action"] in ("retry", "practice"):

                    retry_prompt = create_retry_prompt(
                        question_data,
                        evaluation
                    )

                    st.subheader("Focus Areas")

                    for gap in next_action["focus_areas"]:
                        st.write(f"📌 {gap}")

                    st.write(retry_prompt)

                    with st.form(
                        f"retry_form_{st.session_state.retry_count}"
                    ):
                        retry_answer = st.text_area(
                            "Try explaining it again",
                            height=150
                        )

                        retry_submitted = st.form_submit_button(
                            "Submit Improved Answer"
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

                                st.success(
                                    f"Previous score: {old_score}% | "
                                    f"New score: {new_score}%"
                                )

                                st.rerun()

                            except Exception as error:
                                st.error(f"Retry failed: {error}")

                elif next_action["action"] == "next":
                    st.success(
                        "You're ready to practise another function. "
                        "Choose a different function above."
                    )

    # 7. LEARNING HISTORY

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
        st.info("No evaluations yet.")


if __name__ == "__main__":
    main()
