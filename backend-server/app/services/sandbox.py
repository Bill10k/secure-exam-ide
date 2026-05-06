import asyncio

async def execute_code_mock(code: str, language: str) -> dict:
    """
    Simulates code execution inside a Docker container.
    Benjamin will replace this with actual Docker Engine API calls.
    """
    await asyncio.sleep(0.5)  # Simulate execution delay
    
    if "error" in code.lower():
        return {
            "stdout": "",
            "stderr": "SyntaxError: invalid syntax",
            "exit_code": 1,
            "execution_time": 0.1
        }
    
    return {
        "stdout": f"Successfully executed {language} code.\nOutput: Hello World!\n",
        "stderr": "",
        "exit_code": 0,
        "execution_time": 0.15
    }

async def grade_submission_mock(code: str, question_id: int) -> dict:
    """
    Simulates executing code against hidden test cases and grading.
    """
    await asyncio.sleep(1) # Simulate test cases execution
    
    if "error" in code.lower():
        return {
            "status": "failed",
            "score": 0.0,
            "feedback": "Failed 3/3 test cases."
        }
        
    return {
        "status": "passed",
        "score": 100.0,
        "feedback": "Passed 3/3 test cases."
    }
