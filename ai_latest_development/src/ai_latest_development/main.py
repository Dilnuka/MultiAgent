#!/usr/bin/env python
import sys
import warnings
import os
from pathlib import Path
from dotenv import load_dotenv

from datetime import datetime

from .crew import AiLatestDevelopment

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path)

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# This main file is intended to be a way for you to run your
# crew locally, so refrain from adding unnecessary logic into this file.
# Replace with inputs you want to test with, it will automatically
# interpolate any tasks and agents information

def run():
    """
    Run the crew.
    """
    inputs = {
        'topic': 'AI LLMs',
        'current_year': str(datetime.now().year),
        'region': os.getenv('REGION', 'EU'),
        'data_use': os.getenv('DATA_USE', 'Personal data, user prompts, model logs'),
        'scenario': os.getenv('SCENARIO', 'Prompt injection leading to data exfiltration')
    }

    def _print_header():
        print("\n=== AI Risk & Compliance Run ===")
        print(f"Topic: {inputs['topic']}")
        print(f"Year: {inputs['current_year']}")
        print(f"Region: {inputs['region']}")
        print(f"Data use: {inputs['data_use']}")
        print(f"Scenario: {inputs['scenario']}")
        print("================================\n")

    def _print_success_summary(report_path: Path):
        print("\n--- Run Summary ---")
        if report_path.exists():
            print(f"Report saved to: {report_path.resolve()}")
            try:
                preview_lines = report_path.read_text(encoding="utf-8", errors="ignore").splitlines()
                preview = "\n".join(preview_lines[:20])  # Show first 20 lines
                print("\nReport preview:")
                print("""\n--------------------\n""" + preview + "\n--------------------")
            except Exception:
                pass
        else:
            print("Tasks completed. No report file detected.")
        print("-------------------\n")

    _print_header()
    try:
        AiLatestDevelopment().crew().kickoff(inputs=inputs)
        # Print a friendly summary and preview of the generated report, if any
        report_path = Path.cwd() / 'report.md'
        _print_success_summary(report_path)
    except Exception as e:
        msg = str(e)
        # Friendlier guidance for transient VertexAI overloads
        if ("503" in msg) or ("overloaded" in msg.lower()) or ("unavailable" in msg.lower()):
            print("\n[Transient service issue] Vertex AI is temporarily overloaded (503 UNAVAILABLE).")
            print("What you can do:")
            print("  - Re-run the command in a minute. These errors usually clear quickly.")
            print("  - The app will automatically retry with backoff. You can increase retries via env:")
            print("    GEMINI_MAX_RETRIES=6 GEMINI_BACKOFF_BASE=1.5")
            print("  - If it persists, check the service status and reduce concurrency.")
        # Re-raise to keep non-transient errors visible to callers / logs
        raise Exception(f"An error occurred while running the crew: {e}")
run()



# def train():
#     """
#     Train the crew for a given number of iterations.
#     """
#     inputs = {
#         "topic": "AI LLMs",
#         'current_year': str(datetime.now().year)
#     }
#     try:
#         AiLatestDevelopment().crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)

#     except Exception as e:
#         raise Exception(f"An error occurred while training the crew: {e}")

# def replay():
#     """
#     Replay the crew execution from a specific task.
#     """
#     try:
#         AiLatestDevelopment().crew().replay(task_id=sys.argv[1])

#     except Exception as e:
#         raise Exception(f"An error occurred while replaying the crew: {e}")

# def test():
#     """
#     Test the crew execution and returns the results.
#     """
#     inputs = {
#         "topic": "AI LLMs",
#         "current_year": str(datetime.now().year)
#     }
    
#     try:
#         AiLatestDevelopment().crew().test(n_iterations=int(sys.argv[1]), eval_llm=sys.argv[2], inputs=inputs)

#     except Exception as e:
#         raise Exception(f"An error occurred while testing the crew: {e}")
