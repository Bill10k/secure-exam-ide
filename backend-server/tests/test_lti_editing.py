import unittest
import json
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:8000"


def http_request(url, method="GET", data=None):
    headers = {"Content-Type": "application/json"} if data is not None else {}
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode("utf-8")
            return resp.status, json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8")
        try:
            body = json.loads(content)
        except Exception:
            body = {"detail": content}
        return e.code, body


class TestLTIEditingAPI(unittest.TestCase):

    def test_01_get_all_exams(self):
        status, data = http_request(f"{BASE_URL}/lti/exams")
        self.assertEqual(status, 200)
        self.assertIsInstance(data, list)

    def test_02_create_exam_question_testcase_workflow(self):
        # 1. Create Exam
        exam_payload = {
            "title": "Integration Test Exam",
            "description": "Created for testing",
            "duration": 60,
            "language": "python"
        }
        status, exam_data = http_request(f"{BASE_URL}/api/launch/api/exam", method="POST", data=exam_payload)
        self.assertEqual(status, 200)
        exam_id = exam_data["exam_id"]

        # 2. Try publishing exam before questions exist -> Fail
        status_pub, pub_err = http_request(f"{BASE_URL}/lti/exams/{exam_id}", method="PUT", data={
            "title": "Integration Test Exam",
            "description": "Created for testing",
            "duration": 60,
            "published": True
        })
        self.assertEqual(status_pub, 400)
        self.assertIn("has no questions", pub_err["detail"])

        # 3. Create Question
        q_payload = {
            "exam_id": exam_id,
            "title": "Square Function",
            "description": "Return square of n",
            "diff_level": 1,
            "language": "python",
            "functional_weight": 80.0,
            "static_weight": 20.0,
            "default_code": "def square(n):\n    return n * n",
            "static_rules": [
                {
                    "rule_type": "required_function",
                    "expected_value": "square",
                    "weight": 1.0,
                    "required": True
                }
            ]
        }
        status_q, q_data = http_request(f"{BASE_URL}/api/launch/api/question", method="POST", data=q_payload)
        self.assertEqual(status_q, 200)
        q_id = q_data["question_id"]
        rule_id = q_data["static_rules"][0]["rule_id"]

        # 4. Try publishing exam before test cases exist -> Fail
        status_pub2, pub_err2 = http_request(f"{BASE_URL}/lti/exams/{exam_id}", method="PUT", data={
            "title": "Integration Test Exam",
            "description": "Created for testing",
            "duration": 60,
            "published": True
        })
        self.assertEqual(status_pub2, 400)
        self.assertIn("has no test cases", pub_err2["detail"])

        # 5. Add Test Case
        tc_payload = {
            "question_id": q_id,
            "input_data": "4",
            "expected_output": "16",
            "is_hidden": False,
            "weight": 1.0
        }
        status_tc, tc_data = http_request(f"{BASE_URL}/lti/testcases", method="POST", data=tc_payload)
        self.assertEqual(status_tc, 200)
        tc_id = tc_data["test_case_id"]

        # 6. Publish Exam -> Success
        status_pub_ok, pub_ok = http_request(f"{BASE_URL}/lti/exams/{exam_id}", method="PUT", data={
            "title": "Integration Test Exam",
            "description": "Created for testing",
            "duration": 60,
            "published": True
        })
        self.assertEqual(status_pub_ok, 200)
        self.assertTrue(pub_ok["published"])

        # 7. Update Question (Differential static rule sync)
        q_update = {
            "title": "Square Function Updated",
            "description": "Return square of n updated",
            "diff_level": 2,
            "language": "python",
            "functional_weight": 70.0,
            "static_weight": 30.0,
            "default_code": "def square(n):\n    return n ** 2",
            "static_rules": [
                {
                    "rule_id": rule_id,
                    "rule_type": "required_function",
                    "expected_value": "square",
                    "weight": 2.0,
                    "required": True
                }
            ]
        }
        status_qupd, q_upd_data = http_request(f"{BASE_URL}/lti/questions/{q_id}", method="PUT", data=q_update)
        self.assertEqual(status_qupd, 200)
        self.assertEqual(q_upd_data["title"], "Square Function Updated")

        # 8. Update Test Case
        tc_update = {
            "input_data": "5",
            "expected_output": "25",
            "is_hidden": True,
            "weight": 2.0
        }
        status_tcupd, tc_upd_data = http_request(f"{BASE_URL}/lti/testcases/{tc_id}", method="PUT", data=tc_update)
        self.assertEqual(status_tcupd, 200)
        self.assertEqual(tc_upd_data["input_data"], "5")

        # 9. Delete Test Case
        status_tcdel, _ = http_request(f"{BASE_URL}/lti/testcases/{tc_id}", method="DELETE")
        self.assertEqual(status_tcdel, 200)

        # 10. Delete Question
        status_qdel, _ = http_request(f"{BASE_URL}/lti/questions/{q_id}", method="DELETE")
        self.assertEqual(status_qdel, 200)

        # 11. Delete Exam (204 No Content)
        status_examdel, _ = http_request(f"{BASE_URL}/lti/exams/{exam_id}", method="DELETE")
        self.assertEqual(status_examdel, 204)

        # 12. Verify Exam is gone
        status_get_del, _ = http_request(f"{BASE_URL}/lti/exams/{exam_id}")
        self.assertEqual(status_get_del, 404)

    def test_03_delete_nonexistent_exam(self):
        status, data = http_request(f"{BASE_URL}/lti/exams/999999", method="DELETE")
        self.assertEqual(status, 404)
        self.assertIn("detail", data)

    def test_04_delete_exam_cascade(self):
        # Create Exam
        _, exam_data = http_request(f"{BASE_URL}/api/launch/api/exam", method="POST", data={
            "title": "Cascade Delete Exam",
            "description": "To be cascade deleted",
            "duration": 30,
            "language": "python"
        })
        exam_id = exam_data["exam_id"]

        # Create Question with rules
        _, q_data = http_request(f"{BASE_URL}/api/launch/api/question", method="POST", data={
            "exam_id": exam_id,
            "title": "Cascade Q",
            "description": "Desc",
            "diff_level": 1,
            "language": "python",
            "functional_weight": 80.0,
            "static_weight": 20.0,
            "default_code": "",
            "static_rules": [{"rule_type": "required_function", "expected_value": "foo", "weight": 1.0, "required": True}]
        })
        q_id = q_data["question_id"]

        # Add Test Case
        _, tc_data = http_request(f"{BASE_URL}/lti/testcases", method="POST", data={
            "question_id": q_id,
            "input_data": "1",
            "expected_output": "2",
            "is_hidden": False,
            "weight": 1.0
        })

        # Delete Exam -> 204 No Content
        status_del, _ = http_request(f"{BASE_URL}/lti/exams/{exam_id}", method="DELETE")
        self.assertEqual(status_del, 204)

        # Verify Exam and Question no longer exist
        status_e, _ = http_request(f"{BASE_URL}/lti/exams/{exam_id}")
        self.assertEqual(status_e, 404)
        status_q, _ = http_request(f"{BASE_URL}/lti/questions/{q_id}")
        self.assertEqual(status_q, 404)


if __name__ == "__main__":
    unittest.main()
