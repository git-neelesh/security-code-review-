"""Stateful Session & Human-in-the-Loop Runner for the Security Code Reviewer.

Combines:
- InMemorySessionService (Day 3a)
- App with ResumabilityConfig(is_resumable=True) + plugins + adk_request_confirmation handling (Day 2b & Day 4a)
"""

import argparse
import asyncio
import uuid
from typing import Optional

from google.genai import types
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from agent import create_security_review_app
from observability import configure_logging, get_observability_plugins

APP_NAME = "security_code_reviewer"
DEFAULT_USER_ID = "security_reviewer_user"


# ============================================================================
# Helper Functions for Human-in-the-Loop Event Processing (from Day-2b sample)
# ============================================================================
def check_for_approval(events: list) -> Optional[dict]:
    """Checks if emitted events contain the special `adk_request_confirmation` call.

    Returns:
        dict with `approval_id`, `invocation_id`, and `hint`/`payload` if paused, else None.
    """
    for event in events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if (
                    part.function_call
                    and part.function_call.name == "adk_request_confirmation"
                ):
                    args = part.function_call.args or {}
                    return {
                        "approval_id": part.function_call.id,
                        "invocation_id": event.invocation_id,
                        "hint": args.get("hint", "Do you approve creating the GitHub issue?"),
                        "payload": args.get("payload", {}),
                    }
    return None


def create_approval_response(approval_info: dict, approved: bool) -> types.Content:
    """Builds the FunctionResponse Content object to resume a paused `adk_request_confirmation`."""
    confirmation_response = types.FunctionResponse(
        id=approval_info["approval_id"],
        name="adk_request_confirmation",
        response={"confirmed": approved},
    )
    return types.Content(
        role="user",
        parts=[types.Part(function_response=confirmation_response)],
    )


def print_agent_events(events: list) -> None:
    """Prints text responses emitted by each agent in the pipeline."""
    for event in events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text and part.text.strip() and part.text.strip() != "None":
                    author = getattr(event, "author", "Agent")
                    print(f"\n[{author}] >\n{part.text}")


# ============================================================================
# Main Stateful Multi-Agent Workflow Runner
# ============================================================================
async def run_security_review_workflow(
    repo_name: str,
    commit_id: str,
    auto_approve: Optional[bool] = None,
    user_id: str = DEFAULT_USER_ID,
    session_id: Optional[str] = None,
) -> dict:
    """Executes the 4-agent Security Code Review workflow with Session & Approval support.

    Args:
        repo_name: GitHub repository in 'owner/repo' format.
        commit_id: Commit SHA to inspect.
        auto_approve:
            - True: Automatically approves issue creation (for automated tests).
            - False: Automatically rejects issue creation (returns brief summary).
            - None: Prompts the user interactively in the terminal (y/n).
        user_id: User identifier for the ADK session.
        session_id: Optional custom session ID; generated automatically if omitted.

    Returns:
        Dictionary containing final session state and observability metrics.
    """
    configure_logging()
    plugins, metrics_plugin = get_observability_plugins()

    # Attach plugins directly to the resumable App (required by ADK when passing `app` to Runner)
    app = (plugins=plugins)

    # Initialize InMemorySessionService and Runner
    session_service = InMemorySessionService()
    runner = Runner(
        app=app,
        session_service=session_service,
    )

    session_id = session_id or f"sec_review_{uuid.uuid4().hex[:8]}"
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )

    prompt = (
        f"Please perform a security code review for repository `{repo_name}` "
        f"on commit `{commit_id}`."
    )
    print(f"\n{'=' * 70}")
    print(f"🚀 Starting Security Code Review Session: {session_id}")
    print(f"📦 Repository: {repo_name} | 🔍 Commit: {commit_id}")
    print(f"{'=' * 70}")

    query_content = types.Content(role="user", parts=[types.Part(text=prompt)])
    initial_events = []

    # STEP 1: Run pipeline (repoFetchAgent -> securityReviewAgent -> SummaryDecisionAgent)
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=query_content,
    ):
        initial_events.append(event)

    print_agent_events(initial_events)

    # STEP 2: Check if SummaryDecisionAgent paused for Human-in-the-Loop confirmation
    approval_info = check_for_approval(initial_events)

    if approval_info:
        print(f"\n{'-' * 70}")
        print("⏸️  WORKFLOW PAUSED FOR HUMAN CONFIRMATION")
        print(f"📋 {approval_info['hint']}")
        print(f"{'-' * 70}")

        if auto_approve is None:
            user_input = input("\n👉 Approve creating GitHub Issue in repo? [y/N]: ").strip().lower()
            approved = user_input in ("y", "yes")
        else:
            approved = auto_approve
            print(f"🤖 Simulated Human Decision: {'APPROVE ✅' if approved else 'REJECT ❌'}")

        # STEP 3: Resume the exact invocation with the user's approval/rejection
        resumed_events = []
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=create_approval_response(approval_info, approved),
            invocation_id=approval_info["invocation_id"],
        ):
            resumed_events.append(event)

        print_agent_events(resumed_events)

    # Retrieve final session state & observability metrics
    final_session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )
    metrics = metrics_plugin.get_metrics_summary()

    print(f"\n{'=' * 70}")
    print("📊 Observability Metrics Summary:")
    print(f"   • Agent Execution Trace : {' -> '.join(metrics['agent_execution_trace'])}")
    print(f"   • Total Agent Runs      : {metrics['total_agent_invocations']}")
    print(f"   • Total LLM Requests    : {metrics['total_llm_requests']}")
    print(f"   • Total Model Errors    : {metrics['total_model_errors']}")
    print(f"   • Detailed Debug Log    : security_reviewer.log")
    print(f"{'=' * 70}\n")

    return {
        "session_id": session_id,
        "state": dict(final_session.state) if final_session and final_session.state else {},
        "metrics": metrics,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the ADK Multi-Agent Security Code Reviewer."
    )
    parser.add_argument(
        "--repo",
        required=True,
        help="GitHub repository name in 'owner/repo' format (e.g., 'octocat/Hello-World')",
    )
    parser.add_argument(
        "--commit",
        required=True,
        help="Commit SHA to analyze (e.g., '7fd1a60b01f91b314f59955a4e4d4e80d8edf11d')",
    )
    parser.add_argument(
        "--decision",
        choices=["approve", "reject", "interactive"],
        default="interactive",
        help="Human approval mode: 'interactive' (prompt in CLI), 'approve', or 'reject'.",
    )
    args = parser.parse_args()

    auto_approve: Optional[bool] = None
    if args.decision == "approve":
        auto_approve = True
    elif args.decision == "reject":
        auto_approve = False

    asyncio.run(
        run_security_review_workflow(
            repo_name=args.repo,
            commit_id=args.commit,
            auto_approve=auto_approve,
        )
    )


if __name__ == "__main__":
    main()
