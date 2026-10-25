"""Root SequentialAgent & Resumable App assembling the 4 Security Code Reviewer agents."""

import os
from typing import Optional

from google.adk.agents import SequentialAgent
from google.adk.apps.app import App, ResumabilityConfig
from google.adk.plugins.base_plugin import BasePlugin

from issue_report_agent import issue_report_agent
from observability import get_observability_plugins
from repo_fetch_agent import repo_fetch_agent
from security_review_agent import security_review_agent
from summary_decision_agent import summary_decision_agent

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
            repo_fetch_agent(),
            security_review_agent(),
            summary_decision_agent(),
            issue_report_agent(),
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

# ADK Web looks for an `app` export before falling back to `root_agent`.
app = security_review_app
