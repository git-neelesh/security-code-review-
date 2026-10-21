"""Observability setup: Logging configuration and custom ADK Plugin for Security Code Reviewer."""

import logging
from typing import Optional

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.plugins.logging_plugin import LoggingPlugin


def configure_logging(log_file: str = "security_reviewer.log", level: int = logging.DEBUG) -> None:
    """Configures file and console logging as demonstrated in day-4a-agent-observability."""
    logging.basicConfig(
        filename=log_file,
        level=level,
        format="%(asctime)s %(filename)s:%(lineno)s %(levelname)s: %(message)s",
        force=True,
    )


class SecurityReviewObservabilityPlugin(BasePlugin):
    """Custom observability plugin tracking agent runs, LLM requests, and errors.

    Follows the CountInvocationPlugin pattern from day-4a-agent-observability.ipynb.
    """

    def __init__(self) -> None:
        super().__init__(name="security_review_observability")
        self.agent_count: int = 0
        self.llm_request_count: int = 0
        self.error_count: int = 0
        self.agent_execution_order: list[str] = []

    async def before_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> None:
        """Records when each specialist agent in the SequentialAgent pipeline starts."""
        self.agent_count += 1
        self.agent_execution_order.append(agent.name)
        msg = f"[ObservabilityPlugin] Starting agent #{self.agent_count}: {agent.name}"
        logging.info(msg)
        print(f"🔎 {msg}")

    async def after_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> None:
        """Logs completion of each agent stage."""
        msg = f"[ObservabilityPlugin] Completed agent: {agent.name}"
        logging.info(msg)

    async def before_model_callback(
        self, *, callback_context: CallbackContext, llm_request: LlmRequest
    ) -> Optional[LlmResponse]:
        """Counts LLM requests across all agents in the pipeline."""
        self.llm_request_count += 1
        msg = (
            f"[ObservabilityPlugin] LLM request #{self.llm_request_count} "
            f"(agent: {callback_context.agent_name})"
        )
        logging.info(msg)
        return None

    async def on_model_error_callback(
        self,
        *,
        callback_context: CallbackContext,
        llm_request: LlmRequest,
        error: Exception,
    ) -> Optional[LlmResponse]:
        """Captures and logs any model errors during pipeline execution."""
        self.error_count += 1
        logging.error(
            f"[ObservabilityPlugin] Model error #{self.error_count} in "
            f"{callback_context.agent_name}: {error}"
        )
        return None

    def get_metrics_summary(self) -> dict:
        """Returns collected metrics for inspection at the end of a session."""
        return {
            "total_agent_invocations": self.agent_count,
            "total_llm_requests": self.llm_request_count,
            "total_model_errors": self.error_count,
            "agent_execution_trace": self.agent_execution_order,
        }


def get_observability_plugins() -> tuple[list[BasePlugin], SecurityReviewObservabilityPlugin]:
    """Returns both ADK's built-in LoggingPlugin and our custom metrics plugin."""
    metrics_plugin = SecurityReviewObservabilityPlugin()
    plugins: list[BasePlugin] = [
        LoggingPlugin(),
        metrics_plugin,
    ]
    return plugins, metrics_plugin
