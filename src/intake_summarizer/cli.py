import argparse
from pathlib import Path
from typing import List

from intake_summarizer.flow import intake_batch_flow
from intake_summarizer.results import IntakeResult


def read_inputs(path: Path) -> List[str]:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    lines = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    if not lines:
        raise ValueError("Input file is empty.")

    return lines


def print_summary(results: List[IntakeResult]) -> None:
    ok = sum(1 for r in results if r.status == "ok")
    failed = len(results) - ok

    print("\nBatch Summary")
    print("=" * 40)
    print(f"Total   : {len(results)}")
    print(f"Success : {ok}")
    print(f"Failed  : {failed}")
    print()

    if failed:
        print("Failures:")
        for i, r in enumerate(results, 1):
            if r.status == "failed":
                print(
                    f"- #{i} {r.error_type}: {r.error_message}\n"
                    f"  artifact: {r.failure_artifact}"
                )
        print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run intake summarizer batch from a text file"
    )
    parser.add_argument(
        "input_file",
        type=Path,
        help="Path to inputs.txt (one intake per line)",
    )

    args = parser.parse_args()

    texts = read_inputs(args.input_file)
    results = intake_batch_flow(texts)

    print_summary(results)


if __name__ == "__main__":
    main()