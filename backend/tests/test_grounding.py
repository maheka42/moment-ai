"""Regression tests for evidence-grounded corporate generation."""
import json
import unittest

from backend.app.services.grounding import validate_corporate_output


SOURCE = (
    "Product Launch Planning. 9 November 2026. "
    "Asha, Project Manager, said the team is targeting 20 November 2026. "
    "Ravi, Engineering, reported that payment testing is still in progress. "
    "Neha, Marketing, said the first marketing campaign draft is ready and will be shared tomorrow. "
    "Ravi will complete payment testing by 12 November 2026."
)


class CorporateGroundingTests(unittest.TestCase):
    def setUp(self):
        self.generated = {
            "meeting_title": "Product Launch Planning",
            "date": "9 November 2026",
            "attendees": [
                {"name": "Asha", "role": "Project Manager"},
                {"name": "Ravi", "role": "Engineering"},
                {"name": "Neha", "role": "Marketing"},
                {"name": "Invented Person", "role": "Finance"},
            ],
            "executive_summary": "The team confirmed the launch date and approved the marketing budget.",
            "agenda": [
                {"item": "Review launch readiness", "evidence": "Review launch readiness"},
            ],
            "discussion_points": [
                {
                    "summary": "Payment testing is still in progress",
                    "evidence": "Ravi, Engineering, reported that payment testing is still in progress.",
                }
            ],
            "decisions": [
                {
                    "description": "The team confirmed the planned launch date.",
                    "evidence": "Asha, Project Manager, said the team is targeting 20 November 2026.",
                }
            ],
            "action_items": [
                {
                    "task": "Complete payment testing",
                    "owner": "Ravi",
                    "deadline": "12 November 2026",
                    "evidence": "Ravi will complete payment testing by 12 November 2026.",
                },
                {
                    "task": "Approve the marketing budget",
                    "owner": "Neha",
                    "deadline": "10 November 2026",
                    "evidence": "Neha, Marketing, said the first marketing campaign draft is ready and will be shared tomorrow.",
                },
            ],
            "open_questions": [
                {
                    "question": "Has the final marketing budget been approved?",
                    "evidence": "Has the final marketing budget been approved?",
                }
            ],
            "risks_and_dependencies": [
                {
                    "description": "Payment testing may affect launch readiness.",
                    "evidence": "Ravi, Engineering, reported that payment testing is still in progress.",
                }
            ],
            "follow_up_email": "The model-generated email contains unsupported claims.",
        }

    def test_removes_unsupported_items_and_rebuilds_email(self):
        result = json.loads(validate_corporate_output(json.dumps(self.generated), SOURCE))
        self.assertEqual(result["decisions"], [])
        self.assertEqual(result["open_questions"], [])
        self.assertEqual(result["risks_and_dependencies"], [])
        self.assertEqual(len(result["action_items"]), 1)
        self.assertEqual(result["action_items"][0]["task"], "Complete payment testing")
        self.assertEqual(result["attendees"][-1]["name"], "Neha")
        self.assertNotIn("approved the marketing budget", result["executive_summary"])
        self.assertIn("Payment testing is still in progress", result["executive_summary"])
        self.assertNotIn("unsupported claims", result["follow_up_email"])
        self.assertIn("Complete payment testing", result["follow_up_email"])
        self.assertNotIn("marketing budget", result["follow_up_email"].lower())

    def test_rejects_non_json_response(self):
        with self.assertRaises(ValueError):
            validate_corporate_output("not json", SOURCE)

    def test_missing_fields_get_safe_defaults(self):
        result = json.loads(validate_corporate_output("{}", SOURCE))
        self.assertEqual(result["decisions"], [])
        self.assertEqual(result["action_items"], [])
        self.assertEqual(result["open_questions"], [])
        self.assertEqual(result["follow_up_email"].splitlines()[0], "Subject: Meeting follow-up")


if __name__ == "__main__":
    unittest.main()
