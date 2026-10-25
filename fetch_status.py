"""Callbacks for stopping the review when GitHub commit retrieval fails."""

from google.adk.agents.context import Context
from google.genai import types

FETCH_FAILURE_STATE_KEY = "commit_fetch_failure"

_FETCH_FAILURE_MESSAGES = {
    "REPOSITORY_NOT_FOUND": (
        "Repository could not be found, or your GitHub token does not have access "
        "to it. Verify the owner/repository name and token permissions."
    ),
    "COMMIT_NOT_FOUND": (
        "Commit could not be found in the specified repository. Verify the commit ID."
    ),
    "ACCESS_DENIED": (
        "GitHub denied access to the repository or commit. Check your token permissions."
    ),
    "OTHER": "GitHub could not retrieve the requested commit.",
}


def record_commit_fetch_status(callback_context: Context) -> None:
    """Record fetch failure from the explicit status emitted by repoFetchAgent."""
    fetch_result = callback_context.state.get("commit_code_details", "")
    print(f"[record_commit_fetch_status] fetch_result123:\n{fetch_result}11111")
    first_line = str(fetch_result).splitlines()[0].strip() if fetch_result else ""

    if first_line == "FETCH_STATUS: SUCCESS":
        if FETCH_FAILURE_STATE_KEY in callback_context.state:
            callback_context.state[FETCH_FAILURE_STATE_KEY] = ""
        return

    failure_type = "OTHER"
    for line in str(fetch_result).splitlines()[1:]:
        if line.startswith("FETCH_FAILURE:"):
            candidate = line.partition(":")[2].strip()
            if candidate in _FETCH_FAILURE_MESSAGES:
                failure_type = candidate
            break

    callback_context.state[FETCH_FAILURE_STATE_KEY] = _FETCH_FAILURE_MESSAGES[
        failure_type
    ]


def stop_after_failed_commit_fetch(
    callback_context: Context,
) -> types.Content | None:
    """Return a user-facing error and end the workflow before security analysis."""
    failure_message = callback_context.state.get(FETCH_FAILURE_STATE_KEY)
    if not failure_message:
        return None

    response = (
        f"{failure_message} No security review was performed and no GitHub issue "
        "was created."
    )
    callback_context.state["final_issue_or_summary"] = response
    return types.Content(
        role="model",
        parts=[types.Part(text=response)],
    )


def skip_agent_after_failed_commit_fetch(
    callback_context: Context,
) -> types.Content | None:
    """Skip a downstream agent when commit retrieval has already failed."""
    if not callback_context.state.get(FETCH_FAILURE_STATE_KEY):
        return None

    return types.Content(role="model", parts=[])
