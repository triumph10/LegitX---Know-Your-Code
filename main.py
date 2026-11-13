
from scanner import scan_project


def main():

    print("\n===== LEGITX =====")
    print("Know Your Code. Own Your Skills.")

    project_path = input(
        "\nEnter the path of your Python project: "
    ).strip().strip('"')

    try:
        print("\nScanning your project...")

        result = scan_project(project_path)

        print("\n===== SCAN COMPLETE =====")

        print(f"Project: {result['project']}")
        print(f"Files scanned: {result['total_files']}")
        print(f"Functions found: {result['total_functions']}")

        print("\n===== FUNCTIONS DISCOVERED =====")

        for function in result["functions"]:
            print(
                f"\n{function['qualified_name']}"
                f" | File: {function['file']}"
                f" | Line: {function['line']}"
            )

        print("\n===== IMPORTS DISCOVERED =====")

        for imported in result["imports"]:
            print(imported)

        if result["errors"]:
            print("\nSome files could not be analyzed:")

            for error in result["errors"]:
                print(error["file"], error["error"])

    except Exception as error:
        print(f"\nLegitX encountered an error: {error}")


if __name__ == "__main__":
    main()
