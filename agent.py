"""Root SequentialAgent & Resumable App assembling the 4 Security Code Reviewer agents."""

import os
from typing import Optional

from google.adk.agents import SequentialAgent
from google.adk.apps.app import App, ResumabilityConfig
from google.adk.plugins.base_plugin import BasePlugin

from issue_report_agent import IssueReportAgent
from observability import get_observability_plugins
from repo_fetch_agent import repoFetchAgent
from security_review_agent import securityReviewAgent
from summary_decision_agent
import SummaryDecisionAgent


def _ensure_google_api_key() -> None:
    """Loads environment variables from .env (if present) or Kaggle secrets fallback."""
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    if not os.environ.get("GOOGLE_API_KEY"):
        try:
            from kaggle_secrets import UserSecretsClient

            os.environ["GOOGLE_API_KEY"] = UserSecretsClient().get_secret("GOOGLE_API_KEY")
        except Exception:
            pass


_ensure_google_api_key()


def build_root_agent() -> SequentialAgent:
    """Builds a fresh SequentialAgent pipeline with all 4 specialist sub-agents."""
    return SequentialAgent(
        name="SecurityCodeReviewPipeline",
        description=(
            "Sequential multi-agent pipeline that fetches commit details from GitHub MCP, "
            "performs a security code review, pauses for human approval, and either creates "
            "a GitHub issue or outputs a brief summary."
        ),
        sub_agents=[
            repoFetchAgent(),
            securityReviewAgent(),
            SummaryDecisionAgent(),
            IssueReportAgent(),
        ],
    )


def create_security_review_app(
        plugins: Optional[list[BasePlugin]] = None,
) -> App:
    """Creates the resumable ADK App with plugins attached directly to the App."""
    if plugins is None:
        plugins, _ = get_observability_plugins()

    return App(
        name="security_code_reviewer",
        root_agent=build_root_agent(),
        resumability_config=ResumabilityConfig(is_resumable=True),
        plugins=plugins,
    )


# Default root_agent and app exports for `adk web` and `adk eval`
default_plugins, default_metrics_plugin = get_observability_plugins()
root_agent = build_root_agent()
security_review_app = App(
    name="security_code_reviewer",
    root_agent=root_agent,
    resumability_config=ResumabilityConfig(is_resumable=True),
    plugins=default_plugins,
)
