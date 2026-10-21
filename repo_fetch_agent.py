"""repoFetchAgent: Fetches commit metadata, diffs, and modified code files from GitHub via MCP."""

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.genai import types

from tools import create_github_readonly_mcp_toolset

MODEL_NAME = "gemini-3.5-flash-lite"

retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],
)


def repoFetchAgent() -> LlmAgent:
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
3. Present a structured summary containing:
   - Repository Name (`owner/repo`)
   - Commit ID (`sha`)
   - Commit Message & Author
   - Modified Files and their complete code diffs/patches.
""",
        tools=[create_github_readonly_mcp_toolset()],
        output_key="commit_code_details",
    )
