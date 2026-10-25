import io
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace

from fetch_status import (
    FETCH_FAILURE_STATE_KEY,
    record_commit_fetch_status,
    skip_agent_after_failed_commit_fetch,
    stop_after_failed_commit_fetch,
)


class FetchStatusTests(unittest.TestCase):
    def make_context(self, fetch_result):
        return SimpleNamespace(state={"commit_code_details": fetch_result})

    def record_status(self, context):
        with redirect_stdout(io.StringIO()):
            record_commit_fetch_status(context)

    def test_failed_fetch_types_stop_pipeline_with_specific_errors(self):
        failure_messages = {
            "REPOSITORY_NOT_FOUND": (
                "Repository could not be found, or your GitHub token does not have "
                "access to it. Verify the owner/repository name and token permissions."
            ),
            "COMMIT_NOT_FOUND": (
                "Commit could not be found in the specified repository. Verify the "
                "commit ID."
            ),
            "ACCESS_DENIED": (
                "GitHub denied access to the repository or commit. Check your token "
                "permissions."
            ),
        }

        for failure_type, message in failure_messages.items():
            with self.subTest(failure_type=failure_type):
                context = self.make_context(
                    f"FETCH_STATUS: FAILED\nFETCH_FAILURE: {failure_type}"
                )
                self.record_status(context)

                self.assertEqual(context.state[FETCH_FAILURE_STATE_KEY], message)
                response = stop_after_failed_commit_fetch(context)
                self.assertEqual(
                    response.parts[0].text,
                    f"{message} No security review was performed and no GitHub issue "
                    "was created.",
                )
                self.assertEqual(
                    context.state["final_issue_or_summary"],
                    response.parts[0].text,
                )
                self.assertEqual(skip_agent_after_failed_commit_fetch(context).parts, [])

    def test_unrecognized_fetch_failure_fails_closed(self):
        context = self.make_context("Unexpected tool response")
        self.record_status(context)

        self.assertEqual(
            context.state[FETCH_FAILURE_STATE_KEY],
            "GitHub could not retrieve the requested commit.",
        )
        self.assertIsNotNone(stop_after_failed_commit_fetch(context))

    def test_success_clears_previous_failure_and_allows_downstream_agents(self):
        context = SimpleNamespace(
            state={
                "commit_code_details": "FETCH_STATUS: SUCCESS\nCommit details...",
                FETCH_FAILURE_STATE_KEY: "previous failure",
            }
        )
        self.record_status(context)

        self.assertEqual(context.state[FETCH_FAILURE_STATE_KEY], "")
        self.assertIsNone(stop_after_failed_commit_fetch(context))
        self.assertIsNone(skip_agent_after_failed_commit_fetch(context))


if __name__ == "__main__":
    unittest.main()
