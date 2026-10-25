"""repoFetchAgent: Fetches commit metadata, diffs, and modified code files from GitHub via MCP."""

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.genai import types

from fetch_status import record_commit_fetch_status
from tools import create_github_readonly_mcp_toolset

MODEL_NAME = "gemini-3.5-flash-lite"

retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],
)


def repo_fetch_agent() -> LlmAgent:
    """Creates the agent responsible for fetching commit and file details from GitHub MCP."""
    return LlmAgent(
        name="repoFetchAgent",
        model=Gemini(model=MODEL_NAME, retry_options=retry_config),
        description="Fetches commit metadata, diffs, and modified code files from GitHub via MCP.",
        instruction="""You are a GitHub Repository Fetch Specialist.
The user will provide a repository name (e.g., 'owner/repo') and a commit ID (SHA).

Your responsibilities:
1. Extract the exact repository owner, repository name, and commit ID from the user's request.
2. Use the GitHub MCP server tools (such as `get_commit` or `get_file_contents`) to fetch the commit metadata, commit message, author, and the exact code diff/patches for all files modified in that commit.
3. If GitHub reports that the repository does not exist or is inaccessible, the commit does not exist, or any fetch fails, do not invent commit details. Return exactly one of these failure formats as the first lines of your response:
   - `FETCH_STATUS: FAILED` followed by `FETCH_FAILURE: REPOSITORY_NOT_FOUND` when the repository is missing or inaccessible.
   - `FETCH_STATUS: FAILED` followed by `FETCH_FAILURE: COMMIT_NOT_FOUND` when the commit is missing.
   - `FETCH_STATUS: FAILED` followed by `FETCH_FAILURE: ACCESS_DENIED` for an explicit access-denied response.
   - `FETCH_STATUS: FAILED` followed by `FETCH_FAILURE: OTHER` for any other fetch failure.
   Do not include a commit diff or continue as if the fetch succeeded after a failure.
4. Only after all required commit details and diffs are fetched successfully, begin your response with the exact line `FETCH_STATUS: SUCCESS` and present a structured summary containing:
   - Repository Name (`owner/repo`)
   - Commit ID (`sha`)
   - Commit Message & Author
   - Modified Files and their complete code diffs/patches.
""",
        tools=[create_github_readonly_mcp_toolset()],
        output_key="commit_code_details",
        after_agent_callback=record_commit_fetch_status,
    )
