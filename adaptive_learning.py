
def choose_next_action(evaluation):
    """
    Decide what the user should do next based
    on their evaluation.
    """

    percentage = evaluation["percentage"]
    knowledge_gaps = evaluation.get("knowledge_gaps", [])

    if percentage < 50:
        return {
            "action": "retry",
            "message": (
                "You have some important knowledge gaps. "
                "Review the feedback and try again."
            ),
            "focus_areas": knowledge_gaps
        }

    elif percentage < 80:
        return {
            "action": "practice",
            "message": (
                "Good progress! Let's strengthen "
                "the areas you partially understood."
            ),
            "focus_areas": knowledge_gaps
        }

    else:
        return {
            "action": "next",
            "message": (
                "Excellent understanding! "
                "You're ready for another challenge."
            ),
            "focus_areas": []
        }


def create_retry_prompt(question_data, evaluation):
    """
    Create a retry question based on the user's
    knowledge gaps.
    """

    gaps = evaluation.get("knowledge_gaps", [])

    if not gaps:
        return question_data["question"]

    gap_text = "\n".join(
        f"- {gap}" for gap in gaps
    )

    return (
        "Let's strengthen your understanding.\n\n"
        "Your previous answer missed these areas:\n"
        f"{gap_text}\n\n"
        "Try explaining the original question again:\n"
        f"{question_data['question']}"
    )
