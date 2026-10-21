"""Custom Function Tools and GitHub MCP Toolsets for the Security Code Reviewer."""

import os
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.tool_context import ToolContext

# Support StreamableHTTPServerParams as shown in Day-2b sample notebook
try:
    from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPServerParams
except ImportError:
    from google.adk.tools.mcp_tool.mcp_session_manager import (
        StreamableHTTPConnectionParams as StreamableHTTPServerParams,
    )

GITHUB_MCP_URL = "https://api.githubcopilot.com/mcp/"


def _get_github_token() -> str:
    """Retrieves GITHUB_TOKEN from environment or Kaggle secrets fallback."""
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        try:
            from kaggle_secrets import UserSecretsClient

            token = UserSecretsClient().get_secret("GITHUB_TOKEN")
            os.environ["GITHUB_TOKEN"] = token
        except Exception:
            pass
    return token


def create_github_readonly_mcp_toolset() -> McpToolset:
    """Creates a read-only GitHub MCP toolset for repoFetchAgent.

    Connects to https://api.githubcopilot.com/mcp/ with X-MCP-Readonly set to 'true'
    to fetch commit diffs, file contents, and repository metadata safely.
    """
    github_token = _get_github_token()
    return McpToolset(
        connection_params=StreamableHTTPServerParams(
            url=GITHUB_MCP_URL,
            headers={
                "Authorization": f"Bearer {github_token}",
                "X-MCP-Toolsets": "all",
                "X-MCP-Readonly": "true",
            },
        ),
    )


def create_github_write_mcp_toolset() -> McpToolset:
    """Creates a write-enabled GitHub MCP toolset for IssueReportAgent.

    Connects to https://api.githubcopilot.com/mcp/ with write permissions enabled
    so the agent can create a GitHub issue in the repository after human approval.
    """
    github_token = _get_github_token()
    return McpToolset(
        connection_params=StreamableHTTPServerParams(
            url=GITHUB_MCP_URL,
            headers={
                "Authorization": f"Bearer {github_token}",
                "X-MCP-Toolsets": "repos,issues",
                "X-MCP-Readonly": "false",
            },
        ),
    )


def request_security_issue_approval(
    repo_name: str,
    commit_id: str,
    issue_title: str,
    severity_summary: str,
    tool_context: ToolContext,
) -> dict:
    """Pauses execution to request human-in-the-loop approval before creating a GitHub issue.

    Follows the ADK Long-Running Operation (LRO) pattern from day-2b-agent-tools-best-practices:
    - First call: invokes tool_context.request_confirmation() and returns 'pending'.
    - Resumed call: reads tool_context.tool_confirmation.confirmed and returns 'approved' or 'rejected'.

    Args:
        repo_name: Full repository name in 'owner/repo' format.
        commit_id: Commit SHA that was analyzed.
        issue_title: Proposed title for the GitHub security issue.
        severity_summary: Brief summary of discovered vulnerabilities and severity levels.

    Returns:
        Dictionary with approval status ('pending', 'approved', or 'rejected') and details.
    """
    # SCENARIO 1: First time this tool is called -> Pause and request human confirmation
    if not tool_context.tool_confirmation:
        tool_context.request_confirmation(
            hint=(
                f"Security review completed for {repo_name} @ {commit_id}.\n"
                f"Proposed Issue: {issue_title}\n"
                f"Summary: {severity_summary}\n"
                f"Do you approve creating this GitHub issue in {repo_name}?"
            ),
            payload={
                "repo_name": repo_name,
                "commit_id": commit_id,
                "issue_title": issue_title,
                "severity_summary": severity_summary,
            },
        )
        tool_context.state["approval_status"] = "pending"
        return {
            "status": "pending",
            "repo_name": repo_name,
            "commit_id": commit_id,
            "issue_title": issue_title,
            "message": (
                f"Awaiting human confirmation to create security issue '{issue_title}' "
                f"in repository '{repo_name}' for commit '{commit_id}'."
            ),
        }

    # SCENARIO 2: Resuming after human decision -> Check confirmed boolean
    if tool_context.tool_confirmation.confirmed:
        tool_context.state["approval_status"] = "approved"
        return {
            "status": "approved",
            "decision": "APPROVED",
            "repo_name": repo_name,
            "commit_id": commit_id,
            "issue_title": issue_title,
            "severity_summary": severity_summary,
            "message": (
                f"User APPROVED creating the GitHub issue in {repo_name} for commit {commit_id}."
            ),
        }
    else:
        tool_context.state["approval_status"] = "rejected"
        return {
            "status": "rejected",
            "decision": "REJECTED",
            "repo_name": repo_name,
            "commit_id": commit_id,
            "issue_title": issue_title,
            "severity_summary": severity_summary,
            "message": (
                f"User REJECTED creating a GitHub issue for {repo_name} @ {commit_id}. "
                "Provide a brief summary of the security analysis instead."
            ),
        }


approval_function_tool = FunctionTool(func=request_security_issue_approval)
