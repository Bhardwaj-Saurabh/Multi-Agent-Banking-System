# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-agent banking prototype using Google's Agent Development Kit (ADK). Three independent agents communicate via the A2A (Agent-to-Agent) protocol:
- **manager**: Routes customer requests to appropriate agents, answers general banking questions
- **deposit**: Handles deposit account queries (balance, transactions), includes equity check tool
- **loan**: Handles loan queries and complex loan approval workflow with sub-agents

## Commands

### Install Dependencies
```bash
pip install -r starter/requirements.txt
```

### Run the Agent Server
```bash
cd starter
adk web --a2a
# Default: http://localhost:8000
# Use --port 8001 to change port
```

### Run MCP Database Toolbox
Requires the `toolbox` binary (Google MCP Toolbox for Databases). The combined `starter/tools.yaml` holds ALL deposit + loan tools, so one instance serves every agent (per-agent `deposit/tools.yaml` and `loan/tools.yaml` also exist for running them in isolation).
```bash
cd starter
export $(grep -v '^#' .env | xargs)   # export env vars (bash)
./toolbox --tools-file tools.yaml --port 5001
```
Note: `toolbox` defaults to port **5000** and the code's `TOOLBOX_URL` default is `http://127.0.0.1:5000`, but `.env-sample` sets `:5001`. Keep the `--port` flag and `TOOLBOX_URL` in sync.

### Test Agents via A2A Protocol
```bash
# Get agent card
python testing/bin/a2a.py --url http://localhost:8000/a2a/manager --card

# Send single prompt
python testing/bin/a2a.py --url http://localhost:8000/a2a/deposit --prompt "How much is in my vacation account?"

# Run test scenarios (produces .txt, .json, .csv output files)
python testing/bin/a2a.py --in testing/test_scenarios.csv --out test_results
```

Test scenarios CSV format: `url,prompt,message_id,task_id,context_id` (message_id groups multi-turn conversations)

## Architecture

### Agent Structure
Each agent follows this pattern:
- `agent.py`: Defines `root_agent` using `Agent` class from `google.adk.agents`
- `agent.json`: A2A Agent Card (name, url, description, skills)
- `agent-prompt.txt`: System instructions loaded at runtime
- `tools.yaml`: MCP Toolbox config for database tools (MySQL)

### Inter-Agent Communication
- Manager connects to deposit/loan agents as `RemoteA2aAgent` **sub-agents** (ADK delegation/transfer), not tools — it has no DB tools of its own
- Agents do NOT import each other's code - all cross-agent calls go through A2A over the agent card URLs
- Agent cards accessible at: `http://localhost:8000/a2a/<agent>/.well-known/agent-card.json`
- Cross-agent equity check: the loan agent's `check_equity_agent` reaches the deposit agent the same way — via `sub_agents=[deposit_a2a_agent]`, which calls deposit's `check-minimum-balance` tool (returns only a boolean, never the actual balance)

### Loan Approval Workflow (loan/loan.py)
A single `SequentialAgent` (`loan_approval_agent`) runs 5 phases; state flows between them via each sub-agent's `output_key` (Pydantic `output_schema` validates the shape). Actual execution order:
1. **Phase 1** — `get_requested_value_agent` → `loan_request` {loan_type, amount}
2. **Phase 2** (`ParallelAgent`, run concurrently):
   - `outstanding_balance_agent` → `outstanding_balance` (DB tool `get-total-outstanding-balance`)
   - `policy_agent` → `policy_criteria` {debt_to_equity_ratio, required_rating} (reads policy PDF via `load_artifacts`)
   - `user_profile_agent` → `user_profile` {customer_rating} (reads customer PDF via `load_artifacts`)
3. **Phase 3** — `total_value_agent`, a custom non-LLM `BaseAgent` computing `minimum_equity = (outstanding_balance + amount) / debt_to_equity_ratio` → `minimum_equity`
4. **Phase 4** — `check_equity_agent` → `equity_check` {meets_equity_requirement} (A2A to deposit, see above)
5. **Phase 5** — `approval_decision_agent` → `approval_decision` (final approve/reject message)

Note: the GCS PDFs (loan policy, customer profile) are surfaced to the `load_artifacts` tool; `GCS_BUCKET` must be configured.

### Database Schema
- **accounts**: id, customer_id, account_type, balance
- **transactions**: id, account_id, transaction_date, amount, description
- **loans**: id, customer_id, loan_type, origination_date, amount, outstanding_balance, terms, monthly_payment, next_payment_date

## Environment Setup

Copy `starter/.env-sample` to `starter/.env` and configure:
- `GOOGLE_GENAI_USE_VERTEXAI=TRUE`
- `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`
- `TOOLBOX_URL` (MCP Toolbox endpoint; code default `http://127.0.0.1:5000`, `.env-sample` uses `:5001`)
- `MYSQL_HOST`, `MYSQL_USER`, `MYSQL_PASSWORD`
- `GCS_BUCKET` (for loan policy and customer profile PDFs)
- `A2A_BASE_URL` (optional, defaults to `http://localhost:8000`)

## Key Constraints

- Deposit agent must NOT reveal total balance of all accounts (security guardrail)
- Deposit agent CAN report if total balance exceeds a target value (for loan equity checks)
- Loan rejection responses must NOT reveal policy details, thresholds, or customer ratings
- Model: `gemini-2.5-flash`
