import asyncio
import tempfile
import os
from sqlalchemy.orm import Session
from ..models import TestCase

async def execute_code_docker(code: str, language: str, custom_input: str = "") -> dict:
    """
    Executes code inside the sandbox Docker container with optional custom stdin.
    """
    if language.lower() != "python":
        return {
            "stdout": "",
            "stderr": f"Language {language} is not supported yet.",
            "exit_code": 1,
            "execution_time": 0.0
        }

    # Create a temporary file to hold the code
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
        temp_file.write(code)
        temp_file_path = temp_file.name

    try:
        # Run docker container
        # Mount the temp file as /app/main.py
        # Use --network none for security (no internet access for student code)
        process = await asyncio.create_subprocess_exec(
            'docker', 'run', '--rm', '-i',
            '--network', 'none',
            '--memory=128m', '--cpus=0.5',
            '--read-only', '--pids-limit=64',
            '-v', f'{temp_file_path}:/app/main.py:ro',
            'sandbox-image',
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            # Pass custom input if provided
            input_bytes = custom_input.encode('utf-8') if custom_input else b''
            # Wait with a timeout to prevent infinite loops
            stdout, stderr = await asyncio.wait_for(process.communicate(input=input_bytes), timeout=10.0)
            exit_code = process.returncode
            
            return {
                "stdout": stdout.decode('utf-8'),
                "stderr": stderr.decode('utf-8'),
                "exit_code": exit_code,
                "execution_time": 0.0 # Real time tracking can be added later
            }
            
        except asyncio.TimeoutError:
            process.kill()
            await process.communicate()
            return {
                "stdout": "",
                "stderr": "Execution timed out (10 seconds).",
                "exit_code": 124,
                "execution_time": 10.0
            }

    finally:
        # Clean up the temporary file
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
            "feedback": "No test cases found for this question."
        }

    passed = 0
    total_weight = 0.0
    earned_weight = 0.0
    total = len(test_cases)
    feedback_messages = []

    # Create a temporary file for the code
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
        temp_file.write(code)
        temp_file_path = temp_file.name

    try:
        for i, tc in enumerate(test_cases, 1):
            tc_weight = tc.weight if hasattr(tc, 'weight') and tc.weight is not None else 1.0
            total_weight += tc_weight

            # Run docker container interactively to pass stdin
            process = await asyncio.create_subprocess_exec(
                'docker', 'run', '--rm', '-i',
                '--network', 'none',
                '--memory=128m', '--cpus=0.5',
                '--read-only', '--pids-limit=64',
                '-v', f'{temp_file_path}:/app/main.py:ro',
                'sandbox-image',
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                # Pass the test case input data to stdin
                # Schema uses 'input', fallback to 'input_data' if model hasn't been updated yet
                tc_input = getattr(tc, 'input', getattr(tc, 'input_data', ''))
                input_bytes = tc_input.encode('utf-8') if tc_input else b''
                
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input=input_bytes), 
                    timeout=10.0
                )
                
                output_str = stdout.decode('utf-8').strip()
                expected_str = tc.expected_output.strip() if tc.expected_output else ""
                
                if process.returncode == 0 and output_str == expected_str:
                    passed += 1
                    earned_weight += tc_weight
                else:
                    err = stderr.decode('utf-8').strip()
                    if err:
                        feedback_messages.append(f"Test case {i} failed with error: {err}")
                    elif process.returncode != 0:
                        feedback_messages.append(f"Test case {i} failed with exit code {process.returncode}")
                    else:
                        feedback_messages.append(f"Test case {i} failed. Expected output didn't match.")
                        
            except asyncio.TimeoutError:
                process.kill()
                await process.communicate()
                feedback_messages.append(f"Test case {i} timed out (10s).")

    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

    # Use weight-based scoring if total_weight > 0, otherwise standard percentage
    score = (earned_weight / total_weight) * 100.0 if total_weight > 0 else 0.0
    status = "passed" if passed == total else "failed"
    
    feedback = f"Passed {passed}/{total} test cases."
    if feedback_messages:
        feedback += "\n" + "\n".join(feedback_messages)

    return {
        "status": status,
        "score": score,
        "feedback": feedback
    }
