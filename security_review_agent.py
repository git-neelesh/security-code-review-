"""securityReviewAgent: Performs static security analysis on fetched commit code."""

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.genai import types

from fetch_status import stop_after_failed_commit_fetch

MODEL_NAME = "gemini-3.5-flash-lite"

retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],
)


def security_review_agent() -> LlmAgent:
    """Creates the specialist agent that reviews the fetched commit diff for security flaws."""
    return LlmAgent(
        name="securityReviewAgent",
        model=Gemini(model=MODEL_NAME, retry_options=retry_config),
        description="Performs static security analysis on the fetched commit code and produces a security report.",
        before_agent_callback=stop_after_failed_commit_fetch,
        instruction="""You are an Application Security Code Reviewer.
Review the commit code details fetched by the previous agent:
{commit_code_details}

Your responsibilities:
1. Analyze the modified code and diffs for security vulnerabilities, including:
   - Hardcoded secrets, API keys, tokens, or credentials
   - Injection vulnerabilities (SQLi, Command Injection, XSS, SSRF)
   - Broken authentication, missing authorization checks, or insecure session handling
   - Insecure cryptography, weak hashing, or unsafe deserialization
   - Vulnerable dependencies or unsafe configuration changes
2. Never include the literal value of a password, API key, token, or other secret in your report. Describe the issue and identify the affected variable or location, but replace every secret value in snippets or examples with `[REDACTED]`.
3. Produce a structured Security Analysis Report with:
   - **Repository & Commit**: The exact `owner/repo` and `commit_id`
   - **Overall Risk Level**: Critical / High / Medium / Low / Informational
   - **Findings List**: For each vulnerability found, include:
     * Title & Severity
     * Affected File & Line/Snippet, with any secret values replaced by `[REDACTED]`
     * Vulnerability Explanation & Potential Impact
     * Concrete Remediation / Fix Recommendation
   - **Proposed GitHub Issue Title**: A concise title suitable for a GitHub issue (e.g., `[Security] <Severity>: <Brief Summary> in commit <short_sha>`).
""",
        output_key="security_analysis_report",
    )
