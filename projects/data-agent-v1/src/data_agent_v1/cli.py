from __future__ import annotations

import argparse
import json

from data_agent_v1.engine import DataAgentEngine


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask the deterministic Data-Agent V1 engine.")
    parser.add_argument("question", help="Business question to answer")
    parser.add_argument("--json", action="store_true", help="Print structured JSON")
    args = parser.parse_args()

    response = DataAgentEngine().answer(args.question)
    if args.json:
        print(json.dumps(response.to_dict(), ensure_ascii=False, indent=2))
        return

    print(f"Intent: {response.intent}")
    print(f"Answer: {response.answer}")
    print("Evidence:")
    for item in response.evidence:
        print(f"- {item}")
    print(f"Calculation: {response.calculation}")
    print(f"SQL: {response.sql}")
    if response.follow_up_questions:
        print("Follow-up questions:")
        for question in response.follow_up_questions:
            print(f"- {question}")


if __name__ == "__main__":
    main()
