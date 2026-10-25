"""IssueReportAgent: Creates a GitHub issue via MCP if approved, or outputs a brief summary if rejected."""

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.genai import types

from fetch_status import skip_agent_after_failed_commit_fetch
from tools import create_github_write_mcp_toolset

MODEL_NAME = "gemini-3.5-flash-lite"

retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],
)


def issue_report_agent() -> LlmAgent:
    """Creates the final agent that either opens a GitHub issue via MCP or provides a brief summary."""
    return LlmAgent(
        name="IssueReportAgent",
        model=Gemini(model=MODEL_NAME, retry_options=retry_config),
        description="Creates a GitHub issue in the repository if approved, or provides a brief summary if rejected.",
        before_agent_callback=skip_agent_after_failed_commit_fetch,
        instruction="""You are the Security Issue & Reporting Agent.
Review the security analysis report and the user's approval decision from the previous stages:

Security Analysis Report:
{security_analysis_report}

User Approval Decision:
{summary_decision_output}

Your responsibilities:
1. Check whether the user's decision in `{summary_decision_output}` is `APPROVED` (or `status: approved`) versus `REJECTED` (or `status: rejected`).
2. **IF APPROVED**:
   - Use the GitHub MCP server tool (`create_issue` / `issue_write`) to create a new issue in the same repository (`owner/repo`).
   - Set the issue title to the proposed security issue title.
   - Populate the issue body with the structured Security Analysis Report (commit ID, severity, affected files, impact, and remediation steps).
   - Never include literal passwords, API keys, tokens, or other secret values in the issue title or body. If any appear in the report, replace each value with `[REDACTED]` before creating the issue, including inside code snippets.
   - Return a confirmation to the user with the created GitHub issue number, title, and URL.
3. **IF REJECTED**:
   - Do NOT call any GitHub issue creation tool.
   - State clearly that no GitHub issue was created per the user's rejection.
   - Provide a concise, bulleted executive summary (3-5 bullet points) of the security analysis findings and recommended fixes for the user's reference.
""",
        tools=[create_github_write_mcp_toolset()],
        output_key="final_issue_or_summary",
    )
