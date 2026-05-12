import asyncio
import tempfile
import os
import subprocess
from sqlalchemy.orm import Session
from ..models import TestCase


def _run_docker_container(command: list[str], input_data: str = "") -> tuple[str, str, int]:
    """Run the Docker command synchronously in a background thread."""
    try:
        completed = subprocess.run(
            command,
            input=input_data,
            capture_output=True,
            text=True,
            timeout=10.0,
            check=False,
        )
        return completed.stdout, completed.stderr, completed.returncode

    except subprocess.TimeoutExpired:
        return "", "Execution timed out (10 seconds).", 124
    except FileNotFoundError as exc:
        return "", f"Docker is not installed or not available in PATH: {exc}", 1
    except OSError as exc:
        return "", f"Failed to execute docker command: {exc}", 1


async def execute_code_docker(code: str, language: str, custom_input: str = "") -> dict:
    """
    Executes code inside the sandbox Docker container with optional custom stdin.
    """
    if language.lower() != "python":
        return {
            "stdout": "",
            "stderr": f"Language {language} is not supported yet.",
            "exit_code": 1,
            "execution_time": 0.0,
        }

    # Create a temporary file to hold the code
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as temp_file:
        temp_file.write(code)
        temp_file_path = temp_file.name

    try:
        command = [
            'docker', 'run', '--rm', '-i',
            '--network', 'none',
            '--memory=128m', '--cpus=0.5',
            '--read-only', '--pids-limit=64',
            '-v', f'{temp_file_path}:/app/main.py:ro',
            'sandbox-image',
        ]

        stdout, stderr, exit_code = await asyncio.to_thread(
            _run_docker_container, command, custom_input
        )

        return {
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": exit_code,
            "execution_time": 0.0,
        }

    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


async def grade_submission_docker(code: str, question_id: int, db: Session) -> dict:
    """
    Executes code against hidden test cases from the database and calculates a score.
    """
    test_cases = db.query(TestCase).filter(TestCase.question_id == question_id).all()

    if not test_cases:
        return {
            "status": "failed",
            "score": 0.0,
            "feedback": "No test cases found for this question.",
        }

    passed = 0
    total_weight = 0.0
    earned_weight = 0.0
    total = len(test_cases)
    feedback_messages = []

    # Create a temporary file for the code
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as temp_file:
        temp_file.write(code)
        temp_file_path = temp_file.name

    try:
        for i, tc in enumerate(test_cases, 1):
            tc_weight = tc.weight if hasattr(tc, 'weight') and tc.weight is not None else 1.0
            total_weight += tc_weight

            command = [
                'docker', 'run', '--rm', '-i',
                '--network', 'none',
                '--memory=128m', '--cpus=0.5',
                '--read-only', '--pids-limit=64',
                '-v', f'{temp_file_path}:/app/main.py:ro',
                'sandbox-image',
            ]

            tc_input = getattr(tc, 'input', getattr(tc, 'input_data', ''))
            stdout, stderr, return_code = await asyncio.to_thread(
                _run_docker_container, command, tc_input
            )

            output_str = stdout.strip()
            expected_str = tc.expected_output.strip() if tc.expected_output else ""

            if return_code == 0 and output_str == expected_str:
                passed += 1
                earned_weight += tc_weight
            else:
                err = stderr.strip()
                if err:
                    feedback_messages.append(f"Test case {i} failed with error: {err}")
                elif return_code != 0:
                    feedback_messages.append(f"Test case {i} failed with exit code {return_code}")
                else:
                    feedback_messages.append(f"Test case {i} failed. Expected output didn't match.")

    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

    score = (earned_weight / total_weight) * 100.0 if total_weight > 0 else 0.0
    status = "passed" if passed == total else "failed"
    feedback = f"Passed {passed}/{total} test cases."
    if feedback_messages:
        feedback += "\n" + "\n".join(feedback_messages)

    return {
        "status": status,
        "score": score,
        "feedback": feedback,
    }
