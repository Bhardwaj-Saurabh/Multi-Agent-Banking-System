# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-agent banking prototype using Google's Agent Development Kit (ADK). Three independent agents communicate via the A2A (Agent-to-Agent) protocol:
- **manager**: Routes customer requests to appropriate agents, answers general banking questions
- **deposit**: Handles deposit account queries (balance, transactions), includes equity check tool
- **loan**: Handles loan queries and complex loan approval workflow with sub-agents

## Commands

### Run the Agent Server
```bash
adk web --a2a
# Default: http://localhost:8000
# Use --port 8001 to change port
```

### Run MCP Database Toolbox
```bash
cd starter/<agent>
# Export env vars first (bash example):
export $(grep -v '^#' ../.env | xargs)
/path/to/toolbox --tools-files "tools.yaml"
# Default: http://127.0.0.1:5001
```

### Test Agents via A2A Protocol
```bash
# Get agent card
python testing/bin/a2a.py --url http://localhost:8000/a2a/manager --card

# Send single prompt
python testing/bin/a2a.py --url http://localhost:8000/a2a/deposit --prompt "How much is in my vacation account?"

# Run test scenarios (produces .txt, .json, .csv output files)
python testing/bin/a2a.py --in testing/test_scenarios.csv --out test_results
```

## Architecture

### Agent Structure
Each agent follows this pattern:
- `agent.py`: Defines `root_agent` using `Agent` class from `google.adk.agents`
- `agent.json`: A2A Agent Card (name, url, description, skills)
- `agent-prompt.txt`: System instructions loaded at runtime
- `tools.yaml`: MCP Toolbox config for database tools (MySQL)

### Inter-Agent Communication
- Manager uses `RemoteA2aAgent` to connect to deposit/loan agents by their agent card URLs
- Agents do NOT import each other's code - all cross-agent calls go through A2A
- Agent cards accessible at: `http://localhost:8000/a2a/<agent>/.well-known/agent-card.json`

### Loan Approval Workflow (loan/loan.py)
Complex orchestration using multiple sub-agents:
1. `get_requested_value_agent` - Extract loan type and amount from request
2. `outstanding_balance_agent` - Get total outstanding loan balance
3. `policy_agent` - Load policy PDF from GCS, extract criteria
4. `total_value_agent` - Custom agent (not LLM) to compute minimum required equity
5. `check_equity_agent` - A2A call to deposit agent's check-minimum-balance tool
6. `user_profile_agent` - Load customer profile PDF from GCS

Sub-agents use `output_schema` and `output_key` for state management. Orchestration uses `SequentialAgent` and `ParallelAgent`.

### Database Schema
- **accounts**: id, customer_id, account_type, balance
- **transactions**: id, account_id, transaction_date, amount, description
- **loans**: id, customer_id, loan_type, origination_date, amount, outstanding_balance, terms, monthly_payment, next_payment_date

## Environment Setup

Copy `starter/.env-sample` to `.env` and configure:
- `GOOGLE_GENAI_USE_VERTEXAI=TRUE`
- `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`
- `TOOLBOX_URL` (MCP Toolbox endpoint)
- `MYSQL_HOST`, `MYSQL_USER`, `MYSQL_PASSWORD`

## Key Constraints

- Deposit agent must NOT reveal total balance of all accounts (security guardrail)
- Deposit agent CAN report if total balance exceeds a target value (for loan equity checks)
- Loan rejection responses must NOT reveal policy details, thresholds, or customer ratings
- Model: `gemini-2.5-flash`
