
import streamlit as st
import pandas as pd

from database import (
    initialize_database,
    get_overall_stats,
    get_function_progress,
    get_recent_evaluations
)

st.set_page_config(
    page_title="LegitX Dashboard",
    page_icon="🧠",
    layout="wide"
)


def main():
    initialize_database()

    st.title("🧠 LegitX")
    st.subheader("Know Your Code. Own Your Skills.")
    st.caption("Track your code understanding and learning progress.")

    total_attempts, average_score, functions_practiced = get_overall_stats()
    progress = get_function_progress()
    recent = get_recent_evaluations()

    st.divider()
    st.subheader("Your Learning Overview")

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Attempts", total_attempts)
    col2.metric("Average Score", f"{average_score:.1f}%")
    col3.metric("Functions Practiced", functions_practiced)

    st.divider()
    st.subheader("Function-wise Progress")

    if progress:
        progress_df = pd.DataFrame(
            [
                {
                    "Function": row[0],
                    "Attempts": row[1],
                    "Average Score": round(row[2] or 0, 1),
                    "Best Score": round(row[3] or 0, 1)
                }
                for row in progress
            ]
        )

        st.bar_chart(
            progress_df,
            x="Function",
            y="Average Score",
            y_label="Average Score (%)",
            x_label="Function",
            height=350
        )

        st.dataframe(
            progress_df,
            use_container_width=True,
            hide_index=True
        )

        weakest_function = min(progress, key=lambda row: row[2] or 0)

        st.info(
            f"Area to practise: **{weakest_function[0]}** "
            f"(average score: {(weakest_function[2] or 0):.1f}%)"
        )

    else:
        st.info("No progress recorded yet. Complete an evaluation to get started.")

    st.divider()
    st.subheader("Recent Evaluations")

    if recent:
        recent_df = pd.DataFrame(
            [
                {
                    "Function": row[0],
                    "File": row[1],
                    "Score": f"{row[2]}/{row[3]}",
                    "Percentage": f"{row[4]:.1f}%",
                    "Date": str(row[5])
                }
                for row in recent
            ]
        )

        st.dataframe(
            recent_df,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No evaluations available yet.")


if __name__ == "__main__":
    main()
