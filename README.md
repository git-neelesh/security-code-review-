# Multi-Agent Security Code Reviewer (`google-adk`)

A 4-stage multi-agent security code review pipeline built with the [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/), modeled directly after your Day 1–4 Kaggle course notebooks.

## Architecture Overview

```text
User Input (repo_name, commit_id)
       │
       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ SequentialAgent: SecurityCodeReviewPipeline                                │
│ (Wrapped in App with ResumabilityConfig(is_resumable=True))                │
├────────────────────────────────────────────────────────────────────────────┤
│ 1. repoFetchAgent()  (repo_fetch_agent.py)                                 │
│    • Connects to https://api.githubcopilot.com/mcp/ (Read-Only)            │
│    • Fetches commit metadata, diffs, and modified files                    │
│    • Writes -> session.state["commit_code_details"]                        │
│    • Stops with a clear error if the repository/commit cannot be fetched   │
│                                                                            │
│ 2. securityReviewAgent()  (security_review_agent.py)                       │
│    • Reads {commit_code_details}                                           │
│    • Analyzes diff for OWASP Top 10, secrets, auth, and injection flaws    │
│    • Writes -> session.state["security_analysis_report"]                   │
│                                                                            │
│ 3. SummaryDecisionAgent()  (summary_decision_agent.py)                     │
│    • Reads {security_analysis_report}                                      │ 
│    • Calls `request_security_issue_approval` (ToolContext LRO)             │
│    • PAUSES execution (`adk_request_confirmation`) for Human Approval      │
│    • Writes -> session.state["summary_decision_output"]                    │
│                                                                            │
│ 4. IssueReportAgent()  (issue_report_agent.py)                             │
│    • Reads {security_analysis_report} & {summary_decision_output}          │
│    • IF APPROVED -> Calls GitHub MCP (`create_issue`) in same repo         │
│    • IF REJECTED -> Skips issue creation & outputs brief summary           │
│    • Writes -> session.state["final_issue_or_summary"]                     │
└────────────────────────────────────────────────────────────────────────────┘
```

## Project Structure

- `repo_fetch_agent.py`: Defines `repo_fetch_agent()` with read-only GitHub MCP (`output_key="commit_code_details"`).
- `security_review_agent.py`: Defines `security_review_agent()` reading `{commit_code_details}` (`output_key="security_analysis_report"`).
- `summary_decision_agent.py`: Defines `summary_decision_agent()` reading `{security_analysis_report}` and calling `request_security_issue_approval` (`output_key="summary_decision_output"`).
- `issue_report_agent.py`: Defines `issue_report_agent()` reading `{security_analysis_report}` and `{summary_decision_output}` to create a GitHub issue via MCP if approved or summarize if rejected (`output_key="final_issue_or_summary"`).
- `agent.py`: Composes the 4 agents into `root_agent` (`SequentialAgent`) and wraps them in `security_review_app` (`App` with `ResumabilityConfig(is_resumable=True)`).
- `tools.py`: Configures `McpToolset` with `StreamableHTTPServerParams` for `https://api.githubcopilot.com/mcp/` and implements the `request_security_issue_approval` Human-in-the-Loop tool using `ToolContext.request_confirmation()`.
- `workflow.py`: Stateful session and LRO execution loop using `InMemorySessionService`, `Runner`, `check_for_approval()`, and `create_approval_response()`.
- `observability.py`: Configures `security_reviewer.log` (`DEBUG` level) and combines ADK's `LoggingPlugin()` with a custom `SecurityReviewObservabilityPlugin(BasePlugin)`.
- `test_config.json`, `security_reviewer.evalset.json`, `security_reviewer.test.json`: Agent evaluation test suites and thresholds (`tool_trajectory_avg_score` & `response_match_score`).

## Setup & Usage

### 1. Environment Variables

Export your `GOOGLE_API_KEY` and `GITHUB_TOKEN` (or copy `.env.example` to `.env`):

```bash
source .venv/bin/activate # select python source venv
export GOOGLE_API_KEY="your-gemini-api-key"
export GITHUB_TOKEN="your-github-personal-access-token"
```

### 2. Run the Workflow from CLI (Interactive Approval or Automated)

From `/Users/neelesh/ai-projects/kaggle-ai-classes`:

```bash
# Interactive terminal prompt (asks y/N when SummaryDecisionAgent pauses):
python -m workflow --repo owner/repo --commit <commit_sha>

# Simulate Human Approval (creates GitHub issue via MCP):
python -m workflow --repo owner/repo --commit <commit_sha> --decision approve

# Simulate Human Rejection (skips issue creation and outputs brief summary):
python -m workflow --repo owner/repo --commit <commit_sha> --decision reject
```

### 3. Run in ADK Web UI (with Debug Logs & Traces)

```bash
adk web --log_level DEBUG
```

### 4. Run Agent Evaluation

```bash
adk eval security_code_reviewer security_code_reviewer/security_reviewer.evalset.json \
  --config_file_path=security_code_reviewer/test_config.json \
  --print_detailed_results
```
