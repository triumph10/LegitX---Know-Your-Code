
from scanner import scan_project
from question_generator import generate_question
from evaluator import evaluate_answer


def main():

    print("\n===== LEGITX =====")
    print("Know Your Code. Own Your Skills.")

    project_path = input(
        "\nEnter the path of your Python project: "
    ).strip().strip('"')

    try:
        print("\nScanning your project...")

        result = scan_project(project_path)

        functions = result["functions"]

        print("\n===== SCAN COMPLETE =====")
        print(f"Project: {result['project']}")
        print(f"Files scanned: {result['total_files']}")
        print(f"Functions found: {result['total_functions']}")

        if not functions:
            print("\nNo Python functions found.")
            return

        print("\n===== SELECT A FUNCTION =====")

        for index, function in enumerate(functions, start=1):
            print(
                f"{index}. {function['qualified_name']} "
                f"({function['file']})"
            )

        selection = int(
            input("\nChoose a function number: ")
        )

        if selection < 1 or selection > len(functions):
            print("Invalid selection.")
            return

        selected_function = functions[selection - 1]

        print("\nGenerating your challenge...")

        question_data = generate_question(selected_function)

        print("\n===== LEGITX CHALLENGE =====")
        print(f"\nFunction: {selected_function['qualified_name']}")
        print(f"Difficulty: {question_data['difficulty']}")
        print(f"Question type: {question_data['question_type']}")

        print("\nQUESTION:")
        print(question_data["question"])

        print("\nTake your time. Explain the function in your own words.")

        user_answer = input("\nYour explanation: ").strip()

        print("\nEvaluating your understanding...")

        evaluation = evaluate_answer(
            selected_function,
            question_data,
            user_answer
        )

        print("\n===== LEGITX EVALUATION =====")

        print(
            f"\nUnderstanding score: "
            f"{evaluation['percentage']}%"
        )

        print(
            f"Points: {evaluation['total_score']} / "
            f"{evaluation['maximum_score']}"
        )

        print("\n===== CRITERION BREAKDOWN =====")

        for index, item in enumerate(
            evaluation["criterion_results"], start=1
        ):
            print(f"\n{index}. {item['criterion']}")
            print(f"Score: {item['score']} / 2")
            print(f"Feedback: {item['feedback']}")
            print(f"Evidence: {item['evidence']}")

        print("\n===== YOUR STRENGTHS =====")

        for strength in evaluation.get("strengths", []):
            print(f"- {strength}")

        print("\n===== KNOWLEDGE GAPS =====")

        for gap in evaluation.get("knowledge_gaps", []):
            print(f"- {gap}")

        print("\n===== OVERALL FEEDBACK =====")
        print(evaluation.get("overall_feedback", ""))

        print("\n===== SUGGESTED ANSWER =====")
        print(evaluation.get("suggested_answer", ""))

    except ValueError as error:
        print(f"\nInput or validation error: {error}")

    except Exception as error:
        print(f"\nLegitX encountered an error: {error}")


if __name__ == "__main__":
    main()