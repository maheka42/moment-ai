"""Unit tests for workflow prompt construction."""
import unittest

from backend.app.services.workflow import build_workflow_prompt


class WorkflowTests(unittest.TestCase):
    def test_corporate_prompt_contains_source(self):
        prompt = build_workflow_prompt("corporate", "Budget approved in meeting.")
        self.assertIn("Budget approved in meeting.", prompt)
        self.assertIn("action_items", prompt)

    def test_student_prompt_contains_source(self):
        prompt = build_workflow_prompt("student", "Ohm's law: V = IR")
        self.assertIn("Ohm's law: V = IR", prompt)
        self.assertIn("formulas", prompt)

    def test_empty_source_rejected(self):
        with self.assertRaises(ValueError):
            build_workflow_prompt("student", "   ")


if __name__ == "__main__":
    unittest.main()
